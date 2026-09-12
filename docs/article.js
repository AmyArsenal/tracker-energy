/* article page: specialist analysis + in-site document viewer (split view) */
const $ = s => document.querySelector(s);
const esc = s => String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function tryLoad(p){ const r = await fetch(p,{cache:'no-store'}); return r.ok ? r.json() : null; }

(async()=>{
  const acc = new URLSearchParams(location.search).get('acc');
  const ferc = await tryLoad('data/ferc.json');
  const item = ferc && (ferc.items||[]).find(i=>i.accession===acc);
  if(!item){
    $('#arthead').innerHTML = `<h1>Filing not found</h1><p class="dek">This accession is outside the current 60-day window. <a href="/news.html">Back to News</a>.</p>`;
    return;
  }
  const art = await tryLoad(`data/articles/${acc}.json`);
  const articleIds = ['20260903-5199','20260903-5243','20260904-5013','20260904-5197','20260908-5083','20260908-5211','20260908-5312','20260908-5330'];
  const relatedArts = (await Promise.all(articleIds.filter(x=>x!==acc).map(async x=>({acc:x, art:await tryLoad(`data/articles/${x}.json`), item:(ferc.items||[]).find(i=>i.accession===x)})))).filter(x=>x.art&&x.item);
  const itemDockets = new Set((item.dockets||[]).map(d=>d.replace(/-000$/,'')));
  relatedArts.sort((a,b)=>{ const am=(a.item.dockets||[]).some(d=>itemDockets.has(d.replace(/-000$/,'')))?1:0, bm=(b.item.dockets||[]).some(d=>itemDockets.has(d.replace(/-000$/,'')))?1:0; return bm-am || (b.art.written_at||'').localeCompare(a.art.written_at||''); });
  $('#related').innerHTML = `<h2>Recommended reading</h2><p class="rintro">Related cited analysis from the record.</p>` + relatedArts.slice(0,4).map((r,n)=>`<article class="relitem"><div class="rk">${(r.item.dockets||[]).some(d=>itemDockets.has(d.replace(/-000$/,'')))?'Same docket':'From the record'}</div><h3><a href="article.html?acc=${encodeURIComponent(r.acc)}">${esc(r.art.title)}</a></h3><p>${esc(r.item.filed||'')} · ${esc((r.item.dockets||[])[0]?.replace(/-000$/,'')||'FERC')}</p></article>`).join('');
  const chips = `${item.class?`<span class="chip cls">${esc(item.class)}</span>`:''}` +
    (item.dockets||[]).slice(0,4).map(d=>`<span class="chip">${esc(d.replace(/-000$/,''))}</span>`).join('');
  $('#arthead').innerHTML = `
    <div class="eyebrow">FILED ${esc(item.filed||'')} · ${esc(item.category||'SUBMITTAL').toUpperCase()}</div>
    <h1>${esc(art?.title || item.summary)}</h1>
    ${art?.dek ? `<p class="dek">${esc(art.dek)}</p>` : ''}
    <div class="chips">${chips}<span class="chip">ACC ${esc(item.accession)}</span></div>`;
  document.title = `${(art?.title||item.summary).slice(0,70)} - tracker.energy`;

  const facts = `
    <div class="factbox"><table>
      <tr><td>Filed by</td><td><b>${esc(item.author||'Unknown')}</b></td></tr>
      <tr><td>Filing date</td><td>${esc(item.filed||'—')} (issued ${esc(item.issued||'—')})</td></tr>
      <tr><td>Docket(s)</td><td>${esc((item.dockets||[]).join(', ')||'—')}</td></tr>
      <tr><td>Document class</td><td>${esc(item.class||'—')}${item.type?` · ${esc(item.type)}`:''}</td></tr>
      <tr><td>Source file</td><td>${esc(item.file_name||'—')}</td></tr>
      <tr><td>Official record</td><td><a class="src" href="${esc(item.url)}" target="_blank" rel="noopener">Open in FERC eLibrary ↗</a></td></tr>
    </table></div>`;

  let body;
  if(art){
    body = `
      <div class="byline"><div class="ava">${esc((art.byline||'Data Center Desk').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase())}</div><div><div class="who">${esc(art.byline||'Data Center Desk')}</div><div class="role">tracker.energy analysis · ${esc(art.written_at||'')}</div></div></div>
      ${art.body_html||''}
      ${art.key_points?.length?`<div class="kpoints"><h3>Key points</h3><ul>${art.key_points.map(k=>`<li>${esc(k)}</li>`).join('')}</ul></div>`:''}
      ${art.deep_dives?.length? art.deep_dives.map(d=>`<details class="dd"><summary>${esc(d.title)}</summary><div class="ddbody">${d.body_html||''}</div></details>`).join(''):''}
      ${art.watch?.length?`<div class="watch"><h3>What to watch</h3><ul>${art.watch.map(k=>`<li>${esc(k)}</li>`).join('')}</ul></div>`:''}
      ${facts}`;
  } else {
    body = `
      <div class="byline"><div class="ava">DC</div><div><div class="who">Data Center Desk</div><div class="role">filing brief · full analysis pending next nightly cycle</div></div></div>
      <h2>The filing</h2>
      <p>${esc(item.description)}</p>
      <p>This document matched our nightly "data center" scan of FERC eLibrary. It may reference data centers directly - a large-load interconnection, co-location arrangement or related rate issue - or mention them in passing. The document itself is definitive: it opens on the right.</p>
      ${facts}`;
  }

  const pdfLocal = item.doc_local ? item.doc_local.replace(/\.pdf$/, '.pdfdata') : null;
  const doc = pdfLocal
    ? `<div class="docpane"><div class="bar"><span class="t">Source document</span><a class="src" href="${esc(pdfLocal)}" target="_blank" rel="noopener">raw PDF ↗</a></div>
       <div class="pdfv">
         <div class="vbar">
           <button id="pv-prev">‹</button><span class="pg" id="pv-pg">…</span><button id="pv-next">›</button>
           <span class="sp"></span><span class="pg" id="pv-note" style="color:var(--green2)"></span>
         </div>
         <div class="stage" id="pv-stage"><div class="vload">Loading document…</div></div>
       </div></div>`
    : `<div class="docpane"><div class="nodoc"><b>Source document available at FERC</b><br><br>${(item.file_size||0)>15000000?`The ${((item.file_size||0)/1000000).toFixed(1)} MB source exceeds this site's 15 MB mirror limit. `:`This filing is metadata-only in the local preview. `}Nothing is missing from the official record.<br><br><a href="${esc(item.url)}" target="_blank" rel="noopener">Open the exact FERC record ↗</a></div></div>`;

  $('#split').innerHTML = `<div class="article">${body}
      <div class="mobdoc">${pdfLocal?`<a class="btn" href="${esc(pdfLocal)}" target="_blank" rel="noopener">Open the source document →</a>`:''}</div>
      <p style="margin-top:28px"><a href="/news.html">← Back to News</a></p></div>${doc}`;
  if(pdfLocal){
    initViewer(pdfLocal, (art && art.annotations) || []).catch(e=>{
      const st = document.getElementById('pv-stage');
      if(st) st.innerHTML = '<div class="vload">Document failed to render.</div>';
    });
  }
})();

