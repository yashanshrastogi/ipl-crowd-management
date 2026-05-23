/**
 * Backend REST API client.
 * Communicates with the FastAPI backend through the Vite proxy.
 */

import { API_BASE_URL } from '../utils/constants';

class ApiClient {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
    this.apiKey = localStorage.getItem('admin_api_key') || 'supersecret-admin-key';
  }

  setApiKey(key) {
    this.apiKey = key;
    localStorage.setItem('admin_api_key', key);
  }

  async _fetch(path, options = {}) {
    const url = `${this.baseUrl}${path}`;
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }
    const config = {
      headers,
      ...options,
    };


    const response = await fetch(url, config);
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`API Error ${response.status}: ${error}`);
    }
    return response.json();
  }

  // ── Gates ──────────────────────────────────────────────────
  getGates(stadiumId) {
    const params = stadiumId ? `?stadium_id=${stadiumId}` : '';
    return this._fetch(`/gates${params}`);
  }

  getGate(gateId) {
    return this._fetch(`/gates/${gateId}`);
  }

  updateSignage(gateId, message, priority = 'normal') {
    return this._fetch(`/gates/${gateId}/signage`, {
      method: 'POST',
      body: JSON.stringify({ gate_id: gateId, message, priority }),
    });
  }

  // ── Telemetry ──────────────────────────────────────────────
  submitTelemetry(payload) {
    return this._fetch('/telemetry', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // ── Evacuation ─────────────────────────────────────────────
  assessEvacuation(stadiumId, sensorData = {}) {
    return this._fetch('/evacuation/assess', {
      method: 'POST',
      body: JSON.stringify({ stadium_id: stadiumId, sensor_data: sensorData }),
    });
  }

  getEvacuationStatus(stadiumId) {
    const params = stadiumId ? `?stadium_id=${stadiumId}` : '';
    return this._fetch(`/evacuation/status${params}`);
  }

  triggerEvacuation(stadiumId, reason, zones = []) {
    return this._fetch('/evacuation/trigger', {
      method: 'POST',
      body: JSON.stringify({ stadium_id: stadiumId, reason, affected_zones: zones }),
    });
  }

  // ── Agents ─────────────────────────────────────────────────
  dispatchAgent(prompt, stadiumId = '') {
    return this._fetch('/agents/dispatch', {
      method: 'POST',
      body: JSON.stringify({ prompt, stadium_id: stadiumId }),
    });
  }

  getAgentStatus() {
    return this._fetch('/agents/status');
  }

  runSecurityScan(stadiumId) {
    const params = stadiumId ? `?stadium_id=${stadiumId}` : '';
    return this._fetch(`/agents/security-scan${params}`, { method: 'POST' });
  }

  requestReroute(congestedGateId, stadiumId = '') {
    return this._fetch('/agents/reroute', {
      method: 'POST',
      body: JSON.stringify({ congested_gate_id: congestedGateId, stadium_id: stadiumId }),
    });
  }

  // ── Reports ────────────────────────────────────────────────
  getReports(stadiumId, limit = 50) {
    const params = new URLSearchParams();
    if (stadiumId) params.set('stadium_id', stadiumId);
    params.set('limit', limit);
    return this._fetch(`/reports?${params}`);
  }

  submitReport(report, stadiumId) {
    const params = stadiumId ? `?stadium_id=${stadiumId}` : '';
    return this._fetch(`/reports${params}`, {
      method: 'POST',
      body: JSON.stringify(report),
    });
  }

  // ── Health ─────────────────────────────────────────────────
  healthCheck() {
    return this._fetch('/health');
  }
}

const api = new ApiClient();
export default api;
