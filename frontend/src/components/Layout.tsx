import React from 'react';
import { useAriaStore } from '../store/useAriaStore';
import { SessionSidebar } from './SessionSidebar';
import { Chat } from './Chat';
import { NotesLibrary } from './NotesLibrary';
import { Dashboard } from './Dashboard';

export const Layout: React.FC = () => {
  const { isDarkMode, toggleDarkMode, activeTab, setActiveTab } = useAriaStore();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
      {/* Sidebar for Sessions */}
      <SessionSidebar />

      {/* Main Container */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Navbar */}
        <header className="h-14 border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-md px-4 flex items-center justify-between flex-shrink-0 z-10">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-teal-600 flex items-center justify-center text-white font-bold text-sm shadow-xs">
                A
              </div>
              <span className="font-semibold tracking-tight text-sm text-zinc-900 dark:text-zinc-100">
                Project Aria
              </span>
            </div>

            {/* Navigation Tabs */}
            <nav className="flex items-center gap-1">
              <button
                onClick={() => setActiveTab('chat')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  activeTab === 'chat'
                    ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100'
                    : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                }`}
              >
                Agent Chat
              </button>
              <button
                onClick={() => setActiveTab('notes')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  activeTab === 'notes'
                    ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100'
                    : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                }`}
              >
                Notes Library
              </button>
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  activeTab === 'dashboard'
                    ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100'
                    : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                }`}
              >
                Audit Dashboard
              </button>
            </nav>
          </div>

          <div className="flex items-center gap-2">
            {/* Dark Mode Toggle */}
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-lg text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
              title={isDarkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {isDarkMode ? (
                <svg className="w-4 h-4 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
                </svg>
              ) : (
                <svg className="w-4 h-4 text-zinc-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>
                </svg>
              )}
            </button>
          </div>
        </header>

        {/* Dynamic Tab Body */}
        <main className="flex-1 flex flex-col overflow-hidden relative">
          {activeTab === 'chat' && <Chat />}
          {activeTab === 'notes' && <NotesLibrary />}
          {activeTab === 'dashboard' && <Dashboard />}
        </main>

        {/* Footer */}
        <footer className="h-7 border-t border-zinc-200 dark:border-zinc-800/60 bg-zinc-50 dark:bg-zinc-950 px-4 flex items-center justify-between text-[11px] text-zinc-400 select-none flex-shrink-0">
          <span>Aria v1.0 • Hybrid RAG + ReAct Agent</span>
          <span className="font-mono">Powered by Aria</span>
        </footer>
      </div>
    </div>
  );
};