import { Session, Message, AgentRun, Note, SSEEvent } from '../types';

const BASE_URL = '/api';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorBody = await res.text();
    let detail = errorBody;
    try {
      const parsed = JSON.parse(errorBody);
      detail = parsed.detail || errorBody;
    } catch (_) {}
    throw new Error(detail || `HTTP Error ${res.status}`);
  }
  return res.json();
}

export const api = {
  async getSessions(): Promise<Session[]> {
    const res = await fetch(`${BASE_URL}/sessions`);
    return handleResponse<Session[]>(res);
  },

  async createSession(title: string = "New Session"): Promise<Session> {
    const res = await fetch(`${BASE_URL}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, user_id: 'default_user' })
    });
    return handleResponse<Session>(res);
  },

  async getSessionMessages(sessionId: string): Promise<Message[]> {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/messages`);
    return handleResponse<Message[]>(res);
  },

  async getNotes(sessionId?: string): Promise<Note[]> {
    const url = sessionId ? `${BASE_URL}/notes?session_id=${sessionId}` : `${BASE_URL}/notes`;
    const res = await fetch(url);
    return handleResponse<Note[]>(res);
  },

  async searchNotes(query: string, limit = 5, threshold = 0.4): Promise<Note[]> {
    const res = await fetch(`${BASE_URL}/notes/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, limit, threshold })
    });
    return handleResponse<Note[]>(res);
  },

  async deleteNote(noteId: string): Promise<void> {
    const res = await fetch(`${BASE_URL}/notes/${noteId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error("Failed to delete note");
  },

  async getRunsForSession(sessionId: string): Promise<AgentRun[]> {
    const res = await fetch(`${BASE_URL}/agent/runs/${sessionId}`);
    return handleResponse<AgentRun[]>(res);
  },

  async getRunById(runId: string): Promise<AgentRun> {
    const res = await fetch(`${BASE_URL}/agent/runs/id/${runId}`);
    return handleResponse<AgentRun>(res);
  },

  async cancelRun(runId: string): Promise<void> {
    await fetch(`${BASE_URL}/agent/run/${runId}/cancel`, { method: 'POST' });
  },

  async *streamAgentRun(sessionId: string, input: string): AsyncGenerator<SSEEvent, void, unknown> {
    const res = await fetch(`${BASE_URL}/agent/run/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, input })
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(errorText || `Streaming failed: ${res.statusText}`);
    }

    if (!res.body) throw new Error("No response body for streaming");

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const block of lines) {
          if (!block.trim()) continue;
          
          let eventType: string = 'token';
          let rawData: any = '';

          for (const line of block.split('\n')) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              rawData = line.slice(6).trim();
            }
          }

          if (rawData) {
            try {
              const parsed = JSON.parse(rawData);
              // Normalize if the backend embeds event name inside the JSON object
              if (parsed && typeof parsed === 'object') {
                if (parsed.event) eventType = parsed.event;
                if (parsed.type) eventType = parsed.type;
                yield { event: eventType as any, data: parsed.data !== undefined ? parsed.data : parsed };
              } else {
                yield { event: eventType as any, data: parsed };
              }
            } catch {
              yield { event: eventType as any, data: rawData };
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
};