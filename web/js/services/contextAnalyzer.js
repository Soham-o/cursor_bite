/**
 * Cursor Bite - Context Intelligence Analyzer
 * Microsecond local deterministic context analyzer.
 * Infers:
 *   1. Language & Script
 *   2. Domain (ai_ml, programming, business, science, legal, general)
 *   3. Content Type (paragraph, heading, code, error_message, list, short_phrase, question)
 *   4. Grounded Acronyms (e.g. RAG -> Retrieval-Augmented Generation in AI context)
 */

export const GROUNDED_ACRONYMS = {
  'RAG': { meaning: 'Retrieval-Augmented Generation (AI / LLMs)', domain: 'ai_ml' },
  'LLM': { meaning: 'Large Language Model (AI / Deep Learning)', domain: 'ai_ml' },
  'AST': { meaning: 'Abstract Syntax Tree (Compilers / Parsing)', domain: 'programming' },
  'DOM': { meaning: 'Document Object Model (Web / Browser)', domain: 'programming' },
  'CRUD': { meaning: 'Create, Read, Update, Delete (Database / APIs)', domain: 'programming' },
  'JWT': { meaning: 'JSON Web Token (Authentication & Security)', domain: 'programming' },
  'REST': { meaning: 'Representational State Transfer (Web Services)', domain: 'programming' },
  'CI/CD': { meaning: 'Continuous Integration / Continuous Deployment (DevOps)', domain: 'programming' },
  'API': { meaning: 'Application Programming Interface', domain: 'programming' },
  'SDK': { meaning: 'Software Development Kit', domain: 'programming' },
  'HWND': { meaning: 'Handle to a Window (Win32 Architecture)', domain: 'programming' },
  'UAC': { meaning: 'User Account Control (Windows Security)', domain: 'programming' },
  'DPI': { meaning: 'Dots Per Inch / Display Scaling', domain: 'programming' },
  'ORM': { meaning: 'Object-Relational Mapping (Databases)', domain: 'programming' },
  'SQL': { meaning: 'Structured Query Language (Databases)', domain: 'programming' },
  'GPU': { meaning: 'Graphics Processing Unit (Hardware / Compute)', domain: 'programming' },
  'TPU': { meaning: 'Tensor Processing Unit (AI Hardware)', domain: 'ai_ml' },
  'VRAM': { meaning: 'Video Random Access Memory', domain: 'programming' },
  'ROI': { meaning: 'Return on Investment (Finance / Business)', domain: 'business' },
  'KPI': { meaning: 'Key Performance Indicator (Management)', domain: 'business' },
  'GDPR': { meaning: 'General Data Protection Regulation (Privacy)', domain: 'legal' }
};

