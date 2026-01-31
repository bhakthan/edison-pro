import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Play, Clock, Search, FileCheck, Loader2, FileText } from 'lucide-react';
import { api } from '../api/client';
import type { AnalysisTemplate, TemplateExecutionRequest, TemplateExecutionResponse } from '../types';

interface TemplateSelectorProps {
  onTemplateExecute: (response: TemplateExecutionResponse) => void;
  useWebSearch: boolean;
}

export function TemplateSelector({ onTemplateExecute, useWebSearch }: TemplateSelectorProps) {
  const [templates, setTemplates] = useState<AnalysisTemplate[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchKeywords, setSearchKeywords] = useState('');
  const [isExpanded, setIsExpanded] = useState(true);
  const [selectedTemplate, setSelectedTemplate] = useState<AnalysisTemplate | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [loading, setLoading] = useState(false);

  const categories = [
    { value: 'all', label: 'All Templates' },
    { value: 'ELECTRICAL', label: 'Electrical' },
    { value: 'MECHANICAL', label: 'Mechanical' },
    { value: 'PID', label: 'P&ID' },
    { value: 'STRUCTURAL', label: 'Structural' },
    { value: 'GENERAL', label: 'General' }
  ];

  useEffect(() => {
    loadTemplates();
  }, [selectedCategory]);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const categoryParam = selectedCategory === 'all' ? undefined : selectedCategory;
      const templateList = await api.getTemplates(categoryParam);
      setTemplates(templateList);
    } catch (error) {
      console.error('Failed to load templates:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchKeywords.trim()) {
      loadTemplates();
      return;
    }

    try {
      setLoading(true);
      const keywords = searchKeywords.split(' ').filter(k => k.trim());
      const searchResults = await api.searchTemplates(keywords);
      setTemplates(searchResults);
    } catch (error) {
      console.error('Failed to search templates:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteTemplate = async (template: AnalysisTemplate) => {
    if (isExecuting) return;

    try {
      setIsExecuting(true);
      setSelectedTemplate(template);

      const request: TemplateExecutionRequest = {
        template_id: template.template_id,
        use_web_search: useWebSearch,
        skip_questions: []
      };

      const response = await api.executeTemplate(request);
      onTemplateExecute(response);
      setIsExpanded(false);
    } catch (error) {
      console.error('Failed to execute template:', error);
    } finally {
      setIsExecuting(false);
      setSelectedTemplate(null);
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-lg mb-6 overflow-visible">
      {/* Header - Clickable Button */}
      <button
        type="button"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          console.log('Template selector clicked, current state:', isExpanded);
          setIsExpanded(!isExpanded);
        }}
        className="w-full px-6 py-6 flex items-center justify-between text-left hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 transition-all duration-200 bg-white border-b border-gray-100 cursor-pointer min-h-[80px] relative z-10"
      >
        <div className="flex items-center gap-4 pointer-events-none">
          <div className="p-3 bg-blue-100 rounded-lg">
            <FileCheck className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <span className="font-semibold text-gray-900 text-xl block">Analysis Templates</span>
            <p className="text-sm text-gray-500 mt-1">{templates.length} professional templates available</p>
          </div>
        </div>
        <div className="flex items-center gap-3 pointer-events-none">
          <span className="px-4 py-2 bg-blue-100 text-blue-700 text-sm font-medium rounded-full">
            {isExpanded ? 'Click to collapse' : 'Click to expand'}
          </span>
          {isExpanded ? (
            <ChevronUp className="w-6 h-6 text-gray-600" />
          ) : (
            <ChevronDown className="w-6 h-6 text-gray-600" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-6 py-6 bg-gradient-to-br from-gray-50 to-blue-50 max-h-[600px] overflow-y-auto">
          {/* Search and Filter */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
            <div className="lg:col-span-2">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search templates by keywords, category, or use case..."
                  value={searchKeywords}
                  onChange={(e) => setSearchKeywords(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900 placeholder-gray-500 shadow-sm transition-all duration-200"
                />
              </div>
            </div>
            <div className="flex gap-3">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="flex-1 px-4 py-3 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900 shadow-sm transition-all duration-200"
                aria-label="Select template category"
              >
                {categories.map(cat => (
                  <option key={cat.value} value={cat.value}>{cat.label}</option>
                ))}
              </select>
              <button
                onClick={handleSearch}
                disabled={loading}
                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg text-sm font-medium hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg hover:shadow-xl transition-all duration-200"
              >
                <Search className="w-4 h-4" />
                Search
              </button>
            </div>
          </div>

          {/* Templates Grid */}
          {loading ? (
            <div className="flex items-center justify-center py-12 bg-white rounded-xl">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-3" />
                <p className="text-gray-600 font-medium">Loading professional templates...</p>
                <p className="text-gray-400 text-sm">Please wait while we prepare your analysis tools</p>
              </div>
            </div>
          ) : templates.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-xl border-2 border-dashed border-gray-200">
              <FileCheck className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-700 mb-2">No templates found</h3>
              <p className="text-gray-500">Try different search keywords or select a different category.</p>
            </div>
          ) : (
            <div className="grid gap-6">
              {templates.map((template) => (
                <div
                  key={template.template_id}
                  className="group bg-white border border-gray-200 rounded-xl p-6 hover:border-blue-300 hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      {/* Header */}
                      <div className="flex items-center gap-3 mb-4">
                        <div className="p-2 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-lg">
                          <FileCheck className="w-5 h-5 text-blue-600" />
                        </div>
                        <div className="flex-1">
                          <h3 className="font-bold text-gray-900 text-lg group-hover:text-blue-700 transition-colors">{template.name}</h3>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="px-3 py-1 bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-800 text-xs font-semibold rounded-full border border-blue-200">
                              {template.category}
                            </span>
                            <span className="text-xs text-gray-500">• Professional Grade</span>
                          </div>
                        </div>
                      </div>
                      
                      {/* Description */}
                      <p className="text-gray-600 mb-4 leading-relaxed">{template.description}</p>
                      
                      {/* Stats */}
                      <div className="grid grid-cols-3 gap-4 mb-4 p-4 bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg border border-gray-100">
                        <div className="text-center">
                          <Clock className="w-4 h-4 text-blue-600 mx-auto mb-1" />
                          <div className="text-sm font-semibold text-gray-900">{template.estimated_time_minutes} min</div>
                          <div className="text-xs text-gray-500">Duration</div>
                        </div>
                        <div className="text-center">
                          <FileText className="w-4 h-4 text-green-600 mx-auto mb-1" />
                          <div className="text-sm font-semibold text-gray-900">{template.questions.length}</div>
                          <div className="text-xs text-gray-500">Questions</div>
                        </div>
                        <div className="text-center">
                          {template.requires_web_search ? (
                            <Search className="w-4 h-4 text-purple-600 mx-auto mb-1" />
                          ) : (
                            <FileCheck className="w-4 h-4 text-blue-600 mx-auto mb-1" />
                          )}
                          <div className="text-xs text-gray-500">
                            {template.requires_web_search ? 'Web Enhanced' : 'Offline Ready'}
                          </div>
                        </div>
                      </div>

                      {/* Use Case */}
                      <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg mb-4">
                        <div className="flex items-start gap-2">
                          <div className="p-1 bg-amber-200 rounded">
                            <FileText className="w-3 h-3 text-amber-700" />
                          </div>
                          <div>
                            <div className="text-xs font-semibold text-amber-800 uppercase tracking-wide mb-1">Use Case</div>
                            <div className="text-sm text-amber-700">{template.use_case}</div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Execute Button */}
                    <div className="ml-6">
                      <button
                        onClick={() => handleExecuteTemplate(template)}
                        disabled={isExecuting}
                        className="px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg font-semibold hover:from-green-700 hover:to-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105"
                      >
                        {isExecuting && selectedTemplate?.template_id === template.template_id ? (
                          <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            <span className="text-white">Executing...</span>
                          </>
                        ) : (
                          <>
                            <Play className="w-5 h-5" />
                            <span className="text-white">Execute</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Questions Preview */}
                  {template.questions.length > 0 && (
                    <details className="mt-6 group-hover:bg-blue-50 rounded-lg transition-colors duration-200">
                      <summary className="px-4 py-3 text-sm font-medium text-blue-700 cursor-pointer hover:text-blue-800 transition-colors flex items-center gap-2">
                        <ChevronDown className="w-4 h-4" />
                        Preview Analysis Questions ({template.questions.length})
                      </summary>
                      <div className="px-4 pb-4 mt-2">
                        <div className="bg-white border border-blue-200 rounded-lg p-4 space-y-3">
                          {template.questions.slice(0, 3).map((question, idx) => (
                            <div key={idx} className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                              <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">
                                {idx + 1}
                              </div>
                              <div className="flex-1">
                                <div className="text-sm font-medium text-gray-900 mb-1">{question.question}</div>
                                <div className="text-xs text-blue-600 font-medium">{question.purpose}</div>
                              </div>
                            </div>
                          ))}
                          {template.questions.length > 3 && (
                            <div className="text-center py-2 text-sm text-gray-500 border-t border-gray-200">
                              <span className="bg-gray-100 px-3 py-1 rounded-full">
                                +{template.questions.length - 3} more professional questions
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    </details>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}