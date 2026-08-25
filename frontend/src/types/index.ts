export interface Session {
  id: string;
  user_id: string;
  title: string;
  is_active: boolean;
  created_at?: string;
}

export interface Message {
  id?: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  reasoning_trace?: ReasoningStep[];
  tools_used?: string[];
}

export interface ReasoningStep {
  step: number;
  thought?: string;
  action?: string;
  input?: Record<string, any> | string;
  observation?: string;
}

export interface AgentRun {
  id: string;
  session_id: string;
  input: string;
  output: string | null;
  reasoning_trace: ReasoningStep[] | null;
  tools_used: string[] | null;
  token_usage: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  } | null;
  duration: number | null;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  error: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface Note {
  id: string;
  session_id: string;
  title: string;
  content: string;
  similarity?: number;
}

export interface SSEEvent {
  event: 'agent_action' | 'tool_start' | 'tool_end' | 'token' | 'agent_finish' | 'done' | 'error';
  data: any;
}