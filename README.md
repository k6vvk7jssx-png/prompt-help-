# Prompt Optimizer Background Tray App

Select text in any Windows app, press `Ctrl + Win + 4`, send the selected text to DeepSeek, and replace it with an optimized Markdown prompt.

This is a local Windows background app with a system tray icon. It does not integrate with any specific app, browser, Gmail, Notion, Word, ChatGPT, or Supabase. It only uses a global hotkey, clipboard copy/paste, and simulated keyboard shortcuts.

## Features

- Runs in the Windows system tray.
- Registers `Ctrl + Win + 4` as a global hotkey.
- Copies the selected text from the active app.
- Sends it to the DeepSeek API.
- Replaces the selected text with the optimized Markdown prompt.
- Logs status and errors to `logs/prompt_optimizer.log`.
- Saves prompt history to `data/prompt_history.sqlite3`.
- Includes tray menu actions for start/stop, clipboard test, dashboard, config reload, logs, and quit.
- Opens a local dashboard at `http://127.0.0.1:8765`.

## Setup

Install Python 3.11 or newer for Windows first, and enable **Add python.exe to PATH** during installation.

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
PROMPT_OPTIMIZER_HOTKEY=ctrl+windows+4
COPY_SETTLE_SECONDS=0.25
PASTE_SETTLE_SECONDS=0.1
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=8765
```

## Run

```powershell
python prompt_optimizer.py
```

Then:

1. Write rough text in any app.
2. Select the text.
3. Press `Ctrl + Win + 4`.
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

- Prompt history.
- Original text and optimized Markdown.
- Success and error status.
- Recent errors.
- Search and status filters.
- Copy button for optimized prompts.

Local files:

```text
data/prompt_history.sqlite3
logs/prompt_optimizer.log
```

The `data/` and `logs/` folders are ignored by Git so private prompts, API errors, and local history are not published by mistake.

## Repository Export

To use this from another machine or repository:

```powershell
git clone <your-repository-url>
cd <your-repository-folder>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python prompt_optimizer.py
```

Add the real DeepSeek API key to `.env` before using the hotkey.

To publish on GitHub later:

```powershell
git add .
git commit -m "Add local prompt optimizer tray app"
git branch -M main
git remote add origin <your-github-repository-url>
git push -u origin main
```

Do not commit `.env`, `data/`, or `logs/`.

## Notes

- On some Windows systems, global hotkeys may require running the terminal as Administrator.
- The script temporarily uses the clipboard. If optimization fails, it tries to restore the previous clipboard content.
- `Ctrl + Win + 4` may conflict with system or app shortcuts on some machines. Change it with `PROMPT_OPTIMIZER_HOTKEY` in `.env`, then use **Reload config** from the tray menu.
- Keep `.env` private. It is ignored by Git.
- Supabase is intentionally not used in this version. Configuration and logs stay local.
