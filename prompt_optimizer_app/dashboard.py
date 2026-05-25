import logging
import threading
import webbrowser

from flask import Flask, redirect, render_template_string, request, url_for

from prompt_optimizer_app.config import AppConfig, DATABASE_FILE, LOG_FILE, SYSTEM_PROMPT_FILE
from prompt_optimizer_app.deepseek import (
    DeepSeekClient,
    get_system_prompt,
    reset_system_prompt,
    save_system_prompt,
)
from prompt_optimizer_app.hotkeys import HotkeyController
from prompt_optimizer_app.optimization_router import OptimizationRouter
from prompt_optimizer_app.runtime_settings import RuntimeSettingsStore
from prompt_optimizer_app.storage import PromptHistoryStore


logger = logging.getLogger(__name__)


class DashboardServer:
    def __init__(
        self,
        config: AppConfig,
        history_store: PromptHistoryStore,
        hotkeys: HotkeyController,
        optimization_router: OptimizationRouter,
        runtime_settings_store: RuntimeSettingsStore,
        on_status,
    ):
        self.config = config
        self.history_store = history_store
        self.hotkeys = hotkeys
        self.optimization_router = optimization_router
        self.runtime_settings_store = runtime_settings_store
        self.on_status = on_status
        self._app = self._create_app()
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://{self.config.dashboard_host}:{self.config.dashboard_port}"

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if not self.is_running:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            logger.info("Dashboard started at %s", self.url)

    def open(self) -> None:
        self.start()
        webbrowser.open(self.url)

    def update_config(self, config: AppConfig) -> None:
        self.config = config

    def _run(self) -> None:
        self._app.run(
            host=self.config.dashboard_host,
            port=self.config.dashboard_port,
            debug=False,
            use_reloader=False,
        )

    def _create_app(self) -> Flask:
        app = Flask(__name__)

        @app.get("/")
        def index():
            query = request.args.get("q", "").strip()
            status = request.args.get("status", "all").strip()
            provider = request.args.get("provider", "all").strip()
            records = self.history_store.list_records(query=query, status=status, provider=provider)
            recent_errors = self.history_store.list_recent_errors()
            runtime_settings = self.runtime_settings_store.load()
            pipeline_status = self.optimization_router.status
            return render_template_string(
                DASHBOARD_TEMPLATE,
                records=records,
                recent_errors=recent_errors,
                query=query,
                status=status,
                provider=provider,
                database_file=DATABASE_FILE,
                log_file=LOG_FILE,
                hotkey=self.config.hotkey,
                hotkey_running=self.hotkeys.is_running,
                web_helpers_enabled=self.config.web_helpers_enabled,
                web_helper_timeout_seconds=self.config.web_helper_timeout_seconds,
                web_helper_retry_count=self.config.web_helper_retry_count,
                web_helper_fallback_local=self.config.web_helper_fallback_local,
                openai_helper_url=self.config.openai_helper_url,
                claude_helper_url=self.config.claude_helper_url,
                gemini_helper_url=self.config.gemini_helper_url,
                auto_provider_detection=runtime_settings.auto_provider_detection,
                web_access_armed=runtime_settings.web_access_armed,
                pipeline_status=pipeline_status,
            )

        @app.post("/toggle-power")
        def toggle_power():
            try:
                if self.hotkeys.is_running:
                    self.hotkeys.stop()
                    self.on_status("Hotkey stopped from dashboard.")
                else:
                    self.hotkeys.start()
                    self.on_status(f"Hotkey running from dashboard: {self.config.hotkey}")
            except Exception as exc:
                logger.exception("Failed to toggle dashboard power.")
                self.on_status(f"Dashboard power toggle failed: {exc}")

            return redirect(url_for("index"))

        @app.post("/test-api")
        def test_api():
            original_text = "Create a short test prompt for a todo app."
            try:
                optimized_text = DeepSeekClient(self.config).optimize_prompt(original_text)
                self.history_store.add_success(
                    source="api_test",
                    original_text=original_text,
                    optimized_text=optimized_text,
                )
                self.on_status("DeepSeek API test succeeded.")
            except Exception as exc:
                self.history_store.add_error(
                    source="api_test",
                    original_text=original_text,
                    error_message=str(exc),
                )
                logger.exception("DeepSeek API test failed.")
                self.on_status(f"DeepSeek API test failed: {exc}")

            return redirect(url_for("index"))

        @app.post("/toggle-auto-provider-detection")
        def toggle_auto_provider_detection():
            try:
                updated = self.runtime_settings_store.toggle_auto_provider_detection()
                state = "ON" if updated.auto_provider_detection else "OFF"
                self.on_status(f"Auto provider detection: {state}")
            except Exception as exc:
                logger.exception("Failed to toggle auto provider detection.")
                self.on_status(f"Failed to toggle auto provider detection: {exc}")
            return redirect(url_for("index"))

        @app.post("/set-web-access")
        def set_web_access():
            mode = request.form.get("mode", "").strip().lower()
            arm = mode == "arm"
            try:
                updated = self.runtime_settings_store.set_web_access_armed(arm)
                state = "ARMED" if updated.web_access_armed else "DISARMED"
                self.on_status(f"Web access: {state}")
            except Exception as exc:
                logger.exception("Failed to set web access state.")
                self.on_status(f"Failed to set web access: {exc}")
            return redirect(url_for("index"))

        @app.get("/system-prompt")
        def system_prompt_page():
            return render_template_string(
                SYSTEM_PROMPT_TEMPLATE,
                system_prompt=get_system_prompt(),
                system_prompt_file=SYSTEM_PROMPT_FILE,
            )

        @app.post("/system-prompt")
        def save_system_prompt_page():
            try:
                save_system_prompt(request.form.get("system_prompt", ""))
                self.on_status("System prompt saved from dashboard.")
            except Exception as exc:
                logger.exception("Failed to save system prompt.")
                self.on_status(f"Failed to save system prompt: {exc}")

            return redirect(url_for("system_prompt_page"))

        @app.post("/system-prompt/reset")
        def reset_system_prompt_page():
            try:
                reset_system_prompt()
                self.on_status("System prompt reset to default.")
            except Exception as exc:
                logger.exception("Failed to reset system prompt.")
                self.on_status(f"Failed to reset system prompt: {exc}")

            return redirect(url_for("system_prompt_page"))

        return app


