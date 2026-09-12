/* State PUC docket watch */
const $ = s => document.querySelector(s);
const esc = s => String(s??'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

let DATA = null;
const state = { state: 'ALL', topic: 'ALL' };
const ORDER = ["large load / data centers","interconnection","rates / tariffs","certificates / siting","general"];

function allTopics(){
  const seen = new Set();
  DATA.dockets.forEach(d => d.topics.forEach(t => seen.add(t)));
  return ORDER.filter(t => seen.has(t));
}

function renderFilters(){
  const states = ['ALL', ...DATA.coverage.live, ...DATA.coverage.degraded];
  $('#stateFilters').innerHTML = '<span class="lbl">State</span>' + states.map(s =>
    `<button class="fbtn ${state.state===s?'on':''}" data-state="${s}">${s==='ALL'?'All':s}</button>`).join('');
  const topics = ['ALL', ...allTopics()];
  $('#topicFilters').innerHTML = '<span class="lbl">Topic</span>' + topics.map(t =>
    `<button class="fbtn ${state.topic===t?'on':''}" data-topic="${esc(t)}">${t==='ALL'?'All topics':esc(t)}</button>`).join('');
  document.querySelectorAll('[data-state]').forEach(b => b.onclick = () => { state.state = b.dataset.state; renderFilters(); renderList(); });
  document.querySelectorAll('[data-topic]').forEach(b => b.onclick = () => { state.topic = b.dataset.topic; renderFilters(); renderList(); });
}

function renderList(){
  let ds = DATA.dockets.filter(d =>
    (state.state==='ALL' || d.state===state.state) &&
    (state.topic==='ALL' || d.topics.includes(state.topic)));
  let html = '';
  (DATA.notes||[]).forEach(n => { html += `<div class="note">${esc(n)}</div>`; });
  if(!ds.length){ html += '<div class="empty">No dockets match those filters in the current window.</div>'; }
  html += ds.map(d => `
    <div class="dk">
      <span class="stb ${d.state}">${d.state}</span>
      <div class="bd">
        <h3><a href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.title)}</a></h3>
        <div class="meta">${[d.docket, d.status, d.established ? 'opened ' + d.established : null, d.recent_docs!=null ? d.recent_docs + ' filing' + (d.recent_docs>1?'s':'') + ' mentioning data centers / large loads in 45d' : null].filter(Boolean).map(esc).join('  ·  ')}</div>
        <div class="tags">${d.topics.map(t=>`<span class="tg ${t==='large load / data centers'||t==='interconnection'?'hl':''}">${esc(t)}</span>`).join('')}</div>
      </div>
    </div>`).join('');
  $('#list').innerHTML = html;
}

function renderHeader(){
  const n = DATA.dockets.length;
  const ll = DATA.dockets.filter(d => d.topics.includes('large load / data centers')).length;
  const ic = DATA.dockets.filter(d => d.topics.includes('interconnection')).length;
  const states = new Set(DATA.dockets.map(d => d.state)).size;
  $('#stats').innerHTML = `
    <div class="st"><b>${n}</b><span>active dockets</span></div>
    <div class="st"><b>${states}</b><span>states live</span></div>
    <div class="st"><b>${ll}</b><span>large load / DC</span></div>
    <div class="st"><b>${ic}</b><span>interconnection</span></div>`;
  $('#cov').innerHTML =
    DATA.coverage.live.map(s=>`<span class="c on">${s} · live</span>`).join('') +
    (DATA.coverage.degraded||[]).map(s=>`<span class="c deg">${s} · source down</span>`).join('') +
    DATA.coverage.coming.map(s=>`<span class="c">${s} · coming</span>`).join('');
  $('#fresh').textContent = `${DATA.source} · ${DATA.window_days}-day window · refreshed ${DATA.refreshed_at.replace('T',' ').replace('Z',' UTC')}`;
}

fetch('data/puc.json').then(r=>r.json()).then(d => {
  DATA = d;
  renderHeader(); renderFilters(); renderList();
}).catch(e => { $('#list').innerHTML = '<div class="empty">Docket data failed to load.</div>'; });
