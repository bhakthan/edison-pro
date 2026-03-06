import { useState, useRef, useEffect } from 'react';
import {
  Send,
  Loader2,
  FileText,
  FileDown,
  Menu,
  MessageSquare,
  Sparkles,
  Orbit,
  PanelLeftClose,
  PanelLeftOpen,
  CloudUpload,
  LayoutTemplate,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
import { api } from './api/client';
import type { Message, ChatResponse, TemplateExecutionResponse } from './types';
import { UploadPanel } from './components/UploadPanel';
import { TemplateSelector } from './components/TemplateSelector';
import { TemplateResults } from './components/TemplateResults';
import { FlickeringAnalysis } from './components/FlickeringAnalysis';
import { InnovativeFeatures } from './components/InnovativeFeatures';
import './App.css';

function App() {
  type TabId = 'upload' | 'chat' | 'templates' | 'features' | 'flickering';
  const [activeTab, setActiveTab] = useState<TabId>('upload');
  const [isNavCollapsed, setIsNavCollapsed] = useState(true);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const [activeDocument, setActiveDocument] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [useWebSearch, setUseWebSearch] = useState(false);
  const [templateResults, setTemplateResults] = useState<TemplateExecutionResponse[]>([]);
  const [isGeneratingResults, setIsGeneratingResults] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const history: Array<[string, string]> = [];
      for (let i = 0; i < messages.length; i += 2) {
        if (messages[i] && messages[i + 1]) {
          history.push([messages[i].content, messages[i + 1].content]);
        }
      }

      const response = await api.askQuestion(input, history, useWebSearch);

      const assistantMessage: Message = {
        role: 'assistant',
        content: formatResponse(response),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error asking question:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Error: Failed to get response from server. Please check if the backend is running.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatResponse = (response: ChatResponse): string => {
    let formatted = response.answer;

    if (response.web_search_used && response.web_sources && response.web_sources.length > 0) {
      formatted += '\n\nWeb Search Results:\n';
      response.web_sources.forEach((source) => {
        formatted += `\n• [${source.title}](${source.url})\n  ${source.snippet}`;
      });
    }

    if (response.tables && response.tables.length > 0) {
      formatted += '\n\nGenerated Tables:\n';
      response.tables.forEach((table, idx) => {
        formatted += `\nTable ${idx + 1}:\n${table.content}`;
      });
    }

    if (response.files && response.files.length > 0) {
      formatted += '\n\nGenerated Files:\n';
      response.files.forEach((file) => {
        formatted += `\n• ${file}`;
      });
    }

    if (response.charts && response.charts.length > 0) {
      formatted += `\n\nGenerated ${response.charts.length} interactive chart(s)`;
    }

    if (response.code_executed) {
      formatted += '\n\nCode executed successfully';
    }

    return formatted;
  };

  const handleDocumentReady = (filename: string) => {
    setActiveDocument(filename);
  };

  const handleTemplateExecute = (response: TemplateExecutionResponse) => {
    setTemplateResults((prev) => [response, ...prev]);

    const templateMessage: Message = {
      role: 'assistant',
      content: `Template "${response.template.name}" executed successfully with ${response.results.length} questions in ${response.total_execution_time_seconds.toFixed(1)} seconds.`,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, templateMessage]);
  };

  const handleGenerateResults = async () => {
    if (isGeneratingResults) return;

    setIsGeneratingResults(true);
    try {
      const result = await api.generateResults();
      const resultsUrl = api.getLatestResultsUrl();
      window.open(resultsUrl, '_blank');

      const successMessage: Message = {
        role: 'assistant',
        content: `${result.message}\n\nComprehensive results page has been opened in a new tab.`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, successMessage]);
    } catch (error) {
      console.error('Error generating results:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Failed to generate results page. Make sure you have asked some questions first.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsGeneratingResults(false);
    }
  };

  const sampleQuestions = [
    'What type of diagram is this?',
    'List all transformers and their ratings',
    'What are the clearance requirements?',
    'Explain the grounding system',
    'What standards are referenced?',
    'Describe the primary distribution layout',
    'Show all transformers as a table',
    'Export components to CSV',
  ];

  const navItems: { id: TabId; label: string; hint: string; icon: React.ElementType; badge?: string }[] = [
    {
      id: 'upload',
      label: 'Upload',
      hint: 'PDFs, images & drawings',
      icon: CloudUpload,
    },
    {
      id: 'chat',
      label: 'Chat Analysis',
      hint: 'Ask about your diagram',
      icon: MessageSquare,
    },
    {
      id: 'templates',
      label: 'Templates',
      hint: 'Professional analysis packs',
      icon: LayoutTemplate,
    },
    {
      id: 'features',
      label: 'Innovative AI',
      hint: 'Proactive review tools',
      icon: Sparkles,
    },
    {
      id: 'flickering',
      label: 'Flickering',
      hint: 'Novelty & attention trace',
      icon: Orbit,
    },
  ];

  const handleNavSelect = (tab: TabId) => {
    setActiveTab(tab);
    setIsMobileNavOpen(false);
  };

  return (
    <div className="app-shell">
      <aside className={`side-nav ${isNavCollapsed ? 'collapsed' : ''} ${isMobileNavOpen ? 'open' : ''}`}>
        <div className="side-nav-header">
          <button
            type="button"
            className="side-nav-toggle"
            onClick={() => setIsNavCollapsed((prev) => !prev)}
            aria-label={isNavCollapsed ? 'Expand navigation menu' : 'Collapse navigation menu'}
          >
            {isNavCollapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
            {!isNavCollapsed && <span>Collapse</span>}
          </button>
        </div>

        <nav className="side-nav-menu" aria-label="Primary navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                type="button"
                className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
                onClick={() => handleNavSelect(item.id)}
                title={item.label}
              >
                <span className="nav-item-icon">
                  <Icon size={18} />
                </span>
                <span className="nav-item-text">
                  <strong>{item.label}</strong>
                  <small>{item.hint}</small>
                </span>
              </button>
            );
          })}
        </nav>

        {!isNavCollapsed && (
          <div className="side-nav-footer">
            <p>EDISON PRO</p>
            <span>AI engineering workspace</span>
          </div>
        )}
      </aside>

      <div
        className={`side-nav-overlay ${isMobileNavOpen ? 'visible' : ''}`}
        onClick={() => setIsMobileNavOpen(false)}
        aria-hidden="true"
      />

      <div className="main-frame">
        <header className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="mobile-nav-toggle"
              onClick={() => setIsMobileNavOpen((prev) => !prev)}
              aria-label="Toggle navigation menu"
            >
              <Menu size={18} />
            </button>

            <div className="topbar-brand">
              <span className="topbar-brand-icon">⚡</span>
              <div>
                <h1>Edison Pro</h1>
                <p>Engineering diagram intelligence</p>
              </div>
            </div>
          </div>

          <div className="topbar-actions">
            {messages.length > 0 && (
              <button
                onClick={handleGenerateResults}
                disabled={isGeneratingResults}
                className="results-button"
                title="Generate comprehensive results page with all Q&A and generated files"
              >
                {isGeneratingResults ? (
                  <>
                    <Loader2 className="spinner" size={16} />
                    <span>Generating...</span>
                  </>
                ) : (
                  <>
                    <FileDown size={16} />
                    <span>Full Results</span>
                  </>
                )}
              </button>
            )}
          </div>
        </header>

        <main className="workspace-content">
          {activeTab === 'upload' ? (
            <div className="chat-container" style={{ overflowY: 'auto', display: 'block' }}>
              <UploadPanel
                activeDocument={activeDocument}
                onDocumentReady={handleDocumentReady}
                onGoToChat={() => handleNavSelect('chat')}
                onGoToTemplates={() => handleNavSelect('templates')}
              />
            </div>
          ) : activeTab === 'templates' ? (
            <div className="chat-container" style={{ overflowY: 'auto', display: 'block' }}>
              <div className="p-4">
                {!activeDocument && (
                  <div className="flex items-center gap-3 mb-4 px-4 py-3 bg-amber-50 border border-amber-200 rounded-xl max-w-3xl mx-auto">
                    <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                    <span className="text-sm text-amber-800">
                      No document loaded.{' '}
                      <button
                        onClick={() => handleNavSelect('upload')}
                        className="underline font-semibold hover:text-amber-900"
                      >
                        Upload one
                      </button>{' '}
                      first to get the best results from templates.
                    </span>
                  </div>
                )}
                <TemplateSelector
                  onTemplateExecute={handleTemplateExecute}
                  useWebSearch={useWebSearch}
                />
                {templateResults.map((result, index) => (
                  <TemplateResults key={index} response={result} />
                ))}
              </div>
            </div>
          ) : activeTab === 'chat' ? (
            <>
              <div className="chat-container">

                {/* Document context banner */}
                {activeDocument ? (
                  <div className="flex items-center gap-3 px-5 py-3 border-b border-gray-100 bg-green-50">
                    <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0" />
                    <span className="text-sm text-green-800">
                      Analysing: <strong className="font-semibold">{activeDocument}</strong>
                    </span>
                    <button
                      onClick={() => handleNavSelect('upload')}
                      className="ml-auto text-xs text-green-700 underline hover:text-green-900"
                    >
                      Change document
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-3 px-5 py-3 border-b border-amber-100 bg-amber-50">
                    <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                    <span className="text-sm text-amber-800">
                      No document loaded —{' '}
                      <button
                        onClick={() => handleNavSelect('upload')}
                        className="underline font-semibold hover:text-amber-900"
                      >
                        upload a file
                      </button>{' '}
                      to start analysing your engineering diagrams.
                    </span>
                  </div>
                )}

                {messages.length === 0 ? (
                  <div className="welcome">
                    <div className="welcome-icon">
                      <FileText size={44} />
                    </div>
                    <h2>
                      {activeDocument
                        ? 'Ask anything about your diagram'
                        : 'Ready to analyse your engineering diagram'}
                    </h2>
                    <p>
                      {activeDocument
                        ? `Chatting with: ${activeDocument}`
                        : 'Upload a PDF, image, or schematic to get started.'}
                    </p>
                    <p className="welcome-hint">Click any example question below to begin.</p>
                  </div>
                ) : (
                  <div className="messages">
                    {messages.map((message, idx) => (
                      <div key={idx} className={`message message-${message.role}`}>
                        <div className="message-avatar">{message.role === 'user' ? 'U' : 'AI'}</div>
                        <div className="message-content">
                          <div className="message-text">{message.content}</div>
                          <div className="message-time">{message.timestamp.toLocaleTimeString()}</div>
                        </div>
                      </div>
                    ))}
                    {isLoading && (
                      <div className="message message-assistant">
                        <div className="message-avatar">AI</div>
                        <div className="message-content">
                          <div className="message-loading">
                            <Loader2 className="spinner" size={20} />
                            <span>Thinking...</span>
                          </div>
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </div>

              <div className="composer-panel">
                <div className="example-questions-bar">
                  <p className="example-questions-title">Example Questions</p>
                  <div className="example-questions-grid">
                    {sampleQuestions.map((question, idx) => (
                      <button
                        key={idx}
                        className="example-question-btn"
                        onClick={() => setInput(question)}
                        disabled={isLoading}
                        type="button"
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                </div>

                <form className="input-form" onSubmit={handleSubmit}>
                  <div className="input-form-wrapper">
                    <input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Ask a question about your diagrams..."
                      disabled={isLoading}
                      className="input-field"
                    />
                    <label className="web-search-label">
                      <input
                        type="checkbox"
                        checked={useWebSearch}
                        onChange={(e) => setUseWebSearch(e.target.checked)}
                        disabled={isLoading}
                        className="web-search-checkbox"
                      />
                      Enable Bing web search context
                    </label>
                  </div>
                  <button
                    type="submit"
                    disabled={isLoading || !input.trim()}
                    className="send-button"
                  >
                    {isLoading ? <Loader2 className="spinner" size={20} /> : <Send size={20} />}
                  </button>
                </form>
              </div>
            </>
          ) : activeTab === 'features' ? (
            <InnovativeFeatures />
          ) : (
            <FlickeringAnalysis />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
