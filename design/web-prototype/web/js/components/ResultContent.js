/**
 * ResultContent Component - Strict Action Contract Renderer
 * Renders pure tool output:
 *   - REWRITE: Pure rewritten content matching input type (zero analytical headings)
 *   - SUMMARIZE: 1 concise paragraph or 3-5 bullets (no artificial sections)
 *   - EXPLAIN: 2-4 sentences + key idea + example
 *   - TRANSLATE: Pure translation without commentary
 *   - ASK AI: Contextual answer with interactive follow-up question input
 *   - SEARCH WEB: DuckDuckGo results with explicit error/empty/success statuses
 */

import { LoadingState } from './LoadingState.js';
import { ErrorState } from './ErrorState.js';

export class ResultContent {
  constructor() {
    this.element = document.createElement('div');
    this.element.className = 'cb-result-content';
    this.streamInterval = null;
    this.onAskFollowUp = null;
  }

  showLoading(message = 'Preparing local tool…') {
    this.stopStreaming();
    this.element.innerHTML = LoadingState.createHtml(message);
  }

  updateStream(text) {
    const formatted = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>');

    this.element.innerHTML = `
      <div style="color: #F1F5F9; font-size: 13px; line-height: 1.5;">
        <p>${formatted}<span class="cb-streaming-cursor"></span></p>
      </div>
    `;
    this.element.scrollTop = this.element.scrollHeight;
  }

