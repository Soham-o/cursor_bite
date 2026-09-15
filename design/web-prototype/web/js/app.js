/**
 * Cursor Bite - Application Coordinator
 * Integrates all overlay components, host page selection, keyboard hotkeys, and demo flows.
 */

import { store } from './state.js';
import { ACTIONS } from './tokens.js';
import { actionService } from './services/actionService.js';
import { ActivationToast } from './components/ActivationToast.js';
import { RadialMenu } from './components/RadialMenu.js';
import { ResultPanel } from './components/ResultPanel.js';
import { CursorBiteStatusPill } from './components/CursorBiteStatusPill.js';
import { ThemeSwitcher } from './components/ThemeSwitcher.js';

class CursorBiteApp {
  constructor() {
    this.mousePos = { x: 0, y: 0 };
    this.lastSelectedText = store.get().selectedText;
    
    // Components
    this.toast = null;
    this.radialMenu = null;
    this.resultPanel = null;
    this.statusPill = null;
    this.themeSwitcher = null;

    this.init();
  }

  init() {
    // 1. Set initial theme
    const initialTheme = store.get().theme;
    document.documentElement.setAttribute('data-theme', initialTheme);

    // 2. Mount overlay components
    const overlayRoot = document.getElementById('cb-overlay-root') || document.body;

    this.toast = new ActivationToast(overlayRoot);

    this.radialMenu = new RadialMenu(
      overlayRoot,
      (action) => this.handleActionSelected(action),
      () => store.set({ isRadialOpen: false })
    );

    this.resultPanel = new ResultPanel(
      overlayRoot,
      (pinned) => store.set({ isPinned: pinned }),
      () => {
        store.set({ isResultOpen: false });
        this.radialMenu.clearFocus();
      },
      (settingEvent) => this.handleSettingEvent(settingEvent)
    );

    this.statusPill = new CursorBiteStatusPill(overlayRoot, () => {
      this.triggerActivation();
    });

    // Mount theme switcher in the bottom helper bar
    const themeSlot = document.getElementById('cb-theme-slot');
    if (themeSlot) {
      this.themeSwitcher = new ThemeSwitcher(themeSlot);
    }

    // Setup interactive context editor & preset chips
    this.setupContextEditor();

    // 3. Bind Global Mouse & Keyboard Listeners
    this.bindEvents();

    // 4. Initial Showcase State (Matching Reference Screenshot)
    // Delay slightly to ensure layout and fonts are ready
    setTimeout(() => {
      this.setupInitialShowcase();
    }, 100);
  }

