/**
 * analytics.js — Chart.js rendering helpers and export utilities.
 * Depends on: Chart.js (CDN), jsPDF (CDN), api.js, utils.js
 */

const SCMAnalytics = (() => {

  // ── Palette ──────────────────────────────────────────────────────────────
  const COLORS = {
    status:   ['#ffc107','#0dcaf0','#0d6efd','#198754','#6c757d','#dc3545'],
    category: ['#4e9af1','#f4a261','#2a9d8f','#e76f51','#457b9d','#a8dadc'],
    priority: ['#6c757d','#ffc107','#dc3545','#1e2a3a'],
    escalation:['#dee2e6','#ffc107','#dc3545','#1e2a3a'],
    green10:  Array.from({length:10}, (_,i) => `hsl(${140 + i*18},60%,${45+i*3}%)`),
    blue10:   Array.from({length:10}, (_,i) => `hsl(${210 + i*8},70%,${45+i*2}%)`),
  };

  const _charts = {};   // registry for destroy-on-refresh

  function _destroy(id) {
    if (_charts[id]) { _charts[id].destroy(); delete _charts[id]; }
  }

  function _make(id, config) {
    _destroy(id);
    const ctx = document.getElementById(id);
    if (!ctx) return;
    _charts[id] = new Chart(ctx, config);
    return _charts[id];
  }

  const BASE_OPTS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, padding: 12 } } },
  };

  // ── Status ───────────────────────────────────────────────────────────────

  function renderStatusDoughnut(status) {
    const labels = ['Pending','Assigned','In Progress','Resolved','Closed','Escalated'];
    const data   = [status.pending, status.assigned, status.in_progress, status.resolved, status.closed, status.escalated];
    _make('chartStatus', {
      type: 'doughnut',
      data: { labels, datasets: [{ data, backgroundColor: COLORS.status, borderWidth: 2 }] },
      options: { ...BASE_OPTS, plugins: { ...BASE_OPTS.plugins, tooltip: { callbacks: { label: (c) => ` ${c.label}: ${c.raw}` } } } },
    });
  }

  // ── Category ─────────────────────────────────────────────────────────────

  function renderCategoryBar(category) {
    const sorted = [...category.breakdown].sort((a, b) => b.total - a.total);
    _make('chartCategory', {
      type: 'bar',
      data: {
        labels: sorted.map(c => c.category),
        datasets: [
          { label: 'Total', data: sorted.map(c => c.total), backgroundColor: COLORS.category, borderRadius: 6 },
          { label: 'Resolved', data: sorted.map(c => c.resolved), backgroundColor: '#198754', borderRadius: 6 },
        ],
      },
      options: { ...BASE_OPTS, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } },
    });
  }

  function renderCategoryResolutionRate(category) {
    const sorted = [...category.breakdown].sort((a, b) => b.resolution_rate_pct - a.resolution_rate_pct);
    _make('chartCategoryRate', {
      type: 'bar',
      data: {
        labels: sorted.map(c => c.category),
        datasets: [{ label: 'Resolution Rate (%)', data: sorted.map(c => c.resolution_rate_pct), backgroundColor: COLORS.blue10, borderRadius: 6 }],
      },
      options: { ...BASE_OPTS, scales: { y: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%' } } } },
    });
  }

  // ── Priority ─────────────────────────────────────────────────────────────

  function renderPriorityPie(priority) {
    _make('chartPriority', {
      type: 'pie',
      data: {
        labels: priority.breakdown.map(p => p.priority),
        datasets: [{ data: priority.breakdown.map(p => p.total), backgroundColor: COLORS.priority, borderWidth: 2 }],
      },
      options: BASE_OPTS,
    });
  }

  function renderPriorityStacked(priority) {
    _make('chartPriorityStacked', {
      type: 'bar',
      data: {
        labels: priority.breakdown.map(p => p.priority),
        datasets: [
          { label: 'Resolved', data: priority.breakdown.map(p => p.resolved), backgroundColor: '#198754', borderRadius: 4 },
          { label: 'Unresolved', data: priority.breakdown.map(p => p.total - p.resolved), backgroundColor: '#dc3545', borderRadius: 4 },
        ],
      },
      options: { ...BASE_OPTS, scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } } },
    });
  }

  // ── Department ───────────────────────────────────────────────────────────

  function renderDeptBar(department) {
    const top8 = department.breakdown.slice(0, 8);
    _make('chartDept', {
      type: 'bar',
      data: {
        labels: top8.map(d => d.department_name),
        datasets: [
          { label: 'Total', data: top8.map(d => d.total), backgroundColor: COLORS.blue10, borderRadius: 6 },
          { label: 'Resolved', data: top8.map(d => d.resolved), backgroundColor: '#198754', borderRadius: 6 },
        ],
      },
      options: { ...BASE_OPTS, indexAxis: 'y', scales: { x: { beginAtZero: true } } },
    });
  }

  function renderDeptResolutionLine(department) {
    const top8 = department.breakdown.filter(d => d.total > 0).slice(0, 8);
    _make('chartDeptRate', {
      type: 'line',
      data: {
        labels: top8.map(d => d.department_name),
        datasets: [{ label: 'Resolution Rate (%)', data: top8.map(d => d.resolution_rate_pct), borderColor: '#4e9af1', backgroundColor: 'rgba(78,154,241,.12)', fill: true, tension: 0.3, pointRadius: 5 }],
      },
      options: { ...BASE_OPTS, scales: { y: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%' } } } },
    });
  }

  // ── Duplicates ───────────────────────────────────────────────────────────

  function renderDuplicateDoughnut(dup) {
    _make('chartDuplicate', {
      type: 'doughnut',
      data: {
        labels: ['Duplicates', 'Unique'],
        datasets: [{ data: [dup.duplicate_count, dup.total_complaints - dup.duplicate_count], backgroundColor: ['#ffc107', '#198754'], borderWidth: 2 }],
      },
      options: BASE_OPTS,
    });
  }

  function renderDuplicateByCategory(dup) {
    if (!dup.by_category.length) return;
    _make('chartDupCategory', {
      type: 'bar',
      data: {
        labels: dup.by_category.map(d => d.label),
        datasets: [{ label: 'Duplicates', data: dup.by_category.map(d => d.value), backgroundColor: '#ffc107', borderRadius: 6 }],
      },
      options: { ...BASE_OPTS, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } },
    });
  }

  // ── Clusters ─────────────────────────────────────────────────────────────

  function renderClusterBubble(cluster) {
    if (!cluster.clusters.length) return;
    _make('chartCluster', {
      type: 'bar',
      data: {
        labels: cluster.clusters.map(c => `Cluster ${c.cluster_id}`),
        datasets: [
          { label: 'Complaints', data: cluster.clusters.map(c => c.complaint_count), backgroundColor: COLORS.green10, borderRadius: 6 },
          { label: 'Affected Users', data: cluster.clusters.map(c => c.affected_users), backgroundColor: '#4e9af1', borderRadius: 6 },
        ],
      },
      options: { ...BASE_OPTS, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } },
    });
  }

  function renderTopLocations(cluster) {
    if (!cluster.top_locations.length) return;
    _make('chartLocations', {
      type: 'bar',
      data: {
        labels: cluster.top_locations.map(l => l.label),
        datasets: [{ label: 'Complaints', data: cluster.top_locations.map(l => l.value), backgroundColor: COLORS.blue10, borderRadius: 6 }],
      },
      options: { ...BASE_OPTS, indexAxis: 'y', scales: { x: { beginAtZero: true } } },
    });
  }

  // ── Predictions ──────────────────────────────────────────────────────────

  function renderPredictionScatter(prediction) {
    const pts = prediction.breakdown.filter(p => p.avg_actual_hours !== null);
    _make('chartPrediction', {
      type: 'scatter',
      data: {
        datasets: [{
          label: 'Est. vs Actual (hours)',
          data: pts.map(p => ({ x: p.avg_estimated_hours, y: p.avg_actual_hours })),
          backgroundColor: 'rgba(78,154,241,.7)',
          pointRadius: 7,
        }],
      },
      options: {
        ...BASE_OPTS,
        scales: {
          x: { title: { display: true, text: 'Estimated Hours' }, beginAtZero: true },
          y: { title: { display: true, text: 'Actual Hours' }, beginAtZero: true },
        },
        plugins: {
          ...BASE_OPTS.plugins,
          tooltip: { callbacks: { label: (c) => `${c.raw.x}h est → ${c.raw.y}h actual` } },
        },
      },
    });
  }

  function renderVarianceBar(prediction) {
    const pts = prediction.breakdown.filter(p => p.variance_hours !== null).slice(0, 10);
    if (!pts.length) return;
    _make('chartVariance', {
      type: 'bar',
      data: {
        labels: pts.map(p => `${p.category}/${p.priority}`),
        datasets: [{ label: 'Variance (hours)', data: pts.map(p => p.variance_hours), backgroundColor: pts.map(p => p.variance_hours > 12 ? '#dc3545' : p.variance_hours > 6 ? '#ffc107' : '#198754'), borderRadius: 6 }],
      },
      options: { ...BASE_OPTS, scales: { y: { beginAtZero: true } } },
    });
  }

  // ── Escalation ───────────────────────────────────────────────────────────

  function renderEscalationLevelPie(esc) {
    _make('chartEscLevels', {
      type: 'doughnut',
      data: {
        labels: ['Level 1 (Notified)', 'Level 2 (Escalated)', 'Level 3 (Critical)'],
        datasets: [{ data: [esc.level_1_count, esc.level_2_count, esc.level_3_count], backgroundColor: ['#ffc107','#dc3545','#1e2a3a'], borderWidth: 2 }],
      },
      options: BASE_OPTS,
    });
  }

  function renderEscalationTrend(esc) {
    if (!esc.trend_last_30_days.length) return;
    _make('chartEscTrend', {
      type: 'line',
      data: {
        labels: esc.trend_last_30_days.map(t => t.date),
        datasets: [
          { label: 'Level 1', data: esc.trend_last_30_days.map(t => t.level_1), borderColor: '#ffc107', backgroundColor: 'rgba(255,193,7,.1)', fill: true, tension: 0.3 },
          { label: 'Level 2', data: esc.trend_last_30_days.map(t => t.level_2), borderColor: '#dc3545', backgroundColor: 'rgba(220,53,69,.1)', fill: true, tension: 0.3 },
          { label: 'Level 3', data: esc.trend_last_30_days.map(t => t.level_3), borderColor: '#1e2a3a', backgroundColor: 'rgba(30,42,58,.1)', fill: true, tension: 0.3 },
        ],
      },
      options: { ...BASE_OPTS, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } },
    });
  }

  function renderEscalationByDept(esc) {
    if (!esc.by_department.length) return;
    const top8 = esc.by_department.slice(0, 8);
    _make('chartEscDept', {
      type: 'bar',
      data: {
        labels: top8.map(d => d.department_name),
        datasets: [
          { label: 'Level 1', data: top8.map(d => d.level_1), backgroundColor: '#ffc107', borderRadius: 4 },
          { label: 'Level 2', data: top8.map(d => d.level_2), backgroundColor: '#dc3545', borderRadius: 4 },
          { label: 'Level 3', data: top8.map(d => d.level_3), backgroundColor: '#1e2a3a', borderRadius: 4 },
        ],
      },
      options: { ...BASE_OPTS, scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } } },
    });
  }

  // ── CSV Export ───────────────────────────────────────────────────────────

  function _csvRow(row) { return row.map(v => `"${String(v ?? '').replace(/"/g,'""')}"`).join(','); }

  function exportCSV(data) {
    const sections = [];

    // Status
    sections.push(['=== STATUS SUMMARY ===']);
    sections.push(_csvRow(['Metric','Value']));
    sections.push(_csvRow(['Total', data.status.total]));
    sections.push(_csvRow(['Pending', data.status.pending]));
    sections.push(_csvRow(['In Progress', data.status.in_progress]));
    sections.push(_csvRow(['Resolved', data.status.resolved]));
    sections.push(_csvRow(['Escalated', data.status.escalated]));
    sections.push(_csvRow(['Resolution Rate %', data.status.resolution_rate_pct]));
    sections.push(['']);

    // Category
    sections.push(['=== CATEGORY ANALYTICS ===']);
    sections.push(_csvRow(['Category','Total','Resolved','Resolution Rate %','Avg Resolution Hours']));
    data.category.breakdown.forEach(c => sections.push(_csvRow([c.category, c.total, c.resolved, c.resolution_rate_pct, c.avg_resolution_hours ?? ''])));
    sections.push(['']);

    // Priority
    sections.push(['=== PRIORITY ANALYTICS ===']);
    sections.push(_csvRow(['Priority','Total','Resolved','Resolution Rate %']));
    data.priority.breakdown.forEach(p => sections.push(_csvRow([p.priority, p.total, p.resolved, p.resolution_rate_pct])));
    sections.push(['']);

    // Department
    sections.push(['=== DEPARTMENT ANALYTICS ===']);
    sections.push(_csvRow(['Department','Total','Resolved','Resolution Rate %','Avg Resolution Hours','Staff Count']));
    data.department.breakdown.forEach(d => sections.push(_csvRow([d.department_name, d.total, d.resolved, d.resolution_rate_pct, d.avg_resolution_hours ?? '', d.staff_count])));
    sections.push(['']);

    // Duplicates
    sections.push(['=== DUPLICATE ANALYTICS ===']);
    sections.push(_csvRow(['Total Complaints','Duplicates','Duplicate Rate %']));
    sections.push(_csvRow([data.duplicate.total_complaints, data.duplicate.duplicate_count, data.duplicate.duplicate_rate_pct]));
    sections.push(['']);

    // Escalation
    sections.push(['=== ESCALATION ANALYTICS ===']);
    sections.push(_csvRow(['Total Escalated','Level 1','Level 2','Level 3']));
    sections.push(_csvRow([data.escalation.total_escalated, data.escalation.level_1_count, data.escalation.level_2_count, data.escalation.level_3_count]));
    sections.push(['']);

    // Prediction
    sections.push(['=== PREDICTION ACCURACY ===']);
    sections.push(_csvRow(['Category','Priority','Avg Estimated Hours','Avg Actual Hours','Variance Hours','Sample Count']));
    data.prediction.breakdown.forEach(p => sections.push(_csvRow([p.category, p.priority, p.avg_estimated_hours, p.avg_actual_hours ?? '', p.variance_hours ?? '', p.sample_count])));

    const csv = sections.map(r => Array.isArray(r) ? r.join('') : r).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `scm_analytics_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ── PDF Export ───────────────────────────────────────────────────────────

  function exportPDF(data) {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    let y = 20;

    const addLine = (text, size = 10, bold = false, color = [0,0,0]) => {
      doc.setFontSize(size);
      doc.setFont('helvetica', bold ? 'bold' : 'normal');
      doc.setTextColor(...color);
      doc.text(text, 15, y);
      y += size * 0.5 + 2;
      if (y > 270) { doc.addPage(); y = 20; }
    };

    const addSeparator = () => { doc.setDrawColor(200,200,200); doc.line(15, y, 195, y); y += 4; };

    addLine('Smart Complaint Management System', 18, true, [30,42,58]);
    addLine(`Analytics Report — Generated ${new Date().toLocaleString()}`, 9, false, [100,100,100]);
    addSeparator();

    // Status
    addLine('STATUS SUMMARY', 13, true, [30,42,58]);
    y += 2;
    [['Total Complaints', data.status.total], ['Pending', data.status.pending], ['In Progress', data.status.in_progress],
     ['Resolved', data.status.resolved], ['Escalated', data.status.escalated], ['Resolution Rate', `${data.status.resolution_rate_pct}%`]
    ].forEach(([k, v]) => addLine(`  ${k}: ${v}`, 10));
    y += 4;

    // Category
    addSeparator();
    addLine('CATEGORY ANALYTICS', 13, true, [30,42,58]);
    y += 2;
    data.category.breakdown.forEach(c => addLine(`  ${c.category}: ${c.total} total, ${c.resolved} resolved (${c.resolution_rate_pct}%)`, 9));
    y += 4;

    // Priority
    addSeparator();
    addLine('PRIORITY ANALYTICS', 13, true, [30,42,58]);
    y += 2;
    data.priority.breakdown.forEach(p => addLine(`  ${p.priority}: ${p.total} total, ${p.resolved} resolved (${p.resolution_rate_pct}%)`, 9));
    y += 4;

    // Duplicates
    addSeparator();
    addLine('DUPLICATE ANALYTICS', 13, true, [30,42,58]);
    y += 2;
    addLine(`  Total: ${data.duplicate.total_complaints}  Duplicates: ${data.duplicate.duplicate_count}  Rate: ${data.duplicate.duplicate_rate_pct}%`, 9);
    y += 4;

    // Escalation
    addSeparator();
    addLine('ESCALATION ANALYTICS', 13, true, [30,42,58]);
    y += 2;
    addLine(`  Total Escalated: ${data.escalation.total_escalated}`, 9);
    addLine(`  Level 1: ${data.escalation.level_1_count}  |  Level 2: ${data.escalation.level_2_count}  |  Level 3: ${data.escalation.level_3_count}`, 9);
    y += 4;

    // Prediction
    addSeparator();
    addLine('PREDICTION ACCURACY', 13, true, [30,42,58]);
    y += 2;
    addLine(`  Avg Estimated: ${data.prediction.overall_avg_estimated}h  |  Avg Actual: ${data.prediction.overall_avg_actual ?? 'N/A'}h`, 9);

    doc.save(`scm_analytics_${new Date().toISOString().slice(0,10)}.pdf`);
  }

  // ── Master render ─────────────────────────────────────────────────────────

  function renderAll(data) {
    renderStatusDoughnut(data.status);
    renderCategoryBar(data.category);
    renderCategoryResolutionRate(data.category);
    renderPriorityPie(data.priority);
    renderPriorityStacked(data.priority);
    if (data.department) { renderDeptBar(data.department); renderDeptResolutionLine(data.department); }
    renderDuplicateDoughnut(data.duplicate);
    renderDuplicateByCategory(data.duplicate);
    renderClusterBubble(data.cluster);
    renderTopLocations(data.cluster);
    renderPredictionScatter(data.prediction);
    renderVarianceBar(data.prediction);
    renderEscalationLevelPie(data.escalation);
    renderEscalationTrend(data.escalation);
    renderEscalationByDept(data.escalation);
  }

  return { renderAll, exportCSV, exportPDF };
})();

window.SCMAnalytics = SCMAnalytics;
