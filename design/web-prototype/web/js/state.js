/**
 * Cursor Bite - Application State Store
 * Centralized state with pub/sub for clean modular component reactivity.
 */

const DEFAULT_SELECTED_TEXT = 
`The most important thing in AI right now has nothing to do with picking the right models. The model is becoming a commodity. The teams shipping the most impressive AI systems will tell you that the secret is actually Harness Engineering.`;

class StateStore {
  constructor() {
    const savedTheme = localStorage.getItem('cursorbite_theme') || 'light';
    
    this.state = {
      theme: savedTheme,
      isRadialOpen: false,
      isResultOpen: false,
      isPinned: false,
      activeAction: null,
      cursorPos: { x: window.innerWidth * 0.42, y: window.innerHeight * 0.52 },
      selectedText: DEFAULT_SELECTED_TEXT,
      status: 'success', // 'working' | 'success' | 'failed'
      latency: '1.2s',
      soundEnabled: true,
      simulateError: false // Used to demonstrate realistic error state
    };

    this.listeners = new Set();
  }

  get() {
    return this.state;
  }

  set(partial) {
    this.state = { ...this.state, ...partial };
    
    if (partial.theme) {
      localStorage.setItem('cursorbite_theme', partial.theme);
      document.documentElement.setAttribute('data-theme', partial.theme);
    }
    
    this.notify();
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  notify() {
    for (const listener of this.listeners) {
      listener(this.state);
    }
  }

  toggleTheme() {
    const nextTheme = this.state.theme === 'light' ? 'dark' : 'light';
    this.set({ theme: nextTheme });
  }

  setCursorPos(x, y) {
    this.state.cursorPos = { x, y };
  }
}

export const store = new StateStore();
