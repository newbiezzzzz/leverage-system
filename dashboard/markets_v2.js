const markets={
 BTCUSDT:{name:'Bitcoin / USDT',type:'Crypto',next:'Begin technical-strategy screening',data:'500 validated daily rows'},
 XAUUSDT:{name:'Gold / USDT',type:'Gold',next:'Verify public-data provenance and ingest',data:'Historical source validation pending'},
 CL:{name:'WTI Crude Oil',type:'Futures',next:'Verify continuous-contract and roll handling',data:'Historical source validation pending'},
 FCPO:{name:'FCPO Palm Oil',type:'Futures',next:'Find zero-cost verifiable history',data:'Source investigation active'}
};
const param=new URLSearchParams(location.search).get('instrument')?.toUpperCase();
const state=id=>id==='BTCUSDT'?['READY','NOT TESTED','NOT TESTED','LOCKED','LOCKED','NOT TRADEABLE']:['PENDING','NOT TESTED','NOT TESTED','LOCKED','LOCKED','NOT TRADEABLE'];
const labels=['Data','Strategy','Backtest','OOS','Paper','Tradeable'];
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function card(id,m){const s=state(id);return `<article class="card panel market-detail-card"><div class="panel-head"><div><p class="eyebrow">${id}</p><h2>${m.name}</h2></div><span class="pill blue-pill">${m.type}</span></div><div class="metrics"><div><b>${s[0]}</b><span>data</span></div><div><b>${s[1]}</b><span>strategy</span></div><div><b>${s[5]}</b><span>trade readiness</span></div><div><b>RM 0</b><span>capital deployed</span></div></div><div class="market-gates">${labels.map((x,i)=>`<div class="gate-row ${s[i]==='READY'?'gate-ready':s[i]==='PENDING'?'gate-pending':'gate-locked'}"><span>${i+1}</span><strong>${x}</strong><b>${s[i]}</b></div>`).join('')}</div><div class="insight"><span>NEXT ACTION</span><div><strong>${esc(m.next)}</strong><p>${esc(m.data)}. A blocked gate prevents the market from being presented as ready.</p></div></div></article>`}
function boot(){const target=param&&markets[param]?param:null;document.getElementById('title').textContent=target?markets[target].name:'Choose your market';const ids=target?[target]:Object.keys(markets);document.getElementById('marketCards').innerHTML=ids.map(id=>card(id,markets[id])).join('');if(target){document.getElementById('detail').style.display='block';document.getElementById('detail').innerHTML=`<div class="panel-head"><div><p class="eyebrow">${target} CUSTOMER PATH</p><h2>Data → Strategy → Backtest → OOS → Paper → Tradeable</h2></div></div><p class="muted">BTCUSDT has passed the initial data gate with 500 validated daily rows. Strategy and later gates remain untested or blocked until evidence exists.</p>`}}
boot();
