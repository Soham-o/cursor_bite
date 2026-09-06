/**
 * StatusIndicator Component
 * Renders status dot: working (amber pulsing), successful (green), failed (red).
 */

export class StatusIndicator {
  constructor(status = 'success') {
    this.status = status;
    this.element = document.createElement('span');
    this.element.className = 'cb-status-dot';
    this.update(status);
  }

  update(status) {
    this.status = status;
    this.element.className = 'cb-status-dot';
    if (status === 'working') {
      this.element.classList.add('status-working');
    } else if (status === 'failed') {
      this.element.classList.add('status-failed');
    }
  }

  getElement() {
    return this.element;
  }
}
