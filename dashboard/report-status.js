(function(){
"use strict";
var root="https://raw.githubusercontent.com/newbiezzzzz/leverage-system/project-status/status/";
function esc(v){return String(v===null||v===undefined?"UNKNOWN":v).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];});}
function fmt(v){return v===null||v===undefined?"UNKNOWN":v;}
function metric(value,label){return '<div class="lm-metric"><strong>'+esc(value)+'</strong><span>'+label+'</span></div>';}
function card(title,r){
 if(!r)return '<article class="lm-card"><div class="lm-label">'+title+'</div><div class="lm-state unknown">NO REPORT PUBLISHED</div><div class="lm-detail">No completed report is available yet. This is not a zero-return result.</div></article>';
 var full=(r.reference_profile_results&&r.reference_profile_results.full_sample)||(r.results&&r.results.full_sample)||null;
 var m=(full&&full.metrics)||r.metrics||{};
 var status=r.status||"UNKNOWN",reason=r.reason||r.blocker||"No blocker text recorded.";
 var net=m.net_return_usdt!==undefined?"USDT "+m.net_return_usdt:m.net_return_rm!==undefined?"RM "+m.net_return_rm:"UNKNOWN";
 var avg=m.monthly_average_net_return_usdt!==undefined?"USDT "+m.monthly_average_net_return_usdt:m.monthly_average_net_return_rm!==undefined?"RM "+m.monthly_average_net_return_rm:"UNKNOWN";
 var dd=m.max_drawdown_pct!==undefined?m.max_drawdown_pct+"%":"UNKNOWN";
 var wr=m.win_rate_pct!==undefined&&m.win_rate_pct!==null?m.win_rate_pct+"%":"UNKNOWN";
 var trades=m.trades!==undefined?m.trades:"UNKNOWN",losses=m.losses!==undefined?m.losses:"UNKNOWN",lpm="UNKNOWN";
 var months=full&&Array.isArray(full.monthly)?full.monthly:null;
 if(months&&months.length){lpm=(months.reduce(function(a,x){return a+Number(x.losses||0);},0)/months.length).toFixed(2);}
 var kind=/COMPLETED/.test(status)?"success":status==="BLOCKED"?"failure":"unknown";
 return '<article class="lm-card"><div class="lm-label">'+title+' · Latest report</div><div class="lm-state '+kind+'">'+esc(status)+'</div><div class="lm-detail">'+esc(reason)+'</div><div class="lm-metrics">'+metric(net,"Net return")+metric(wr,"Win rate")+metric(losses,"Losing trades")+metric(lpm,"Losing trades / month")+metric(avg,"Average net / month")+metric(dd,"Max drawdown")+metric(trades,"Trades")+'</div></article>';
}
function init(){
 var path=location.pathname.toLowerCase(),isMaster=path.endsWith("/master.html")||path.endsWith("/index.html")||path==="/";
 var key=path.endsWith("project-btcusdt.html")?"btc":path.endsWith("project-fcpo.html")?"fcpo":null;
 if(!isMaster&&!key)return;
 var panel=document.createElement("section");panel.className="live-monitor";panel.id="project-report-monitor";
 panel.innerHTML='<div class="lm-head"><div><div class="lm-label">Verified report data</div><h2>Backtest performance reports</h2><p>Metrics are read from the report JSON published by completed BTCUSDT/FCPO workflows. Missing values remain UNKNOWN.</p></div><button type="button" id="report-refresh">Refresh reports</button></div><div class="lm-grid" id="report-grid"><p>Loading report JSON…</p></div>';
 var footer=document.querySelector("footer"),main=document.querySelector("main");
 if(footer&&footer.parentNode)footer.parentNode.insertBefore(panel,footer);else if(main)main.appendChild(panel);else document.body.appendChild(panel);
 function load(){
  var grid=document.getElementById("report-grid");grid.innerHTML="<p>Loading report JSON…</p>";
  var keys=isMaster?["btc","fcpo"]:[key];
  Promise.all(keys.map(function(k){return fetch(root+k+".json?refresh="+Date.now(),{cache:"no-store"}).then(function(r){if(!r.ok)throw new Error("HTTP "+r.status);return r.json();}).catch(function(){return null;}).then(function(d){return {key:k,data:d};});})).then(function(results){
   grid.innerHTML=results.map(function(x){return card(x.key==="btc"?"BTCUSDT":"FCPO",x.data);}).join("");
  });
 }
 document.getElementById("report-refresh").addEventListener("click",load);load();
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();