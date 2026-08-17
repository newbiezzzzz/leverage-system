async function get(path){const r=await fetch(path,{cache:'no-store'});if(!r.ok)throw new Error(`${path} ${r.status}`);return r.json()}
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function money(v){return `RM ${Number(v||0).toFixed(2)}`}
function decisionClass(status){return status==='ready'?'online':'planned'}
async function refresh(){
  try{
    const [snapshot,projectsReply]=await Promise.all([get('/api/snapshot'),get('/api/projects')]);
    const projects=projectsReply.projects||[];
    document.getElementById('companyStage').textContent='SYSTEM OPERATING';
    document.getElementById('projectCount').textContent=projects.length;
    document.getElementById('revenueCount').textContent=projects.filter(p=>p.revenue_status&&p.revenue_status!=='none').length;
    document.getElementById('payoutCount').textContent=snapshot.payouts_prepared;
    document.getElementById('approvalCount').textContent='See gates';
    document.getElementById('moneyGate').textContent=snapshot.live_money_movement?'ENABLED':'BLOCKED';
    const registry=document.getElementById('projectsList');
    registry.innerHTML=projects.length?projects.map(p=>`<div class="worker"><div class="avatar ${p.status==='paused'?'planned':'online'}">${esc((p.name||'P')[0].toUpperCase())}</div><div class="grow"><strong>${esc(p.name)}</strong><span><b>Stage:</b> ${esc(p.lifecycle_stage||p.status)}</span><small>${esc(p.description||'No description')} · Revenue: ${esc(p.revenue_status||'none')} · Capital: ${money(p.capital_deployed)}</small></div><span class="worker-state ${p.status==='paused'?'planned':'online'}">${esc(String(p.status||'unknown').toUpperCase())}</span></div>`).join(''):'<p class="muted">No projects registered.</p>';
    const gateResults=await Promise.all(projects.map(async p=>{try{return (await get(`/api/projects/${encodeURIComponent(p.id)}/gates`)).report}catch{return null}}));
    const decisions=document.getElementById('decisionList');
    const cards=gateResults.filter(Boolean).map(report=>{const gate=report.current_gate;const waiting=gate.status!=='ready';const attention=gate.owner_decision_required?'Owner decision required':(waiting?'Waiting on evidence':'Ready for next gate');const detail=waiting?(gate.reasons||[]).join(' · '):(gate.evidence||[]).join(' · ');return `<div class="worker"><div class="avatar ${decisionClass(gate.status)}">${gate.status==='ready'?'✓':'!'}</div><div class="grow"><strong>${esc(report.project_id)} · ${esc(gate.label)}</strong><span><b>${esc(attention)}</b></span><small>${esc(gate.requires)}${detail?' · '+esc(detail):''}</small></div><span class="worker-state ${decisionClass(gate.status)}">${esc(gate.status.toUpperCase())}</span></div>`}).join('');
    decisions.innerHTML=cards||'<p class="muted">No project decisions are currently waiting.</p>';
  }catch(e){document.getElementById('projectsList').innerHTML='<p class="muted">Local project registry unavailable.</p>';document.getElementById('decisionList').innerHTML='<p class="muted">Local decision center unavailable.</p>';}
}
refresh();setInterval(refresh,30000);
