# How to Use Cursor Bite

Welcome to **Cursor Bite** — your privacy-first, local-first contextual AI assistant for Windows.

Cursor Bite stays completely out of your way until you summon it. Highlight text anywhere — in a browser, PDF, chat app, code editor, or terminal — press your hotkey, and a modern radial menu instantly appears at your mouse cursor.

---

## Quick Start (30 Seconds)

### 1. Start the Application
Open a terminal (Command Prompt or PowerShell) in the project directory:

```powershell
# Using the virtual environment
.\venv\Scripts\python.exe main.py
```

Cursor Bite will start quietly in your Windows **System Tray** (near the clock on your taskbar). Look for the dark indigo **CB** icon.

### 2. Summon the Menu
Select any text on your screen (or don't select anything), and press:

$$\mathbf{Ctrl + Alt + B}$$

A glowing, dark glassmorphic **Radial Menu** will bloom directly around your mouse cursor!

```
                    [1] 🌐 Translate
           [8] 🤖 Ask AI         [2] 📑 Summarize
      [7] ✍️ Rewrite      (  CB  )      [3] 💡 Explain
           [6] 📷 OCR            [4] 🔍 Search Web
                    [5] ⚙️ Settings
```

---

## Two Ways to Navigate the Radial Menu

You can interact with the radial menu using either your **Mouse** or your **Keyboard**:

### 🖱️ 1. Mouse Navigation
- **Hover** over any sector: The center hub animates with the action's accent color, glowing icon, and action description.
- **Click** any sector: Instantly activates the action.
- **Dismiss**: Click anywhere outside the menu or press `Esc`.

### ⌨️ 2. Lightning Keyboard Shortcuts (Recommended!)
Once the menu is open, you never have to reach for your mouse:

| Key | Action | What It Does |
| :---: | :--- | :--- |
| **`1`** | **Translate** | Translate highlighted text to your configured language (offline) |
| **`2`** | **Summarize** | Generate concise bullet-point summary using local AI |
| **`3`** | **Explain** | Provide an in-depth breakdown of selected text or code |
| **`4`** | **Search Web** | Look up the query on DuckDuckGo (privacy protected) |
| **`5`** | **Settings** | Open the Cursor Bite Configuration panel |
| **`6`** | **Capture OCR** | Drag a selection box over any screen area to read text |
| **`7`** | **Rewrite** | Polish, clarify, and rephrase text using local AI |
| **`8`** | **Ask AI** | Ask custom questions with or without highlighted context |
| **`Arrows`** | **Navigate** | Use `←`, `↑`, `→`, `↓` to cycle through sectors |
| **`Enter` / `Space`** | **Select** | Execute currently highlighted sector |
| **`Esc`** | **Close** | Dismiss the radial menu without taking action |

---

## Feature Walkthrough & Examples

### 1. 🌐 Translate (Offline Neural Translation)
*Translate foreign text without sending a single byte to the cloud.*

1. **Highlight** any foreign text in your browser, document, or chat (e.g. Spanish, French, German, etc.).
2. Press `Ctrl+Alt+B`.
3. Press **`1`** (or click **Translate**).
4. The floating Result Card will appear with the translated output.
5. Click **"Copy"** (or press `Enter`) to copy the translation to your clipboard.

> **Tip:** You can set your default target language in **Settings** (Key `5`) or `config.json` (e.g., `"en"`, `"es"`, `"de"`). Powered 100% locally by **Argos Translate**.

---

### 2. 📑 Summarize (Local AI)
*Condense lengthy articles, meeting notes, or emails into clear bullet points.*

1. **Select** the article, email, or paragraphs you want to condense.
2. Press `Ctrl+Alt+B`.
3. Press **`2`** (or click **Summarize**).
4. The Result Card will display:
   - Live status indicator (`● Analyzing...` $\rightarrow$ `✓ Ready`).
   - Executive bullet-point summary.
   - Word count and processing duration chips.

---

### 3. 💡 Explain (Local AI)
*Understand complex code, legal terms, error logs, or dense jargon.*

1. **Highlight** the difficult code snippet, math formula, or unfamiliar term.
2. Press `Ctrl+Alt+B`.
3. Press **`3`** (or click **Explain**).
4. Cursor Bite breaks down what the text means in plain English, highlighting underlying principles and gotchas.

---

### 4. 🔍 Search Web (DuckDuckGo via Privacy Gateway)
*Quickly look up search terms without switching windows.*

1. **Select** any term, error message, or question.
2. Press `Ctrl+Alt+B`.
3. Press **`4`** (or click **Search Web**).
4. **Privacy Shield:** If the selected text contains sensitive patterns (API keys, credit cards, emails, tokens), Cursor Bite will alert you before sending anything over the network.
5. Top search results with clickable titles, URLs, and snippets appear in the Result Window.

---

### 5. ⚙️ Settings
*Fine-tune hotkeys, AI models, and interface parameters.*

1. Press `Ctrl+Alt+B` and hit **`5`** (or right-click the tray icon and pick **Settings**).
2. Configure:
   - **Main Hotkey** (e.g. `Ctrl+Alt+B`, `Ctrl+Shift+Space`, `Alt+Space`).
   - **AI Model** (e.g. `llama3.2`, `mistral`, `deepseek-r1:8b`, `qwen2.5`).
   - **Translation Language** (Target language code).
   - **Privacy Policy** (Toggle offline-only mode, sensitive data filters).
   - **Menu Radius & Animations**.

---

### 6. 📷 Capture OCR (Screen Region Sniper)
*Extract text from anywhere: images, YouTube videos, canvas apps, or locked PDFs.*

1. Press `Ctrl+Alt+B` (you do **not** need to select text beforehand).
2. Press **`6`** (or click **Capture OCR**).
3. The screen will dim into a darkened overlay with a glowing cyan crosshair.
4. **Click & Drag** a bounding box over the text you want to read.
5. Release the mouse.
6. Cursor Bite's local **Tesseract OCR** engine reads the text and displays it in the Result Card, ready to copy or edit!

---

### 7. ✍️ Rewrite (Local AI)
*Instantly improve grammar, tone, and clarity for your writing.*

1. **Select** your draft email, message, documentation, or post.
2. Press `Ctrl+Alt+B`.
3. Press **`7`** (or click **Rewrite**).
4. Local AI polishes the text for clarity, professional tone, and flow.
5. Hit **"Copy"** and paste it right back.

---

### 8. 🤖 Ask AI (Context-Aware or Freeform Assistant)
*Chat with your local AI about selected text OR ask any general question.*

There are two modes for **Ask AI**:

- **With Highlighted Text:**
  1. Highlight code or text.
  2. Press `Ctrl+Alt+B` $\rightarrow$ **`8`**.
  3. A prompt box appears: *"What would you like to ask about this context?"*
  4. Type your question (e.g., *"How do I refactor this to use asyncio?"*) and press Enter.
- **Without Any Selection:**
  1. Press `Ctrl+Alt+B` $\rightarrow$ **`8`**.
  2. A prompt box appears: *"Ask AI anything..."*
  3. Ask any general question, brainstorm ideas, or ask for quick formulas.

---

## 📋 Clipboard Safety Guarantee

When you summon Cursor Bite on selected text:
1. Cursor Bite **snapshots** your current Windows clipboard content.
2. It captures the selected text using a simulated copy operation.
3. It immediately **restores your original clipboard content**.

> **Your clipboard is safe:** Using Cursor Bite will **never** overwrite or lose whatever you previously copied (e.g., a link or password you had on your clipboard).

---

## 🛡️ Privacy & Offline Modes

Cursor Bite is built around a strict **local-first** design:

| Feature | Processing Location | Internet Required? |
| :--- | :--- | :---: |
| **Translate** | Local (Argos Translate) | ❌ No |
| **Summarize** | Local (Ollama) | ❌ No |
| **Explain** | Local (Ollama) | ❌ No |
| **Rewrite** | Local (Ollama) | ❌ No |
| **Ask AI** | Local (Ollama) | ❌ No |
| **Capture OCR**| Local (Tesseract) | ❌ No |
| **Search Web** | External (DuckDuckGo) | ✔️ Yes |

### 🔒 Enforcing 100% Airgapped Offline Mode
If you work in a secure or offline environment:
1. Right-click the **CB** icon in the Windows System Tray.
2. Click **"○ Offline Mode"** to toggle it to **"● Offline Mode"**.
3. In Offline Mode, web searches are blocked at the architecture level, ensuring 0 bytes leave your PC.

---

## 🎛️ Windows System Tray Options

Right-click the **CB** icon in your taskbar notification area to access:

- **✓ Enabled / Disabled** — Pause hotkey listening if you need `Ctrl+Alt+B` for another game or application.
- **Open** — Summons the radial menu directly.
- **Settings** — Modify configuration.
- **Privacy** — View active privacy policy and sensitive detection rules.
- **Offline Mode** — Toggle strict offline isolation.
- **Check Components** — Tests connectivity and status of Ollama, Argos Translate, Tesseract OCR, and Internet.
- **About** — Version and system information.
- **Exit** — Completely shut down Cursor Bite.

---

## 🔧 Optional Component Setup

Cursor Bite runs with **graceful degradation**. If an optional component is not installed, the app still launches and all other features work normally.

### Ollama (Powers AI Summarize, Explain, Rewrite, Ask AI)
1. Download Ollama from [ollama.com](https://ollama.com).
2. Install and start Ollama.
3. Open terminal and pull the recommended fast lightweight model:
   ```cmd
   ollama pull llama3.2
   ```

### Argos Translate (Powers Offline Translation)
1. Install languages through the Python environment:
   ```powershell
   .\venv\Scripts\python.exe -m pip install argostranslate
   ```
2. Download language models:
   ```powershell
   .\venv\Scripts\argospm.exe update
   .\venv\Scripts\argospm.exe install translate-es_en
   .\venv\Scripts\argospm.exe install translate-en_es
   ```

### Tesseract OCR (Powers Screen Capture OCR)
1. Download Windows installer from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
2. Install to the standard path `C:\Program Files\Tesseract-OCR\tesseract.exe`.

---

## ❓ Troubleshooting & FAQs

### The hotkey does not open the menu
- Check if Cursor Bite is running in your System Tray.
- Check if another application (like a screen recorder or hotkey utility) has already claimed `Ctrl+Alt+B`. You can change the hotkey anytime in `config.json` or through **Settings**.
- Make sure "Enabled" is checked in the system tray menu.

### "AI service unavailable" message
- Make sure the Ollama application is running (check taskbar or run `ollama list` in terminal).
- Verify the model specified in `config.json` is installed (`ollama pull llama3.2`).

### The radial menu appears off-screen
- Cursor Bite features smart multi-monitor and DPI boundary detection. If you are near a screen corner, the menu automatically shifts inward so all 8 sectors remain fully visible and clickable.

### How do I close the Result Card quickly?
- Simply press `Esc` or click the `✕` button in the upper-right corner of the card.
- Pressing `Ctrl+C` or clicking the "Copy" button copies the markdown result to your clipboard.

---

*Enjoy using Cursor Bite! For technical architecture and code details, refer to [README.md](README.md) and [SETUP_GUIDE.md](SETUP_GUIDE.md).*