  bindEvents() {
    // Track cursor coordinates
    window.addEventListener('mousemove', (e) => {
      this.mousePos = { x: e.clientX, y: e.clientY };
      store.setCursorPos(e.clientX, e.clientY);
    });

    // Detect user text selection
    document.addEventListener('selectionchange', () => {
      const selection = window.getSelection();
      const text = selection ? selection.toString().trim() : '';
      if (text.length > 2) {
        this.lastSelectedText = text;
        store.set({ selectedText: text });
      }
    });

    document.addEventListener('mouseup', (e) => {
      const selection = window.getSelection();
      const text = selection ? selection.toString().trim() : '';
      if (text.length > 2 && !e.target.closest('#cb-overlay-root') && !e.target.closest('.cb-interactive-bar') && !e.target.closest('.cb-context-modal')) {
        this.lastSelectedText = text;
        store.set({ selectedText: text });
      }
    });

    // Global Hotkey: Ctrl + Alt + B (or Meta + Alt + B on macOS)
    window.addEventListener('keydown', (e) => {
      const isCtrlOrMeta = e.ctrlKey || e.metaKey;
      const isAlt = e.altKey;
      const isKeyB = e.key.toLowerCase() === 'b';

      if (isCtrlOrMeta && isAlt && isKeyB) {
        e.preventDefault();
        this.triggerActivation();
        return;
      }

      // Escape to dismiss
      if (e.key === 'Escape') {
        if (this.radialMenu.isOpen && this.resultPanel.isOpen) {
          this.radialMenu.close();
          if (!this.resultPanel.isPinned) {
            this.resultPanel.close();
          }
        } else if (this.radialMenu.isOpen) {
          this.radialMenu.close();
        } else if (this.resultPanel.isOpen && !this.resultPanel.isPinned) {
          this.resultPanel.close();
        }
        return;
      }

      // 1-8 keys to select radial action
      const num = parseInt(e.key, 10);
      if (num >= 1 && num <= 8) {
        const action = ACTIONS.find(a => a.num === num);
        if (action) {
          e.preventDefault();
          this.handleActionSelected(action);
        }
      }
    });

    // Outside click dismissal
    document.addEventListener('click', (e) => {
      const clickedInRadial = e.target.closest('#cb-radial-menu');
      const clickedInResult = e.target.closest('#cb-result-panel');
      const clickedInStatus = e.target.closest('#cb-status-pill');
      const clickedInHelper = e.target.closest('.cb-interactive-bar');

      if (!clickedInRadial && !clickedInResult && !clickedInStatus && !clickedInHelper) {
        if (this.radialMenu.isOpen) {
          this.radialMenu.close();
        }
        if (this.resultPanel.isOpen && !this.resultPanel.isPinned) {
          this.resultPanel.close();
        }
      }
    });

    // Interactive helper trigger button
    const triggerBtn = document.getElementById('cb-trigger-hotkey-btn');
    if (triggerBtn) {
      triggerBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.triggerActivation();
      });
    }

    // Interactive selection click trigger
    const highlightEl = document.querySelector('.yt-selected-highlight');
    if (highlightEl) {
      highlightEl.addEventListener('click', (e) => {
        this.mousePos = { x: e.clientX, y: e.clientY };
        this.triggerActivation();
      });
    }
  }

  triggerActivation() {
    // 1. Show activation toast
    this.toast.show(3200);

    // 2. Open radial menu at mouse position (or center near highlighted selection)
    const highlight = document.querySelector('.yt-selected-highlight');
    let x = this.mousePos.x;
    let y = this.mousePos.y;

    if ((!x || x === 0) && highlight) {
      const rect = highlight.getBoundingClientRect();
      x = rect.left + rect.width * 0.75;
      y = rect.top + rect.height * 0.6;
    }

    this.radialMenu.open(x, y);
    store.set({ isRadialOpen: true });
  }

  handleActionSelected(action) {
    store.set({ activeAction: action });
    
    // Highlight sector on radial menu
    this.highlightSector(action.id);

    // If radial is not open, open it near current position
    if (!this.radialMenu.isOpen) {
      const highlight = document.querySelector('.yt-selected-highlight');
      let x = this.mousePos.x || (highlight ? highlight.getBoundingClientRect().right - 30 : window.innerWidth * 0.42);
      let y = this.mousePos.y || (highlight ? highlight.getBoundingClientRect().top + 30 : window.innerHeight * 0.52);
      this.radialMenu.open(x, y);
    }

    // Anchor result panel beside the radial HUD and stream real-time response!
    const hudRect = this.radialMenu.getPosition();
    const currentState = store.get();
    
    // Call openBeside in REAL-TIME streaming mode with current selected text!
    this.resultPanel.openBeside(hudRect, action, currentState.selectedText);
    store.set({ isResultOpen: true });
  }

  highlightSector(actionId) {
    this.radialMenu.items.forEach(item => {
      if (item.element) {
        if (item.action.id === actionId) {
          item.element.classList.add('cb-selected');
        } else {
          item.element.classList.remove('cb-selected');
        }
      }
    });
  }

  handleSettingEvent(event) {
    if (event === 'toggleError') {
      window.__simulateError = !window.__simulateError;
      
      // Re-trigger Translate with error
      const translateAction = ACTIONS.find(a => a.id === 'translate');
      this.handleActionSelected(translateAction);
    }
  }

  setupContextEditor() {
    const helperBar = document.getElementById('cb-interactive-bar');
    if (!helperBar) return;

    // 1. Context Pill
    const contextPill = document.createElement('button');
    contextPill.className = 'cb-context-pill';
    contextPill.id = 'cb-context-pill';
    contextPill.title = 'Click to edit custom context or pick presets';
    
    const updatePillText = (text) => {
      const preview = (text || '').replace(/\s+/g, ' ').slice(0, 24);
      contextPill.innerHTML = `
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
        </svg>
        <span>Context: "${preview}..."</span>
      `;
    };

    updatePillText(store.get().selectedText);
    helperBar.appendChild(contextPill);

    // 2. Context Editor Popover Modal
    const modal = document.createElement('div');
    modal.className = 'cb-context-modal';
    modal.id = 'cb-context-modal';

    modal.innerHTML = `
      <div class="cb-context-header">
        <span>Edit Active Context (Real-Time AI)</span>
        <button class="cb-header-btn" id="cb-close-context-modal" style="width:20px;height:20px;">✕</button>
      </div>
      <textarea class="cb-context-textarea" id="cb-context-input" placeholder="Type or paste any text, code, or article...">${store.get().selectedText}</textarea>
      <div class="cb-context-presets">
        <span style="font-size: 10px; color: #94A3B8; align-self: center;">Presets:</span>
        <button class="cb-preset-chip" data-preset="youtube">YouTube AI</button>
        <button class="cb-preset-chip" data-preset="code">Python Code</button>
        <button class="cb-preset-chip" data-preset="review">Product Review</button>
        <button class="cb-preset-chip" data-preset="quantum">Quantum Physics</button>
      </div>
      <div class="cb-context-actions">
        <div class="cb-ollama-live-badge">
          <span class="cb-status-dot"></span>
          <span>llama3.2:latest (Connected)</span>
        </div>
        <button class="cb-apply-context-btn" id="cb-apply-context-btn">Apply & Run</button>
      </div>
    `;

    document.body.appendChild(modal);

    const textarea = modal.querySelector('#cb-context-input');
    const closeBtn = modal.querySelector('#cb-close-context-modal');
    const applyBtn = modal.querySelector('#cb-apply-context-btn');

    const presets = {
      youtube: `The most important thing in AI right now has nothing to do with picking the right models. The model is becoming a commodity. The teams shipping the most impressive AI systems will tell you that the secret is actually Harness Engineering.`,
      code: `def memoize(fn):\n    cache = {}\n    def wrapper(*args):\n        if args not in cache:\n            cache[args] = fn(*args)\n        return cache[args]\n    return wrapper`,
      review: `The battery life easily lasts over 15 hours of continuous coding, but the key travel feels a bit shallow compared to the previous model.`,
      quantum: `Quantum entanglement is a phenomenon where two or more particles become interconnected such that the physical state of one instantly influences the other, regardless of spatial distance.`
    };

    contextPill.addEventListener('click', (e) => {
      e.stopPropagation();
      textarea.value = store.get().selectedText;
      modal.classList.toggle('cb-visible');
    });

    closeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      modal.classList.remove('cb-visible');
    });

    modal.querySelectorAll('.cb-preset-chip').forEach(chip => {
      chip.addEventListener('click', (e) => {
        e.stopPropagation();
        const key = chip.getAttribute('data-preset');
        if (presets[key]) {
          textarea.value = presets[key];
        }
      });
    });

    applyBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const val = textarea.value.trim();
      if (val) {
        store.set({ selectedText: val });
        updatePillText(val);
        modal.classList.remove('cb-visible');
        this.triggerActivation();
      }
    });

    // Update pill when selection changes on page
    store.subscribe((state) => {
      updatePillText(state.selectedText);
    });

    // Dismiss modal on outside click
    document.addEventListener('click', (e) => {
      if (!modal.contains(e.target) && e.target !== contextPill) {
        modal.classList.remove('cb-visible');
      }
    });
  }

  setupInitialShowcase() {
    // 1. Anchor position from the selected highlight text
    const highlight = document.querySelector('.yt-selected-highlight');
    let x = window.innerWidth * 0.42;
    let y = window.innerHeight * 0.52;

    if (highlight) {
      const rect = highlight.getBoundingClientRect();
      x = rect.right - 20;
      y = rect.top + 30;
    }

    // 2. Open Toast
    this.toast.show(5000);

    // 3. Open Radial HUD
    this.radialMenu.open(x, y);

    // 4. Highlight Sector 3 ("Explain")
    this.highlightSector('explain');

    // 5. Open Explain Result Panel beside HUD (matching reference composition)
    const hudRect = this.radialMenu.getPosition();
    const explainAction = ACTIONS.find(a => a.id === 'explain');
    const resultData = actionService.getActionResult('explain', store.get().selectedText, false);

    this.resultPanel.openBeside(hudRect, explainAction, resultData);

    store.set({
      isRadialOpen: true,
      isResultOpen: true,
      activeAction: explainAction
    });
  }
}

// Instantiate on DOM load
window.addEventListener('DOMContentLoaded', () => {
  window.cursorBiteApp = new CursorBiteApp();
});
