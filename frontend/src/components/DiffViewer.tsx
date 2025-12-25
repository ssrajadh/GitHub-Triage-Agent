import React from 'react';
import ReactMarkdown from 'react-markdown';
import { AgentState } from '@/types';
import { FileText, Sparkles, AlertTriangle } from 'lucide-react';

interface DiffViewerProps {
  state: AgentState | null;
}

const DiffViewer: React.FC<DiffViewerProps> = ({ state }) => {
  if (!state) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center text-gray-500">
          <FileText className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <p className="text-lg font-medium">Select an issue to view details</p>
          <p className="text-sm mt-2">Choose an issue from the feed on the left</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="p-4 border-b bg-gray-50">
        <h2 className="text-xl font-bold text-gray-800 mb-1">{state.issue_title}</h2>
        <p className="text-sm text-gray-600">Issue ID: {state.issue_id}</p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="grid grid-cols-2 divide-x h-full">
          {/* Original Issue */}
          <div className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <FileText className="w-5 h-5 text-gray-600" />
              <h3 className="text-lg font-semibold text-gray-800">Original Issue</h3>
            </div>
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown>{state.issue_body}</ReactMarkdown>
            </div>

            {/* Retrieved Context */}
            {state.retrieved_context && state.retrieved_context.length > 0 && (
              <div className="mt-6 pt-6 border-t">
                <h4 className="text-md font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-500" />
                  Retrieved Context ({state.retrieved_context.length} chunks)
                </h4>
                <div className="space-y-2">
                  {state.retrieved_context.slice(0, 3).map((context, idx) => (
                    <div key={idx} className="p-3 bg-purple-50 border border-purple-200 rounded text-sm">
                      <p className="text-gray-700 line-clamp-3">{context}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Agent's Draft Response */}
          <div className="p-6 bg-blue-50">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-5 h-5 text-blue-600" />
              <h3 className="text-lg font-semibold text-gray-800">Agent's Draft Response</h3>
            </div>

            {state.draft_response ? (
              <div className="prose prose-sm max-w-none prose-headings:text-blue-900 prose-a:text-blue-600">
                <ReactMarkdown>{state.draft_response}</ReactMarkdown>
              </div>
            ) : (
              <div className="flex items-center justify-center h-48">
                <div className="text-center text-gray-500">
                  {state.processing_stage === 'error' ? (
                    <>
                      <AlertTriangle className="w-10 h-10 mx-auto mb-2 text-red-500" />
                      <p className="font-medium">Error generating response</p>
                    </>
                  ) : (
                    <>
                      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto mb-2" />
                      <p className="font-medium">Generating response...</p>
                      <p className="text-sm mt-1 capitalize">{state.processing_stage.replace('_', ' ')}</p>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DiffViewer;
