/**
 * LoadingState Component
 * Displays subtle shimmer lines, lightweight spinner, and streaming cursor.
 */

export class LoadingState {
  static createHtml(label = 'Preparing local model…') {
    return `
      <div class="cb-loading-container">
        <div class="cb-loading-header">
          <div class="cb-loading-spinner"></div>
          <span>${label}</span>
        </div>
        <div class="cb-shimmer-line w-95"></div>
        <div class="cb-shimmer-line w-80"></div>
        <div class="cb-shimmer-line w-60"></div>
      </div>
    `;
  }
}
