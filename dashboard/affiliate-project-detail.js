(() => {
  const params = new URLSearchParams(location.search);
  if (params.get('id') !== 'affiliate-project' || params.get('product')) return;
  const esc = v => String(v ?? '').replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
  const waitForDetail = () => {
    const root = document.getElementById('detail');
    if (!root || !root.querySelector('.detail-hero')) return setTimeout(waitForDetail, 100);
    if (document.getElementById('affiliate-control-center')) return;
    fetch('/api/projects', {cache:'no-store'}).then(r => r.json()).then(payload => {
      const p = (payload.projects || []).find(x => x.id === 'affiliate-project');
      if (!p) return;
      const steps = p.continue_list || [];
      const platforms = p.platforms || [];
      const products = p.product_strategy || {};
      const section = document.createElement('section');
      section.className = 'section';
      section.id = 'affiliate-control-center';
      section.innerHTML = `
        <div class="panel-head"><div><p class="eyebrow">AFFILIATE PROJECT CONTROL CENTER</p><h2>Continue</h2><p class="muted2">Build sequence is tracked here while implementation progresses.</p></div><span class="pill2">${steps.filter(s => s.status === 'active').length} active · ${steps.filter(s => s.status === 'queued').length} queued</span></div>
        <div class="grid2">${steps.map(s => `<div class="metric-box"><span>${esc(s.step)} · ${esc(s.status).toUpperCase()}</span><strong>${esc(s.name)}</strong><small class="muted2">${esc(s.description)}</small></div>`).join('')}</div>
        <div class="panel-head" style="margin-top:22px"><div><p class="eyebrow">PLATFORMS</p><h2>Platform detail</h2></div></div>
        <div class="grid3">${platforms.map(x => `<div class="metric-box"><span>${esc(x.priority || 'channel')} · ${esc(x.status || 'planned')}</span><strong>${esc(x.name)}</strong><small class="muted2">${esc(x.role)}</small><small class="muted2">Monetization: ${esc(x.monetization)}</small></div>`).join('')}</div>
        <div class="panel-head" style="margin-top:22px"><div><p class="eyebrow">PRODUCTS</p><h2>Product pipeline</h2></div><span class="pill2">${esc(products.catalog_status || 'pending')}</span></div>
        <div class="grid2"><div class="metric-box"><span>Current catalog</span><strong>No product selected yet</strong><small class="muted2">Leverage will research and rank automotive offers in B4 after B3 opportunity validation.</small></div><div class="metric-box"><span>Selection rule</span><strong>Problem-solving first</strong><small class="muted2">${esc(products.selection_rule || '')}</small></div></div>
      `;
      const hero = root.querySelector('.detail-hero');
      hero.insertAdjacentElement('afterend', section);
    }).catch(() => {});
  };
  waitForDetail();
})();
