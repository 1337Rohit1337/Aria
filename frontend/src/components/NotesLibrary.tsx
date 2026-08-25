import React, { useState, useEffect } from 'react';
import { useAriaStore } from '../store/useAriaStore';
import { Note } from '../types';

export const NotesLibrary: React.FC = () => {
  const { notes, isLoadingNotes, fetchNotes, searchNotes, deleteNote } = useAriaStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);

  useEffect(() => {
    fetchNotes();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    searchNotes(searchQuery);
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-zinc-50 dark:bg-zinc-950 p-6 md:p-8">
      <div className="max-w-5xl w-full mx-auto flex flex-col h-full space-y-6">
        {/* Header & Semantic Search Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">Notes & Knowledge Base</h1>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
              Saved research and insights with vector embeddings (pgvector)
            </p>
          </div>

          <form onSubmit={handleSearch} className="flex items-center gap-2 max-w-md w-full">
            <div className="relative flex-1">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Semantic vector search across notes..."
                className="w-full pl-9 pr-4 py-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none text-zinc-900 dark:text-zinc-100"
              />
              <svg className="w-4 h-4 absolute left-3 top-2.5 text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
              </svg>
            </div>
            <button
              type="submit"
              className="px-3 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-medium transition-colors"
            >
              Search
            </button>
          </form>
        </div>

        {/* Notes Grid */}
        <div className="flex-1 overflow-y-auto pr-1">
          {isLoadingNotes ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-40 rounded-xl bg-zinc-200 dark:bg-zinc-900 animate-pulse border border-zinc-300/40 dark:border-zinc-800" />
              ))}
            </div>
          ) : notes.length === 0 ? (
            <div className="h-64 flex flex-col items-center justify-center text-center p-6 border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-2xl">
              <svg className="w-10 h-10 text-zinc-400 mb-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/>
              </svg>
              <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">No notes indexed yet</h3>
              <p className="text-xs text-zinc-500 max-w-sm mt-1">
                Ask Aria to "save note" during any research session and it will appear here automatically.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {notes.map((note) => (
                <div
                  key={note.id}
                  onClick={() => setSelectedNote(note)}
                  className="p-4 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 hover:border-teal-500 dark:hover:border-teal-600 transition-all cursor-pointer flex flex-col justify-between group shadow-xs"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <h3 className="font-semibold text-sm text-zinc-900 dark:text-zinc-100 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                        {note.title}
                      </h3>
                      {note.similarity !== undefined && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-teal-50 dark:bg-teal-950 text-teal-600 dark:text-teal-400 border border-teal-200 dark:border-teal-800">
                          {(note.similarity * 100).toFixed(0)}% match
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-zinc-600 dark:text-zinc-400 line-clamp-4 leading-relaxed font-sans">
                      {note.content}
                    </p>
                  </div>

                  <div className="pt-3 mt-3 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
                    <span className="text-[10px] text-zinc-400 font-mono">
                      pgvector 384-dim
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTargetId(note.id);
                      }}
                      className="p-1 text-zinc-400 hover:text-red-500 transition-colors rounded"
                      title="Delete Note"
                    >
                      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Expanded Note Modal */}
      {selectedNote && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl animate-in zoom-in-95">
            <div className="p-4 md:p-6 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
              <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100">{selectedNote.title}</h2>
              <button
                onClick={() => setSelectedNote(null)}
                className="p-1 rounded-lg text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
            <div className="p-4 md:p-6 overflow-y-auto text-sm text-zinc-800 dark:text-zinc-200 leading-relaxed font-sans whitespace-pre-wrap">
              {selectedNote.content}
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteTargetId && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl max-w-sm w-full p-6 shadow-2xl animate-in zoom-in-95 space-y-4">
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">Delete note?</h3>
            <p className="text-xs text-zinc-500">
              This will remove the embedding from PostgreSQL pgvector permanently.
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setDeleteTargetId(null)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  await deleteNote(deleteTargetId);
                  setDeleteTargetId(null);
                }}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-600 hover:bg-red-700 text-white transition-colors"
              >
                Confirm Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};