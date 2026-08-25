import { create } from 'zustand';
import { Session, Message, Note, ReasoningStep, AgentRun } from '../types';
import { api } from '../api/api';

const extractText = (d: any): string => {
  if (typeof d === 'string') return d;
  if (!d) return '';
  // Handle LangChain token chunks
  if (d.chunk && d.chunk.content) return d.chunk.content;
  if (d.data && d.data.chunk && d.data.chunk.content) return d.data.chunk.content;
  return d.token || d.data || d.content || d.output || d.text || (typeof d.delta === 'string' ? d.delta : d.delta?.content) || '';
};

interface AriaState {
  isDarkMode: boolean;
  toggleDarkMode: () => void;
  activeTab: 'chat' | 'notes' | 'dashboard';
  setActiveTab: (tab: 'chat' | 'notes' | 'dashboard') => void;
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  sessions: Session[];
  currentSessionId: string | null;
  isLoadingSessions: boolean;
  fetchSessions: () => Promise<void>;
  selectSession: (sessionId: string) => Promise<void>;
  createNewSession: (initialTitle?: string) => Promise<string>;
  messages: Message[];
  isStreaming: boolean;
  currentRunId: string | null;
  activeReasoningSteps: ReasoningStep[];
  streamingAnswer: string;
  sendMessage: (content: string) => Promise<void>;
  cancelCurrentRun: () => Promise<void>;
  notes: Note[];
  isLoadingNotes: boolean;
  fetchNotes: () => Promise<void>;
  searchNotes: (query: string) => Promise<void>;
  deleteNote: (id: string) => Promise<void>;
  allRuns: AgentRun[];
  isLoadingRuns: boolean;
  fetchDashboardData: () => Promise<void>;
}

