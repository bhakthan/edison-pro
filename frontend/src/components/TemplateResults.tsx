import { CheckCircle, XCircle, Clock, FileText, BarChart3, Code } from 'lucide-react';
import type { TemplateExecutionResponse } from '../types';

interface TemplateResultsProps {
  response: TemplateExecutionResponse;
}

export function TemplateResults({ response }: TemplateResultsProps) {
  const successfulQuestions = response.results.filter(r => !r.answer.startsWith('Error:'));
  const failedQuestions = response.results.filter(r => r.answer.startsWith('Error:'));

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-8 mb-6 shadow-lg">
      {/* Header */}
      <div className="flex items-start justify-between mb-6 pb-6 border-b border-gray-100">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-gradient-to-br from-green-100 to-emerald-100 rounded-xl">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          <div>
            <h3 className="text-2xl font-bold text-gray-900 mb-2">{response.template.name}</h3>
            <p className="text-gray-600 leading-relaxed">{response.template.description}</p>
            <div className="flex items-center gap-3 mt-3">
              <span className="px-3 py-1 bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-800 text-sm font-semibold rounded-full border border-blue-200">
                {response.template.category}
              </span>
              <span className="text-sm text-gray-500">• Completed Successfully</span>
            </div>
          </div>
        </div>
      </div>

      {/* Execution Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="text-center p-6 bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl border border-green-200">
          <div className="flex items-center justify-center gap-2 text-green-600 mb-3">
            <CheckCircle className="w-8 h-8" />
          </div>
          <div className="text-3xl font-bold text-gray-900 mb-1">{successfulQuestions.length}</div>
          <div className="text-sm font-medium text-green-700">Successful</div>
        </div>
        
        <div className="text-center p-6 bg-gradient-to-br from-red-50 to-pink-50 rounded-xl border border-red-200">
          <div className="flex items-center justify-center gap-2 text-red-600 mb-3">
            <XCircle className="w-8 h-8" />
          </div>
          <div className="text-3xl font-bold text-gray-900 mb-1">{failedQuestions.length}</div>
          <div className="text-sm font-medium text-red-700">Failed</div>
        </div>
        
        <div className="text-center p-6 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-200">
          <div className="flex items-center justify-center gap-2 text-blue-600 mb-3">
            <Clock className="w-8 h-8" />
          </div>
          <div className="text-3xl font-bold text-gray-900 mb-1">{response.total_execution_time_seconds.toFixed(1)}s</div>
          <div className="text-sm font-medium text-blue-700">Total Time</div>
        </div>
        
        <div className="text-center p-6 bg-gradient-to-br from-purple-50 to-violet-50 rounded-xl border border-purple-200">
          <div className="flex items-center justify-center gap-2 text-purple-600 mb-3">
            <FileText className="w-8 h-8" />
          </div>
          <div className="text-3xl font-bold text-gray-900 mb-1">{response.results.length}</div>
          <div className="text-sm font-medium text-purple-700">Questions</div>
        </div>
      </div>

      {/* Summary */}
      <div className="mb-8 p-6 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-blue-600 rounded-lg">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <div>
            <h4 className="font-bold text-blue-900 mb-2 text-lg">Execution Summary</h4>
            <p className="text-blue-800 leading-relaxed">{response.summary}</p>
          </div>
        </div>
      </div>

      {/* Question Results */}
      <div className="space-y-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-gray-600 rounded-lg">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <h4 className="font-bold text-gray-900 text-xl">Detailed Question Results</h4>
        </div>
        
        {response.results.map((result, index) => (
          <div
            key={index}
            className={`border-2 rounded-xl p-6 transition-all duration-200 ${
              result.answer.startsWith('Error:') 
                ? 'border-red-200 bg-gradient-to-br from-red-50 to-pink-50' 
                : 'border-green-200 bg-gradient-to-br from-green-50 to-emerald-50'
            }`}
          >
            {/* Question Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-start gap-4 flex-1">
                <div className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold ${
                  result.answer.startsWith('Error:') ? 'bg-red-500' : 'bg-green-500'
                }`}>
                  {result.answer.startsWith('Error:') ? (
                    <XCircle className="w-6 h-6" />
                  ) : (
                    <CheckCircle className="w-6 h-6" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                      result.answer.startsWith('Error:') 
                        ? 'bg-red-600 text-white' 
                        : 'bg-green-600 text-white'
                    }`}>
                      Question {result.question_index + 1}
                    </span>
                    <span className="text-sm text-gray-500 font-medium">
                      Completed in {(result.execution_time_seconds ?? 0).toFixed(1)}s
                    </span>
                  </div>
                  <h5 className="text-lg font-semibold text-gray-900 mb-3 leading-relaxed">{result.question}</h5>
                </div>
              </div>
            </div>

            {/* Answer */}
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                <h6 className="text-sm font-bold text-gray-700 uppercase tracking-wide">
                  Analysis Result
                </h6>
              </div>
              <div className={`p-4 rounded-xl border-2 ${
                result.answer.startsWith('Error:')
                  ? 'bg-red-100 border-red-300 text-red-900'
                  : 'bg-white border-gray-200 text-gray-800'
              }`}>
                <div className="prose prose-sm max-w-none">
                  {result.answer.split('\n').map((line, idx) => (
                    <p key={idx} className="mb-2 last:mb-0 leading-relaxed">
                      {line}
                    </p>
                  ))}
                </div>
              </div>
            </div>

            {/* Additional Results */}
            {!result.answer.startsWith('Error:') && (
              <div className="flex flex-wrap gap-3 mt-4 pt-4 border-t border-gray-200">
                {result.tables && result.tables.length > 0 && (
                  <div className="flex items-center gap-2 px-3 py-2 bg-blue-100 text-blue-800 rounded-lg border border-blue-200">
                    <BarChart3 className="w-4 h-4" />
                    <span className="text-sm font-medium">{result.tables.length} Table(s)</span>
                  </div>
                )}
                {result.files && result.files.length > 0 && (
                  <div className="flex items-center gap-2 px-3 py-2 bg-purple-100 text-purple-800 rounded-lg border border-purple-200">
                    <FileText className="w-4 h-4" />
                    <span className="text-sm font-medium">{result.files.length} File(s)</span>
                  </div>
                )}
                {result.charts && result.charts.length > 0 && (
                  <div className="flex items-center gap-2 px-3 py-2 bg-green-100 text-green-800 rounded-lg border border-green-200">
                    <BarChart3 className="w-4 h-4" />
                    <span className="text-sm font-medium">{result.charts.length} Chart(s)</span>
                  </div>
                )}
                {result.code_executed && (
                  <div className="flex items-center gap-2 px-3 py-2 bg-orange-100 text-orange-800 rounded-lg border border-orange-200">
                    <Code className="w-4 h-4" />
                    <span className="text-sm font-medium">Code Executed</span>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Quality Checks */}
      {response.template.quality_checks && response.template.quality_checks.length > 0 && (
        <div className="mt-8 p-6 bg-gradient-to-r from-amber-50 to-yellow-50 border-2 border-amber-200 rounded-xl">
          <div className="flex items-start gap-3 mb-4">
            <div className="p-2 bg-amber-500 rounded-lg">
              <CheckCircle className="w-5 h-5 text-white" />
            </div>
            <div>
              <h4 className="font-bold text-amber-900 text-lg">Quality Assurance Checklist</h4>
              <p className="text-amber-700 text-sm">Recommended validation steps for your analysis</p>
            </div>
          </div>
          <div className="grid gap-3">
            {response.template.quality_checks.map((check, index) => (
              <div key={index} className="flex items-start gap-3 p-3 bg-white rounded-lg border border-amber-200">
                <div className="flex-shrink-0 w-6 h-6 bg-amber-500 text-white rounded-full flex items-center justify-center text-xs font-bold mt-0.5">
                  {index + 1}
                </div>
                <div className="text-sm text-amber-800 leading-relaxed">{check}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Expected Outputs */}
      {response.template.expected_outputs && response.template.expected_outputs.length > 0 && (
        <div className="mt-6 p-6 bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-xl">
          <div className="flex items-start gap-3 mb-4">
            <div className="p-2 bg-blue-600 rounded-lg">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <div>
              <h4 className="font-bold text-blue-900 text-lg">Expected Deliverables</h4>
              <p className="text-blue-700 text-sm">Professional outputs generated by this template</p>
            </div>
          </div>
          <div className="grid gap-3">
            {response.template.expected_outputs.map((output, index) => (
              <div key={index} className="flex items-start gap-3 p-3 bg-white rounded-lg border border-blue-200">
                <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold mt-0.5">
                  {index + 1}
                </div>
                <div className="text-sm text-blue-800 leading-relaxed">{output}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}