(function(){
  const pages=[
    ['company.html','Overview'],
    ['trading.html','Trading'],
    ['markets.html','Markets'],
    ['strategies.html','Toolkit'],
    ['workers.html','System']
  ];
  const current=(location.pathname.split('/').pop()||'company.html').split('?')[0];
  document.querySelectorAll('.dashboard-select').forEach(old=>{
    const wrap=document.createElement('div');wrap.className='dashboard-dropdown';
    const button=document.createElement('button');button.type='button';button.className='dashboard-trigger';button.setAttribute('aria-expanded','false');
    const label=pages.find(p=>p[0]===current)?.[1]||'Dashboard';
    button.innerHTML=`<span>Dashboard</span><b>▾</b>`;
    const menu=document.createElement('div');menu.className='dashboard-menu';menu.setAttribute('role','menu');
    pages.forEach(([href,text])=>{const a=document.createElement('a');a.href=href;a.textContent=text;a.setAttribute('role','menuitem');if(href===current)a.className='active';menu.appendChild(a)});
    wrap.append(button,menu);old.replaceWith(wrap);
    button.addEventListener('click',e=>{e.stopPropagation();const open=wrap.classList.toggle('open');button.setAttribute('aria-expanded',String(open))});
  });
  document.addEventListener('click',()=>document.querySelectorAll('.dashboard-dropdown.open').forEach(x=>{x.classList.remove('open');x.querySelector('button')?.setAttribute('aria-expanded','false')}));
})();
