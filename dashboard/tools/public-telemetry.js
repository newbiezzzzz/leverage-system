(function(){
  const path=location.pathname.replace(/\/+$/,'')||'/';
  const tool=path.split('/').pop()||'home';
  const query=new URLSearchParams(location.search);
  const source=query.get('utm_source')||query.get('source')||'';
  let visitorId='';
  try{visitorId=localStorage.getItem('leverage_visitor_id')||crypto.randomUUID();localStorage.setItem('leverage_visitor_id',visitorId)}catch{visitorId=''}
  let lastQuote=0;
  async function event(type,extra){
    try{await fetch('/api/public-event',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type,tool,path,visitor_id:visitorId,utm_source:source,referrer:document.referrer,...(extra||{})}),keepalive:true});}catch{}
  }
  event('page_view');
  document.addEventListener('click',e=>{
    const a=e.target.closest('a');
    if(!a) return;
    try{
      const u=new URL(a.href,location.href);
      if(u.hostname==='newbiezz.gumroad.com') event('pro_click');
      else if(u.origin===location.origin && /fabrication-profit-system|\/p001\/?$/.test(u.pathname)) event('pro_click');
      else if(u.origin===location.origin && /calculator|guide/.test(u.pathname)) event('tool_open');
    }catch{}
  });
  const inputs=document.querySelectorAll('input');
  if(inputs.length){
    const mark=()=>{const now=Date.now();if(now-lastQuote>3000){lastQuote=now;event('quote_calculated');}};
    inputs.forEach(i=>i.addEventListener('input',mark));
    document.querySelectorAll('button').forEach(b=>b.addEventListener('click',mark));
  }
})();
