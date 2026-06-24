/**
 * components.js
 * Renders sidebar + navbar into #scm-sidebar and #scm-navbar placeholders.
 * Page content inside #app is NEVER touched.
 */

const SCMComponents = (() => {

  const NAV = {
    student: [
      { href: '/frontend/pages/student/dashboard.html',         icon: 'bi-house',               label: 'Dashboard' },
      { href: '/frontend/pages/student/create-complaint.html',  icon: 'bi-plus-circle',         label: 'New Complaint' },
      { href: '/frontend/pages/student/complaint-history.html', icon: 'bi-clock-history',       label: 'My Complaints' },
      { href: '/frontend/pages/student/feedback.html',          icon: 'bi-star',                label: 'Feedback' },
    ],
    staff: [
      { href: '/frontend/pages/staff/dashboard.html',           icon: 'bi-house',               label: 'Dashboard' },
      { href: '/frontend/pages/staff/assigned-complaints.html', icon: 'bi-list-task',           label: 'Assigned Complaints' },
    ],
    admin: [
      { href: '/frontend/pages/admin/dashboard.html',           icon: 'bi-speedometer2',        label: 'Dashboard' },
      { href: '/frontend/pages/admin/assign-complaints.html',   icon: 'bi-person-check',        label: 'Assign Complaints' },
      { href: '/frontend/pages/admin/analytics.html',           icon: 'bi-bar-chart-line',      label: 'Analytics' },
      { href: '/frontend/pages/admin/escalation.html',          icon: 'bi-exclamation-octagon', label: 'Escalation' },
      { href: '/frontend/pages/admin/users.html',               icon: 'bi-people',              label: 'Users' },
      { href: '/frontend/pages/admin/departments.html',         icon: 'bi-building',            label: 'Departments' },
    ],
  };

  async function init(pageTitle = 'SCM', allowedRoles = null) {
    const roles = allowedRoles || ['student', 'staff', 'admin'];
    const user  = await API.requireRole(...roles);
    if (!user) return null;

    const current = window.location.pathname;
    const links   = NAV[user.role] || [];

    // Render sidebar
    const sidebarEl = document.getElementById('scm-sidebar');
    if (sidebarEl) {
      sidebarEl.innerHTML = `
        <a class="sidebar-brand d-flex align-items-center gap-2"
           href="/frontend/pages/${user.role}/dashboard.html">
          <i class="bi bi-shield-check"></i> SCM System
        </a>
        <div class="pt-2 flex-grow-1">
          <div class="nav-section">Navigation</div>
          <ul class="nav flex-column">
            ${links.map(l => `
              <li class="nav-item">
                <a class="nav-link ${current.includes(l.href.split('/').pop().replace('.html','')) ? 'active':''}"
                   href="${l.href}">
                  <i class="bi ${l.icon}"></i>${l.label}
                </a>
              </li>`).join('')}
          </ul>
        </div>
        <div class="p-3" style="border-top:1px solid rgba(255,255,255,.08);">
          <div class="d-flex align-items-center gap-2 mb-2">
            <div class="rounded-circle bg-primary d-flex align-items-center justify-content-center text-white"
                 style="width:36px;height:36px;font-size:.9rem;flex-shrink:0;">
              ${user.full_name.charAt(0).toUpperCase()}
            </div>
            <div style="overflow:hidden;">
              <div class="text-white fw-semibold text-truncate" style="font-size:.85rem;">${user.full_name}</div>
              <div style="font-size:.72rem;color:rgba(201,214,227,.6);">${user.role}</div>
            </div>
          </div>
          <button class="btn btn-outline-danger btn-sm w-100" onclick="API.logout()">
            <i class="bi bi-box-arrow-right me-1"></i>Logout
          </button>
        </div>`;
    }

    // Render navbar
    const navbarEl = document.getElementById('scm-navbar');
    if (navbarEl) {
      navbarEl.innerHTML = `
        <div class="d-flex align-items-center gap-2">
          <button class="sidebar-toggle" onclick="SCMComponents.toggleSidebar()">
            <i class="bi bi-list"></i>
          </button>
          <span class="fw-semibold text-dark">${pageTitle}</span>
        </div>
        <div class="d-flex align-items-center gap-2">
          <span class="badge bg-primary">${user.role.toUpperCase()}</span>
          <span class="text-muted small d-none d-md-inline">${user.full_name}</span>
        </div>`;
    }

    API.setCachedUser(user);
    return user;
  }

  function toggleSidebar() {
    document.getElementById('scm-sidebar')?.classList.toggle('show');
  }

  return { init, toggleSidebar };
})();

window.SCMComponents = SCMComponents;
