import React, { useState } from 'react';
import { ReasoningStep } from '../types';
import { ToolBadge } from './ToolBadge';

interface ReasoningChainProps {
  steps: ReasoningStep[];
  isStreaming?: boolean;
}

export const ReasoningChain: React.FC<ReasoningChainProps> = ({ steps, isStreaming = false }) => {
  const [isOpen, setIsOpen] = useState(isStreaming);

  if (!steps || steps.length === 0) return null;

  return (
    <div className="my-3 border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-hidden bg-zinc-50/50 dark:bg-zinc-900/40 text-xs">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3.5 py-2.5 flex items-center justify-between text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/60 transition-colors font-medium select-none"
      >
        <div className="flex items-center gap-2">
          {isStreaming ? (
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-teal-500"></span>
            </span>
          ) : (
            <svg className="w-3.5 h-3.5 text-zinc-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>
            </svg>
          )}
          <span>{isStreaming ? 'Thinking & Executing Tools...' : `Reasoning Chain (${steps.length} ${steps.length === 1 ? 'step' : 'steps'})`}</span>
        </div>
        <svg
          className={`w-4 h-4 transform transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="m6 9 6 6 6-6"/>
        </svg>
      </button>

      {isOpen && (
        <div className="px-3.5 py-3 border-t border-zinc-200 dark:border-zinc-800 space-y-3 font-mono">
          {steps.map((step, idx) => (
            <div key={idx} className="space-y-1.5">
              {step.thought && (
                <div className="text-zinc-600 dark:text-zinc-300 font-sans text-[13px] leading-relaxed">
                  <span className="font-mono text-xs font-semibold text-zinc-400 dark:text-zinc-500 mr-1.5">[{step.step}]</span>
                  {step.thought}
                </div>
              )}

              {step.action && (
                <div className="flex items-center gap-2 pt-0.5">
                  <span className="text-zinc-400 text-xs">Action:</span>
                  <ToolBadge
                    name={step.action}
                    status={step.observation ? 'success' : isStreaming && idx === steps.length - 1 ? 'running' : 'success'}
                    input={step.input}
                    output={step.observation}
                  />
                </div>
              )}

              {step.observation && (
                <div className="pl-3 border-l-2 border-zinc-200 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400 text-[11px] truncate max-w-xl">
                  ↳ <span className="italic">{step.observation}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};