/**
 * RadialMenu Component
 * Compact 180-220px 8-sector radial HUD with glowing interaction core.
 * Cursor-relative positioning, smart boundary detection, keyboard 1-8 navigation.
 */

import { ACTIONS, RADIAL_CONFIG } from '../tokens.js';
import { RadialCenter } from './RadialCenter.js';
import { RadialMenuItem } from './RadialMenuItem.js';
import { ActionTooltip } from './ActionTooltip.js';
import { audioService } from '../services/audioService.js';

export class RadialMenu {
  constructor(container, onActionSelected, onClose) {
    this.container = container;
    this.onActionSelected = onActionSelected;
    this.onClose = onClose;
    
    this.element = null;
    this.svgElement = null;
    this.items = [];
    this.tooltip = null;
    this.centerCore = null;
    this.isOpen = false;
    this.focusedIndex = -1;

    this.render();
  }

  render() {
    this.element = document.createElement('div');
    this.element.className = 'cb-radial-container';
    this.element.id = 'cb-radial-menu';
    this.element.setAttribute('role', 'menu');
    this.element.setAttribute('aria-label', 'Cursor Bite Radial Actions');

    // SVG Element for HUD background and sectors
    this.svgElement = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    this.svgElement.setAttribute('class', 'cb-radial-svg');
    this.svgElement.setAttribute('viewBox', `0 0 ${RADIAL_CONFIG.totalDiameter} ${RADIAL_CONFIG.totalDiameter}`);

    // Outer HUD frame circle
    const outerCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    outerCircle.setAttribute('cx', (RADIAL_CONFIG.totalDiameter / 2).toString());
    outerCircle.setAttribute('cy', (RADIAL_CONFIG.totalDiameter / 2).toString());
    outerCircle.setAttribute('r', RADIAL_CONFIG.outerRadius.toString());
    outerCircle.setAttribute('class', 'cb-hud-outer-ring');
    this.svgElement.appendChild(outerCircle);

    // Build the 8 sectors
    ACTIONS.forEach((action) => {
      const item = new RadialMenuItem(
        action,
        (act) => this.selectAction(act),
        (act, isHovered) => this.handleHover(act, isHovered)
      );
      item.render(this.svgElement);
      this.items.push(item);
    });

    this.element.appendChild(this.svgElement);

    // Glowing Center Core (NO cursor icon!)
    this.centerCore = new RadialCenter(this.element);

    // Dynamic Action Tooltip
    this.tooltip = new ActionTooltip(this.element);

    this.container.appendChild(this.element);
  }

  open(x, y) {
    const halfSize = RADIAL_CONFIG.totalDiameter / 2 + 10;
    const pad = 16;
    const winW = window.innerWidth;
    const winH = window.innerHeight;

    // Smart screen boundary collision avoidance
    let posX = Math.max(halfSize + pad, Math.min(x, winW - halfSize - pad));
    let posY = Math.max(halfSize + pad, Math.min(y, winH - halfSize - pad));

    this.element.style.left = `${posX}px`;
    this.element.style.top = `${posY}px`;

    this.element.classList.remove('cb-closing');
    this.element.classList.add('cb-visible');
    this.isOpen = true;
    this.focusedIndex = -1;

    audioService.playHover();
  }

  close() {
    if (!this.isOpen) return;
    this.element.classList.remove('cb-visible');
    this.element.classList.add('cb-closing');
    this.isOpen = false;
    this.tooltip.hide();
    this.clearFocus();
    
    if (this.onClose) {
      this.onClose();
    }
  }

  handleHover(action, isHovered) {
    if (isHovered) {
      this.element.classList.add('has-hovered-sector');
      this.tooltip.show(action);
      audioService.playHover();
    } else {
      this.element.classList.remove('has-hovered-sector');
      this.tooltip.hide();
    }
  }

  selectAction(action) {
    audioService.playSelect();
    this.close();
    if (this.onActionSelected) {
      this.onActionSelected(action);
    }
  }

  selectByNumber(num) {
    const action = ACTIONS.find(a => a.num === num);
    if (action) {
      this.selectAction(action);
    }
  }

  clearFocus() {
    this.items.forEach(item => {
      if (item.element) {
        item.element.classList.remove('cb-focused');
      }
    });
  }

  getPosition() {
    const rect = this.element.getBoundingClientRect();
    return {
      x: rect.left + rect.width / 2,
      y: rect.top + rect.height / 2,
      right: rect.right,
      bottom: rect.bottom,
      top: rect.top,
      left: rect.left
    };
  }
}
