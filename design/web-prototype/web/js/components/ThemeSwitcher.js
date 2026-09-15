/**
 * ThemeSwitcher Component
 * Toggles between Light Mode (Default) and Dark Mode with persistence in localStorage.
 */

import { store } from '../state.js';

export class ThemeSwitcher {
  constructor(container) {
    this.container = container;
    this.element = null;
    this.render();

    store.subscribe((state) => {
      this.updateIcon(state.theme);
    });
  }

  render() {
    this.element = document.createElement('button');
    this.element.className = 'cb-theme-btn';
    this.element.id = 'cb-theme-switcher';
    this.element.setAttribute('title', 'Toggle Light / Dark Mode');
    this.element.setAttribute('aria-label', 'Toggle Light / Dark Mode');

    this.updateIcon(store.get().theme);

    this.element.addEventListener('click', (e) => {
      e.stopPropagation();
      store.toggleTheme();
    });

    this.container.appendChild(this.element);
  }

  updateIcon(theme) {
    if (theme === 'dark') {
      // Moon / Dark icon, clicking turns to Light
      this.element.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="5"></circle>
          <line x1="12" y1="1" x2="12" y2="3"></line>
          <line x1="12" y1="21" x2="12" y2="23"></line>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
          <line x1="1" y1="12" x2="3" y2="12"></line>
          <line x1="21" y1="12" x2="23" y2="12"></line>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
        </svg>
      `;
    } else {
      // Sun / Light icon, clicking turns to Dark
      this.element.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
        </svg>
      `;
    }
  }
}
