/**
 * RadialMenuItem Component
 * Renders a single sector (SVG path, micro-number, icon, and label).
 * Visual priority: ICON > NUMBER > LABEL.
 */

import { RADIAL_CONFIG } from '../tokens.js';

export class RadialMenuItem {
  constructor(action, onSelect, onHover) {
    this.action = action;
    this.onSelect = onSelect;
    this.onHover = onHover;
    this.element = null;
  }

  getIconSvg(name) {
    const icons = {
      translate: `
        <svg class="cb-sector-icon" width="13" height="13" viewBox="0 0 24 24">
          <path d="M2 5h10M7 2v3m-3 7c1.5-2 3.5-4 5-6 1 1 2 2.5 3 4M14 11l4 8m-3-3h5"/>
        </svg>
      `,
      summarize: `
        <svg class="cb-sector-icon" width="12" height="12" viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
      `,
      explain: `
        <svg class="cb-sector-icon" width="13" height="13" viewBox="0 0 24 24">
          <path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-7 7c0 2.5 1.5 4.5 3 6h8c1.5-1.5 3-3.5 3-6a7 7 0 0 0-7-7z"/>
        </svg>
      `,
      search: `
        <svg class="cb-sector-icon" width="12" height="12" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="7"/>
          <line x1="21" y1="21" x2="16" y2="16"/>
        </svg>
      `,
      ocr: `
        <svg class="cb-sector-icon" width="12" height="12" viewBox="0 0 24 24">
          <path d="M3 7V5a2 2 0 0 1 2-2h2m10 0h2a2 2 0 0 1 2 2v2m0 10v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/>
        </svg>
      `,
      rewrite: `
        <svg class="cb-sector-icon" width="12" height="12" viewBox="0 0 24 24">
          <path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
        </svg>
      `,
      ask: `
        <svg class="cb-sector-icon" width="12" height="12" viewBox="0 0 24 24">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          <line x1="8" y1="10" x2="8.01" y2="10"/>
          <line x1="12" y1="10" x2="12.01" y2="10"/>
          <line x1="16" y1="10" x2="16.01" y2="10"/>
        </svg>
      `,
      settings: `
        <svg class="cb-sector-icon" width="12" height="12" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
      `
    };
    return icons[name] || icons.explain;
  }

  render(svgContainer) {
    const cx = RADIAL_CONFIG.totalDiameter / 2;
    const cy = RADIAL_CONFIG.totalDiameter / 2;
    const rOut = RADIAL_CONFIG.outerRadius;
    const rIn = RADIAL_CONFIG.innerRadius;

    // Angle calculation: 0 is top (12 o'clock), moving clockwise
    const thetaDeg = this.action.angle;
    const halfSpan = 22.5; // 45 / 2
    const startDeg = thetaDeg - halfSpan;
    const endDeg = thetaDeg + halfSpan;

    const toRad = deg => (deg * Math.PI) / 180;

    // Outer & Inner arc points
    const pOutStart = {
      x: cx + rOut * Math.sin(toRad(startDeg)),
      y: cy - rOut * Math.cos(toRad(startDeg))
    };
    const pOutEnd = {
      x: cx + rOut * Math.sin(toRad(endDeg)),
      y: cy - rOut * Math.cos(toRad(endDeg))
    };
    const pInEnd = {
      x: cx + rIn * Math.sin(toRad(endDeg)),
      y: cy - rIn * Math.cos(toRad(endDeg))
    };
    const pInStart = {
      x: cx + rIn * Math.sin(toRad(startDeg)),
      y: cy - rIn * Math.cos(toRad(startDeg))
    };

    const d = `
      M ${pOutStart.x.toFixed(2)} ${pOutStart.y.toFixed(2)}
      A ${rOut} ${rOut} 0 0 1 ${pOutEnd.x.toFixed(2)} ${pOutEnd.y.toFixed(2)}
      L ${pInEnd.x.toFixed(2)} ${pInEnd.y.toFixed(2)}
      A ${rIn} ${rIn} 0 0 0 ${pInStart.x.toFixed(2)} ${pInStart.y.toFixed(2)}
      Z
    `;

    // Positions for Number, Icon, and Label
    const numPos = {
      x: cx + 86 * Math.sin(toRad(thetaDeg)),
      y: cy - 86 * Math.cos(toRad(thetaDeg))
    };

    const iconPos = {
      x: cx + 67 * Math.sin(toRad(thetaDeg)),
      y: cy - 67 * Math.cos(toRad(thetaDeg))
    };

    const labelPos = {
      x: cx + 49 * Math.sin(toRad(thetaDeg)),
      y: cy - 49 * Math.cos(toRad(thetaDeg))
    };

    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.setAttribute('class', 'cb-sector-group');
    group.setAttribute('data-action', this.action.id);
    group.setAttribute('data-num', this.action.num);

    // Path element
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', d);
    path.setAttribute('class', 'cb-sector');
    group.appendChild(path);

    // 1. Micro-number badge [1]..[8]
    const numText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    numText.setAttribute('x', numPos.x.toFixed(2));
    numText.setAttribute('y', numPos.y.toFixed(2));
    numText.setAttribute('class', 'cb-sector-num');
    numText.textContent = this.action.num;
    group.appendChild(numText);

    // 2. Icon foreignObject
    const foreign = document.createElementNS('http://www.w3.org/2000/svg', 'foreignObject');
    foreign.setAttribute('x', (iconPos.x - 9).toFixed(2));
    foreign.setAttribute('y', (iconPos.y - 9).toFixed(2));
    foreign.setAttribute('width', '18');
    foreign.setAttribute('height', '18');
    foreign.style.pointerEvents = 'none';

    const iconWrap = document.createElement('div');
    iconWrap.style.width = '100%';
    iconWrap.style.height = '100%';
    iconWrap.style.display = 'flex';
    iconWrap.style.alignItems = 'center';
    iconWrap.style.justifyContent = 'center';
    iconWrap.innerHTML = this.getIconSvg(this.action.icon);
    foreign.appendChild(iconWrap);
    group.appendChild(foreign);

    // 3. Short Sector Label
    const labelText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    labelText.setAttribute('x', labelPos.x.toFixed(2));
    labelText.setAttribute('y', labelPos.y.toFixed(2));
    labelText.setAttribute('class', 'cb-sector-label');
    labelText.textContent = this.action.name;
    group.appendChild(labelText);

    // Event listeners
    group.addEventListener('mouseenter', () => {
      this.onHover(this.action, true);
    });

    group.addEventListener('mouseleave', () => {
      this.onHover(this.action, false);
    });

    group.addEventListener('click', (e) => {
      e.stopPropagation();
      this.onSelect(this.action);
    });

    svgContainer.appendChild(group);
    this.element = group;
  }
}
