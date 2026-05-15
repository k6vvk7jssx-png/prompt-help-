import os

from flask import Flask, render_template_string


app = Flask(__name__)


@app.get("/")
def index():
    has_deepseek_key = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Prompt Help</title>
          <style>
            :root {
              --bg: #f7f7f3;
              --panel: #ffffff;
              --text: #1f2937;
              --muted: #667085;
              --border: #d9ddd5;
              --accent: #2563eb;
              --ok: #13795b;
              --warn: #b54708;
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
              font-size: 16px;
              line-height: 1.55;
            }

            .wrap {
              width: min(980px, calc(100vw - 32px));
              margin: 0 auto;
            }

            header {
              padding: 56px 0 28px;
              border-bottom: 1px solid var(--border);
              background: var(--panel);
            }

            h1 {
              margin: 0 0 12px;
              font-size: clamp(34px, 5vw, 58px);
              line-height: 1.02;
              letter-spacing: 0;
            }

            .lead {
              max-width: 760px;
              margin: 0;
              color: var(--muted);
              font-size: 19px;
            }

            .actions {
              display: flex;
              flex-wrap: wrap;
              gap: 12px;
              margin-top: 26px;
            }

            a.button {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              min-height: 42px;
              border-radius: 7px;
              padding: 0 16px;
              background: var(--accent);
              color: white;
              font-weight: 700;
              text-decoration: none;
            }

            a.secondary {
              background: #374151;
            }

            main {
              padding: 30px 0 56px;
            }

            .grid {
              display: grid;
              grid-template-columns: repeat(3, 1fr);
              gap: 14px;
              margin-bottom: 24px;
            }

            .card,
            .panel {
              background: var(--panel);
              border: 1px solid var(--border);
              border-radius: 8px;
            }

            .card {
              padding: 18px;
            }

            .card strong {
              display: block;
              margin-bottom: 6px;
            }

            .card span,
            .note {
              color: var(--muted);
            }

            .panel {
              padding: 20px;
              margin-top: 16px;
            }

            h2 {
              margin: 0 0 12px;
              font-size: 22px;
            }

            ol {
              margin: 0;
              padding-left: 22px;
            }

            li + li {
              margin-top: 8px;
            }

            code,
            pre {
              background: var(--code);
              border-radius: 6px;
              font-family: Consolas, "Courier New", monospace;
            }

            code {
              padding: 2px 5px;
            }

            pre {
              overflow: auto;
              padding: 14px;
              white-space: pre-wrap;
            }

            .status {
              color: var(--ok);
              font-weight: 700;
            }

            .warning {
              color: var(--warn);
              font-weight: 700;
            }

            @media (max-width: 760px) {
              header {
                padding-top: 38px;
              }

              .grid {
                grid-template-columns: 1fr;
              }
            }
          </style>
        </head>
        <body>
          <header>
            <div class="wrap">
              <h1>Prompt Help</h1>
              <p class="lead">
                A Windows desktop prompt optimizer. Select text in any app, press
                Ctrl + Win + 4, and replace it with a cleaner Markdown prompt using DeepSeek.
              </p>
              <div class="actions">
                <a class="button" href="https://github.com/k6vvk7jssx-png/prompt-help-">Open GitHub repo</a>
                <a class="button secondary" href="https://github.com/k6vvk7jssx-png/prompt-help-/archive/refs/heads/master.zip">Download ZIP</a>
              </div>
            </div>
          </header>

          <main class="wrap">
            <div class="grid">
              <div class="card">
                <strong>Desktop first</strong>
                <span>Runs locally on Windows with a tray icon and global hotkey.</span>
              </div>
              <div class="card">
                <strong>Local dashboard</strong>
                <span>Shows prompt history and errors at 127.0.0.1:8765.</span>
              </div>
              <div class="card">
                <strong>No cloud storage</strong>
                <span>Your API key, logs, and history stay on your machine.</span>
              </div>
            </div>

            <section class="panel">
              <h2>Install on Windows</h2>
              <ol>
                <li>Install Python 3.11 or newer and enable <code>Add python.exe to PATH</code>.</li>
                <li>Download or clone the GitHub repository.</li>
                <li>Run <code>setup.bat</code>.</li>
                <li>Open <code>.env</code> and add your <code>DEEPSEEK_API_KEY</code>.</li>
                <li>Run <code>run.bat</code>.</li>
              </ol>
            </section>

            <section class="panel">
              <h2>Commands</h2>
              <pre>git clone https://github.com/k6vvk7jssx-png/prompt-help-.git
cd prompt-help-
setup.bat
run.bat</pre>
              <p class="note">
                Vercel hosts this project page only. The hotkey, clipboard replacement,
                and tray app must run on your Windows computer.
              </p>
            </section>

            <section class="panel">
              <h2>Deployment Status</h2>
              <p class="status">Vercel entrypoint is configured.</p>
              {% if has_deepseek_key %}
                <p class="status">DEEPSEEK_API_KEY is configured on Vercel.</p>
              {% else %}
                <p class="warning">DEEPSEEK_API_KEY is not configured on Vercel.</p>
              {% endif %}
              <p class="note">
                The desktop automation is intentionally not executed on Vercel because
                cloud servers cannot access your Windows keyboard, clipboard, or tray.
              </p>
            </section>
          </main>
        </body>
        </html>
        """,
        has_deepseek_key=has_deepseek_key,
    )
