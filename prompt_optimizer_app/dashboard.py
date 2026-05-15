import logging
import threading
import webbrowser

from flask import Flask, redirect, render_template_string, request, url_for

from prompt_optimizer_app.config import AppConfig, DATABASE_FILE, LOG_FILE
from prompt_optimizer_app.deepseek import DeepSeekClient
from prompt_optimizer_app.hotkeys import HotkeyController
from prompt_optimizer_app.storage import PromptHistoryStore


logger = logging.getLogger(__name__)


class DashboardServer:
    def __init__(
        self,
        config: AppConfig,
        history_store: PromptHistoryStore,
        hotkeys: HotkeyController,
        on_status,
    ):
        self.config = config
        self.history_store = history_store
        self.hotkeys = hotkeys
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
            records = self.history_store.list_records(query=query, status=status)
            recent_errors = self.history_store.list_recent_errors()
            return render_template_string(
                DASHBOARD_TEMPLATE,
                records=records,
                recent_errors=recent_errors,
                query=query,
                status=status,
                database_file=DATABASE_FILE,
                log_file=LOG_FILE,
                hotkey=self.config.hotkey,
                hotkey_running=self.hotkeys.is_running,
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
      grid-template-columns: minmax(220px, 1fr) 180px auto;
      gap: 10px;
      margin-bottom: 18px;
    }

    input,
    select,
    button {
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
        <form class="header-actions" method="post" action="{{ url_for('test_api') }}">
          <button class="test-api" type="submit">Test DeepSeek API</button>
        </form>
      </div>
    </div>
  </header>

  <main class="wrap">
    <form class="filters" method="get">
      <input name="q" value="{{ query }}" placeholder="Search original, optimized, or error text">
      <select name="status">
        <option value="all" {% if status == "all" %}selected{% endif %}>All statuses</option>
        <option value="success" {% if status == "success" %}selected{% endif %}>Success only</option>
        <option value="error" {% if status == "error" %}selected{% endif %}>Errors only</option>
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
                  <span class="meta">{{ record.created_at }} - {{ record.source }}</span>
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