  showError(errorData, onActionClick) {
    this.stopStreaming();
    this.element.innerHTML = ErrorState.createHtml(errorData);
    const actionBtn = this.element.querySelector('#cb-error-action-btn');
    if (actionBtn && onActionClick) {
      actionBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        onActionClick();
      });
    }
  }

  renderResult(data, onSettingChange) {
    this.stopStreaming();

    if (data.type === 'error') {
      this.showError(data);
      return;
    }

    const domainBadge = data.context?.domain 
      ? `<span class="cb-privacy-badge" style="font-size: 10px; margin-bottom: 6px;">Domain: ${data.context.domain.toUpperCase()}</span>` 
      : '';

    // 1. REWRITE (Deterministic tool output: pure rewritten content ONLY)
    if (data.type === 'rewrite_pure') {
      this.element.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 11px; color: #94A3B8; font-weight: 500;">Rewritten Text (${data.originalType || 'Prose'})</span>
          ${domainBadge}
        </div>
        <p style="font-size: 13.5px; line-height: 1.55; color: #F8FAFC; white-space: pre-wrap;">${data.rewrittenText}</p>
      `;
      return;
    }

    // 2. SUMMARIZE: Single Concise Paragraph
    if (data.type === 'paragraph_summary') {
      this.element.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 11px; color: #94A3B8; font-weight: 500;">Concise Summary</span>
          ${domainBadge}
        </div>
        <p style="font-size: 13px; line-height: 1.5; color: #F1F5F9;">${data.text}</p>
      `;
      return;
    }

    // 3. SUMMARIZE: Concise Bullets
    if (data.type === 'bullets') {
      const bulletsHtml = data.bullets
        .map(b => `
          <li class="cb-bullet-item">
            <div class="cb-bullet-dot"></div>
            <span>${b}</span>
          </li>
        `)
        .join('');

      this.element.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 11px; color: #94A3B8; font-weight: 500;">${data.intro || 'Summary'}</span>
          ${domainBadge}
        </div>
        <ul class="cb-bullet-list">
          ${bulletsHtml}
        </ul>
      `;
      return;
    }

    // 4. EXPLAIN: Simple explanation + key idea + quote
    if (data.type === 'explain') {
      const quoteHtml = data.quote 
        ? `<div class="cb-callout-quote">"${data.quote}"</div>` 
        : '';

      this.element.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 11px; color: #94A3B8; font-weight: 500;">Explanation</span>
          ${domainBadge}
        </div>
        <p style="font-size: 13px; line-height: 1.5; color: #E2E8F0;">${data.p1}</p>
        ${data.p2 ? `<p style="font-size: 13px; line-height: 1.5; color: #CBD5E1;">${data.p2}</p>` : ''}
        ${quoteHtml}
      `;
      return;
    }

    // 5. TRANSLATE: Pure Translation output ONLY
    if (data.type === 'translate') {
      this.element.innerHTML = `
        <div style="display: flex; justify-content: space-between; font-size: 11px; color: #94A3B8; margin-bottom: 2px;">
          <span>${data.sourceLang}</span>
          <span style="color: var(--accent-purple-light); font-weight: 600;">→ ${data.targetLang}</span>
        </div>
        <p style="line-height: 1.55; color: #F8FAFC; font-size: 13.5px;">${data.translatedText}</p>
      `;
      return;
    }

    // 6. ASK AI: Freeform Contextual Q&A + Interactive follow-up input
    if (data.type === 'ask') {
      this.element.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 11px; color: #94A3B8; font-weight: 500;">Contextual Answer</span>
          ${domainBadge}
        </div>
        <p style="font-size: 13px; line-height: 1.5; color: #F1F5F9;">${data.response}</p>
        
        <!-- Interactive Follow-up Query Row -->
        <div style="margin-top: 10px; display: flex; gap: 6px;">
          <input type="text" id="cb-ask-followup-input" placeholder="Ask follow-up about selection..." 
            style="flex: 1; background: var(--cb-panel-surface-elevated); border: 1px solid rgba(255,255,255,0.12); border-radius: 4px; padding: 4px 8px; font-size: 11.5px; color: #F1F5F9; outline: none;">
          <button id="cb-ask-followup-btn" style="background: var(--accent-purple); color: #fff; border: none; border-radius: 4px; padding: 0 10px; font-size: 11px; cursor: pointer; font-weight: 600;">Ask</button>
        </div>
      `;

      const input = this.element.querySelector('#cb-ask-followup-input');
      const btn = this.element.querySelector('#cb-ask-followup-btn');
      const submitFollowUp = () => {
        const q = input.value.trim();
        if (q && this.onAskFollowUp) {
          this.onAskFollowUp(q);
        }
      };

      btn.addEventListener('click', submitFollowUp);
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') submitFollowUp();
      });
      return;
    }

    // 7. SEARCH WEB: Explicit status handling
    if (data.type === 'search') {
      if (data.status === 'empty') {
        this.element.innerHTML = `
          <div style="display: flex; justify-content: space-between; font-size: 11px; color: #94A3B8;">
            <span>DuckDuckGo Web Search</span>
            <span class="cb-privacy-badge privacy-external">0 Results</span>
          </div>
          <p style="font-size: 12.5px; color: #94A3B8; padding: 8px 0;">No web search results found for query: <em>"${data.query}"</em></p>
        `;
        return;
      }

      if (data.status === 'provider_failure' || data.status === 'timeout' || data.status === 'network_unavailable') {
        this.element.innerHTML = `
          <div class="cb-error-card">
            <div class="cb-error-title-row">
              <span>Web Search Error (${data.status.toUpperCase()})</span>
            </div>
            <p class="cb-error-desc">${data.errorMessage || 'Unable to connect to DuckDuckGo search service.'}</p>
          </div>
        `;
        return;
      }

      // Success
      const resultsHtml = (data.results || [])
        .map(r => `
          <div class="cb-search-item">
            <a href="${r.url}" target="_blank" rel="noopener noreferrer" class="cb-search-title">${r.title}</a>
            <span class="cb-search-snippet">${r.snippet}</span>
          </div>
        `)
        .join('');

      this.element.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; font-size: 11px; color: #94A3B8; margin-bottom: 4px;">
          <span>DuckDuckGo: "${data.query}"</span>
          <span class="cb-privacy-badge privacy-external">${data.results?.length || 0} Results</span>
        </div>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          ${resultsHtml}
        </div>
      `;
      return;
    }

    // 8. OCR Capture
    if (data.type === 'ocr') {
      this.element.innerHTML = `
        <div style="display: flex; justify-content: space-between; font-size: 11px; color: #94A3B8; margin-bottom: 4px;">
          <span>${data.source}</span>
          <span class="cb-privacy-badge">Confidence: ${data.confidence}</span>
        </div>
        <div class="cb-callout-quote" style="border-left-color: var(--accent-blue);">
          ${data.extractedText}
        </div>
      `;
      return;
    }

    // 9. SETTINGS
    if (data.type === 'settings') {
      this.element.innerHTML = `
        <div class="cb-settings-row">
          <span class="cb-settings-label">Active AI Engine</span>
          <span class="cb-settings-value">${data.model}</span>
        </div>
        <div class="cb-settings-row">
          <span class="cb-settings-label">Action Contract Enforcement</span>
          <span class="cb-settings-value">Strict Deterministic Mode</span>
        </div>
        <div class="cb-settings-row">
          <span class="cb-settings-label">Output Validation</span>
          <span class="cb-settings-value">Single-Shot Correction (Active)</span>
        </div>
        <div class="cb-settings-row">
          <span class="cb-settings-label">Simulate Missing Pack</span>
          <button class="cb-btn-bg" id="cb-toggle-error-demo" style="border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; padding: 2px 8px; font-size: 11px; color: #E2E8F0; cursor: pointer;">
            Test Error State
          </button>
        </div>
      `;

      const toggleErrorBtn = this.element.querySelector('#cb-toggle-error-demo');
      if (toggleErrorBtn && onSettingChange) {
        toggleErrorBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          onSettingChange('toggleError');
        });
      }
      return;
    }
  }

  stopStreaming() {
    if (this.streamInterval) {
      clearInterval(this.streamInterval);
      this.streamInterval = null;
    }
  }

  getElement() {
    return this.element;
  }
}
