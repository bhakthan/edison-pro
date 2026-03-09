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
  status?: string;
  success?: boolean;
  message: string;
  filename?: string;
  filenames?: string[];
  file_count?: number;
  input_type?: string;
  chunks?: number;
  images_processed?: number;
  files?: string[];
  native_insights?: NativeInsights;
}

export interface SheetCorrelationHint {
  sheet_id: string;
  page_span?: number[];
  top_components?: string[];
  top_references?: string[];
  top_standards?: string[];
  top_tags?: string[];
}

export interface CrossSheetEdge {
  from_sheet_id: string;
  to_sheet_id: string;
  weight: number;
  relationship_strength?: string;
  shared_components?: string[];
  shared_references?: string[];
  shared_standards?: string[];
  shared_tags?: string[];
}

export interface ConnectorHub {
  signal: string;
  kind: string;
  sheet_count: number;
}

export interface CrossSheetGraph {
  edges?: CrossSheetEdge[];
  connector_hubs?: ConnectorHub[];
  summary_lines?: string[];
}

export interface AnomalyDetectionSummary {
  has_anomalies: boolean;
  risk_score: number;
  anomaly_count: number;
  severity_counts?: Record<string, number>;
  top_failure_types?: Array<[string, number]>;
  anomalies?: AnomalyRecord[];
  summary_lines?: string[];
}

export interface AnomalyRecord {
  chunk_id?: string;
  sheet_id?: string;
  domain?: string;
  failure_type?: string;
  severity?: string;
  signals?: string[];
  confidence?: number;
}

export interface NativeInsights {
  backend?: string;
  measurement_frequency?: Array<[string, number]>;
  standard_frequency?: Array<[string, number]>;
  tag_frequency?: Array<[string, number]>;
  sheet_correlation_hints?: SheetCorrelationHint[];
  cross_sheet_graph?: CrossSheetGraph;
  anomaly_detection?: AnomalyDetectionSummary;
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

export interface DynamicAgentSpec {
  agent_id: string;
  name: string;
  instructions: string;
  capabilities: string[];
  model: string;
  created_by?: string;
  created_at?: string;
  version?: number;
  last_refined_at?: string | null;
  status?: string;
}

export interface DynamicAgentsStatus {
  available: boolean;
  provider_available: boolean;
  metrics: Record<string, unknown>;
}

export interface EnsureDynamicAgentResponse {
  status: string;
  reason: string;
  agent: DynamicAgentSpec | null;
}

export interface RunDynamicAgentResponse {
  agent_id: string;
  agent_name: string;
  answer: string;
  session_id: string;
  evaluation?: Record<string, any>;
  refinement_applied?: boolean;
  refinement_rounds?: number;
  agent_version?: number;
}

// P&ID Digitization types — mirrors PIDAnalysisResponse in api.py

export interface PIDSymbol {
  id: string;
  category: string;
  label: string;
  bbox: [number, number, number, number]; // [x, y, w, h]
  confidence: number;
  sheet_id?: string;
  [key: string]: unknown;
}

export interface PIDLine {
  id: string;
  start: [number, number];
  end: [number, number];
  angle_deg: number;
  length_px: number;
  sheet_id?: string;
  [key: string]: unknown;
}

export interface PIDTextAnnotation {
  id: string;
  text: string;
  bbox: [number, number, number, number];
  confidence: number;
  [key: string]: unknown;
}

export interface PIDGraphNode {
  id: string;
  kind: string;
  label: string;
  sheet_id?: string;
  [key: string]: unknown;
}

export interface PIDGraphEdge {
  source: string;
  target: string;
  weight?: number;
  [key: string]: unknown;
}

export interface PIDTraversalPath {
  source: string;
  target: string;
  path: string[];
  [key: string]: unknown;
}

export interface PIDAnalysisResult {
  success: boolean;
  filename: string;
  sheet_id: string;
  image_width: number;
  image_height: number;
  symbol_count: number;
  line_count: number;
  text_token_count: number;
  node_count: number;
  edge_count: number;
  traversal_path_count: number;
  symbols: PIDSymbol[];
  lines: PIDLine[];
  text_annotations: PIDTextAnnotation[];
  nodes: PIDGraphNode[];
  edges: PIDGraphEdge[];
  traversal_paths: PIDTraversalPath[];
  processing_stages: string[];
  warnings: string[];
  latency_ms: number;
}
