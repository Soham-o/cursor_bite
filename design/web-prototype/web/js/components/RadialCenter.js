/**
 * RadialCenter Component
 * Circular interaction core (NO cursor graphic).
 * Features subtle purple/blue ambient glow, soft outer ring, glowing ring, and pulsing core dot.
 */

export class RadialCenter {
  constructor(parent) {
    this.parent = parent;
    this.element = null;
    this.render();
  }

  render() {
    this.element = document.createElement('div');
    this.element.className = 'cb-center-core';
    this.element.id = 'cb-radial-center';
    this.element.setAttribute('aria-hidden', 'true');

    this.element.innerHTML = `
      <div class="cb-center-ring-glow"></div>
      <div class="cb-center-inner-dot"></div>
    `;

    this.parent.appendChild(this.element);
  }
}
