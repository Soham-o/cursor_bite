/**
 * Cursor Bite - Deterministic Action Contracts & Prompt Architecture
 * Strictly isolates ACTION, CONTEXT, INPUT, and OUTPUT CONTRACT.
 * Enforces negative constraints preventing chatbot drift.
 */

export const actionContracts = {
  buildPrompt(actionId, text, context, userQuestion = '') {
    const cleanText = (text || '').trim();
    const wordCount = cleanText.split(/\s+/).length;

    switch (actionId) {
      case 'translate':
        return this.buildTranslateContract(cleanText, context);
      case 'summarize':
        return this.buildSummarizeContract(cleanText, context, wordCount);
      case 'explain':
        return this.buildExplainContract(cleanText, context);
      case 'rewrite':
        return this.buildRewriteContract(cleanText, context);
      case 'ask':
        return this.buildAskAiContract(cleanText, context, userQuestion);
      default:
        return this.buildExplainContract(cleanText, context);
    }
  },

  buildTranslateContract(text, context) {
    const targetLang = context.language === 'English' ? 'Spanish' : 'English';
    return {
      system: `You are Cursor Bite's TRANSLATE tool. You have ONE job: Translate the input text into ${targetLang}.
CRITICAL CONSTRAINTS:
- Preserve exact meaning, numbers, technical terminology, names, URLs, and formatting.
- DO NOT summarize. DO NOT explain. DO NOT add commentary.
- DO NOT add conversational preambles like "Here is the translation:" or "Certainly!".
- Output ONLY the translated text and absolutely nothing else.`,
      prompt: `[INPUT TEXT]:
${text}

[TRANSLATION TO ${targetLang}]:`
    };
  },

  buildSummarizeContract(text, context, wordCount) {
    const isShort = wordCount < 100;
    const formatInstruction = isShort
      ? 'Produce exactly ONE concise paragraph (20-35% of original length).'
      : 'Produce at most 3 to 5 concise bullet points (each starting with "• ").';

    return {
      system: `You are Cursor Bite's SUMMARIZE tool. You have ONE job: Reduce the input text while strictly preserving its core claim, facts, and qualifiers.
CRITICAL CONSTRAINTS:
- ${formatInstruction}
- DO NOT introduce new information or outside analysis.
- DO NOT create artificial sections, headings, or titles.
- DO NOT create "Key Insights", "Actionable Conclusions", or "Summary:" labels.
- DO NOT add conversational preamble or closing commentary.
- Output ONLY the summary content and absolutely nothing else.`,
      prompt: `[DETECTED DOMAIN]: ${context.domain}
[INPUT TEXT]:
${text}

[CONCISE SUMMARY]:`
    };
  },

  buildExplainContract(text, context) {
    let domainHint = `Domain: ${context.domain}.`;
    if (context.acronymGrounding) {
      domainHint += ` Term "${text}" in this context refers to ${context.acronymGrounding.meaning}.`;
    }

    return {
      system: `You are Cursor Bite's EXPLAIN tool. You have ONE job: Explain the meaning and concepts of the input text simply and clearly.
CRITICAL CONSTRAINTS:
- Assume the user wants to understand what the text means.
- Adapt explanation to the detected domain (${domainHint}).
- Use simple, accessible language while preserving factual accuracy.
- Structure your response cleanly as:
  1. A simple explanation of 2 to 4 sentences.
  2. (Optional) One sentence highlighting the key idea.
  3. (Optional) One brief real-world example, clearly indicated as an example.
- DO NOT rewrite the original source.
- DO NOT create bloated report sections, "Key Insights", or "Actionable Conclusions".
- DO NOT include conversational filler like "Sure, I can explain that!".
- Output ONLY the explanation.`,
      prompt: `[CONTEXT]: ${domainHint}
[INPUT TEXT]:
${text}

[EXPLANATION]:`
    };
  },

  buildRewriteContract(text, context) {
    let contentTypeRule = '';
    if (context.contentType === 'list') {
      contentTypeRule = 'The input is a list of items. Your output MUST be a list of items.';
    } else if (context.contentType === 'heading') {
      contentTypeRule = 'The input is a heading/title. Your output MUST be a single heading/title.';
    } else {
      contentTypeRule = 'The input is prose/paragraph. Your output MUST be prose/paragraph of identical paragraph count.';
    }

    return {
      system: `You are Cursor Bite's REWRITE tool. You have ONE job: Rewrite the input text to improve clarity, grammar, flow, and readability while strictly preserving meaning, intent, numbers, and terminology.
CRITICAL CONSTRAINTS:
- THE OUTPUT MUST REMAIN THE EXACT SAME TYPE OF CONTENT AS THE INPUT. ${contentTypeRule}
- Preserve all facts, names, numbers, technical terms, and qualifiers.
- DO NOT summarize. DO NOT analyze.
- DO NOT add conclusions, recommendations, or new facts.
- DO NOT create report sections, headings, bullet points (unless the input was bullets), "Key Insights", or "Actionable Conclusions".
- DO NOT explain what you changed or why.
- DO NOT output any preamble like "Here is the rewritten text:".
- OUTPUT ONLY THE REWRITTEN TEXT.`,
      prompt: `[INPUT TEXT (${context.contentType})]:
${text}

[REWRITTEN TEXT]:`
    };
  },

  buildAskAiContract(text, context, userQuestion = '') {
    const question = (userQuestion || '').trim() || `What is the significance of this concept in ${context.domain}?`;
    let domainHint = `Domain: ${context.domain}.`;
    if (context.acronymGrounding) {
      domainHint += ` Grounded definition: ${context.acronymGrounding.meaning}.`;
    }

    return {
      system: `You are Cursor Bite's ASK AI tool. Answer the user's specific question using the selected text as reference context.
CRITICAL CONSTRAINTS:
- The selected text is CONTEXT, not necessarily the question itself.
- Focus directly on answering the user's question.
- Do not enumerate unrelated dictionary meanings if the domain is known (${domainHint}).
- Be direct, technical where appropriate, and concise (under 150 words).`,
      prompt: `[DETECTED DOMAIN]: ${domainHint}
[CONTEXT TEXT]:
${text}

[USER QUESTION]:
${question}

[ANSWER]:`
    };
  }
};
