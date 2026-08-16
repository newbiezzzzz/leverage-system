(() => {
  const API = 'https://api.github.com/repos/newbiezzzzz/leverage-system/actions/workflows/acquire-btcusdt.yml/runs?per_page=1';
  const JOB = id => `https://api.github.com/repos/newbiezzzzz/leverage-system/actions/runs/${id}/jobs?per_page=10`;
  const ART = id => `https://api.github.com/repos/newbiezzzzz/leverage-system/actions/runs/${id}/artifacts?per_page=50`;
  const esc = v => String(v ?? '').replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
  const stateClass = s => s === 'success' ? 'success' : s === 'failure' ? 'failure' : s === 'in_progress' || s === 'queued' ? 'running' : 'neutral';
  const stateLabel = s => ({success:'PASSED',failure:'FAILED',in_progress:'RUNNING',queued:'QUEUED',cancelled:'CANCELLED'}[s] || String(s || 'UNKNOWN').toUpperCase());
  const stepLabel = s => s?.status === 'completed' ? (s.conclusion === 'success' ? 'DONE' : String(s.conclusion || 'FAILED').toUpperCase()) : String(s?.status || 'WAITING').toUpperCase();
  function ensurePanel(){
    if(document.getElementById('liveRunPanel')) return;
    const main=document.querySelector('main'); if(!main) return;
    const s=document.createElement('section'); s.id='liveRunPanel'; s.className='card panel';
    s.style.marginBottom='24px';
    s.innerHTML=`<div class="panel-head"><div><p class="eyebrow">LIVE WORKER MONITOR</p><h2>BTCUSDT Acquisition</h2></div><span id="liveRunBadge" class="pill blue-pill">CHECKING</span></div>
      <div class="metrics"><div><b id="liveRunState">Checking…</b><span>workflow state</span></div><div><b id="liveRunStep">—</b><span>current step</span></div><div><b id="liveRunRows">500</b><span>target rows</span></div><div><b id="liveRunGate">250</b><span>validation gate</span></div></div>
      <div class="insight"><span>LIVE SOURCE</span><div><strong id="liveRunTitle">GitHub Actions</strong><p id="liveRunDetail">Reading the latest BTCUSDT acquisition run directly from GitHub.</p><small id="liveRunChecked">Not checked yet</small></div></div>`;
    const hero=main.querySelector('.hero'); hero?.insertAdjacentElement('afterend',s);
  }
  async function getJson(url){ const r=await fetch(url,{headers:{Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'},cache:'no-store'}); if(!r.ok) throw new Error(`GitHub API ${r.status}`); return r.json(); }
  async function refresh(){
    ensurePanel();
    const badge=document.getElementById('liveRunBadge'), state=document.getElementById('liveRunState'), step=document.getElementById('liveRunStep'), detail=document.getElementById('liveRunDetail'), title=document.getElementById('liveRunTitle'), checked=document.getElementById('liveRunChecked');
    try{
      const runs=await getJson(`${API}&t=${Date.now()}`); const run=runs.workflow_runs?.[0];
      if(!run){ badge.textContent='NO RUN'; state.textContent='No run'; step.textContent='—'; detail.textContent='No BTCUSDT acquisition workflow run has been published yet.'; checked.textContent=`Checked ${new Date().toLocaleString()}`; return; }
      badge.textContent=stateLabel(run.status==='completed'?run.conclusion:run.status); badge.className=`pill ${stateClass(run.status==='completed'?run.conclusion:run.status)}-pill`;
      state.textContent=stateLabel(run.status==='completed'?run.conclusion:run.status);
      title.innerHTML=`GitHub Actions · Run <a href="${esc(run.html_url)}" target="_blank" rel="noopener">#${esc(run.run_number)}</a>`;
      detail.textContent=run.status==='completed' ? (run.conclusion==='success' ? 'Workflow completed successfully. Dataset artifact and validation result are the next evidence checks.' : `Workflow completed with ${run.conclusion}. Open the run for details.`) : 'Worker is executing. The dashboard is reading GitHub Actions directly.';
      const jobs=await getJson(`${JOB(run.id)}&t=${Date.now()}`); const job=jobs.jobs?.[0];
      const active=job?.steps?.find(s=>s.status==='in_progress') || job?.steps?.find(s=>s.status==='queued') || job?.steps?.slice(-1)[0];
      step.textContent=active ? stepLabel(active) : (job?.status || 'WAITING').toUpperCase();
      if(run.status==='completed'){
        try{
          const arts=await getJson(`${ART(run.id)}&t=${Date.now()}`); const ok=arts.artifacts?.some(a=>a.name==='btcusdt-daily-research' && !a.expired);
          detail.textContent=run.conclusion==='success' && ok ? 'PASSED: acquisition completed and the BTCUSDT dataset artifact is available for validation/research.' : detail.textContent;
        }catch(e){}
      }
      checked.textContent=`Last checked ${new Date().toLocaleString()} · GitHub is the source of truth`;
    }catch(e){ badge.textContent='UNAVAILABLE'; badge.className='pill blue-pill'; state.textContent='Unavailable'; step.textContent='—'; detail.textContent='GitHub Actions live status could not be read from this browser session. Use Refresh and retry.'; checked.textContent=`Checked ${new Date().toLocaleString()}`; }
  }
  window.LeavergeLiveRun={refresh};
  document.addEventListener('DOMContentLoaded',()=>{ ensurePanel(); refresh(); setInterval(refresh,120000); document.getElementById('refreshBtn')?.addEventListener('click',()=>setTimeout(refresh,200)); });
})();
