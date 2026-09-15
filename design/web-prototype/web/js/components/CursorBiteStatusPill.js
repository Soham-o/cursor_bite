/**
 * CursorBiteStatusPill Component
 * Bottom-right status element communicating that Cursor Bite is active/available.
 * Clicking it opens or toggles the radial HUD.
 */

export class CursorBiteStatusPill {
  constructor(container, onClick) {
    this.container = container;
    this.onClick = onClick;
    this.element = null;
    this.render();
  }

  render() {
    this.element = document.createElement('div');
    this.element.className = 'cb-status-pill';
    this.element.id = 'cb-status-pill';
    this.element.setAttribute('title', 'Cursor Bite (Local & Ready) • Click or press Ctrl+Alt+B');
    this.element.setAttribute('role', 'button');
    this.element.setAttribute('tabindex', '0');

    this.element.innerHTML = `
      <span>Cursor Bite</span>
      <span class="cb-status-pill-dot"></span>
    `;

    this.element.addEventListener('click', (e) => {
      e.stopPropagation();
      if (this.onClick) {
        this.onClick();
      }
    });

    this.element.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (this.onClick) this.onClick();
      }
    });

    this.container.appendChild(this.element);
  }
}