DASHBOARD_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Prompt Optimizer Dashboard</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f7f3;
      --panel: #ffffff;
      --text: #1f2937;
      --muted: #667085;
      --border: #d9ddd5;
      --accent: #2563eb;
      --ok: #13795b;
      --error: #b42318;
      --code: #f1f5f9;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
      font-size: 14px;
      line-height: 1.45;
    }

    header {
      border-bottom: 1px solid var(--border);
      background: var(--panel);
    }

    .wrap {
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-height: 72px;
    }

    h1 {
      margin: 0;
      font-size: 22px;
      letter-spacing: 0;
    }

    .paths {
      color: var(--muted);
      font-size: 12px;
      text-align: right;
    }

    .controls {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 8px;
    }

    .header-actions {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 10px;
    }

    main {
      padding: 24px 0 48px;
    }

    form.filters {
      display: grid;
      grid-template-columns: minmax(220px, 1fr) 180px 180px auto;
      gap: 10px;
      margin-bottom: 18px;
    }

    input,
    select,
    button,
    .button-link {
      height: 38px;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: white;
      color: var(--text);
      font: inherit;
      padding: 0 12px;
    }

    button {
      cursor: pointer;
      background: var(--accent);
      border-color: var(--accent);
      color: white;
      font-weight: 700;
    }

    .button-link {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      text-decoration: none;
      font-weight: 700;
      background: white;
      color: var(--text);
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 320px;
      gap: 18px;
      align-items: start;
    }

    .section-title {
      margin: 0 0 10px;
      font-size: 15px;
    }

    .record,
    .error-item {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      margin-bottom: 12px;
      overflow: hidden;
    }

    .record-head,
    .error-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--border);
    }

    .meta {
      color: var(--muted);
      font-size: 12px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      height: 24px;
      border-radius: 999px;
      padding: 0 9px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }

    .success {
      background: #e7f6ef;
      color: var(--ok);
    }

    .error {
      background: #fef3f2;
      color: var(--error);
    }

    .record-body {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0;
    }

    .text-block {
      padding: 14px;
      min-width: 0;
    }

    .text-block + .text-block {
      border-left: 1px solid var(--border);
    }

    .label {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 8px;
      text-transform: uppercase;
    }

    pre {
      margin: 0;
      min-height: 84px;
      max-height: 320px;
      overflow: auto;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: var(--code);
      border-radius: 6px;
      padding: 10px;
      font-family: Consolas, "Courier New", monospace;
      font-size: 13px;
    }

    .actions {
      display: flex;
      justify-content: flex-end;
      padding: 0 14px 14px;
    }

    .copy {
      height: 32px;
      background: #374151;
      border-color: #374151;
      font-size: 12px;
    }

    .power {
      min-width: 112px;
      height: 38px;
      border-radius: 999px;
      border: 0;
    }

    .power-on {
      background: var(--ok);
    }

    .power-off {
      background: var(--error);
    }

    .test-api {
      background: #374151;
      border-color: #374151;
    }

    aside {
      position: sticky;
      top: 16px;
    }

    .empty {
      color: var(--muted);
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }

    .error-message {
      padding: 12px 14px;
      color: var(--error);
      overflow-wrap: anywhere;
    }

    .helper-links {
      display: grid;
      gap: 8px;
      margin-top: 8px;
    }

    .helper-links a {
      color: var(--accent);
      text-decoration: none;
      overflow-wrap: anywhere;
    }

    .helper-links a:hover {
      text-decoration: underline;
    }

    .pipeline {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 12px;
    }

    .pipeline p {
      margin: 6px 0;
    }

    .auto-detect-form {
      margin-top: 8px;
      display: flex;
      gap: 8px;
      align-items: center;
    }

    @media (max-width: 860px) {
      .topbar,
      .layout,
      .record-body,
      form.filters {
        grid-template-columns: 1fr;
      }

      .topbar {
        display: grid;
      }

      .paths {
        text-align: left;
      }

      .controls {
        justify-content: flex-start;
      }

      .header-actions {
        justify-content: flex-start;
      }

      .text-block + .text-block {
        border-left: 0;
        border-top: 1px solid var(--border);
      }

      aside {
        position: static;
      }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <div>
        <h1>Prompt Optimizer</h1>
        <div class="meta">Local dashboard for prompt history and errors</div>
      </div>
      <div class="paths">
        <div>DB: {{ database_file }}</div>
        <div>Logs: {{ log_file }}</div>
        <div>Hotkey: {{ hotkey }}</div>
        <div>Web helpers: {{ 'ON' if web_helpers_enabled else 'OFF' }}</div>
        <form class="controls" method="post" action="{{ url_for('toggle_power') }}">
          <span class="badge {{ 'success' if hotkey_running else 'error' }}">
            {{ 'ON' if hotkey_running else 'OFF' }}
          </span>
          <button
            class="power {{ 'power-on' if hotkey_running else 'power-off' }}"
            type="submit"
          >
            {{ 'Turn off' if hotkey_running else 'Turn on' }}
          </button>
        </form>
        <div class="header-actions">
          <a class="button-link" href="{{ url_for('system_prompt_page') }}">Edit system prompt</a>
          <form method="post" action="{{ url_for('test_api') }}">
            <button class="test-api" type="submit">Test DeepSeek API</button>
          </form>
        </div>
        <div class="helper-links">
          <a href="{{ openai_helper_url }}" target="_blank" rel="noopener noreferrer">OpenAI helper</a>
          <a href="{{ claude_helper_url }}" target="_blank" rel="noopener noreferrer">Claude helper</a>
          <a href="{{ gemini_helper_url }}" target="_blank" rel="noopener noreferrer">Gemini AI Studio</a>
        </div>
      </div>
    </div>
  </header>

  <main class="wrap">
    <section class="pipeline">
      <h2 class="section-title">Web Helper Pipeline</h2>
      <p><strong>Web access:</strong> {{ 'ARMED' if web_access_armed else 'DISARMED' }}</p>
      <p><strong>Per-run consent:</strong> REQUIRED</p>
      <p><strong>Last provider:</strong> {{ pipeline_status.last_provider }}</p>
      <p><strong>Last execution path:</strong> {{ pipeline_status.last_execution_path }}</p>
      <p><strong>Last helper:</strong> {{ pipeline_status.last_helper_name }}</p>
      <p><strong>Last helper latency:</strong> {{ pipeline_status.last_helper_latency_ms }} ms</p>
      <p><strong>Last helper error:</strong> {{ pipeline_status.last_helper_error or "None" }}</p>
      <p><strong>Last consent:</strong>
        {% if pipeline_status.consent_denied %}
          DENIED
        {% elif pipeline_status.consent_granted %}
          GRANTED
        {% elif pipeline_status.consent_required %}
          REQUIRED
        {% else %}
          N/A
        {% endif %}
      </p>
      <p><strong>Timeout:</strong> {{ web_helper_timeout_seconds }}s | <strong>Retry:</strong> {{ web_helper_retry_count }} | <strong>Fallback local:</strong> {{ 'ON' if web_helper_fallback_local else 'OFF' }}</p>
      <form class="auto-detect-form" method="post" action="{{ url_for('set_web_access') }}">
        <input type="hidden" name="mode" value="{{ 'disarm' if web_access_armed else 'arm' }}">
        <span class="badge {{ 'success' if web_access_armed else 'error' }}">
          {{ 'ARMED' if web_access_armed else 'DISARMED' }}
        </span>
        <button type="submit">{{ 'Disable web access' if web_access_armed else 'Enable web access' }}</button>
      </form>
      <form class="auto-detect-form" method="post" action="{{ url_for('toggle_auto_provider_detection') }}">
        <span class="badge {{ 'success' if auto_provider_detection else 'error' }}">
          {{ 'AUTO DETECT ON' if auto_provider_detection else 'AUTO DETECT OFF' }}
        </span>
        <button type="submit">{{ 'Disable auto detection' if auto_provider_detection else 'Enable auto detection' }}</button>
      </form>
    </section>

    <form class="filters" method="get">
      <input name="q" value="{{ query }}" placeholder="Search original, optimized, or error text">
      <select name="status">
        <option value="all" {% if status == "all" %}selected{% endif %}>All statuses</option>
        <option value="success" {% if status == "success" %}selected{% endif %}>Success only</option>
        <option value="error" {% if status == "error" %}selected{% endif %}>Errors only</option>
      </select>
      <select name="provider">
        <option value="all" {% if provider == "all" %}selected{% endif %}>All providers</option>
        <option value="chatgpt" {% if provider == "chatgpt" %}selected{% endif %}>ChatGPT</option>
        <option value="claude" {% if provider == "claude" %}selected{% endif %}>Claude</option>
        <option value="gemini" {% if provider == "gemini" %}selected{% endif %}>Gemini</option>
        <option value="generic" {% if provider == "generic" %}selected{% endif %}>Generic</option>
      </select>
      <button type="submit">Filter</button>
    </form>

    <div class="layout">
      <section>
        <h2 class="section-title">History</h2>
        {% if records %}
          {% for record in records %}
            <article class="record">
              <div class="record-head">
                <div>
                  <strong>#{{ record.id }}</strong>
                  <span class="meta">{{ record.created_at }} - {{ record.source }} - {{ record.detected_provider }} - {{ record.execution_path or "-" }}</span>
                  <span class="meta">consent_required={{ record.consent_required }} | consent_granted={{ record.consent_granted }} | consent_denied={{ record.consent_denied }}</span>
                </div>
                <span class="badge {{ record.status }}">{{ record.status }}</span>
              </div>
              <div class="record-body">
                <div class="text-block">
                  <div class="label">Original</div>
                  <pre>{{ record.original_text or "No original text captured." }}</pre>
                </div>
                <div class="text-block">
                  <div class="label">Optimized</div>
                  <pre id="optimized-{{ record.id }}">{{ record.optimized_text or record.error_message or "No optimized prompt." }}</pre>
                </div>
              </div>
              {% if record.optimized_text %}
                <div class="actions">
                  <button class="copy" type="button" data-target="optimized-{{ record.id }}">Copy optimized</button>
                </div>
              {% endif %}
            </article>
          {% endfor %}
        {% else %}
          <div class="empty">No history yet. Use the hotkey or clipboard test, then refresh this page.</div>
        {% endif %}
      </section>

      <aside>
        <h2 class="section-title">Latest Errors</h2>
        {% if recent_errors %}
          {% for error in recent_errors %}
            <div class="error-item">
              <div class="error-head">
                <strong>#{{ error.id }}</strong>
                <span class="meta">{{ error.created_at }}</span>
              </div>
              <div class="error-message">{{ error.error_message or "Unknown error" }}</div>
            </div>
          {% endfor %}
        {% else %}
          <div class="empty">No errors recorded.</div>
        {% endif %}
      </aside>
    </div>
  </main>

  <script>
    document.querySelectorAll("[data-target]").forEach((button) => {
      button.addEventListener("click", async () => {
        const target = document.getElementById(button.dataset.target);
        if (!target) return;
        await navigator.clipboard.writeText(target.innerText);
        const original = button.innerText;
        button.innerText = "Copied";
        window.setTimeout(() => {
          button.innerText = original;
        }, 1200);
      });
    });
  </script>
</body>
</html>
"""


SYSTEM_PROMPT_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Edit System Prompt</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f7f3;
      --panel: #ffffff;
      --text: #1f2937;
      --muted: #667085;
      --border: #d9ddd5;
      --accent: #2563eb;
      --danger: #b42318;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
      font-size: 14px;
      line-height: 1.45;
    }

    header {
      background: var(--panel);
      border-bottom: 1px solid var(--border);
    }

    .wrap {
      width: min(1040px, calc(100vw - 32px));
      margin: 0 auto;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-height: 72px;
    }

    h1 {
      margin: 0;
      font-size: 22px;
      letter-spacing: 0;
    }

    main {
      padding: 24px 0 48px;
    }

    .meta {
      color: var(--muted);
      font-size: 12px;
      overflow-wrap: anywhere;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }

    textarea {
      width: 100%;
      min-height: 68vh;
      resize: vertical;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 12px;
      color: var(--text);
      font: 13px/1.5 Consolas, "Courier New", monospace;
      white-space: pre;
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 12px;
    }

    button,
    .button-link {
      height: 38px;
      border: 1px solid var(--accent);
      border-radius: 6px;
      padding: 0 12px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      background: var(--accent);
      color: white;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .secondary {
      background: white;
      border-color: var(--border);
      color: var(--text);
    }

    .danger {
      background: var(--danger);
      border-color: var(--danger);
    }

    @media (max-width: 720px) {
      .topbar {
        display: grid;
      }

      textarea {
        min-height: 60vh;
      }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <div>
        <h1>Edit System Prompt</h1>
        <div class="meta">Saved locally at: {{ system_prompt_file }}</div>
      </div>
      <a class="button-link secondary" href="{{ url_for('index') }}">Back to dashboard</a>
    </div>
  </header>

  <main class="wrap">
    <section class="panel">
      <form method="post" action="{{ url_for('save_system_prompt_page') }}">
        <textarea name="system_prompt" spellcheck="false">{{ system_prompt }}</textarea>
        <div class="actions">
          <button type="submit">Save system prompt</button>
          <a class="button-link secondary" href="{{ url_for('index') }}">Cancel</a>
        </div>
      </form>
      <form class="actions" method="post" action="{{ url_for('reset_system_prompt_page') }}">
        <button class="danger" type="submit">Reset to default prompt</button>
      </form>
    </section>
  </main>
</body>
</html>
"""
