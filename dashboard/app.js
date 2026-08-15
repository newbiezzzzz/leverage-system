const FALLBACK = {
  project: { name: 'Project Leverage', overall_progress: 25 },
  workers: [],
  tasks: { queued: 0, running: 0, completed: 0, failed: 0, blocked: 0 },
  cost: { amount: 0, currency: 'RM' }
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

function refresh(data) {
  const workers = data.workers || [];
  const tasks = data.tasks || {};
  const online = workers.filter(w => w.status === 'online').length;
  const activeTasks = (tasks.queued || 0) + (tasks.running || 0);

  setText('workerCount', workers.length);
  setText('workerSummary', `${online} active · ${workers.length - online} planned/offline`);
  setText('taskCount', activeTasks);
  setText('projectCount', 1);
  setText('cost', Number(data.cost?.amount || 0).toFixed(2));
  setText('lastUpdated', `Live data checked ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`);
  setText('overallProgress', `${data.project?.overall_progress ?? 0}%`);
  setText('completedTasks', tasks.completed || 0);
  setText('failedTasks', tasks.failed || 0);
  setText('blockedTasks', tasks.blocked || 0);
}

async function updateDashboard() {
  const data = await loadLiveData();
  refresh(data);
}

document.getElementById('refreshBtn')?.addEventListener('click', updateDashboard);
updateDashboard();
setInterval(updateDashboard, 60_000);
