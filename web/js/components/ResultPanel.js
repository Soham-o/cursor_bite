/**
 * ResultPanel Component
 * Compact floating dark charcoal result card positioned beside cursor/radial HUD.
 * Integrates ResultHeader, ResultContent, ResultFooter, and drag interactions.
 */

import { ResultHeader } from './ResultHeader.js';
import { ResultContent } from './ResultContent.js';
import { ResultFooter } from './ResultFooter.js';

export class ResultPanel {
  constructor(container, onPinToggle, onClose, onSettingChange) {
    this.container = container;
    this.onPinToggle = onPinToggle;
    this.onClose = onClose;
    this.onSettingChange = onSettingChange;

    this.element = null;
    this.header = null;
    this.content = null;
    this.footer = null;
    this.isOpen = false;
    this.isPinned = false;
    this.currentTextToCopy = '';

    this.render();
    this.setupDraggable();
  }

  render() {
    this.element = document.createElement('div');
    this.element.className = 'cb-result-panel';
    this.element.id = 'cb-result-panel';
    this.element.setAttribute('role', 'dialog');
    this.element.setAttribute('aria-label', 'Cursor Bite Result');

    // Header
    this.header = new ResultHeader(
      { id: 'explain', name: 'Explain' },
      this.isPinned,
      (pinned) => this.handlePinToggle(pinned),
      () => this.close()
    );
    this.element.appendChild(this.header.getElement());

    // Content
    this.content = new ResultContent();
    this.element.appendChild(this.content.getElement());

    // Footer
    this.footer = new ResultFooter(() => this.copyCurrentText());
    this.element.appendChild(this.footer.getElement());

    // Wire Ask AI follow-up query handler
    this.content.onAskFollowUp = (userQuestion) => {
      import('../services/actionService.js').then(({ actionService }) => {
        this.content.showLoading('Analyzing question…');
        this.footer.updateLatency('...', 'working');
        actionService.streamAction(
          'ask',
          this.currentSelectedText || '',
          (tokenText) => this.content.updateStream(tokenText),
          (finalData) => {
            this.content.renderResult(finalData, this.onSettingChange);
            this.footer.updateLatency(finalData.latency || '1.0s', 'success');
            this.updateCopyBuffer(finalData);
          },
          (err) => {
            this.content.showError({ title: 'Error', message: err.message });
          },
          userQuestion
        );
      });
    };

    this.container.appendChild(this.element);
  }

  handlePinToggle(pinned) {
    this.isPinned = pinned;
    this.element.classList.toggle('cb-pinned', pinned);
    if (this.onPinToggle) {
      this.onPinToggle(pinned);
    }
  }

  openBeside(hudRect, action, selectedText, initialData = null) {
    this.header.updateAction(action);
    this.isOpen = true;

    // Intelligent placement beside the radial HUD
    const winW = window.innerWidth;
    const winH = window.innerHeight;
    const panelW = 345;
    const panelH = 340;
    const gap = 16;

    let posX = hudRect.right + gap;
    let posY = Math.min(hudRect.top - 10, winH - panelH - 16);

    // If overflowing right edge, position to the left of HUD
    if (posX + panelW > winW - 16) {
      posX = Math.max(16, hudRect.left - panelW - gap);
    }

    // Boundary guards
    if (posY < 16) posY = 16;
    if (posX < 16) posX = 16;

    this.element.style.left = `${posX}px`;
    this.element.style.top = `${posY}px`;

    this.element.classList.remove('cb-closing');
    this.element.classList.add('cb-visible');

    this.currentSelectedText = selectedText;

    // If initial static data is supplied (for instant initial showcase)
    if (initialData) {
      this.content.renderResult(initialData, this.onSettingChange);
      this.footer.updateLatency(initialData.latency || '1.2s', 'success');
      this.updateCopyBuffer(initialData);
      return;
    }

    // Otherwise, perform REAL-TIME streaming
    this.content.showLoading(`Running ${action.name} with local llama3.2…`);
    this.footer.updateLatency('...', 'working');

    import('../services/actionService.js').then(({ actionService }) => {
      actionService.streamAction(
        action.id,
        selectedText,
        (tokenText) => {
          this.content.updateStream(tokenText);
        },
        (finalData) => {
          this.content.renderResult(finalData, this.onSettingChange);
          this.footer.updateLatency(finalData.latency || '1.0s', finalData.type === 'error' ? 'failed' : 'success');
          this.updateCopyBuffer(finalData);
        },
        (err) => {
          this.content.showError({
            title: 'Model Error',
            message: err.message || 'Could not complete local generation.'
          });
          this.footer.updateLatency('err', 'failed');
        }
      );
    });
  }

  updateCopyBuffer(data) {
    if (data.type === 'rewrite_pure') {
      this.currentTextToCopy = data.rewrittenText;
    } else if (data.type === 'paragraph_summary') {
      this.currentTextToCopy = data.text;
    } else if (data.type === 'explain') {
      this.currentTextToCopy = data.quote ? `${data.p1}\n\n${data.p2}\n\n"${data.quote}"` : `${data.p1}\n\n${data.p2}`;
    } else if (data.type === 'translate') {
      this.currentTextToCopy = data.translatedText;
    } else if (data.type === 'bullets') {
      this.currentTextToCopy = data.bullets.join('\n• ');
    } else if (data.type === 'ocr') {
      this.currentTextToCopy = data.extractedText;
    } else if (data.type === 'ask') {
      this.currentTextToCopy = data.response;
    } else {
      this.currentTextToCopy = 'Cursor Bite result';
    }
  }

  copyCurrentText() {
    if (navigator.clipboard && this.currentTextToCopy) {
      navigator.clipboard.writeText(this.currentTextToCopy).catch(() => {});
    }
  }

  close() {
    if (this.isPinned) return; // Ignore close if pinned
    if (!this.isOpen) return;

    this.element.classList.remove('cb-visible');
    this.element.classList.add('cb-closing');
    this.isOpen = false;

    if (this.onClose) {
      this.onClose();
    }
  }

  forceClose() {
    this.isPinned = false;
    this.element.classList.remove('cb-pinned');
    this.element.classList.remove('cb-visible');
    this.element.classList.add('cb-closing');
    this.isOpen = false;
  }

  setupDraggable() {
    const headerEl = this.header.getElement();
    let isDragging = false;
    let startX, startY, origX, origY;

    headerEl.addEventListener('mousedown', (e) => {
      if (e.target.closest('button')) return;
      isDragging = true;
      startX = e.clientX;
      startY = e.clientY;
      const rect = this.element.getBoundingClientRect();
      origX = rect.left;
      origY = rect.top;

      const onMouseMove = (moveEvent) => {
        if (!isDragging) return;
        const dx = moveEvent.clientX - startX;
        const dy = moveEvent.clientY - startY;
        this.element.style.left = `${origX + dx}px`;
        this.element.style.top = `${origY + dy}px`;
      };

      const onMouseUp = () => {
        isDragging = false;
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
      };

      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onMouseUp);
    });
  }
}
