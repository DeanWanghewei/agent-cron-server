const API_BASE = '/api/v1';

const api = {
  // Health
  async getHealth() {
    const res = await fetch('/health');
    return res.json();
  },

  // Tasks
  async listTasks(params = {}) {
    const qs = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/tasks?${qs}`);
    return res.json();
  },

  async getTask(id) {
    const res = await fetch(`${API_BASE}/tasks/${id}`);
    if (!res.ok) return null;
    return res.json();
  },

  async deleteTask(id) {
    const res = await fetch(`${API_BASE}/tasks/${id}`, { method: 'DELETE' });
    return res.ok;
  },

  async enableTask(id) {
    const res = await fetch(`${API_BASE}/tasks/${id}/enable`, { method: 'POST' });
    return res.json();
  },

  async disableTask(id) {
    const res = await fetch(`${API_BASE}/tasks/${id}/disable`, { method: 'POST' });
    return res.json();
  },

  async triggerTask(id) {
    const res = await fetch(`${API_BASE}/tasks/${id}/trigger`, { method: 'POST' });
    return res.json();
  },

  // Executions
  async listExecutions(params = {}) {
    const qs = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/executions?${qs}`);
    return res.json();
  },

  async getExecution(id) {
    const res = await fetch(`${API_BASE}/executions/${id}`);
    if (!res.ok) return null;
    return res.json();
  },

  async getExecutionLog(id) {
    const res = await fetch(`${API_BASE}/executions/${id}/log`);
    if (!res.ok) return null;
    return res.json();
  },

  async deleteExecution(id) {
    const res = await fetch(`${API_BASE}/executions/${id}`, { method: 'DELETE' });
    return res.ok;
  },
};
