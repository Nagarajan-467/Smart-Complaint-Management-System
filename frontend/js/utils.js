/**
 * utils.js — shared helpers used across all pages
 */

// ── Toast Notifications ────────────────────────────────────────────────────

let _toastContainer = null;

function _getToastContainer() {
  if (!_toastContainer) {
    _toastContainer = document.createElement('div');
    _toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
    _toastContainer.style.zIndex = 9999;
    document.body.appendChild(_toastContainer);
  }
  return _toastContainer;
}

/**
 * Show a Bootstrap toast.
 * @param {string} message
 * @param {'success'|'danger'|'warning'|'info'} type
 */
function showToast(message, type = 'info') {
  const container = _getToastContainer();
  const id = 'toast-' + Date.now();
  const iconMap = {
    success: 'bi-check-circle-fill',
    danger:  'bi-x-circle-fill',
    warning: 'bi-exclamation-triangle-fill',
    info:    'bi-info-circle-fill',
  };
  const icon = iconMap[type] || iconMap.info;

  const html = `
    <div id="${id}" class="toast align-items-center text-bg-${type} border-0 mb-2" role="alert" aria-live="assertive">
      <div class="d-flex">
        <div class="toast-body">
          <i class="bi ${icon} me-2"></i>${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    </div>`;
  container.insertAdjacentHTML('beforeend', html);
  const el = document.getElementById(id);
  const toast = new bootstrap.Toast(el, { delay: 4000 });
  toast.show();
  el.addEventListener('hidden.bs.toast', () => el.remove());
}

// ── Loading Overlay ────────────────────────────────────────────────────────

function showLoading(show = true) {
  let overlay = document.getElementById('scm-loading-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'scm-loading-overlay';
    overlay.innerHTML = `
      <div class="d-flex justify-content-center align-items-center h-100">
        <div class="spinner-border text-primary" role="status" style="width:3rem;height:3rem;">
          <span class="visually-hidden">Loading…</span>
        </div>
      </div>`;
    overlay.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(255,255,255,.7);z-index:8888;';
    document.body.appendChild(overlay);
  }
  overlay.style.display = show ? 'block' : 'none';
}

// ── Formatters ─────────────────────────────────────────────────────────────

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

function formatDateShort(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString();
}

const PRIORITY_BADGE = {
  low:      'bg-secondary',
  medium:   'bg-warning text-dark',
  high:     'bg-danger',
  critical: 'bg-dark',
};

const STATUS_BADGE = {
  pending:     'bg-warning text-dark',
  assigned:    'bg-info text-dark',
  in_progress: 'bg-primary',
  resolved:    'bg-success',
  closed:      'bg-secondary',
  escalated:   'bg-danger',
};

function priorityBadge(p) {
  return `<span class="badge ${PRIORITY_BADGE[p] || 'bg-secondary'}">${p}</span>`;
}

function statusBadge(s) {
  return `<span class="badge ${STATUS_BADGE[s] || 'bg-secondary'}">${s?.replace('_', ' ')}</span>`;
}

function capitalize(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}

// ── Query Params ───────────────────────────────────────────────────────────

function getParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

// ── Pagination Helper ──────────────────────────────────────────────────────

/**
 * Render Bootstrap pagination nav.
 * @param {number} currentPage
 * @param {number} totalPages
 * @param {function} onPageClick  called with page number
 */
function renderPagination(containerId, currentPage, totalPages, onPageClick) {
  const container = document.getElementById(containerId);
  if (!container || totalPages <= 1) {
    if (container) container.innerHTML = '';
    return;
  }
  const pages = [];
  for (let i = 1; i <= totalPages; i++) pages.push(i);

  container.innerHTML = `
    <nav><ul class="pagination justify-content-center flex-wrap mb-0">
      <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
        <a class="page-link" href="#" data-page="${currentPage - 1}">‹</a>
      </li>
      ${pages.map(p => `
        <li class="page-item ${p === currentPage ? 'active' : ''}">
          <a class="page-link" href="#" data-page="${p}">${p}</a>
        </li>`).join('')}
      <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
        <a class="page-link" href="#" data-page="${currentPage + 1}">›</a>
      </li>
    </ul></nav>`;

  container.querySelectorAll('[data-page]').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      const p = parseInt(a.dataset.page);
      if (p >= 1 && p <= totalPages) onPageClick(p);
    });
  });
}

// ── Expose globals ─────────────────────────────────────────────────────────
window.SCMUtils = {
  showToast, showLoading, formatDate, formatDateShort,
  priorityBadge, statusBadge, capitalize, getParam, renderPagination
};
