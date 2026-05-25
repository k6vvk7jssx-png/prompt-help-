# Prompt Optimizer Background Tray App

Select text in any Windows app, press `Ctrl + Alt + P`, route optimization by detected provider (`ChatGPT`, `Claude`, `Gemini`), and replace the selected text with an optimized Markdown prompt.

This is a local Windows background app with a system tray icon. It uses a global hotkey, clipboard copy/paste, and keyboard/browser automation. It does not require Supabase and keeps all runtime data local.

## Features

- Runs in the Windows system tray.
- Registers `Ctrl + Alt + P` as a global hotkey.
- Copies the selected text from the active app.
- Detects active provider from the foreground window title.
- Keeps web helper access disabled by default (`WEB_HELPERS_ENABLED=false`).
- Requires explicit web access arming from tray/dashboard before any external run.
- Shows a native consent alert before every external run to ChatGPT/Claude/Gemini helper.
- Shows a native consent alert before every DeepSeek API run when `REQUIRE_DEEPSEEK_CONSENT=true`.
- Tries provider-specific web helper automation only after your per-run consent.
- Falls back automatically to DeepSeek if web helper automation fails.
- Replaces the selected text with the optimized Markdown prompt.
- Logs status and errors to `logs/prompt_optimizer.log`.
- Saves prompt history to `data/prompt_history.sqlite3`.
- Saves an optional custom agent system prompt to `data/system_prompt.md`.
- Includes tray menu actions for start/stop, clipboard test, dashboard, config reload, logs, and quit.
- Opens a local dashboard at `http://127.0.0.1:8765`.
- Starts the local dashboard automatically when the tray app starts.

## Setup

Install Python 3.11 or newer for Windows first, and enable **Add python.exe to PATH** during installation.

If `python` is not visible in PowerShell, try the direct path:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" --version
```

If both `python --version` and the direct path fail, reinstall Python from python.org and enable **Add python.exe to PATH**, then close and reopen PowerShell.

Fast Windows setup:

```powershell
.\setup.bat
```

If an old virtual environment is broken, `setup.bat` recreates `.venv` automatically after Python is visible again.

Then open `.env` and set:

```text
DEEPSEEK_API_KEY=your_real_key_here
```

Install the browser runtime once for Playwright:

```powershell
playwright install chromium
```

Start the app without a terminal window:

```powershell
.\run.bat
```

If the app does not appear in the tray, run the debug launcher so Windows keeps the error window open:

```powershell
.\debug_run.bat
```

Manual setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set:

```text
DEEPSEEK_API_KEY=your_real_key_here
```

Optional `.env` settings:

```text
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=60
REQUIRE_DEEPSEEK_CONSENT=true
PROMPT_OPTIMIZER_HOTKEY=ctrl+alt+p
COPY_SETTLE_SECONDS=0.45
PASTE_SETTLE_SECONDS=0.1
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=8765
WEB_HELPERS_ENABLED=false
WEB_HELPER_TIMEOUT_SECONDS=90
WEB_HELPER_RETRY_COUNT=1
WEB_HELPER_FALLBACK_LOCAL=true
OPENAI_HELPER_URL=https://platform.openai.com/chat/edit?models=gpt-5.4-mini&optimize=true
CLAUDE_HELPER_URL=https://claude.ai/public/artifacts/3796db7e-4ef1-4cab-b70c-d045778f23ec
GEMINI_HELPER_URL=https://aistudio.google.com/prompts/new_chat
```

## Run

```powershell
python prompt_optimizer.py
```

Or double-click `run.bat` to start it as a background tray app without keeping a terminal open.

Then:

1. Write rough text in any app.
2. Select the text.
3. Press `Ctrl + Alt + P`.
4. Wait for the optimized Markdown prompt to replace the selection.

Use the tray icon menu to:

- Stop or start the hotkey.
- Test clipboard optimization using the current clipboard content.
- Open the local dashboard.
- Open logs.
- Reload `.env` after editing settings.
- Quit the background app.

## Local Dashboard

Open the tray icon menu and select **Open dashboard**.

The dashboard shows:

- Power button to turn the hotkey on or off.
- DeepSeek API test button.
- System prompt editor for the DeepSeek agent.
- Web helper pipeline status (provider, execution path, helper latency, helper errors).
- Web access ARM/DISARM control.
- Per-run consent status (required/granted/denied).
- Auto provider detection toggle.
- Direct helper links (OpenAI, Claude, Gemini).
- Prompt history.
- Original text and optimized Markdown.
- Success and error status.
- Recent errors.
- Search and status filters.
- Copy button for optimized prompts.

Local files:

```text
data/prompt_history.sqlite3
data/system_prompt.md
data/runtime_settings.json
logs/prompt_optimizer.log
```

The `data/` and `logs/` folders are ignored by Git so private prompts, API errors, custom system prompts, and local history are not published by mistake.

## Edit the Agent System Prompt

Open the dashboard at `http://127.0.0.1:8765` and click **Edit system prompt**.

When you save, the custom prompt is stored only on your machine:

```text
data/system_prompt.md
```

The next hotkey run uses the saved prompt automatically. If you reset it from the dashboard, the app goes back to the default prompt built into `prompt_optimizer_app/deepseek.py`.

## Repository Export

To use this from another machine or repository:

```powershell
git clone <your-repository-url>
cd <your-repository-folder>
.\setup.bat
.\run.bat
```

Add the real DeepSeek API key to `.env` before using the hotkey.

To create a standalone Windows executable:

```powershell
build_exe.bat
```

The output will be:

```text
dist\PromptOptimizer.exe
```

To publish on GitHub later:

```powershell
git add .
git commit -m "Add local prompt optimizer tray app"
git branch -M main
git remote add origin <your-github-repository-url>
git push -u origin main
```

Do not commit `.env`, `data/`, or `logs/`.

## Vercel

Vercel deploys the public project page in `app.py`.

The deployment entrypoint is explicitly set in `pyproject.toml`.

If you want the Vercel page to show that DeepSeek is configured, add this Vercel Environment Variable:

```text
DEEPSEEK_API_KEY=your_real_deepseek_key
```

Add it in Vercel under **Project Settings -> Environment Variables** for Production, Preview, and Development as needed. The page only checks whether the variable exists; it never prints the secret.

The desktop automation itself does not run on Vercel because Vercel cannot access a user's Windows keyboard, clipboard, system tray, or selected text in other apps. Users should install and run the Windows app locally with `setup.bat` and `run.bat`.

## Notes

- On some Windows systems, global hotkeys may require running the terminal as Administrator.
- For web helper mode, stay logged in at least once on OpenAI, Claude, and AI Studio in the browser profile used by Playwright.
- Consent is always required before each external web-helper run. Denied consent triggers automatic local fallback.
- If `REQUIRE_DEEPSEEK_CONSENT=true`, consent is also required before each DeepSeek API call. If denied, no external API request is made and selected text is left unchanged.
- The script temporarily uses the clipboard. If optimization fails, it tries to restore the previous clipboard content.
- `Ctrl + Alt + P` may conflict with system or app shortcuts on some machines. Change it with `PROMPT_OPTIMIZER_HOTKEY` in `.env`, then use **Reload config** from the tray menu.
- Keep `.env` private. It is ignored by Git.
- Supabase is intentionally not used in this version. Configuration and logs stay local.
