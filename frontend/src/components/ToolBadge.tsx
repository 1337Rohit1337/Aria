import React, { useState } from 'react';

export type ToolType = 'web_search' | 'wikipedia' | 'weather' | 'calculator' | 'save_note' | 'search_notes' | 'summarize' | string;

interface ToolBadgeProps {
  name: ToolType;
  status?: 'running' | 'success' | 'failed';
  input?: any;
  output?: string;
}

const toolConfig: Record<string, { label: string; icon: JSX.Element; color: string; darkColor: string }> = {
  web_search: {
    label: 'Web Search',
    color: 'bg-blue-50 text-blue-700 border-blue-200',
    darkColor: 'dark:bg-blue-950/50 dark:text-blue-300 dark:border-blue-800',
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/><path d="M2 12h20"/>
      </svg>
    )
  },
  wikipedia: {
    label: 'Wikipedia',
    color: 'bg-zinc-100 text-zinc-700 border-zinc-300',
    darkColor: 'dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700',
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/><path d="M6 6h10M6 10h10"/>
      </svg>
    )
  },
  weather: {
    label: 'Weather',
    color: 'bg-amber-50 text-amber-700 border-amber-200',
    darkColor: 'dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800',
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
      </svg>
    )
  },
  calculator: {
    label: 'Calculator',
    color: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    darkColor: 'dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800',
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <line x1="4" x2="20" y1="9" y2="9"/><line x1="4" x2="20" y1="15" y2="15"/><line x1="10" x2="8" y1="3" y2="21"/><line x1="16" x2="14" y1="3" y2="21"/>
      </svg>
    )
  },
  save_note: {
    label: 'Save Note',
    color: 'bg-purple-50 text-purple-700 border-purple-200',
    darkColor: 'dark:bg-purple-950/50 dark:text-purple-300 dark:border-purple-800',
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>
      </svg>
    )
  },
  search_notes: {
    label: 'Search Notes',
    color: 'bg-teal-50 text-teal-700 border-teal-200',
    darkColor: 'dark:bg-teal-950/50 dark:text-teal-300 dark:border-teal-800',
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
      </svg>
    )
  },
  summarize: {
    label: 'Summarizer',
    color: 'bg-orange-50 text-orange-700 border-orange-200',
    darkColor: 'dark:bg-orange-950/50 dark:text-orange-300 dark:border-orange-800',
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M4 6h16M4 12h10M4 18h14"/>
      </svg>
    )
  }
};

export const ToolBadge: React.FC<ToolBadgeProps> = ({ name, status = 'success', input, output }) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const cfg = toolConfig[name] || {
    label: name,
    color: 'bg-zinc-100 text-zinc-800 border-zinc-300',
    darkColor: 'dark:bg-zinc-800 dark:text-zinc-200 dark:border-zinc-700',
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10"/><path d="m10 15 5-3-5-3v6z"/>
      </svg>
    )
  };

  return (
    <div 
      className="relative inline-flex items-center"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-medium border shadow-xs transition-colors ${cfg.color} ${cfg.darkColor}`}>
        {status === 'running' ? (
          <svg className="animate-spin w-3 h-3 text-current" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
        ) : (
          cfg.icon
        )}
        <span>{cfg.label}</span>
        {status === 'success' && (
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 ml-0.5"></span>
        )}
        {status === 'failed' && (
          <span className="w-1.5 h-1.5 rounded-full bg-red-500 ml-0.5"></span>
        )}
      </span>

      {/* Tooltip */}
      {showTooltip && (input || output) && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 max-w-sm p-3 bg-zinc-900 text-zinc-100 dark:bg-zinc-800 text-xs rounded-lg shadow-xl border border-zinc-700 z-50 pointer-events-none animate-in fade-in zoom-in-95">
          {input && (
            <div className="mb-2">
              <span className="text-zinc-400 font-semibold uppercase tracking-wider text-[10px]">Input:</span>
              <pre className="font-mono text-zinc-200 mt-0.5 whitespace-pre-wrap break-all max-h-24 overflow-y-auto">
                {typeof input === 'object' ? JSON.stringify(input, null, 2) : input}
              </pre>
            </div>
          )}
          {output && (
            <div>
              <span className="text-zinc-400 font-semibold uppercase tracking-wider text-[10px]">Output:</span>
              <p className="font-mono text-zinc-300 mt-0.5 line-clamp-4 break-words">
                {output}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};