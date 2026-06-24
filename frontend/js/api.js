/**
 * api.js — centralized API service
 */

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : window.location.origin;

const TOKEN_KEY = 'scm_token';
const USER_KEY  = 'scm_user';

// ── Token Management ───────────────────────────────────────────────────────

function getToken()       { return localStorage.getItem(TOKEN_KEY); }
function setToken(t)      { localStorage.setItem(TOKEN_KEY, t); }
function removeToken()    { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); }
function getCachedUser()  { try { return JSON.parse(localStorage.getItem(USER_KEY)); } catch { return null; } }
function setCachedUser(u) { localStorage.setItem(USER_KEY, JSON.stringify(u)); }

// ── Core fetch wrapper ─────────────────────────────────────────────────────

async function request(path, opts = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
  } catch (e) {
    throw { status: 0, detail: 'Cannot reach the server. Make sure the backend is running on port 8000.' };
  }

  if (res.status === 401) {
    removeToken();
    window.location.href = '/frontend/pages/login.html';
    return;
  }

  if (res.status === 204) return null;

  let data;
  try { data = await res.json(); } catch { data = null; }

  if (!res.ok) {
    throw { status: res.status, detail: data?.detail || `HTTP ${res.status}` };
  }
  return data;
}

// ── Auth APIs ──────────────────────────────────────────────────────────────

async function login(username, password) {
  const body = new URLSearchParams({ username, password });
  let res;
  try {
    res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
  } catch (e) {
    throw { status: 0, detail: 'Cannot reach the server. Make sure the backend is running on port 8000.' };
  }
  const data = await res.json();
  if (!res.ok) throw { status: res.status, detail: data?.detail || 'Login failed' };
  return data;
}

async function register(payload) {
  return request('/api/v1/auth/register', { method: 'POST', body: JSON.stringify(payload) });
}

async function getMe() {
  return request('/api/v1/auth/me');
}

// ── Complaint APIs ─────────────────────────────────────────────────────────

async function listComplaints(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== '') qs.set(k, v); });
  return request(`/api/v1/complaints/?${qs}`);
}

async function getComplaint(id) {
  return request(`/api/v1/complaints/${id}`);
}

async function createComplaint(payload) {
  return request('/api/v1/complaints/', { method: 'POST', body: JSON.stringify(payload) });
}

async function updateComplaint(id, payload) {
  return request(`/api/v1/complaints/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
}

async function deleteComplaint(id) {
  return request(`/api/v1/complaints/${id}`, { method: 'DELETE' });
}

async function assignComplaint(id, assignedTo) {
  return request(`/api/v1/complaints/${id}/assign`, {
    method: 'POST',
    body: JSON.stringify({ assigned_to: assignedTo }),
  });
}

async function runClustering() {
  return request('/api/v1/complaints/run-clustering', { method: 'POST' });
}

// ── Escalation APIs ────────────────────────────────────────────────────────

async function runEscalation() {
  return request('/api/v1/escalation/run', { method: 'POST' });
}

async function getEscalationLogs(complaintId = null) {
  const qs = complaintId ? `?complaint_id=${complaintId}` : '';
  return request(`/api/v1/escalation/logs${qs}`);
}

async function getSchedulerStatus() {
  return request('/api/v1/escalation/scheduler-status');
}

// ── Analytics APIs ─────────────────────────────────────────────────────────

async function getAnalyticsDashboard(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== '') qs.set(k, v); });
  return request(`/api/v1/analytics/dashboard?${qs}`);
}

async function getAnalyticsSection(section, params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== '') qs.set(k, v); });
  return request(`/api/v1/analytics/${section}?${qs}`);
}

// ── Route Guards ───────────────────────────────────────────────────────────

function requireAuth() {
  if (!getToken()) {
    window.location.href = '/frontend/pages/login.html';
  }
}

async function requireRole(...allowedRoles) {
  requireAuth();
  let user = getCachedUser();
  if (!user) {
    try {
      user = await getMe();
      setCachedUser(user);
    } catch {
      removeToken();
      window.location.href = '/frontend/pages/login.html';
      return null;
    }
  }
  if (!allowedRoles.includes(user.role)) {
    window.location.href = _homeForRole(user.role);
    return null;
  }
  return user;
}

function _homeForRole(role) {
  const map = {
    student: '/frontend/pages/student/dashboard.html',
    staff:   '/frontend/pages/staff/dashboard.html',
    admin:   '/frontend/pages/admin/dashboard.html',
  };
  return map[role] || '/frontend/pages/login.html';
}

function logout() {
  removeToken();
  window.location.href = '/frontend/pages/login.html';
}

// ── Expose ─────────────────────────────────────────────────────────────────
window.API = {
  login, register, getMe, getCachedUser, setCachedUser,
  listComplaints, getComplaint, createComplaint, updateComplaint,
  deleteComplaint, assignComplaint, runClustering,
  runEscalation, getEscalationLogs, getSchedulerStatus,
  getAnalyticsDashboard, getAnalyticsSection,
  requireAuth, requireRole, logout,
  getToken, setToken, removeToken,
};
