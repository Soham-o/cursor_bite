/**
 * PrivacyIndicator Component
 * Subtle, non-intrusive status badge for Local-first, Offline, Protected, or External status.
 */

export class PrivacyIndicator {
  static createHtml(type = 'local') {
    if (type === 'external') {
      return `
        <span class="cb-privacy-badge privacy-external" title="External search via DuckDuckGo (zero personal data sent)">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
            <polyline points="15 3 21 3 21 9"></polyline>
            <line x1="10" y1="14" x2="21" y2="3"></line>
          </svg>
          External
        </span>
      `;
    }

    if (type === 'protected') {
      return `
        <span class="cb-privacy-badge privacy-protected" title="Local regex filter: Sensitive credentials sanitized">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
          </svg>
          Protected
        </span>
      `;
    }

    return `
      <span class="cb-privacy-badge" title="Local-First: Processing entirely on your device with Ollama">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
        Local
      </span>
    `;
  }
}
