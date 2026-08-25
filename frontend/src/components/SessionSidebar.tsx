import React from 'react';
import { useAriaStore } from '../store/useAriaStore';

export const SessionSidebar: React.FC = () => {
  const {
    sessions,
    currentSessionId,
    selectSession,
    createNewSession,
    isSidebarOpen,
    toggleSidebar
  } = useAriaStore();

  if (!isSidebarOpen) {
    return (
      <div className="p-2 border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 flex flex-col items-center">
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-zinc-200 dark:hover:bg-zinc-800 text-zinc-600 dark:text-zinc-400 transition-colors"
          title="Expand Sidebar"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><path d="M9 3v18"/>
          </svg>
        </button>
      </div>
    );
  }

  return (
    <aside className="w-64 flex-shrink-0 border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 flex flex-col h-full">
      {/* Header & New Chat */}
      <div className="p-3 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between gap-2">
        <button
          onClick={() => createNewSession()}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-medium transition-colors shadow-xs"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          <span>New Chat</span>
        </button>
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-zinc-200 dark:hover:bg-zinc-800 text-zinc-500 transition-colors"
          title="Collapse Sidebar"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><path d="M9 3v18"/>
          </svg>
        </button>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        <span className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-zinc-400 block">
          Recent Sessions
        </span>
        {sessions.map((sess) => {
          const isActive = sess.id === currentSessionId;
          return (
            <button
              key={sess.id}
              onClick={() => selectSession(sess.id)}
              className={`w-full text-left px-2.5 py-2 rounded-lg text-xs transition-colors flex items-center gap-2 ${
                isActive
                  ? 'bg-zinc-200/80 dark:bg-zinc-800 font-medium text-zinc-900 dark:text-zinc-100'
                  : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/50'
              }`}
            >
              <svg className="w-3.5 h-3.5 flex-shrink-0 text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
              <span className="truncate">{sess.title || "Untitled Session"}</span>
            </button>
          );
        })}
      </div>
    </aside>
  );
};