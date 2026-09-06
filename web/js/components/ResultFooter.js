/**
 * ResultFooter Component
 * Displays copy button with animated feedback, 'Esc to close' hint, and latency / status indicator.
 */

import { StatusIndicator } from './StatusIndicator.js';

export class ResultFooter {
  constructor(onCopy) {
    this.onCopy = onCopy;
    this.statusIndicator = new StatusIndicator('success');
    this.element = null;
    this.render();
  }

  render() {
    this.element = document.createElement('div');
    this.element.className = 'cb-result-footer';

    this.element.innerHTML = `
      <button class="cb-copy-btn" id="cb-copy-btn" title="Copy to clipboard">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        <span class="cb-copy-label">Copy</span>
      </button>
      <div class="cb-footer-meta">
        <span class="cb-esc-hint">Esc to close</span>
        <div class="cb-latency-indicator">
          <span class="cb-latency-text">1.2s</span>
          <span class="cb-status-slot"></span>
        </div>
      </div>
    `;

    const statusSlot = this.element.querySelector('.cb-status-slot');
    statusSlot.appendChild(this.statusIndicator.getElement());

    const copyBtn = this.element.querySelector('#cb-copy-btn');
    copyBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.triggerCopyAnimation();
      if (this.onCopy) {
        this.onCopy();
      }
    });
  }

  triggerCopyAnimation() {
    const copyBtn = this.element.querySelector('#cb-copy-btn');
    const label = this.element.querySelector('.cb-copy-label');
    copyBtn.classList.add('cb-copied');
    label.textContent = 'Copied!';

    setTimeout(() => {
      copyBtn.classList.remove('cb-copied');
      label.textContent = 'Copy';
    }, 1800);
  }

  updateLatency(latency = '1.2s', status = 'success') {
    const latencyText = this.element.querySelector('.cb-latency-text');
    if (latencyText) {
      latencyText.textContent = latency;
    }
    this.statusIndicator.update(status);
  }

  getElement() {
    return this.element;
  }
}
