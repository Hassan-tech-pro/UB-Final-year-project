import { WorkflowResponse, BenchmarkResult, ToolMetadata, SampleFile } from '../types';

const API_BASE = 'http://localhost:8000/api';
const WS_BASE = 'ws://localhost:8000/ws';

export const api = {
  async startWorkflow(objective: string, files: File[]): Promise<{ workflow_id: string; status: string }> {
    const formData = new FormData();
    formData.append('objective', objective);
    for (const f of files) {
      formData.append('files', f);
    }
    const res = await fetch(`${API_BASE}/workflows`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to start workflow');
    }
    return res.json();
  },

  async listWorkflows(limit = 20): Promise<Array<any>> {
    const res = await fetch(`${API_BASE}/workflows?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch workflows');
    return res.json();
  },

  async getWorkflow(workflowId: string): Promise<WorkflowResponse> {
    const res = await fetch(`${API_BASE}/workflows/${workflowId}`);
    if (!res.ok) throw new Error(`Failed to load workflow ${workflowId}`);
    return res.json();
  },

  async cancelWorkflow(workflowId: string): Promise<void> {
    await fetch(`${API_BASE}/workflows/${workflowId}/cancel`, { method: 'POST' });
  },

  async listTools(): Promise<ToolMetadata[]> {
    const res = await fetch(`${API_BASE}/tools`);
    if (!res.ok) throw new Error('Failed to list tools');
    return res.json();
  },

  async getSampleFiles(): Promise<SampleFile[]> {
    const res = await fetch(`${API_BASE}/sample-files`);
    if (!res.ok) throw new Error('Failed to fetch sample files');
    return res.json();
  },

  async runBenchmark(): Promise<BenchmarkResult> {
    const res = await fetch(`${API_BASE}/evaluation/run`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to run benchmark suite');
    return res.json();
  },

  async getEvaluationHistory(): Promise<BenchmarkResult[]> {
    const res = await fetch(`${API_BASE}/evaluation/history`);
    if (!res.ok) throw new Error('Failed to fetch benchmark history');
    return res.json();
  },

  getDownloadUrl(filename: string): string {
    return `${API_BASE}/files/download/${encodeURIComponent(filename)}`;
  },

  createWebSocket(workflowId: string, onMessage: (event: any) => void): WebSocket {
    const ws = new WebSocket(`${WS_BASE}/workflows/${workflowId}`);
    ws.onmessage = (msg) => {
      try {
        const parsed = JSON.parse(msg.data);
        onMessage(parsed);
      } catch (e) {
        console.warn('Failed to parse WS message', e);
      }
    };
    return ws;
  }
};
