export async function onRequestPost(context) {
  try {
    const body = await context.request.json();
    const type = String(body?.type || '').trim();
    const tool = String(body?.tool || '').trim();
    if (!type || !tool) return new Response(JSON.stringify({ok:false,error:'invalid_event'}), {status:400, headers:{'content-type':'application/json'}});
    const event = {type, tool, ts: new Date().toISOString()};
    if (!context.env?.EVENTS) return new Response(JSON.stringify({ok:true,accepted:true,storage:'not_configured'}), {status:202,headers:{'content-type':'application/json'}});
    const key = `event:${Date.now()}:${crypto.randomUUID()}`;
    await context.env.EVENTS.put(key, JSON.stringify(event), {expirationTtl: 60 * 60 * 24 * 90});
    return new Response(JSON.stringify({ok:true,accepted:true}), {status:202,headers:{'content-type':'application/json'}});
  } catch {
    return new Response(JSON.stringify({ok:false,error:'bad_request'}), {status:400,headers:{'content-type':'application/json'}});
  }
}
