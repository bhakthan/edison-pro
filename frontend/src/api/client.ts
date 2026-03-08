import axios from 'axios';
import type {
  ChatResponse,
  AnalysisStatus,
  SystemStatus,
  AnalysisTemplate,
  TemplateExecutionRequest,
  TemplateExecutionResponse,
  DynamicAgentsStatus,
  DynamicAgentSpec,
  EnsureDynamicAgentResponse,
  RunDynamicAgentResponse,
} from '../types';

// Configure base URL for your Python backend
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:7861';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2 minutes for o3-pro queries
});

// API endpoints
export const api = {
  // Ask a question
  async askQuestion(
    question: string, 
    history: Array<[string, string]> = [],
    useWebSearch: boolean = false
  ): Promise<ChatResponse> {
    const response = await apiClient.post('/ask', {
      question,
      history,
      use_web_search: useWebSearch,
    });
    return response.data;
  },

  // Upload and analyze document
  async uploadDocument(files: File[], onProgress?: (progress: number) => void): Promise<AnalysisStatus> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await apiClient.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
    return response.data;
  },

  // Get system status
  async getStatus(): Promise<SystemStatus> {
    const response = await apiClient.get('/status');
    return response.data;
  },

  // List analyzed documents
  async listDocuments(): Promise<string[]> {
    const response = await apiClient.get('/documents');
    return response.data;
  },

  // Download generated file
  getFileUrl(filePath: string): string {
    return `${API_BASE_URL}/download/${encodeURIComponent(filePath)}`;
  },

  // Analysis Templates
  async getTemplates(category?: string): Promise<AnalysisTemplate[]> {
    const params = category ? { category } : {};
    const response = await apiClient.get('/templates', { params });
    return response.data;
  },

  async getTemplate(templateId: string): Promise<AnalysisTemplate> {
    const response = await apiClient.get(`/templates/${templateId}`);
    return response.data;
  },

  async executeTemplate(request: TemplateExecutionRequest): Promise<TemplateExecutionResponse> {
    const response = await apiClient.post('/templates/execute', request);
    return response.data;
  },

  async searchTemplates(keywords: string[]): Promise<AnalysisTemplate[]> {
    const response = await apiClient.post('/templates/search', { keywords });
    return response.data;
  },

  // Generate comprehensive results page
  async generateResults(): Promise<{status: string; results_path: string; message: string}> {
    const response = await apiClient.post('/generate-results');
    return response.data;
  },

  // Get latest results page URL
  getLatestResultsUrl(): string {
    return `${API_BASE_URL}/results/latest`;
  },

  // Flickering Analysis
  async analyzeFlickering(request: {
    diagram: string;
    num_cycles?: number;
    theta_frequency?: number;
    domain?: string;
    return_trace?: boolean;
    generate_alternatives?: boolean;
  }): Promise<any> {
    const response = await apiClient.post('/analyze/flickering', request, {
      timeout: 300000, // 5 minutes for flickering analysis
    });
    return response.data;
  },

  async getFlickeringStatus(): Promise<any> {
    const response = await apiClient.get('/flickering/status');
    return response.data;
  },

  async getDynamicAgentsStatus(): Promise<DynamicAgentsStatus> {
    const response = await apiClient.get('/dynamic-agents/status');
    return response.data;
  },

  async listDynamicAgents(): Promise<DynamicAgentSpec[]> {
    const response = await apiClient.get('/dynamic-agents');
    return response.data;
  },

  async ensureDynamicAgent(request: {
    task: string;
    context?: Record<string, unknown>;
    allow_create?: boolean;
  }): Promise<EnsureDynamicAgentResponse> {
    const response = await apiClient.post('/dynamic-agents/ensure', request);
    return response.data;
  },

  async runDynamicAgent(request: {
    agent_id: string;
    prompt: string;
    session_id?: string;
    task?: string;
    auto_refine?: boolean;
    min_score?: number;
    max_refinement_rounds?: number;
  }): Promise<RunDynamicAgentResponse> {
    const response = await apiClient.post('/dynamic-agents/run', request, {
      timeout: 300000,
    });
    return response.data;
  },

  async reloadDynamicAgents(): Promise<{ status: string; metrics: Record<string, unknown> }> {
    const response = await apiClient.post('/dynamic-agents/reload');
    return response.data;
  },

  async getDynamicAgentsLastRun(agentId?: string): Promise<Record<string, unknown>> {
    const response = await apiClient.get('/dynamic-agents/last-run', {
      params: agentId ? { agent_id: agentId } : undefined,
    });
    return response.data;
  },

  async getDynamicAgentLineage(agentId: string): Promise<Record<string, unknown>> {
    const response = await apiClient.get(`/dynamic-agents/${agentId}/lineage`);
    return response.data;
  },
};

export default apiClient;
