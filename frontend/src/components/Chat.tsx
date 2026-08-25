import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { useAriaStore } from '../store/useAriaStore';
import { ReasoningChain } from './ReasoningChain';

const EXAMPLE_PROMPTS = [
  "Research Python async frameworks and save a comparison note",
  "What's the weather in Tokyo right now?",
  "Calculate ((450 * 12) / 3.5) and explain the steps",
  "Summarize what quantum computing is and search my past notes"
];

export const Chat: React.FC = () => {
  const {
    messages,
    sendMessage,
    isStreaming,
    streamingAnswer,
    activeReasoningSteps,
  } = useAriaStore();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingAnswer, activeReasoningSteps]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isStreaming) return;
    const q = input.trim();
    setInput('');
    await sendMessage(q);
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-white dark:bg-zinc-950">
      {/* Scrollable Message List */}
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8 max-w-4xl w-full mx-auto space-y-6">
        {/* Welcome message when chat is pristine */}
        {messages.length === 0 && (
          <div className="text-center py-12 px-4 max-w-xl mx-auto space-y-4">
            <div className="inline-flex p-3 rounded-2xl bg-teal-50 dark:bg-teal-950/60 text-teal-600 dark:text-teal-400 border border-teal-200 dark:border-teal-800/80 mb-2">
              <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
              Hi, I'm Aria.
            </h2>
            <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
              Tell me a goal, task, or research question. I can query real-time data, do multi-step calculations, synthesize reports, and index knowledge into long-term memory.
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div className="flex items-center gap-2 mb-1 px-1">
              <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-400">
                {msg.role === 'user' ? 'You' : 'Aria'}
              </span>
            </div>

            <div
              className={`max-w-[85%] md:max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-teal-600 text-white rounded-br-xs shadow-xs'
                  : 'bg-zinc-100 dark:bg-zinc-900 text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-800 rounded-bl-xs'
              }`}
            >
              {msg.role === 'assistant' ? (
                <div className="prose dark:prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-zinc-800 dark:prose-pre:bg-zinc-950 prose-pre:border prose-pre:border-zinc-700">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              )}
            </div>

            {/* Persistent Reasoning Chain for completed runs */}
            {msg.role === 'assistant' && msg.reasoning_trace && msg.reasoning_trace.length > 0 && (
              <div className="w-full max-w-[85%] md:max-w-[80%]">
                <ReasoningChain steps={msg.reasoning_trace} isStreaming={false} />
              </div>
            )}
          </div>
        ))}

        {/* Live Streaming Assistant Output */}
        {isStreaming && (
          <div className="flex flex-col items-start">
            <div className="flex items-center gap-2 mb-1 px-1">
              <span className="text-[11px] font-medium uppercase tracking-wider text-teal-600 dark:text-teal-400 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse"></span>
                Aria Thinking
              </span>
            </div>

            {/* Live Streaming Reasoning Chain */}
            {activeReasoningSteps.length > 0 && (
              <div className="w-full max-w-[85%] md:max-w-[80%]">
                <ReasoningChain steps={activeReasoningSteps} isStreaming={true} />
              </div>
            )}

            {/* Streaming Text Output or Pulsing Dots */}
            <div className="max-w-[85%] md:max-w-[80%] rounded-2xl rounded-bl-xs px-4 py-3 text-sm bg-zinc-100 dark:bg-zinc-900 text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-800">
              {streamingAnswer ? (
                <div className="prose dark:prose-invert prose-sm max-w-none">
                  <ReactMarkdown>{streamingAnswer}</ReactMarkdown>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 py-1 text-zinc-400">
                  <span className="w-2 h-2 rounded-full bg-zinc-400 dark:bg-zinc-600 animate-bounce"></span>
                  <span className="w-2 h-2 rounded-full bg-zinc-400 dark:bg-zinc-600 animate-bounce [animation-delay:0.2s]"></span>
                  <span className="w-2 h-2 rounded-full bg-zinc-400 dark:bg-zinc-600 animate-bounce [animation-delay:0.4s]"></span>
                </div>
              )}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompt Chips */}
      {messages.length === 0 && (
        <div className="px-4 md:px-8 max-w-4xl mx-auto w-full pb-3">
          <div className="flex flex-wrap gap-2 justify-center">
            {EXAMPLE_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setInput(prompt);
                }}
                className="text-xs bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800 rounded-full px-3 py-1.5 transition-all text-left"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Bottom Input Area */}
      <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md">
        <form
          onSubmit={handleSubmit}
          className="max-w-4xl mx-auto flex items-center gap-2"
        >
          <div className="relative flex-1">
            <input
              type="text"
              value={input}
              disabled={isStreaming}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isStreaming ? "Aria is working..." : "Ask Aria to research, calculate, search, or summarize..."}
              className="w-full pl-4 pr-10 py-3 rounded-xl bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 disabled:opacity-60 transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="p-3 bg-teal-600 hover:bg-teal-700 disabled:bg-zinc-300 dark:disabled:bg-zinc-800 text-white rounded-xl font-medium transition-colors shadow-xs disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
};

export default Chat;