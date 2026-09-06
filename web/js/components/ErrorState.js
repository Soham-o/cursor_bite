/**
 * ErrorState Component
 * Actionable error UI explaining:
 * 1. WHAT happened
 * 2. WHY it happened
 * 3. WHAT the user can do
 */

export class ErrorState {
  static createHtml({ title, message, actionBtn = 'Open Settings' }) {
    return `
      <div class="cb-error-card">
        <div class="cb-error-title-row">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <span>${title}</span>
        </div>
        <p class="cb-error-desc">${message}</p>
        <button class="cb-error-action-btn" id="cb-error-action-btn">${actionBtn}</button>
      </div>
    `;
  }
}
