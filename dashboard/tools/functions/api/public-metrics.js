export async function onRequestGet(context) {
  const events=[];
  const store=context.env?.EVENTS;
  if(store){
    let cursor;
    do {
      const listed=await store.list({prefix:'event:', ...(cursor?{cursor}:{})});
      for(const entry of listed.keys){
        try{const value=await store.get(entry.name,'json');if(value)events.push(value);}catch{}
      }
      cursor=listed.list_complete?undefined:listed.cursor;
    } while(cursor);
  }
  const url=new URL(context.request.url);
  const toolFilter=(url.searchParams.get('tool')||'').trim();
  const filtered=toolFilter?events.filter(e=>e.tool===toolFilter):events;
  const pageViews=filtered.filter(e=>e.type==='page_view');
  const visitors=new Set(pageViews.map(e=>e.visitor_id).filter(Boolean));
  const calculatedQuotes=filtered.filter(e=>e.type==='quote_calculated').length;
  const proClicks=filtered.filter(e=>e.type==='pro_click').length;
  const toolOpens=filtered.filter(e=>e.type==='tool_open').length;
  const engagedVisitors=new Set(filtered.filter(e=>e.type!=='page_view').map(e=>e.visitor_id).filter(Boolean));
  const sourceCounts=new Map();
  const campaignCounts=new Map();
  const contentCounts=new Map();
  for(const e of pageViews){
    const source=e.utm_source||e.referrer_origin||'direct';
    sourceCounts.set(source,(sourceCounts.get(source)||0)+1);
    if(e.utm_campaign){campaignCounts.set(e.utm_campaign,(campaignCounts.get(e.utm_campaign)||0)+1);}
    if(e.utm_content){contentCounts.set(e.utm_content,(contentCounts.get(e.utm_content)||0)+1);}
  }
  const topCounts=(map)=>[...map.entries()].sort((a,b)=>b[1]-a[1]).slice(0,10).map(([name,views])=>({name,views}));
  const lastEvent=[...filtered].sort((a,b)=>String(b.ts).localeCompare(String(a.ts)))[0]?.ts||null;
  const metrics={
    version:3,
    storage_configured:Boolean(store),
    measurement_source:store?'Leverage public telemetry (Cloudflare Pages Functions + KV)':'Telemetry storage not configured',
    retention_days:90,
    events:filtered.length,
    page_views:pageViews.length,
    unique_visitors:visitors.size||null,
    engaged_visitors:engagedVisitors.size||null,
    calculated_quotes:calculatedQuotes,
    pro_clicks:proClicks,
    tool_opens:toolOpens,
    click_through_rate:pageViews.length?Number((proClicks/pageViews.length*100).toFixed(2)):null,
    quote_rate:pageViews.length?Number((calculatedQuotes/pageViews.length*100).toFixed(2)):null,
    engagement_rate:visitors.size?Number((engagedVisitors.size/visitors.size*100).toFixed(2)):null,
    traffic_sources:topCounts(sourceCounts),
    campaigns:topCounts(campaignCounts),
    content:topCounts(contentCounts),
    purchase_tracking:'not connected; Gumroad purchase/revenue must remain UNKNOWN until authoritative evidence is available',
    last_event:lastEvent
  };
  return new Response(JSON.stringify({ok:true,metrics}),{headers:{'content-type':'application/json','cache-control':'no-store','Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET, OPTIONS','Access-Control-Allow-Headers':'Content-Type'}});
}

export async function onRequestOptions(){
  return new Response(null,{status:204,headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET, OPTIONS','Access-Control-Allow-Headers':'Content-Type'}});
}
