const BASE_URL = 'http://127.0.0.1:8000';

export const apiClient = {
  /** GET /models */
  async getModels() {
    const res = await fetch(`${BASE_URL}/models`);
    if (!res.ok) throw new Error('Failed to fetch models');
    return res.json();
  },
  
  /** GET /history */
  async getHistory(limit = 20) {
    const res = await fetch(`${BASE_URL}/history?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch history');
    return res.json();
  },
  
  /** POST /simulate */
  async simulate(payload) {
    const res = await fetch(`${BASE_URL}/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err?.detail || 'Simulation execution failed.');
    }
    return res.json();
  },
  
  /** POST /detect */
  async detect(payload) {
    const res = await fetch(`${BASE_URL}/detect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err?.detail || 'ML Threat Detection failed.');
    }
    return res.json();
  }
};
