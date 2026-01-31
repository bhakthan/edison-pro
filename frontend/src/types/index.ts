// Type definitions for EDISON PRO API

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface ChatResponse {
  answer: string;
  table_html?: string;
  download_html?: string;
  chart_html?: string;
  confidence?: number;
  sources?: Source[];
  code_executed?: boolean;
  tables?: Table[];
  files?: string[];
  charts?: Chart[];
  web_search_used?: boolean;
  web_sources?: WebSource[];
}

export interface Source {
  chunk_id: string;
  page: number;
  relevance: number;
}

export interface WebSource {
  title: string;
  url: string;
  snippet: string;
}

export interface Table {
  type: string;
  content: string;
}

export interface Chart {
  type: string;
  html: string;
}

export interface AnalysisStatus {
  status: string;
  message: string;
  files?: string[];
}

export interface SystemStatus {
  orchestrator: boolean;
  code_agent: boolean;
  azure_search: boolean;
  o3_pro: boolean;
}

// Analysis Templates
export interface AnalysisQuestion {
  question: string;
  purpose: string;
  expected_format: string;
  requires_code_agent: boolean;
  priority: number;
}

export interface AnalysisTemplate {
  template_id: string;
  name: string;
  description: string;
  category: string;
  use_case: string;
  recommended_domain: string;
  recommended_reasoning: string;
  questions: AnalysisQuestion[];
  expected_outputs: string[];
  quality_checks: string[];
  estimated_time_minutes: number;
  requires_web_search: boolean;
}

export interface TemplateExecutionRequest {
  template_id: string;
  use_web_search?: boolean;
  skip_questions?: number[];
}

export interface TemplateExecutionResponse {
  template: AnalysisTemplate;
  results: {
    question_index: number;
    question: string;
    answer: string;
    tables?: Table[];
    files?: string[];
    charts?: Chart[];
    code_executed?: boolean;
    execution_time_seconds?: number;
  }[];
  total_execution_time_seconds: number;
  summary: string;
}
