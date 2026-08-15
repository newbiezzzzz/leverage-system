const DATA = {
  workers: [
    {id:'research-worker',status:'online'},
    {id:'code-worker',status:'planned'},
    {id:'data-worker',status:'planned'}
  ],
  projects: 1,
  activeTasks: 0,
  cost: 0
};

function refresh(){
  document.getElementById('workerCount').textContent = DATA.workers.length;
  document.getElementById('workerSummary').textContent = `${DATA.workers.filter(w=>w.status==='online').length} active · ${DATA.workers.filter(w=>w.status!=='online').length} planned`;
  document.getElementById('taskCount').textContent = DATA.activeTasks;
  document.getElementById('projectCount').textContent = DATA.projects;
  document.getElementById('cost').textContent = Number(DATA.cost).toFixed(2);
  document.getElementById('lastUpdated').textContent = `Dashboard refreshed ${new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}`;
}

document.getElementById('refreshBtn').addEventListener('click', refresh);
refresh();
