/**
 * Cursor Bite - Output Validation & Sanitizer
 * Validates generated text against strict action contracts and provides
 * deterministic cleanup and single-shot correction prompts.
 */

const FORBIDDEN_SECTION_HEADERS = [
  /\bkey insights\b/i,
  /\bactionable conclusions?\b/i,
  /\bsummary\s*:/i,
  /\bconclusion\s*:/i,
  /\banalysis\s*:/i,
  /\btakeaways?\s*:/i,
  /###+\s*(Summary|Key Insights|Conclusions?|Overview|Analysis)/i
];

const CHATBOT_PREAMBLE_PATTERNS = [
  /^(sure thing|sure|certainly|here is|here's|here are|below is|as requested|as an ai)[^:\n]*[:\.\!\n]+/i,
  /^here is the (rewritten|translated|summary|explanation)[^:\n]*[:\.\!\n]+/i,
  /^i'd be happy to (rewrite|translate|summarize|explain)[^:\n]*[:\.\!\n]+/i,
  /^this (text|paragraph|code) (means|explains|shows):?\s*\n+/i
];

const CHATBOT_POSTAMBLE_PATTERNS = [
  /\n+(hope this helps|let me know if you (need|have)|feel free to ask).*$/i,
  /\n+note:\s*.*$/i
];

export const outputValidator = {
  // Deterministic sanitizer that strips conversational fluff
  sanitize(rawText = '') {
    let clean = (rawText || '').trim();

    // Strip leading conversational preambles
    for (const pattern of CHATBOT_PREAMBLE_PATTERNS) {
      clean = clean.replace(pattern, '').trim();
    }

    // Strip trailing conversational sign-offs
    for (const pattern of CHATBOT_POSTAMBLE_PATTERNS) {
      clean = clean.replace(pattern, '').trim();
    }

    // Strip wrapping quotes if entire text is quoted
    if (clean.startsWith('"') && clean.endsWith('"') && clean.indexOf('"', 1) === clean.length - 1) {
      clean = clean.slice(1, -1).trim();
    }

    return clean;
  },

  // Validate output against action contract rules
  validate(actionId, inputText = '', outputText = '', context = {}) {
    const cleanOutput = this.sanitize(outputText);
    const issues = [];

    // Rule 1: No forbidden analytical sections
    for (const forbidden of FORBIDDEN_SECTION_HEADERS) {
      if (forbidden.test(cleanOutput)) {
        issues.push(`Contains forbidden analytical heading (${forbidden})`);
      }
    }

    // Rule 2: Action-specific contract checks
    if (actionId === 'rewrite') {
      const inputIsBullets = /^(\-|\*|•|\d+\.)/m.test(inputText.trim());
      const outputIsBullets = /^(\-|\*|•|\d+\.)/m.test(cleanOutput);

      if (!inputIsBullets && outputIsBullets) {
        issues.push('Converted paragraph into bullet points');
      }

      if (cleanOutput.split('\n\n').length > inputText.split('\n\n').length + 1) {
        issues.push('Introduced extraneous sections or paragraphs');
      }
    }

    if (actionId === 'summarize') {
      const inputWords = inputText.trim().split(/\s+/).length;
      const outputWords = cleanOutput.split(/\s+/).length;

      if (inputWords > 40 && outputWords >= inputWords * 0.85) {
        issues.push('Output was not meaningfully compressed');
      }
    }

    if (actionId === 'translate') {
      if (/here is the translation/i.test(outputText) || /translated text:/i.test(outputText)) {
        issues.push('Contains meta-commentary');
      }
    }

    return {
      isValid: issues.length === 0,
      issues,
      sanitizedOutput: cleanOutput
    };
  },

  // Build single correction prompt if initial response failed validation
  buildCorrectionPrompt(actionId, issues, originalPrompt, inputText) {
    const issueList = issues.join(', ');
    return `[CRITICAL CORRECTION REQUIRED]
Your previous response violated the strict Cursor Bite ${actionId.toUpperCase()} tool contract:
Issues detected: ${issueList}.

STRICT RULES FOR RE-GENERATION:
- Output ONLY the raw ${actionId.toUpperCase()} content.
- DO NOT generate headings like "Key Insights", "Actionable Conclusions", or "Summary:".
- DO NOT add commentary, analysis, or conversational preamble.
- Preserve the exact content type of the input.

${originalPrompt}`;
  }
};
