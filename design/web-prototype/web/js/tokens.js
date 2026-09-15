/**
 * Cursor Bite - Action Definitions & Constants
 * Defines the 8 core actions, shortcuts, icons, and metadata.
 */

export const ACTIONS = [
  {
    id: 'translate',
    num: 1,
    name: 'Translate',
    shortDesc: 'Offline Neural Translation',
    icon: 'translate',
    color: '#818CF8',
    isLocal: true,
    angle: 0 // 12 o'clock
  },
  {
    id: 'summarize',
    num: 2,
    name: 'Summarize',
    shortDesc: 'Key Points with Local AI',
    icon: 'summarize',
    color: '#818CF8',
    isLocal: true,
    angle: 45 // 1:30
  },
  {
    id: 'explain',
    num: 3,
    name: 'Explain',
    shortDesc: 'Context-Aware Breakdown',
    icon: 'explain',
    color: '#FBBF24', // amber/warm lightbulb
    isLocal: true,
    angle: 90 // 3 o'clock
  },
  {
    id: 'search',
    num: 4,
    name: 'Search Web',
    shortDesc: 'DuckDuckGo Web Search',
    icon: 'search',
    color: '#38BDF8',
    isLocal: false,
    angle: 135 // 4:30
  },
  {
    id: 'ocr',
    num: 5,
    name: 'OCR Capture',
    shortDesc: 'Screen Region Sniper',
    icon: 'ocr',
    color: '#A5B4FC',
    isLocal: true,
    angle: 180 // 6 o'clock
  },
  {
    id: 'rewrite',
    num: 6,
    name: 'Rewrite',
    shortDesc: 'Precision Polish (Meaning Preserved)',
    icon: 'rewrite',
    color: '#818CF8',
    isLocal: true,
    angle: 225 // 7:30
  },
  {
    id: 'ask',
    num: 7,
    name: 'Ask AI',
    shortDesc: 'Contextual or Freeform Chat',
    icon: 'ask',
    color: '#818CF8',
    isLocal: true,
    angle: 270 // 9 o'clock
  },
  {
    id: 'settings',
    num: 8,
    name: 'Settings',
    shortDesc: 'Preferences & Local Models',
    icon: 'settings',
    color: '#94A3B8',
    isLocal: true,
    angle: 315 // 10:30
  }
];

export const RADIAL_CONFIG = {
  totalDiameter: 206,
  outerRadius: 98,
  innerRadius: 43,
  centerRadius: 21,
  iconRadius: 69,
  numberRadius: 87,
  labelRadius: 54
};
