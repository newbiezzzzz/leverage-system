async function get(path){const r=await fetch(path,{cache:'no-store'});if(!r.ok)throw new Error(`${path} ${r.status}`);return r.json()}
const METRICS_URL='https://raw.githubusercontent.com/newbiezzzzz/leverage-system/main/control_plane/project_metrics.json';
const TYPES_URL='https://raw.githubusercontent.com/newbiezzzzz/leverage-system/main/control_plane/project_types.json';
const PUBLIC_METRICS_URL='https://leverage-tools.pages.dev/api/public-metrics';
async function getJson(url,label){const r=await fetch(`${url}?live=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw new Error(`${label} ${r.status}`);return r.json()}
async function getMetrics(){return getJson(METRICS_URL,'project_metrics')}
async function getTypes(){return getJson(TYPES_URL,'project_types')}
async function getPublicMetrics(){const r=await fetch(PUBLIC_METRICS_URL,{cache:'no-store'});if(!r.ok)throw new Error(`public_metrics ${r.status}`);return (await r.json()).metrics||{}}
function esc(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]))}
function metricValue(v,suffix=''){return v===null||v===undefined?'UNKNOWN':`${esc(v)}${suffix}`}
function metricCard(label,value,detail,klass=''){return `<div class="card stat ${klass}"><span>${esc(label)}</span><strong>${value}</strong><small>${esc(detail)}</small></div>`}
function renderMetrics(data,preferredId,publicMetrics={}){const root=document.getElementById('metricsList'),state=document.getElementById('metricsState');if(!root)return;const p=data?.projects?.[preferredId]||data?.projects?.['digital-products']||data?.projects?.['engineering-quote-toolkit'];if(!p&&!publicMetrics?.storage_configured){if(state)state.textContent='NO DATA';root.innerHTML='<p class="muted">No verified traffic record is available yet.</p>';return}const t=p?.traffic||{},f=p?.funnel||{},r=p?.revenue||{};const live=publicMetrics?.storage_configured===true;const events=live?publicMetrics.events:f.public_tool_events;const pageViews=live?publicMetrics.page_views:t.product_page_views;const visitors=live?publicMetrics.unique_visitors:t.unique_visitors;const quoteEvents=live?publicMetrics.calculated_quotes:f.calculator_events;const clicks=live?publicMetrics.pro_clicks:f.outbound_product_clicks;const conversion=live?publicMetrics.click_through_rate:f.conversion_rate;if(state)state.textContent=live?'LIVE · PUBLIC':'NOT CONNECTED';const sources=(live?publicMetrics.traffic_sources:t.sources)||[];const source=(sources.length?sources.map(x=>`${esc(x.name||x.source||'Source')}: ${esc(x.views??x.metric??'metric')}`).join(' · '):'No traffic sources verified yet');root.innerHTML=`<div class="grid stats">${metricCard('Public page views',metricValue(pageViews),'Live Cloudflare telemetry')}${metricCard('Unique visitors',metricValue(visitors),'Live verified visitor count')}${metricCard('Tool events',metricValue(events),'Public fabrication-tool activity')}${metricCard('Calculator events',metricValue(quoteEvents),'Quote interactions recorded')}</div><div class="strategy-summary"><div><strong>Traffic status</strong><p>${live?'connected':'not connected'}</p></div><div><strong>Measurement source</strong><p>${esc(live?(publicMetrics.measurement_source||'Leverage public telemetry'):(t.measurement_source||'Not connected'))}</p></div><div><strong>Traffic sources</strong><p>${source}</p></div><div><strong>Product clicks</strong><p>${metricValue(clicks)}</p></div><div><strong>Conversion</strong><p>${conversion==null?'UNKNOWN':`${Number(conversion).toFixed(2)}%`}</p></div><div><strong>Verified revenue</strong><p>USD ${Number(r.verified_revenue_usd||0).toFixed(2)} verified</p></div><div><strong>Next gate</strong><p>${esc(p?.interpretation?.next_gate||'Measure traffic, acquire the first buyer, then evaluate conversion and iterate.')}</p></div></div><p class="muted" style="margin-top:12px">Safety rule: unknown traffic is not treated as zero. Public telemetry is usage evidence, not revenue.</p>`}
function typeInfo(types,p){const key=String(p.type||'').replaceAll('-','_');const t=types?.types?.[key]||types?.types?.[p.type];return {label:t?.label||p.type||'Unclassified',channels:t?.channels||[],delivery:t?.delivery||[],events:t?.revenue_events||[]}}
function projectNumber(projects,p){return p?.project_no||`P-${String(projects.findIndex(x=>x.id===p.id)+1).padStart(3,'0')}`}
function renderRegistry(projects,types){const registry=document.getElementById('projectsList');if(!registry)return;registry.innerHTML=projects.length?projects.map(p=>{const x=typeInfo(types,p);const num=projectNumber(projects,p);return `<a href="project-detail.html?id=${encodeURIComponent(p.id)}" class="worker" style="text-decoration:none;color:inherit;display:flex;align-items:center"><div class="avatar ${p.status==='paused'?'planned':'online'}">${esc((p.name||'P')[0].toUpperCase())}</div><div class="grow"><strong>${esc(num)} · ${esc(p.name)}</strong><span><b>Type:</b> ${esc(x.label)} · <b>Stage:</b> ${esc(p.lifecycle_stage||p.status)}</span><small>${esc(p.description||'No description')}</small><small>${p.id==='affiliate-project'?'Automotive recommendation engine · TikTok + YouTube acquisition · Reddit intelligence.':'Products, acquisition assets and business state inside this project.'}</small><small><b>Open full project detail →</b></small></div><span class="worker-state ${p.status==='paused'?'planned':'online'}">${esc(String(p.status||'unknown').toUpperCase())}</span></a>`}).join(''):'<p class="muted">No projects registered.</p>'}
const STRATEGY_STATUS_URL='https://raw.githubusercontent.com/newbiezzzzz/leverage-system/main/research/results/strategy_hunter_status.json';
const STRATEGY_PIPELINE_URL='https://raw.githubusercontent.com/newbiezzzzz/leverage-system/main/research/results/strategy_hunter_pipeline.json';
async function getStrategyHunterStatus(){return getJson(STRATEGY_STATUS_URL,'strategy_hunter_status')}
async function getStrategyHunterPipeline(){return getJson(STRATEGY_PIPELINE_URL,'strategy_hunter_pipeline')}
function renderStrategyHunterStatus(s){
 const status=s&&s.status||'unknown', jobs=Array.isArray(s&&s.jobs)?s.jobs:[], running=jobs.find(function(j){return j.status==='in_progress'});
 const shown=status==='in_progress'?'RUNNING':status==='completed'?'COMPLETED':status==='queued'?'QUEUED':status==='failure'?'FAILED':status==='no_run'?'NO RUN':'NOT READY';
 function put(id,v){const e=document.getElementById(id);if(e)e.textContent=v}
 put('strategyHunterStatus',shown); put('strategyHunterRun',s&&s.run_id?'#'+s.run_id:'—'); put('strategyHunterStarted',s&&s.started_at?new Date(s.started_at).toLocaleString():'—'); put('strategyHunterUpdated',s&&s.updated_at?new Date(s.updated_at).toLocaleString():'—'); put('strategyHunterStep',running&&running.current_step&&running.current_step!=='—'?running.current_step:'—');
 const root=document.getElementById('strategyHunterJobs');
 if(root) root.innerHTML=jobs.length?jobs.map(function(j){const st=j.status==='in_progress'?'RUNNING':j.conclusion==='success'?'DONE':j.conclusion==='failure'?'FAILED':String(j.status||'UNKNOWN').toUpperCase();return '<div class="worker"><div class="avatar '+(j.status==='in_progress'?'online':'planned')+'">S</div><div class="grow"><strong>'+esc(j.name||'Job')+'</strong><span><b>'+esc(st)+'</b></span><small>'+esc(j.current_step&&j.current_step!=='—'?'Current: '+j.current_step:'No active step')+'</small></div><span class="worker-state '+(j.status==='in_progress'?'online':j.conclusion==='failure'?'planned':'online')+'">'+esc(st)+'</span></div>'}).join(''):'<p class="muted">No Strategy Hunter job details published yet.</p>';
}
function renderStrategyHunterPipeline(p){
 const stages=['baseline','pattern_hunter','adaptive','vectorbt','lightgbm','symbolic','qlib','optuna','lean','chronos2'];
 const labels={baseline:'Baseline',pattern_hunter:'Pattern Hunter',adaptive:'Improve Promising Ideas',vectorbt:'VectorBT',lightgbm:'LightGBM',symbolic:'Symbolic Regression',qlib:'Qlib',optuna:'Optuna',lean:'LEAN',chronos2:'Chronos-2'};
 const stage=p&&p.stage||'—',details=p&&p.stages||{};
 function put(id,v){const e=document.getElementById(id);if(e)e.textContent=v}
 const idx=stages.indexOf(stage);
 const next=stage==='done'||idx<0?'—':labels[stages[Math.min(idx+1,stages.length-1)]]||'—';
 put('strategyHunterPipelineStage',labels[stage]||stage);
 put('strategyHunterPipelineAttempt',p&&p.attempt?String(p.attempt):'—');
 put('strategyHunterNextSpecialist',next);
 put('strategyHunterPipelineState',String(p&&p.status||'unknown').replaceAll('_',' ').toUpperCase());
 const root=document.getElementById('strategyHunterPipeline'); if(!root)return;
 root.innerHTML=stages.map(function(k,i){
   const d=details[k]||{};
   const state=d.status==='done'?'DONE':d.status==='failed'?'FAILED':(stage===k?'ACTIVE':i<(idx<0?0:idx)?'DONE':'QUEUED');
   const klass=state==='FAILED'?'planned':'online';
   return '<div class="worker"><div class="avatar '+klass+'">'+(state==='DONE'?'✓':state==='FAILED'?'!':'S')+'</div><div class="grow"><strong>'+esc(labels[k])+'</strong><span><b>'+state+'</b></span><small>'+esc(d.error||('Attempts: '+(d.attempts??'—')) )+'</small></div><span class="worker-state '+klass+'">'+state+'</span></div>';
 }).join('');
}
async function refreshStrategyHunter(){try{renderStrategyHunterStatus(await getStrategyHunterStatus())}catch(e){const el=document.getElementById('strategyHunterStatus');if(el)el.textContent='NOT READY';const root=document.getElementById('strategyHunterJobs');if(root)root.innerHTML='<p class="muted">Monitor data not published yet.</p>'} try{renderStrategyHunterPipeline(await getStrategyHunterPipeline())}catch(e){const root=document.getElementById('strategyHunterPipeline');if(root)root.innerHTML='<p class="muted">Specialist pipeline status not published yet.</p>'}}
function refresh(){
 const projectsEl=document.getElementById('projectsList');
 try{
   const [projectsReply,snapshot]=await Promise.all([get('/api/projects'),get('/api/snapshot').catch(()=>({}))]);
   const projects=projectsReply.projects||[];
   const countEl=document.getElementById('projectCount'),revenueEl=document.getElementById('revenueCount'),payoutEl=document.getElementById('payoutCount'),approvalEl=document.getElementById('approvalCount'),moneyEl=document.getElementById('moneyGate');
   if(countEl)countEl.textContent=projects.length;
   if(revenueEl)revenueEl.textContent=projects.filter(p=>p.revenue_status&&p.revenue_status!=='none').length;
   if(payoutEl)payoutEl.textContent=snapshot.payouts_prepared??'—';
   if(approvalEl)approvalEl.textContent='See gates';
   if(moneyEl)moneyEl.textContent=snapshot.live_money_movement?'ENABLED':'BLOCKED';
   if(projectsEl){renderRegistry(projects,{types:{}});const registryStatus=document.getElementById('registryStatus');const registryPill=document.getElementById('registryPill');if(registryStatus)registryStatus.textContent='LIVE';if(registryPill)registryPill.textContent=`${projects.length} PROJECT${projects.length===1?'':'S'}`}
   const [metricsResult,typesResult,publicResult]=await Promise.allSettled([getMetrics(),getTypes(),getPublicMetrics()]);
   const metrics=metricsResult.status==='fulfilled'?metricsResult.value:{};
   const types=typesResult.status==='fulfilled'?typesResult.value:{types:{}};
   const publicMetrics=publicResult.status==='fulfilled'?publicResult.value:{};
   const p001=projects.find(p=>p.id==='digital-products')||projects[0];
   renderRegistry(projects,types);
   renderMetrics(metrics,p001?.id,publicMetrics);
   const decisions=document.getElementById('decisionList');
   if(decisions){
     const gateResults=await Promise.all(projects.map(async p=>{try{return (await get(`/api/projects/${encodeURIComponent(p.id)}/gates`)).report}catch{return null}}));
     const cards=gateResults.filter(Boolean).map(report=>{const gate=report.current_gate;const waiting=gate.status!=='ready';const attention=gate.owner_decision_required?'Owner decision required':(waiting?'Waiting on evidence':'Ready for next gate');const detail=waiting?(gate.reasons||[]).join(' · '):(gate.evidence||[]).join(' · ');return `<div class="worker"><div class="avatar ${gate.status==='ready'?'online':'planned'}">${gate.status==='ready'?'✓':'!'}</div><div class="grow"><strong>${esc(report.project_id)} · ${esc(gate.label)}</strong><span><b>${esc(attention)}</b></span><small>${esc(gate.requires)}${detail?' · '+esc(detail):''}</small></div><span class="worker-state ${gate.status==='ready'?'online':'planned'}">${esc(gate.status.toUpperCase())}</span></div>`}).join('');decisions.innerHTML=cards||'<p class="muted">No project decisions are currently waiting.</p>'}
 }catch(e){
   if(projectsEl)projectsEl.innerHTML='<p class="muted">Local project registry unavailable.</p>';
   const decisions=document.getElementById('decisionList');if(decisions)decisions.innerHTML='<p class="muted">Local decision center unavailable.</p>';
   const m=document.getElementById('metricsList');if(m)m.innerHTML='<p class="muted">Project metrics unavailable.</p>';
   const s=document.getElementById('metricsState');if(s)s.textContent='UNAVAILABLE';
   const r=document.getElementById('registryStatus');if(r)r.textContent='UNAVAILABLE';
 }
}
refresh();refreshStrategyHunter();setInterval(refresh,30000);setInterval(refreshStrategyHunter,30000);
