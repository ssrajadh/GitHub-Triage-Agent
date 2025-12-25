import React, { useState } from 'react';
import { Check, X, Edit, Loader2, AlertCircle } from 'lucide-react';
import { AgentState } from '@/types';
import { apiService } from '@/services/api';

interface ActionPanelProps {
  state: AgentState | null;
  onActionComplete: () => void;
}

const ActionPanel: React.FC<ActionPanelProps> = ({ state, onActionComplete }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const canTakeAction = state && 
    state.draft_response && 
    state.approval_status === 'pending' &&
    state.processing_stage === 'awaiting_approval';

  const handleApprove = async () => {
    if (!state) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Generate approval token (in production, this would come from the backend)
      const approvalToken = `approval_${state.issue_id}_${Date.now()}`;
      
      await apiService.approveDraft(state.issue_id, approvalToken);
      setSuccessMessage('Response approved and posted to GitHub!');
      setTimeout(() => {
        onActionComplete();
        setSuccessMessage(null);
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to approve response');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReject = async () => {
    if (!state) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      await apiService.rejectDraft(state.issue_id, 'Manual rejection from dashboard');
      setSuccessMessage('Response rejected');
      setTimeout(() => {
        onActionComplete();
        setSuccessMessage(null);
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to reject response');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEdit = () => {
    if (!state) return;
    setEditedContent(state.draft_response);
    setIsEditing(true);
  };

  const handleSaveEdit = async () => {
    if (!state) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const approvalToken = `approval_${state.issue_id}_${Date.now()}`;
      
      await apiService.editAndApproveDraft(state.issue_id, editedContent, approvalToken);
      setSuccessMessage('Edited response approved and posted!');
      setIsEditing(false);
      setTimeout(() => {
        onActionComplete();
        setSuccessMessage(null);
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to save edited response');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditedContent('');
  };

  if (!state) {
    return (
      <div className="h-full bg-gray-50 border-t p-6 flex items-center justify-center">
        <p className="text-gray-500">Select an issue to take action</p>
      </div>
    );
  }

  return (
    <div className="bg-white border-t p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">Action Center</h3>

      {/* Status Messages */}
      {successMessage && (
        <div className="mb-4 p-3 bg-green-100 border border-green-300 text-green-800 rounded flex items-center gap-2">
          <Check className="w-5 h-5" />
          <span>{successMessage}</span>
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-300 text-red-800 rounded flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      )}

      {/* Edit Mode */}
      {isEditing ? (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Edit Response
            </label>
            <textarea
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              className="w-full h-48 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
              placeholder="Edit the agent's response..."
            />
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleSaveEdit}
              disabled={isLoading || !editedContent.trim()}
              className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Check className="w-5 h-5" />
                  Save & Approve
                </>
              )}
            </button>
            <button
              onClick={handleCancelEdit}
              disabled={isLoading}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        /* Action Buttons */
        <div className="space-y-3">
          <button
            onClick={handleApprove}
            disabled={!canTakeAction || isLoading}
            className="w-full bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium transition-colors"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Check className="w-5 h-5" />
                Approve & Post to GitHub
              </>
            )}
          </button>

          <button
            onClick={handleEdit}
            disabled={!canTakeAction || isLoading}
            className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium transition-colors"
          >
            <Edit className="w-5 h-5" />
            Edit Before Approving
          </button>

          <button
            onClick={handleReject}
            disabled={!canTakeAction || isLoading}
            className="w-full bg-red-600 text-white px-6 py-3 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium transition-colors"
          >
            <X className="w-5 h-5" />
            Reject Response
          </button>

          {!canTakeAction && state && (
            <p className="text-sm text-gray-600 text-center mt-2">
              {state.approval_status === 'approved' && '✓ Already approved'}
              {state.approval_status === 'rejected' && '✗ Already rejected'}
              {!state.draft_response && 'Waiting for agent to generate response...'}
            </p>
          )}
        </div>
      )}

      {/* Metadata */}
      <div className="mt-6 pt-6 border-t text-sm text-gray-600 space-y-1">
        <p><span className="font-medium">Status:</span> {state.processing_stage}</p>
        <p><span className="font-medium">Classification:</span> {state.classification || 'Pending'}</p>
        <p><span className="font-medium">Context Chunks:</span> {state.retrieved_context?.length || 0}</p>
      </div>
    </div>
  );
};

export default ActionPanel;
