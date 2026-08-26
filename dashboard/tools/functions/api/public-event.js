const ALLOWED = new Set(['page_view','quote_calculated','pro_click','tool_open']);

export async function onRequestPost(context) {
  try {
    const body = await context.request.json();
    const type = String(body?.type || '').trim();
    const tool = String(body?.tool || '').trim().slice(0,120);
    const visitorId = String(body?.visitor_id || '').trim().slice(0,80);
    const path = String(body?.path || '').trim().slice(0,240);
    const source = String(body?.utm_source || '').trim().slice(0,80);
    if (!ALLOWED.has(type) || !tool) return new Response(JSON.stringify({ok:false,error:'invalid_event'}), {status:400,headers:{'content-type':'application/json'}});
    const event = {
      type,
      tool,
      path,
      visitor_id: visitorId || null,
      source: source || null,
      referrer_origin: (()=>{try{return body?.referrer ? new URL(String(body.referrer)).origin : null}catch{return null}})(),
      ts:new Date().toISOString()
    };
    if (!context.env?.EVENTS) return new Response(JSON.stringify({ok:true,accepted:true,storage:'not_configured'}), {status:202,headers:{'content-type':'application/json'}});
    const key = `event:${Date.now()}:${crypto.randomUUID()}`;
    await context.env.EVENTS.put(key, JSON.stringify(event), {expirationTtl:60*60*24*90});
    return new Response(JSON.stringify({ok:true,accepted:true}), {status:202,headers:{'content-type':'application/json'}});
  } catch {
    return new Response(JSON.stringify({ok:false,error:'bad_request'}), {status:400,headers:{'content-type':'application/json'}});
  }
}
