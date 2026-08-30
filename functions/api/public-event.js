const ALLOWED = new Set(['page_view','quote_calculated','pro_click','tool_open']);
const LIMITS = {tool:120, path:240, visitor:80, text:120, url:500};

const text = (value, limit) => String(value ?? '').trim().slice(0, limit);
const json = (body, status=200) => new Response(JSON.stringify(body), {
  status,
  headers: {
    'content-type': 'application/json',
    'cache-control': 'no-store',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  }
});

export async function onRequestPost(context) {
  try {
    const body = await context.request.json();
    const type = text(body?.type, 40);
    const tool = text(body?.tool, LIMITS.tool);
    const visitorId = text(body?.visitor_id, LIMITS.visitor);
    const path = text(body?.path, LIMITS.path);
    if (!ALLOWED.has(type) || !tool || !path) return json({ok:false,error:'invalid_event'}, 400);

    const event = {
      event_id: crypto.randomUUID(),
      type,
      tool,
      path,
      visitor_id: visitorId || null,
      utm_source: text(body?.utm_source, LIMITS.text) || null,
      utm_medium: text(body?.utm_medium, LIMITS.text) || null,
      utm_campaign: text(body?.utm_campaign, LIMITS.text) || null,
      utm_content: text(body?.utm_content, LIMITS.text) || null,
      utm_term: text(body?.utm_term, LIMITS.text) || null,
      target_path: text(body?.target_path, LIMITS.path) || null,
      target_url: text(body?.target_url, LIMITS.url) || null,
      referrer_origin: (()=>{try{return body?.referrer ? new URL(String(body.referrer)).origin : null}catch{return null}})(),
      ts:new Date().toISOString()
    };

    const store = context.env?.EVENTS;
    if (!store) return json({ok:true,accepted:true,storage:'not_configured',event_id:event.event_id}, 202);

    const key = `event:${Date.now()}:${event.event_id}`;
    await store.put(key, JSON.stringify(event), {expirationTtl:60*60*24*90});
    return json({ok:true,accepted:true,event_id:event.event_id}, 202);
  } catch (error) {
    return json({ok:false,error:'bad_request'}, 400);
  }
}

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    }
  });
}