const CODE_PATTERNS = [
  /\bdef\s+\w+\s*\(/,
  /\bclass\s+\w+/,
  /\bfunction\s+\w*\s*\(/,
  /\bimport\s+[\w\.]+/,
  /\bfrom\s+[\w\.]+\s+import\b/,
  /\b(const|let|var)\s+\w+\s*=/,
  /\breturn\s+[^;]+[;\n]/,
  /\b(console\.log|print|printf)\s*\(/,
  /=>|\->/,
  /[{};]\s*$/,
  /\b(SELECT|FROM|WHERE|INSERT|UPDATE|DELETE)\b.*\b(FROM|INTO|TABLE|SET)\b/i
];

const ERROR_PATTERNS = [
  /Traceback \(most recent call last\):/i,
  /\b(Error|Exception|Fault|Panic):\s/i,
  /\bat\s+[\w\.<>]+\s*\([^)]+:\d+:\d+\)/,
  /\b(SyntaxError|TypeError|ValueError|KeyError|IndexError|AttributeError|NameError)\b/,
  /\bNullPointerException|Segmentation fault|Access violation\b/i,
  /\bfailed with exit code \d+\b/i,
  /\bHTTP (400|401|403|404|500|502|503)\b/
];

const AI_KEYWORDS = new Set([
  'model', 'models', 'llm', 'llms', 'harness', 'agent', 'agents', 'prompt',
  'embedding', 'embeddings', 'vector', 'rag', 'inference', 'tokens', 'neural',
  'transformer', 'fine-tuning', 'hallucination', 'context window', 'ollama',
  'deepseek', 'gpt', 'llama', 'dataset', 'weights', 'loss', 'training'
]);

const PROGRAMMING_KEYWORDS = new Set([
  'async', 'await', 'promise', 'callback', 'pointer', 'memory', 'thread',
  'mutex', 'coroutine', 'process', 'socket', 'pipeline', 'backend', 'frontend',
  'database', 'postgres', 'redis', 'compiler', 'runtime', 'stack', 'heap'
]);

const BUSINESS_KEYWORDS = new Set([
  'revenue', 'margin', 'ebitda', 'roi', 'kpi', 'churn', 'cac', 'ltv', 'customer',
  'acquisition', 'conversion', 'quarterly', 'growth', 'market', 'pricing'
]);

export const contextAnalyzer = {
  analyze(text = '', surroundingContext = '') {
    const clean = text.trim();
    if (!clean) {
      return {
        language: 'English',
        domain: 'general',
        contentType: 'short_phrase',
        likelyIntent: 'explain',
        acronymGrounding: null,
        confidence: 0.5
      };
    }

    // 1. Language Detection
    const language = this.detectLanguage(clean);

    // 2. Grounded Acronym Check
    const upperText = clean.replace(/[^A-Za-z0-9\/]/g, '').toUpperCase();
    let acronymGrounding = GROUNDED_ACRONYMS[upperText] || null;

    // 3. Content Type Detection
    const contentType = this.detectContentType(clean);

    // 4. Domain Detection
    const domain = this.detectDomain(clean, surroundingContext, acronymGrounding);

    // 5. Likely Intent
    let likelyIntent = 'explain';
    if (contentType === 'error_message' || contentType === 'code') {
      likelyIntent = 'explain';
    } else if (clean.length > 250) {
      likelyIntent = 'summarize';
    } else if (clean.endsWith('?')) {
      likelyIntent = 'ask';
    }

    return {
      language,
      domain,
      contentType,
      likelyIntent,
      acronymGrounding,
      confidence: 0.9
    };
  },

  detectLanguage(text) {
    // Check Devanagari script (Hindi, Marathi, etc.)
    if (/[\u0900-\u097F]/.test(text)) return 'Hindi';
    // Check CJK
    if (/[\u4E00-\u9FFF]/.test(text)) return 'Chinese';
    if (/[\u3040-\u30FF]/.test(text)) return 'Japanese';
    // Check Cyrillic
    if (/[\u0400-\u04FF]/.test(text)) return 'Russian';
    // Check Arabic
    if (/[\u0600-\u06FF]/.test(text)) return 'Arabic';
    // Check Spanish marks
    if (/[áéíóúüñ¿¡]/i.test(text)) return 'Spanish';
    // Check French marks
    if (/[àâçèéêëîïôûù]/i.test(text)) return 'French';
    return 'English';
  },

  detectContentType(text) {
    if (ERROR_PATTERNS.some(p => p.test(text))) {
      return 'error_message';
    }
    if (CODE_PATTERNS.some(p => p.test(text))) {
      return 'code';
    }
    if (text.endsWith('?') && text.length < 120) {
      return 'question';
    }
    if (/^(\d+\.|\-|\*|•)\s+/m.test(text) && text.split('\n').filter(l => l.trim()).length > 1) {
      return 'list';
    }
    if (text.split(/\s+/).length <= 4 && !text.includes('.')) {
      return 'short_phrase';
    }
    if (text.split(/\s+/).length <= 10 && text.split('\n').length === 1 && !text.endsWith('.')) {
      return 'heading';
    }
    return 'paragraph';
  },

  detectDomain(text, surroundingContext = '', acronym = null) {
    if (acronym) return acronym.domain;

    const lower = (text + ' ' + surroundingContext).toLowerCase();
    const words = lower.split(/[\s\W]+/);

    let aiHits = 0;
    let progHits = 0;
    let bizHits = 0;

    for (const w of words) {
      if (AI_KEYWORDS.has(w)) aiHits++;
      if (PROGRAMMING_KEYWORDS.has(w)) progHits++;
      if (BUSINESS_KEYWORDS.has(w)) bizHits++;
    }

    if (aiHits > progHits && aiHits > bizHits && aiHits >= 1) return 'ai_ml';
    if (progHits >= 1) return 'programming';
    if (bizHits >= 1) return 'business';

    return 'general';
  }
};
