export type Citation = {
  document_id: string;
  document_title: string;
  source: string;
  chunk_id: string;
  chunk_position: number;
  score: number;
  excerpt: string;
};

export type RagTrace = {
  original_query: string;
  rewritten_query: string;
  query_rewrite_strategy: string;
  retrieval_strategy: string;
  rerank_strategy: string;
  answer_strategy: string;
  candidate_count: number;
  returned_count: number;
};

export type ChatResponse = {
  answer: string;
  citations: Citation[];
  trace: RagTrace;
};

export type ConversationMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  metadata: {
    citations?: Citation[];
    trace?: RagTrace;
    display_question?: string;
  };
  created_at: string;
};

export type Conversation = {
  id: string;
  title: string;
  messages: ConversationMessage[];
  created_at: string;
  updated_at: string;
};

export type DocumentSummary = {
  id: string;
  title: string;
  source: string;
  chunk_count: number;
  created_at: string;
};

export type AgentAction = {
  id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  preview: string;
  requires_approval: boolean;
  status: string;
  result: Record<string, unknown> | null;
  error: string | null;
  attempt_count: number;
};

export type AgentEvent = {
  id: string;
  event_type: string;
  message: string;
  created_at: string;
};

export type AgentRun = {
  id: string;
  objective: string;
  skill_name: string;
  status: string;
  actions: AgentAction[];
  events: AgentEvent[];
  approval_note: string | null;
  output: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type Capability = { name: string; description: string };

export type WorkItem = {
  id: string;
  kind: string;
  title: string;
  description: string;
  owner: string;
  status: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type EvaluationResult = {
  question: string;
  answer: string;
  expected_terms: string[];
  matched_terms: string[];
  term_score: number;
  citation_count: number;
  passed: boolean;
};

export type EvaluationReport = {
  case_count: number;
  passed_count: number;
  pass_rate: number;
  results: EvaluationResult[];
};
