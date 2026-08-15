const FALLBACK = {
  generated_at: null,
  project: { name: 'Project Leverage', overall_progress: 0, phases: [] },
  workers: [],
  tasks: { queued: 0, running: 0, completed: 0, failed: 0, blocked: 0, cancelled: 0 },
  cost: { amount: 0, currency: 'RM', target: 'zero-cost', tracked: false },
  latest_research: null,
  approvals: [],
  sync: { fresh: false, conclusion: 'unavailable' }
};

async function loadLiveData() {
  try {
    const response = await fetch(`./data.json?ts=${Date.now()}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`data.json returned ${response.status}`);
    return await response.json();
  } catch (error) {
    console.warn('Live dashboard data unavailable; showing safe fallback.', error);
    return FALLBACK;
  }
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[char]));
}

function renderRoadmap(phases) {
  const root = document.getElementById('roadmap');
  if (!root) return;
  root.innerHTML = phases.map((phase, index) => {
    const progress = Number(phase.progress || 0);
    const status = phase.status || (progress >= 100 ? 'complete' : progress > 0 ? 'active' : 'planned');
    const marker = progress >= 100 ? '✓' : (index + 1);
    const cls = progress >= 100 ? 'complete' : status === 'active' ? 'current' : '';
    return `${index ? '<div class="roadmap-line"></div>' : ''}
      <div class="roadmap-step ${cls}">
        <span class="step-dot">${marker}</span>
        <div><strong>${escapeHtml(phase.name)}</strong><small>${escapeHtml(status)}</small></div>
        <b>${progress}%</b>
      </div>`;
  }).join('');
}

function renderWorkers(workers) {
  const root = document.getElementById('workersList');
  if (!root) return;
  root.innerHTML = workers.length ? workers.map(worker => {
    const letter = escapeHtml((worker.id || 'W').slice(0, 1).toUpperCase());
    const state = worker.status === 'online' ? 'online' : 'planned';
    return `<div class="worker">
      <div class="avatar ${escapeHtml(state)}">${letter}</div>
      <div class="grow"><strong>${escapeHtml(worker.id)}</strong><span>${escapeHtml(worker.role)}</span></div>
      <span class="worker-state ${state}">${escapeHtml(String(worker.status || 'unknown').toUpperCase())}</span>
    </div>`;
  }).join('') : '<div class="approval-empty"><span>—</span><div><strong>No workers registered</strong><p>The worker registry is empty.</p></div></div>';
}

function renderAttention(data) {
  const root = document.getElementById('attentionList');
  if (!root) return;
  const tasks = data.tasks || {};
  const failed = tasks.failed || 0;
  const blocked = tasks.blocked || 0;
  const syncFresh = data.sync?.fresh === true;
  const items = [];
  if (!syncFresh) items.push(['⚠', 'Dashboard data is stale', 'The last synchronization was not confirmed successful. No false live status is shown.']);
  if (failed || blocked) items.push(['!', 'Work needs attention', `${failed} failed · ${blocked} blocked task(s).`]);
  if (!items.length) items.push(['✓', 'No approval needed', 'No live trading or money-moving action is authorized.'], ['→', 'Next milestone', 'Continue building the Control Plane and automatic worker triggering.'], ['◎', 'Cost guard', 'Target remains RM0.00. Usage controls stay part of the architecture.']);
  root.innerHTML = items.map(item => `<div class="attention ${item[0] === '✓' ? 'good' : ''}"><span>${item[0]}</span><div><strong>${escapeHtml(item[1])}</strong><p>${escapeHtml(item[2])}</p></div></div>`).join('');
}

function renderResearch(research) {
  if (!research) return;
  setText('researchBadge', String(research.status || 'unknown').toUpperCase());
  setText('researchTitle', `${research.asset || 'Market'} — ${research.period || 'latest'} analysis`);
  setText('researchMeta', `Research Worker · generated ${research.generated_at ? new Date(research.generated_at).toLocaleString() : 'unknown'}`);
  setText('researchObs', research.observations ?? '—');
  setText('researchVol', research.hourly_volatility == null ? '—' : `${(Number(research.hourly_volatility) * 100).toFixed(3)}%`);
  setText('researchEvents', research.large_movement_events ?? '—');
  setText('researchReturn', research.average_hourly_return == null ? '—' : `${(Number(research.average_hourly_return) * 100).toFixed(4)}%`);
  const analysis = research.ai_analysis || 'No AI analysis has been published to the dashboard yet.';
  setText('researchInsight', analysis.length > 650 ? `${analysis.slice(0, 647)}...` : analysis);
  setText('researchStatus', research.status === 'success' ? 'Completed' : String(research.status || 'Unknown'));
}

function renderApprovals(data) {
  const root = document.getElementById('approvalList');
  if (!root) return;
  const approvals = data.approvals || [];
  if (!approvals.length) {
    root.className = 'approval-empty';
    root.innerHTML = '<span>✓</span><div><strong>No decisions waiting</strong><p>When Leverage needs authorization for a sensitive action, it will appear here before anything executes.</p></div>';
    return;
  }
  root.className = 'approval-list';
  root.innerHTML = approvals.map(item => `<div class="attention"><span>⚠</span><div><strong>${escapeHtml(item.title || 'Approval required')}</strong><p>${escapeHtml(item.description || '')}</p></div></div>`).join('');
}

function renderActivity(data) {
  const root = document.getElementById('activity');
  if (!root) return;
  const research = data.latest_research;
  const sync = data.sync || {};
  const items = [];
  if (research) items.push(['done', 'Research Worker published latest result', `${research.observations ?? '—'} observations · ${research.status || 'unknown'}`, research.generated_at ? new Date(research.generated_at).toLocaleString() : 'Latest']);
  items.push([sync.fresh ? 'done' : 'next', 'Dashboard synchronization', sync.fresh ? 'Control Plane state synchronized successfully' : 'Waiting for a confirmed successful synchronization', sync.synced_at ? new Date(sync.synced_at).toLocaleString() : 'Unknown']);
  items.push(['next', 'Automatic worker triggering', 'Next infrastructure milestone', 'Next']);
  root.innerHTML = items.map(item => `<div><span class="timeline-dot ${item[0]}"></span><div><strong>${escapeHtml(item[1])}</strong><small>${escapeHtml(item[2])}</small></div><time>${escapeHtml(item[3])}</time></div>`).join('');
}

function refresh(data) {
  const workers = data.workers || [];
  const tasks = data.tasks || {};
  const online = workers.filter(w => w.status === 'online').length;
  const activeTasks = (tasks.queued || 0) + (tasks.running || 0);
  const progress = Number(data.project?.overall_progress || 0);
  const fresh = data.sync?.fresh === true;

  setText('workerCount', workers.length);
  setText('workerSummary', `${online} active · ${workers.length - online} planned/offline`);
  setText('workerRegistered', `${workers.length} registered`);
  setText('taskCount', activeTasks);
  setText('taskSummary', `${tasks.completed || 0} completed · ${tasks.failed || 0} failed`);
  setText('projectCount', 1);
  setText('cost', Number(data.cost?.amount || 0).toFixed(2));
  setText('overallProgress', `${progress}%`);
  setText('projectProgress', `${progress}%`);
  const progressBar = document.getElementById('projectProgressBar');
  if (progressBar) progressBar.style.width = `${Math.max(0, Math.min(100, progress))}%`;
  setText('lastUpdated', data.generated_at ? `State synced ${new Date(data.generated_at).toLocaleString()}` : 'No sync timestamp');
  setText('systemStatus', fresh ? 'ONLINE' : 'STALE');
  setText('systemText', fresh ? 'System online' : 'Data sync needs attention');
  setText('activityFresh', fresh ? 'Live state synchronized' : 'Data is not confirmed fresh');

  const banner = document.getElementById('syncBanner');
  if (banner) {
    banner.style.display = fresh ? 'none' : 'block';
    banner.innerHTML = '<strong>⚠ Dashboard is not confirmed current.</strong><p class="muted">Leverage will never label stale state as live. Check the Control Plane synchronization before trusting the displayed status.</p>';
  }

  renderRoadmap(data.project?.phases || []);
  renderWorkers(workers);
  renderResearch(data.latest_research);
  renderAttention(data);
  renderApprovals(data);
  renderActivity(data);
}

async function updateDashboard() {
  const data = await loadLiveData();
  refresh(data);
}

document.getElementById('refreshBtn')?.addEventListener('click', updateDashboard);
updateDashboard();
setInterval(updateDashboard, 60_000);
