(function(){
  const path=location.pathname.replace(/\/+$/,'');
  const tool=path.split('/').pop()||'home';
  let lastQuote=0;
  async function event(type){
    try{await fetch('/api/public-event',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type,tool}),keepalive:true});}catch{}
  }
  event('page_view');
  document.addEventListener('click',e=>{const a=e.target.closest('a[href*="gumroad.com"]');if(a)event('pro_click');});
  const inputs=document.querySelectorAll('input');
  if(inputs.length){
    const mark=()=>{const now=Date.now();if(now-lastQuote>3000){lastQuote=now;event('quote_calculated');}};
    inputs.forEach(i=>i.addEventListener('input',mark));
    document.querySelectorAll('button').forEach(b=>b.addEventListener('click',mark));
  }
})();
