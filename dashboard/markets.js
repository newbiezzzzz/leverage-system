const markets={
 BTCUSDT:{name:'Bitcoin / USDT',type:'Crypto',status:'Adapter ready · validation pending',source:'Binance public daily klines',next:'Run acquisition and pass 250-row gate'},
 XAUUSDT:{name:'Gold / USDT',type:'Gold',status:'Source validation pending',source:'Public XAU/USD dataset candidates',next:'Verify provenance and ingest'},
 CL:{name:'WTI Crude Oil',type:'Futures',status:'Source validation pending',source:'Public WTI/CL historical candidates',next:'Verify continuous contract + roll handling'},
 FCPO:{name:'FCPO Palm Oil',type:'Futures',status:'Parallel investigation',source:'Kenanga / TA Futures / Bursa-related sources',next:'Find zero-cost verifiable history'}
};
const base='https://raw.githubusercontent.com/newbiezzzzz/leverage-system/main/';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const param=new URLSearchParams(location.search).get('instrument')?.toUpperCase();
function card(id,m){return `<article class="card panel market-detail-card"><div class="panel-head"><div><p class="eyebrow">${id}</p><h2>${m.name}</h2></div><span class="pill blue-pill">${m.type}</span></div><div class="metrics"><div><b>${m.status.includes('ready')?'SETUP':'PENDING'}</b><span>data status</span></div><div><b>NOT TESTED</b><span>best strategy</span></div><div><b>BLOCKED</b><span>trade readiness</span></div><div><b>RM 0</b><span>capital deployed</span></div></div><div class="insight"><span>SOURCE</span><div><strong>${esc(m.source)}</strong><p>${esc(m.next)}</p></div></div><div class="insight"><span>CUSTOMER VIEW</span><div><strong>No fake score</strong><p>This market stays “Not tested” until the same strategy engine produces validated evidence.</p></div></div></article>`}
async function boot(){
 try{const p=await fetch(`${base}dashboard/project.json?live=${Date.now()}`,{cache:'no-store'}).then(r=>r.json());document.getElementById('marketSync').textContent=`Updated ${new Date(p.generated_at||Date.now()).toLocaleString()}`;}catch(e){document.getElementById('marketSync').textContent='Data check unavailable'}
 const target=param&&markets[param]?param:null; document.getElementById('title').textContent=target?markets[target].name:'Choose your market'; const ids=target?[target]:Object.keys(markets); document.getElementById('marketCards').innerHTML=ids.map(id=>card(id,markets[id])).join('');
 if(target){document.getElementById('detail').style.display='block';document.getElementById('detail').innerHTML='<div class="panel-head"><div><p class="eyebrow">MARKET DETAIL RULE</p><h2>Same evidence standard for every instrument</h2></div></div><p class="muted">Data quality → strategy test → out-of-sample → walk-forward → paper trading. Only after those gates can this instrument move toward live consideration.</p>'}
}
boot();
