export interface Issue {
  id: string;
  number: number;
  title: string;
  body: string;
  user: {
    login: string;
    avatar_url?: string;
  };
  repository: {
    name: string;
    full_name: string;
  };
  state: 'open' | 'closed';
  labels: string[];
  created_at: string;
  updated_at: string;
}

export interface AgentState {
  issue_id: string;
  issue_title: string;
  issue_body: string;
  classification: 'BUG' | 'FEATURE' | 'QUESTION' | null;
  retrieved_context: string[];
  draft_response: string;
  approval_status: 'pending' | 'approved' | 'rejected';
  human_edits?: string;
  processing_stage: ProcessingStage;
  timestamp: string;
}

export type ProcessingStage = 
  | 'received'
  | 'classifying'
  | 'retrieving_context'
  | 'generating_response'
  | 'awaiting_approval'
  | 'approved'
  | 'rejected'
  | 'error';

export interface WebSocketMessage {
  type: 'state_update' | 'error' | 'connection' | 'ping';
  data?: AgentState;
  message?: string;
  timestamp: string;
}

export interface DraftResponse {
  id: string;
  issue_id: string;
  content: string;
  retrieved_context: string[];
  classification: string;
  created_at: string;
  approval_token?: string;
}
