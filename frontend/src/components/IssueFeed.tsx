import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { FileText, Clock, AlertCircle, MessageSquare, GitBranch } from 'lucide-react';
import { AgentState } from '@/types';

interface IssueFeedProps {
  states: AgentState[];
  onSelectIssue: (state: AgentState) => void;
  selectedIssueId?: string;
}

const IssueFeed: React.FC<IssueFeedProps> = ({ states, onSelectIssue, selectedIssueId }) => {
  const getClassificationIcon = (classification: string | null) => {
    switch (classification) {
      case 'BUG':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'FEATURE':
        return <GitBranch className="w-4 h-4 text-blue-500" />;
      case 'QUESTION':
        return <MessageSquare className="w-4 h-4 text-green-500" />;
      default:
        return <FileText className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
      case 'awaiting_approval':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'approved':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'rejected':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'error':
        return 'bg-red-100 text-red-800 border-red-300';
      default:
        return 'bg-blue-100 text-blue-800 border-blue-300';
    }
  };

  const getStatusText = (stage: string) => {
    return stage.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  return (
    <div className="h-full overflow-y-auto bg-gray-50">
      <div className="p-4 bg-white border-b sticky top-0 z-10">
        <h2 className="text-xl font-bold text-gray-800">Live Issue Feed</h2>
        <p className="text-sm text-gray-600 mt-1">
          {states.length} issue{states.length !== 1 ? 's' : ''} being processed
        </p>
      </div>
      
      <div className="divide-y divide-gray-200">
        {states.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <FileText className="w-12 h-12 mx-auto mb-3 text-gray-400" />
            <p className="text-lg font-medium">No issues yet</p>
            <p className="text-sm mt-1">Waiting for GitHub webhooks...</p>
          </div>
        ) : (
          states.map((state) => (
            <div
              key={state.issue_id}
              onClick={() => onSelectIssue(state)}
              className={`p-4 cursor-pointer transition-colors hover:bg-blue-50 ${
                selectedIssueId === state.issue_id ? 'bg-blue-100 border-l-4 border-blue-600' : 'bg-white'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  {getClassificationIcon(state.classification)}
                  <h3 className="font-semibold text-gray-900 truncate">
                    {state.issue_title}
                  </h3>
                </div>
                <span
                  className={`px-2 py-1 text-xs font-medium rounded-full border ${getStatusColor(
                    state.approval_status
                  )}`}
                >
                  {getStatusText(state.processing_stage)}
                </span>
              </div>

              <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                {state.issue_body}
              </p>

              <div className="flex items-center gap-4 text-xs text-gray-500">
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatDistanceToNow(new Date(state.timestamp), { addSuffix: true })}
                </div>
                {state.classification && (
                  <span className="px-2 py-0.5 bg-gray-100 rounded">
                    {state.classification}
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default IssueFeed;
