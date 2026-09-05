(() => {
  const params = new URLSearchParams(location.search);
  if (params.get('id') !== 'affiliate-project' || params.get('product')) return;

  const esc = v => String(v ?? '').replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));

  async function render() {
    const root = document.getElementById('detail');
    if (!root) return setTimeout(render, 100);

    try {
      const payload = await fetch('/api/projects', { cache: 'no-store' }).then(r => r.json());
      const p = (payload.projects || []).find(x => x.id === 'affiliate-project');
      if (!p) return;

      const steps = p.continue_list || [];
      const platforms = p.platforms || [];
      const strategy = p.product_strategy || {};
      const active = steps.filter(s => s.status === 'active').length;
      const queued = steps.filter(s => s.status === 'queued').length;

      root.innerHTML = `
        <section class="detail-hero">
          <div>
            <div class="project-id">${esc(p.project_no || 'P-002')} · AFFILIATE</div>
            <h1>${esc(p.name)}</h1>
            <p class="muted2">Automated product recommendation and content acquisition engine.</p>
          </div>
          <div>
            <span class="pill2 status-good">${esc(String(p.status || 'active').toUpperCase())}</span>
            <span class="pill2">${esc(String(p.lifecycle_stage || 'validation').toUpperCase())}</span>
          </div>
        </section>

        <section class="section">
          <div class="panel-head">
            <div><p class="eyebrow">BUILD ROADMAP</p><h2>Continue</h2></div>
            <span class="pill2">${active} active · ${queued} queued</span>
          </div>
          <div class="grid2">
            ${steps.map(s => `
              <div class="metric-box">
                <span>${esc(s.step)} · ${esc(String(s.status || '').toUpperCase())}</span>
                <strong>${esc(s.name)}</strong>
                <small class="muted2">${esc(s.description)}</small>
              </div>`).join('')}
          </div>
        </section>

        <section class="section">
          <div class="panel-head"><div><p class="eyebrow">ACQUISITION</p><h2>Platforms</h2></div></div>
          <div class="grid3">
            ${platforms.map(x => `
              <div class="metric-box">
                <span>${esc(x.priority || 'channel')} · ${esc(x.status || 'planned')}</span>
                <strong>${esc(x.name)}</strong>
                <small class="muted2">${esc(x.role)}</small>
                <small class="muted2">${esc(x.monetization)}</small>
              </div>`).join('')}
          </div>
        </section>

        <section class="section">
          <div class="panel-head">
            <div><p class="eyebrow">OFFER RESEARCH</p><h2>Product Pipeline</h2></div>
            <span class="pill2">${esc(strategy.catalog_status || 'research_pending')}</span>
          </div>
          <div class="grid2">
            <div class="metric-box">
              <span>Current selection</span>
              <strong>No product selected</strong>
              <small class="muted2">Product research begins in B4 after opportunity validation.</small>
            </div>
            <div class="metric-box">
              <span>Selection rule</span>
              <strong>Problem-solving first</strong>
              <small class="muted2">${esc(strategy.selection_rule || '')}</small>
            </div>
          </div>
        </section>

        <section class="section">
          <div class="panel-head"><div><p class="eyebrow">SYSTEM</p><h2>Automation</h2></div></div>
          <div class="grid3">
            ${(p.automation_modules || []).map(x => `<div class="metric-box"><strong>${esc(x)}</strong></div>`).join('')}
          </div>
          <div class="kv" style="margin-top:16px">
            <b>Business model</b><span>${esc(p.business_model || '')}</span>
            <b>Owner role</b><span>${esc(p.owner_role || '')}</span>
            <b>Capital policy</b><span>${esc(p.capital_policy || 'RM0-first')}</span>
          </div>
        </section>
      `;
    } catch (_) {}
  }

  render();
})();
