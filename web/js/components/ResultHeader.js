/**
 * ResultHeader Component
 * Compact title row with action icon, action title, pin toggle, and close button.
 */

export class ResultHeader {
  constructor(action, isPinned, onPinToggle, onClose) {
    this.action = action;
    this.isPinned = isPinned;
    this.onPinToggle = onPinToggle;
    this.onClose = onClose;
    this.element = null;
    this.render();
  }

  getActionIcon(actionId) {
    const icons = {
      explain: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#FBBF24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-7 7c0 2.5 1.5 4.5 3 6h8c1.5-1.5 3-3.5 3-6a7 7 0 0 0-7-7z"/></svg>`,
      translate: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 5h10M7 2v3m-3 7c1.5-2 3.5-4 5-6 1 1 2 2.5 3 4M14 11l4 8m-3-3h5"/></svg>`,
      summarize: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`,
      search: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16" y2="16"/></svg>`,
      ocr: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#A5B4FC" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7V5a2 2 0 0 1 2-2h2m10 0h2a2 2 0 0 1 2 2v2m0 10v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/></svg>`,
      rewrite: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>`,
      ask: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
      settings: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`
    };
    return icons[actionId] || icons.explain;
  }

  render() {
    this.element = document.createElement('div');
    this.element.className = 'cb-result-header';

    const iconHtml = this.getActionIcon(this.action.id);

    this.element.innerHTML = `
      <div class="cb-header-left">
        <span class="cb-header-icon">${iconHtml}</span>
        <span class="cb-header-title">${this.action.name}</span>
      </div>
      <div class="cb-header-actions">
        <button class="cb-header-btn ${this.isPinned ? 'is-active' : ''}" id="cb-pin-btn" title="Pin result panel" aria-label="Pin panel">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="17" x2="12" y2="22"></line>
            <path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a1 1 0 0 0 0-2H8a1 1 0 0 0 0 2h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"></path>
          </svg>
        </button>
        <button class="cb-header-btn" id="cb-close-btn" title="Close (Esc)" aria-label="Close panel">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    `;

    const pinBtn = this.element.querySelector('#cb-pin-btn');
    pinBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.isPinned = !this.isPinned;
      pinBtn.classList.toggle('is-active', this.isPinned);
      this.onPinToggle(this.isPinned);
    });

    const closeBtn = this.element.querySelector('#cb-close-btn');
    closeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.onClose();
    });
  }

  updateAction(action) {
    this.action = action;
    const titleEl = this.element.querySelector('.cb-header-title');
    const iconEl = this.element.querySelector('.cb-header-icon');
    if (titleEl) titleEl.textContent = action.name;
    if (iconEl) iconEl.innerHTML = this.getActionIcon(action.id);
  }

  getElement() {
    return this.element;
  }
}
