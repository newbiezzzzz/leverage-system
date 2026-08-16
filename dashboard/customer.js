const BASE='https://raw.githubusercontent.com/newbiezzzzz/leverage-system/main/';
const MARKETS=[
 {id:'BTCUSDT',name:'Bitcoin / USDT',type:'Crypto',priority:'PRIMARY',data:'Binance public klines'},
 {id:'XAUUSDT',name:'Gold / USDT',type:'Gold',priority:'PRIMARY',data:'Historical source validation pending'},
 {id:'CL',name:'WTI Crude Oil',type:'Futures',priority:'PRIMARY',data:'Futures/roll source validation pending'},
 {id:'FCPO',name:'FCPO Palm Oil',type:'Futures',priority:'PARALLEL',data:'Public/authorized source investigation'}
];
async function get(path){const r=await fetch(`${BASE}${path}?live=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw new Error(path);return r.json()}
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function card(m){return `<a class="market-card" href="markets.html?instrument=${encodeURIComponent(m.id)}"><div class="market-top"><span class="pill ${m.priority==='PRIMARY'?'blue-pill':'green-pill'}">${m.priority}</span><span class="market-type">${m.type}</span></div><h3>${m.name}</h3><div class="market-status" id="status-${m.id}">Checking data…</div><p>${m.data}</p><div class="market-bottom"><span>Strategy</span><b>Not tested yet</b></div><div class="market-bottom"><span>Readiness</span><b>RESEARCH</b></div></a>`}
function set(id,v){const e=document.getElementById(id);if(e)e.textContent=v}
async function refresh(){
 try{
  const p=await get('dashboard/project.json'); const r=await get('dashboard/research.json').catch(()=>({}));
  set('execution',`${Number(p.progress??54)}%`);set('system',`${Number(p.system_build_progress??94)}%`);set('income',`${Number(p.income_validation_progress??0)}%`);set('capital',`RM ${Number(p.capital_deployed??0).toFixed(0)}`);set('riskGate',(p.risk_gate||'REAL MONEY BLOCKED').replace('REAL MONEY ',''));
  set('next',p.next_phase||'Continue data validation');set('latest',p.latest_result||'No trading edge has been validated yet');
  document.getElementById('marketGrid').innerHTML=MARKETS.map(card).join('');
  for(const m of MARKETS){const el=document.getElementById(`status-${m.id}`);el.textContent=m.id==='BTCUSDT'?'Adapter ready · validation pending':m.id==='FCPO'?'Data source investigation': 'Source validation pending';}
  set('syncText',`Updated ${new Date(p.generated_at||Date.now()).toLocaleString()}`)
 }catch(e){set('syncText','Dashboard data unavailable')}
}
document.getElementById('refreshBtn')?.addEventListener('click',refresh);refresh();setInterval(refresh,120000);
