/**
 * ActionTooltip Component
 * Displays dynamic action name and shortcut key below or adjacent to the radial menu.
 */

export class ActionTooltip {
  constructor(parent) {
    this.parent = parent;
    this.element = null;
    this.render();
  }

  render() {
    this.element = document.createElement('div');
    this.element.className = 'cb-action-tooltip';
    this.element.id = 'cb-action-tooltip';
    this.parent.appendChild(this.element);
  }

  show(action) {
    this.element.innerHTML = `
      <span>${action.name}</span>
      <span class="cb-tooltip-badge">[${action.num}]</span>
    `;
    this.element.classList.add('cb-visible');
  }

  hide() {
    this.element.classList.remove('cb-visible');
  }
}
