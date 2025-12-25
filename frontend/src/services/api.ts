import axios from 'axios';
import { Issue, DraftResponse } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiService = {
  // Health check
  async healthCheck() {
    const response = await api.get('/health');
    return response.data;
  },

  // Get all pending drafts
  async getPendingDrafts(): Promise<DraftResponse[]> {
    const response = await api.get('/api/drafts/pending');
    return response.data;
  },

  // Get draft by ID
  async getDraft(draftId: string): Promise<DraftResponse> {
    const response = await api.get(`/api/drafts/${draftId}`);
    return response.data;
  },

  // Approve draft
  async approveDraft(draftId: string, approvalToken: string) {
    const response = await api.post(`/api/drafts/${draftId}/approve`, {
      approval_token: approvalToken,
    });
    return response.data;
  },

  // Reject draft
  async rejectDraft(draftId: string, reason?: string) {
    const response = await api.post(`/api/drafts/${draftId}/reject`, {
      reason,
    });
    return response.data;
  },

  // Edit and approve draft
  async editAndApproveDraft(draftId: string, editedContent: string, approvalToken: string) {
    const response = await api.post(`/api/drafts/${draftId}/edit-approve`, {
      edited_content: editedContent,
      approval_token: approvalToken,
    });
    return response.data;
  },

  // Get issues
  async getIssues(): Promise<Issue[]> {
    const response = await api.get('/api/issues');
    return response.data;
  },
};

export default api;
