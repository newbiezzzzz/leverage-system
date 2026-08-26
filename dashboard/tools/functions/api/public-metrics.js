export async function onRequestGet(context) {
  const events=[];
  const store=context.env?.EVENTS;
  if(store){
    const listed=await store.list({prefix:'event:'});
    for(const entry of listed.keys){
      try{const value=await store.get(entry.name,'json');if(value)events.push(value);}catch{}
    }
  }
  const url=new URL(context.request.url);
  const toolFilter=(url.searchParams.get('tool')||'').trim();
  const filtered=toolFilter?events.filter(e=>e.tool===toolFilter):events;
  const pageViews=filtered.filter(e=>e.type==='page_view');
  const visitors=new Set(pageViews.map(e=>e.visitor_id).filter(Boolean));
  const calculatedQuotes=filtered.filter(e=>e.type==='quote_calculated').length;
  const proClicks=filtered.filter(e=>e.type==='pro_click').length;
  const toolOpens=filtered.filter(e=>e.type==='tool_open').length;
  const sourceCounts=new Map();
  for(const e of pageViews){const source=e.source||e.referrer_origin||'direct';sourceCounts.set(source,(sourceCounts.get(source)||0)+1)}
  const trafficSources=[...sourceCounts.entries()].sort((a,b)=>b[1]-a[1]).slice(0,10).map(([name,views])=>({name,views}));
  const lastEvent=[...filtered].sort((a,b)=>String(b.ts).localeCompare(String(a.ts)))[0]?.ts||null;
  const metrics={
    version:2,
    storage_configured:Boolean(store),
    measurement_source:store?'Leverage public telemetry (Cloudflare Pages Functions + KV)':'Telemetry storage not configured',
    events:filtered.length,
    page_views:pageViews.length,
    unique_visitors:visitors.size||null,
    calculated_quotes:calculatedQuotes,
    pro_clicks:proClicks,
    tool_opens:toolOpens,
    conversion_rate:pageViews.length?Number((proClicks/pageViews.length*100).toFixed(2)):null,
    traffic_sources:trafficSources,
    last_event:lastEvent
  };
  return new Response(JSON.stringify({ok:true,metrics}),{headers:{'content-type':'application/json','cache-control':'no-store','Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET, OPTIONS','Access-Control-Allow-Headers':'Content-Type'}});
}

export async function onRequestOptions(){
  return new Response(null,{status:204,headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET, OPTIONS','Access-Control-Allow-Headers':'Content-Type'}});
}
