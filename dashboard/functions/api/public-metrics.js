export async function onRequestGet(context) {
  const events = [];
  const store = context.env?.EVENTS;
  if (store) {
    const listed = await store.list({prefix:'event:'});
    for (const entry of listed.keys) {
      try {
        const value = await store.get(entry.name, 'json');
        if (value) events.push(value);
      } catch {}
    }
  }
  const metrics = {version:1, storage_configured:Boolean(store), events:events.length, calculated_quotes:events.filter(e=>e.type==='quote_calculated').length, pro_clicks:events.filter(e=>e.type==='pro_click').length, last_event:events.sort((a,b)=>String(b.ts).localeCompare(String(a.ts)))[0]?.ts||null};
  return new Response(JSON.stringify({ok:true,metrics}), {headers:{'content-type':'application/json','cache-control':'no-store'}});
}
