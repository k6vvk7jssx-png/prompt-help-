# Prompt Optimizer Desktop

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6.svg)](https://microsoft.com/windows)
[![LLM: DeepSeek / OpenAI / Claude](https://img.shields.io/badge/LLM-Multi--Provider-purple.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight, system-wide Windows desktop application that enhances and restructures raw user prompts in real-time across any application via global hotkeys.

---

## 💡 How It Works

1. **Select Text Anywhere:** Highlight any rough prompt in your browser, IDE, or terminal.
2. **Press Hotkey (`Ctrl + Shift + O`):** Prompt Optimizer captures the active window context and highlighted text.
3. **Provider & Domain Detection:** Automatically identifies whether you are querying ChatGPT, Claude, Gemini, or DeepSeek and maps your intent against a **35+ domain role matrix**.
4. **Instant In-Place Optimization:** Replaces the text with a structured, high-context Markdown prompt with expert roles, constraints, and output formats.

---

## 🧠 Domain Metaprompting Matrix

Prompt Optimizer includes specialized expert schemas across major domains:
* **Software Engineering:** Architecture design, full-stack, DevOps, code review, test automation.
* **AI & Agentic Systems:** RAG systems, tool orchestration, metaprompts, system prompts.
* **UI/UX & Design:** Design systems, wireframing, frontend engineering, accessibility.
* **Business & Strategy:** PRD creation, pitch decks, startup roadmaps, legal/financial analysis.
* **Writing & Communication:** Technical copywriting, localisation, tone shaping.

---

## 🛠️ Architecture & Modules

* `prompt_optimizer_app/hotkeys.py`: Win32 low-level global key listener.
* `prompt_optimizer_app/deepseek.py`: Prompt refinement engine and structured metaprompt matrix.
* `prompt_optimizer_app/provider_detector.py`: Heuristic window inspection for target AI models.
* `prompt_optimizer_app/tray.py`: Background system tray integration.
* `build_exe.bat`: One-click PyInstaller packaging for standalone `.exe` binaries.

---

## 🚀 Installation & Usage

```bash
# Clone repository
git clone https://github.com/k6vvk7jssx-png/prompt-help-.git
cd prompt-help-

# Setup environment
setup.bat

# Run application
run.bat
```

To compile a standalone Windows executable:
```bash
build_exe.bat
```

---

## 📄 License
MIT License.