export const useAriaStore = create<AriaState>((set, get) => ({
  isDarkMode: localStorage.getItem('aria_theme') === 'dark' || 
    (!localStorage.getItem('aria_theme') && window.matchMedia('(prefers-color-scheme: dark)').matches),
  
  toggleDarkMode: () => {
    const next = !get().isDarkMode;
    localStorage.setItem('aria_theme', next ? 'dark' : 'light');
    if (next) document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
    set({ isDarkMode: next });
  },

  activeTab: 'chat',
  setActiveTab: (activeTab) => set({ activeTab }),

  isSidebarOpen: true,
  toggleSidebar: () => set((s) => ({ isSidebarOpen: !s.isSidebarOpen })),

  sessions: [],
  currentSessionId: null,
  isLoadingSessions: false,

  fetchSessions: async () => {
    set({ isLoadingSessions: true });
    try {
      const sessions = await api.getSessions();
      set({ sessions });
      if (sessions.length > 0 && !get().currentSessionId) {
        await get().selectSession(sessions[0].id);
      } else if (sessions.length === 0) {
        await get().createNewSession();
      }
    } catch (err) {
      console.error("Failed to fetch sessions:", err);
    } finally {
      set({ isLoadingSessions: false });
    }
  },

  selectSession: async (sessionId: string) => {
    set({ currentSessionId: sessionId, messages: [], activeReasoningSteps: [], streamingAnswer: '' });
    try {
      const messages = await api.getSessionMessages(sessionId);
      set({ messages });
    } catch (err) {
      console.error("Failed to load session history:", err);
    }
  },

  createNewSession: async (initialTitle = "New Conversation") => {
    try {
      const newSession = await api.createSession(initialTitle);
      set((s) => ({
        sessions: [newSession, ...s.sessions],
        currentSessionId: newSession.id,
        messages: [],
        activeReasoningSteps: [],
        streamingAnswer: ''
      }));
      return newSession.id;
    } catch (err) {
      console.error("Failed to create session:", err);
      throw err;
    }
  },

  messages: [],
  isStreaming: false,
  currentRunId: null,
  activeReasoningSteps: [],
  streamingAnswer: '',

  sendMessage: async (content: string) => {
    let sid = get().currentSessionId;
    if (!sid) {
      sid = await get().createNewSession(content.slice(0, 30) + '...');
    }

    const userMessage: Message = {
      session_id: sid,
      role: 'user',
      content
    };

    set((s) => ({
      messages: [...s.messages, userMessage],
      isStreaming: true,
      streamingAnswer: '',
      activeReasoningSteps: []
    }));

    try {
      const stream = api.streamAgentRun(sid, content);
      let fullAnswer = '';
      const liveSteps: ReasoningStep[] = [];
      const usedToolsSet = new Set<string>();

      for await (const event of stream) {
        console.log("SSE Event:", event); // <--- DEBUG LOG TO SEE EXACT SHAPE
        const evType = event.event;
        const d = event.data;

        if (evType === 'agent_action') {
          const tool = d.tool || d.action || (typeof d === 'string' ? d : 'agent');
          usedToolsSet.add(tool);
          liveSteps.push({
            step: liveSteps.length + 1,
            thought: d.thought || d.log || '',
            action: tool,
            input: d.tool_input || d.input || '',
          });
          set({ activeReasoningSteps: [...liveSteps] });
        } else if (evType === 'tool_end') {
          const lastIdx = liveSteps.length - 1;
          if (lastIdx >= 0) {
            liveSteps[lastIdx].observation = typeof d === 'string' ? d : JSON.stringify(d);
            set({ activeReasoningSteps: [...liveSteps] });
          }
        } else if (evType === 'token') {
          const textChunk = extractText(d);
          fullAnswer += textChunk;
          set({ streamingAnswer: fullAnswer });
        } else if (evType === 'agent_finish') {
          // Handle multiple shapes of agent_finish
          const out = d.output || d.return_values?.output || d.data?.output || (typeof d === 'string' ? d : '');
          if (out && typeof out === 'string') {
            fullAnswer = out;
            set({ streamingAnswer: fullAnswer });
          }
        } else if (evType === 'error') {
          const errText = typeof d === 'string' ? d : JSON.stringify(d);
          fullAnswer = `⚠️ **Agent Error:** ${errText}`;
          set({ streamingAnswer: fullAnswer });
        }
      }

      // If fullAnswer is still empty, fetch the persisted messages from backend DB
      if (!fullAnswer.trim()) {
        const refreshedMsgs = await api.getSessionMessages(sid);
        const lastAssistant = refreshedMsgs.filter(m => m.role === 'assistant').pop();
        if (lastAssistant && lastAssistant.content) {
          fullAnswer = lastAssistant.content;
        }
      }

      const assistantMsg: Message = {
        session_id: sid,
        role: 'assistant',
        content: fullAnswer || "Response completed.",
        reasoning_trace: [...liveSteps],
        tools_used: Array.from(usedToolsSet)
      };

      set((s) => ({
        messages: [...s.messages, assistantMsg],
        streamingAnswer: '',
        activeReasoningSteps: [],
        isStreaming: false
      }));

      // Update sidebar session title on first interaction
      if (get().messages.length <= 2) {
        const titleSnippet = content.split(' ').slice(0, 5).join(' ') + '...';
        set((s) => ({
          sessions: s.sessions.map((sess) => (sess.id === sid ? { ...sess, title: titleSnippet } : sess))
        }));
      }
    } catch (err: any) {
      console.error("Agent run error:", err);
      const errorMsg: Message = {
        session_id: sid,
        role: 'assistant',
        content: `⚠️ **Agent Error:** ${err.message || 'An unexpected connection issue occurred.'}`
      };
      set((s) => ({
        messages: [...s.messages, errorMsg],
        isStreaming: false,
        streamingAnswer: '',
        activeReasoningSteps: []
      }));
    }
  },

  cancelCurrentRun: async () => {
    const runId = get().currentRunId;
    if (runId) {
      await api.cancelRun(runId);
      set({ isStreaming: false });
    }
  },

  notes: [],
  isLoadingNotes: false,
  fetchNotes: async () => {
    set({ isLoadingNotes: true });
    try {
      const notes = await api.getNotes();
      set({ notes });
    } catch (err) {
      console.error("Failed to load notes:", err);
    } finally {
      set({ isLoadingNotes: false });
    }
  },

  searchNotes: async (query: string) => {
    if (!query.trim()) {
      return get().fetchNotes();
    }
    set({ isLoadingNotes: true });
    try {
      const results = await api.searchNotes(query);
      set({ notes: results });
    } catch (err) {
      console.error("Semantic note search error:", err);
    } finally {
      set({ isLoadingNotes: false });
    }
  },

  deleteNote: async (id: string) => {
    try {
      await api.deleteNote(id);
      set((s) => ({ notes: s.notes.filter((n) => n.id !== id) }));
    } catch (err) {
      console.error("Note deletion failed:", err);
    }
  },

  allRuns: [],
  isLoadingRuns: false,
  fetchDashboardData: async () => {
    set({ isLoadingRuns: true });
    try {
      const sessions = await api.getSessions();
      const runPromises = sessions.map((sess) => api.getRunsForSession(sess.id).catch(() => []));
      const nestedRuns = await Promise.all(runPromises);
      const flatRuns = nestedRuns.flat().sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
      set({ allRuns: flatRuns, sessions });
    } catch (err) {
      console.error("Dashboard fetch failed:", err);
    } finally {
      set({ isLoadingRuns: false });
    }
  }
}));