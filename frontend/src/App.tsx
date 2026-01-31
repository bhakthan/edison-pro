import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, FileText, FileDown } from 'lucide-react';
import { api } from './api/client';
import type { Message, ChatResponse, TemplateExecutionResponse } from './types';
import { TemplateSelector } from './components/TemplateSelector';
import { TemplateResults } from './components/TemplateResults';
import { FlickeringAnalysis } from './components/FlickeringAnalysis';
import { InnovativeFeatures } from './components/InnovativeFeatures';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'features' | 'flickering'>('chat');
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

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Convert messages to history format expected by backend
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

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error asking question:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: '❌ Error: Failed to get response from server. Please check if the backend is running.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatResponse = (response: ChatResponse): string => {
    let formatted = response.answer;

    // Add web search sources
    if (response.web_search_used && response.web_sources && response.web_sources.length > 0) {
      formatted += '\n\n🔍 **Web Search Results:**\n';
      response.web_sources.forEach((source) => {
        formatted += `\n• [${source.title}](${source.url})\n  ${source.snippet}`;
      });
    }

    // Add tables
    if (response.tables && response.tables.length > 0) {
      formatted += '\n\n📊 **Generated Tables:**\n';
      response.tables.forEach((table, idx) => {
        formatted += `\nTable ${idx + 1}:\n${table.content}`;
      });
    }

    // Add file download links
    if (response.files && response.files.length > 0) {
      formatted += '\n\n📁 **Generated Files:**\n';
      response.files.forEach((file) => {
        formatted += `\n• ${file}`;
      });
    }

    // Add charts info
    if (response.charts && response.charts.length > 0) {
      formatted += `\n\n📈 **Generated ${response.charts.length} interactive chart(s)**`;
    }

    // Add execution status
    if (response.code_executed) {
      formatted += '\n\n✓ *Code executed successfully*';
    }

    return formatted;
  };

  const handleTemplateExecute = (response: TemplateExecutionResponse) => {
    setTemplateResults(prev => [response, ...prev]);
    
    // Add template execution as a system message
    const templateMessage: Message = {
      role: 'assistant',
      content: `Template "${response.template.name}" executed successfully with ${response.results.length} questions in ${response.total_execution_time_seconds.toFixed(1)} seconds.`,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, templateMessage]);
  };

  const handleGenerateResults = async () => {
    if (isGeneratingResults) return;
    
    setIsGeneratingResults(true);
    try {
      const result = await api.generateResults();
      
      // Open the results page in a new tab
      const resultsUrl = api.getLatestResultsUrl();
      window.open(resultsUrl, '_blank');
      
      // Show success message
      const successMessage: Message = {
        role: 'assistant',
        content: `✅ ${result.message}\n\nComprehensive results page has been opened in a new tab!`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, successMessage]);
    } catch (error) {
      console.error('Error generating results:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: '❌ Failed to generate results page. Make sure you have asked some questions first.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsGeneratingResults(false);
    }
  };

  const sampleQuestions = [
    "What type of diagram is this?",
    "List all transformers and their ratings",
    "What are the clearance requirements?",
    "Explain the grounding system",
    "What standards are referenced?",
    "Describe the primary distribution layout",
    "Show all transformers as a table",
    "Export components to CSV",
  ];

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="header-icon">⚡</div>
          <div>
            <h1>EDISON PRO</h1>
            <p>Engineering Diagram Analysis with AI</p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={handleGenerateResults}
              disabled={isGeneratingResults}
              className="results-button"
              title="Generate comprehensive results page with all Q&A and generated files"
            >
              {isGeneratingResults ? (
                <>
                  <Loader2 className="spinner" size={18} />
                  <span>Generating...</span>
                </>
              ) : (
                <>
                  <FileDown size={18} />
                  <span>View Full Results</span>
                </>
              )}
            </button>
          )}
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="tab-navigation">
        <button
          className={`tab-button ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          💬 Chat Analysis
        </button>
        <button
          className={`tab-button ${activeTab === 'features' ? 'active' : ''}`}
          onClick={() => setActiveTab('features')}
        >
          🔮 Innovative Features
        </button>
        <button
          className={`tab-button ${activeTab === 'flickering' ? 'active' : ''}`}
          onClick={() => setActiveTab('flickering')}
        >
          🌊 Flickering Analysis
        </button>
      </div>

      <main className="main-content">
        {activeTab === 'chat' ? (
          <>
            <div className="chat-container">
          {/* Template Selector */}
          <TemplateSelector 
            onTemplateExecute={handleTemplateExecute}
            useWebSearch={useWebSearch}
          />

          {/* Template Results */}
          {templateResults.map((result, index) => (
            <TemplateResults key={index} response={result} />
          ))}

          {messages.length === 0 && templateResults.length === 0 ? (
            <div className="welcome">
              <div className="welcome-icon">
                <FileText size={48} />
              </div>
              <h2>Welcome to EDISON PRO</h2>
              <p>Ask questions about your engineering diagrams</p>
              <p className="welcome-hint">� Click any example question below to get started</p>
            </div>
          ) : (
            <div className="messages">
              {messages.map((message, idx) => (
                <div key={idx} className={`message message-${message.role}`}>
                  <div className="message-avatar">
                    {message.role === 'user' ? '👤' : '🤖'}
                  </div>
                  <div className="message-content">
                    <div className="message-text">{message.content}</div>
                    <div className="message-time">
                      {message.timestamp.toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="message message-assistant">
                  <div className="message-avatar">🤖</div>
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

        {/* Example Questions - Always visible */}
        <div className="example-questions-bar">
          <p className="example-questions-title">💡 Example Questions (click to use):</p>
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
              🔍 Enable Bing Web Search
            </label>
          </div>
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="send-button"
          >
            {isLoading ? (
              <Loader2 className="spinner" size={20} />
            ) : (
              <Send size={20} />
            )}
          </button>
        </form>
        </>
        ) : activeTab === 'features' ? (
          <InnovativeFeatures />
        ) : (
          <FlickeringAnalysis />
        )}
      </main>
    </div>
  );
}

export default App;
