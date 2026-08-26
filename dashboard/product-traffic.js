(function(){
  const params=new URLSearchParams(location.search);
  const product=params.get('product');
  if(!product)return;
  const METRICS='/api/public-metrics';
  const esc=v=>String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
  const analyse=m=>{
    const visitors=m.unique_visitors;
    const pages=Number(m.page_views||0);
    const clicks=Number(m.pro_clicks||0);
    const quotes=Number(m.calculated_quotes||0);
    const sources=m.traffic_sources||[];
    const recommendations=[];
    const evidence=[];
    if(visitors==null&&pages===0){
      evidence.push('No verified traffic totals are available yet.');
      recommendations.push('Keep telemetry live and wait for verified demand evidence before scaling acquisition.');
    }else{
      evidence.push(`Verified traffic: ${pages} page views and ${visitors==null?'unknown':visitors} unique visitors.`);
      evidence.push(`Calculator interactions: ${quotes}.`);
      evidence.push(`Outbound Product 1 clicks: ${clicks}.`);
      if(clicks===0)recommendations.push('Improve the free-tool-to-Product-1 CTA before adding another acquisition channel.');
      else if(pages&&clicks/pages<0.02)recommendations.push('Prioritize CTA placement, offer clarity and Product 1 presentation; buyer intent is present but weak.');
      else recommendations.push('Double down on the strongest measured source and test one additional compliant acquisition angle.');
    }
    if(sources.length)recommendations.unshift(`Prioritize ${sources[0].name}; it currently produces the most measured traffic (${sources[0].views} views).`);
    return {confidence:(pages>0?'medium':'low'),evidence,recommendations:recommendations.slice(0,3)};
  };
  async function load(){
    try{
      const r=await fetch(`${METRICS}?tool=${encodeURIComponent('fabrication-quote-calculator')}&ts=${Date.now()}`,{cache:'no-store'});
      if(!r.ok)throw new Error(`metrics ${r.status}`);
      const payload=await r.json();
      const m=payload.metrics||{};
      const sections=[...document.querySelectorAll('.section')];
      const section=sections.find(s=>/Product traffic & acquisition/i.test(s.textContent||''));
      if(!section)return;
      const status=m.storage_configured?'CONNECTED':'NOT CONNECTED';
      const statusClass=m.storage_configured?'status-good':'status-warn';
      const visitors=m.unique_visitors==null?'UNKNOWN':m.unique_visitors;
      const conversion=m.conversion_rate==null?'UNKNOWN':`${Number(m.conversion_rate).toFixed(2)}%`;
      const sources=(m.traffic_sources||[]).length
        ? m.traffic_sources.map(x=>`<span>${esc(x.name)}: ${esc(x.views)} views</span>`).join(' · ')
        : 'None recorded yet';
      const insight=analyse(m);
      section.innerHTML=`<h2>Product traffic & acquisition</h2>
        <div class="grid3">
          <div class="metric-box"><span>Acquisition</span><strong class="status-good">ACTIVE</strong><small class="muted2">Free fabrication tools → Product 1</small></div>
          <div class="metric-box"><span>Traffic measurement</span><strong class="${statusClass}">${status}</strong><small class="muted2">Cloudflare Pages telemetry</small></div>
          <div class="metric-box"><span>Visitors</span><strong>${esc(visitors)}</strong><small class="muted2">Anonymous measured visitors</small></div>
          <div class="metric-box"><span>Tool events</span><strong>${esc(m.events)}</strong><small class="muted2">Tracked public events</small></div>
          <div class="metric-box"><span>Calculator events</span><strong>${esc(m.calculated_quotes)}</strong><small class="muted2">Quote interactions</small></div>
          <div class="metric-box"><span>Product clicks</span><strong>${esc(m.pro_clicks)}</strong><small class="muted2">Outbound buyer interest</small></div>
          <div class="metric-box"><span>Conversion</span><strong>${esc(conversion)}</strong><small class="muted2">Product clicks ÷ measured page views</small></div>
        </div>
        <div class="kv" style="margin-top:16px">
          <b>Measurement source</b><span>${esc(m.measurement_source||'Not connected')}</span>
          <b>Last verified</b><span>${esc(m.last_event||'Not recorded')}</span>
          <b>Traffic sources</b><span>${sources}</span>
        </div>
        <section class="section" style="margin-top:18px">
          <div class="panel-head"><div><p class="eyebrow">ACQUISITION INTELLIGENCE</p><h2>Leverage Acquisition Analyst</h2></div><span class="pill2">${esc(insight.confidence.toUpperCase())} CONFIDENCE</span></div>
          <div class="kv"><b>Evidence</b><span>${insight.evidence.map(esc).join(' · ')||'None yet'}</span><b>Recommended next actions</b><span>${insight.recommendations.map((x,i)=>`${i+1}. ${esc(x)}`).join(' ')||'No recommendation until verified evidence is available.'}</span></div>
          <p class="muted2" style="margin-top:12px">This view is evidence-first. It does not send outreach, spend money or claim revenue.</p>
        </section>
        <p class="danger muted2">Telemetry is acquisition evidence, not revenue. Revenue remains zero until an authoritative sale/payout event is verified.</p>`;
    }catch{
      const sections=[...document.querySelectorAll('.section')];
      const section=sections.find(s=>/Product traffic & acquisition/i.test(s.textContent||''));
      if(section){
        const note=section.querySelector('.muted2');
        if(note)note.textContent='Telemetry endpoint unavailable; unknown traffic is not treated as zero.';
      }
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',load);else load();
})();
