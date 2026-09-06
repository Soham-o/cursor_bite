/**
 * CursorBiteActivationToast Component
 * Appears quickly when Ctrl + Alt + B is pressed, subtle animation,
 * stays small, auto-dismisses after 2.5s, theme-aware.
 */

export class ActivationToast {
  constructor(container = document.body) {
    this.container = container;
    this.element = null;
    this.timeoutId = null;
    this.render();
  }

  render() {
    this.element = document.createElement('div');
    this.element.className = 'cb-toast-container';
    this.element.id = 'cb-activation-toast';
    this.element.setAttribute('role', 'status');
    this.element.setAttribute('aria-live', 'polite');

    this.element.innerHTML = `
      <div class="cb-toast-pill">
        <div class="cb-toast-leading">
          <div class="cb-toast-check-icon">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
          <span class="cb-toast-title">Cursor Bite activated</span>
        </div>
        <div class="cb-toast-badge">Ctrl + Alt + B</div>
      </div>
    `;

    this.container.appendChild(this.element);
  }

  show(duration = 2400) {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
    }

    this.element.classList.remove('cb-hiding');
    this.element.classList.add('cb-visible');

    this.timeoutId = setTimeout(() => {
      this.hide();
    }, duration);
  }

  hide() {
    this.element.classList.remove('cb-visible');
    this.element.classList.add('cb-hiding');
  }
}