/* ---------- pdf.js viewer with bbox annotations ---------- */
async function initViewer(pdfUrl, annotations){
  window.onerror = (m)=>{ const st=document.getElementById('pv-stage'); if(st) st.innerHTML = '<div class="vload">ERR: '+esc(m)+'</div>'; };
  if(!window.pdfjsLib){
    await new Promise((res, rej)=>{
      const s = document.createElement('script');
      s.src = 'vendor/pdf.min.js';
      s.onload = res; s.onerror = rej; document.head.appendChild(s);
    }).catch(()=>{ $('#pv-stage').innerHTML = `<div class="vload">Viewer failed to load - <a href="${pdfUrl}">open the raw PDF</a>.</div>`; throw new Error('pdfjs cdn'); });
  }
  pdfjsLib.GlobalWorkerOptions.workerSrc = 'vendor/pdf.worker.min.js';
  const doc = await pdfjsLib.getDocument(pdfUrl).promise;
  const stage = $('#pv-stage'); stage.innerHTML = '';
  const canvas = document.createElement('canvas');
  const overlay = document.createElement('div'); overlay.className = 'overlay';
  stage.appendChild(canvas); stage.appendChild(overlay);
  let pageNo = 1;
  const byPage = {};
  (annotations||[]).forEach(a => { (byPage[a.page] = byPage[a.page]||[]).push(a); });
  async function render(n){
    pageNo = Math.max(1, Math.min(doc.numPages, n));
    const page = await doc.getPage(pageNo);
    const base = page.getViewport({scale: 1});
    const scale = (stage.clientWidth || 600) / base.width;
    const vp = page.getViewport({scale});
    const DPR = Math.min(window.devicePixelRatio||1, 2);
    canvas.width = vp.width*DPR; canvas.height = vp.height*DPR;
    canvas.style.width = vp.width+'px'; canvas.style.height = vp.height+'px';
    overlay.style.width = vp.width+'px'; overlay.style.height = vp.height+'px';
    await page.render({canvasContext: canvas.getContext('2d'), viewport: vp, transform: DPR!==1?[DPR,0,0,DPR,0,0]:null}).promise;
    $('#pv-pg').textContent = `p. ${pageNo} / ${doc.numPages}`;
    overlay.innerHTML = '';
    for(const a of (byPage[pageNo]||[])){
      const [x0,y0,x1,y1] = a.rect.map(v=>v*scale);
      const b = document.createElement('div');
      b.className = 'abox'; b.id = 'abox-'+a.id;
      b.style.cssText = `left:${x0}px;top:${y0}px;width:${x1-x0}px;height:${y1-y0}px`;
      if(a.label) b.innerHTML = `<span class="alab">${esc(a.label)}</span>`;
      overlay.appendChild(b);
    }
  }
  await render(1);
  $('#pv-prev').onclick = ()=>render(pageNo-1);
  $('#pv-next').onclick = ()=>render(pageNo+1);
  window.gotoAnno = async function(id){
    const a = (annotations||[]).find(x=>x.id===id); if(!a) return;
    await render(a.page);
    const b = document.getElementById('abox-'+id);
    if(b){ b.classList.add('flash'); b.scrollIntoView({block:'center', behavior:'smooth'});
      setTimeout(()=>b.classList.remove('flash'), 2600); }
    $('#pv-note').textContent = a.label||''; setTimeout(()=>$('#pv-note').textContent='', 4000);
  };
  document.querySelectorAll('a.annolink').forEach(el=>{
    el.addEventListener('click', e=>{ e.preventDefault(); gotoAnno(el.dataset.anno); });
  });
}
