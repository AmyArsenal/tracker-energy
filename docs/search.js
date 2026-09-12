/* Discovery: full-text + combinable facets over the static search shard. */
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let SHARD=null, ARTICLES=new Set();
const STARS={
  get(){ try{return new Set(JSON.parse(localStorage.getItem('te_stars')||'[]'))}catch(e){return new Set()} },
  has(id){ return this.get().has(id); },
  toggle(id){ const s=this.get(); s.has(id)?s.delete(id):s.add(id);
    localStorage.setItem('te_stars',JSON.stringify([...s])); return s.has(id); },
  size(){ return this.get().size; }
};
const state={q:'',src:new Set(),types:new Set(),topics:new Set(),conf:false};

function loadState(){
  const p=new URLSearchParams(location.search);
  state.q=p.get('q')||'';
  (p.get('src')||'').split(',').filter(Boolean).forEach(v=>state.src.add(v));
  (p.get('type')||'').split(',').filter(Boolean).forEach(v=>state.types.add(v));
  (p.get('topic')||'').split(',').filter(Boolean).forEach(v=>state.topics.add(v));
  state.starred = p.get('starred')==='1';
}
function saveState(){
  const p=new URLSearchParams();
  if(state.q)p.set('q',state.q);
  if(state.src.size)p.set('src',[...state.src].join(','));
  if(state.types.size)p.set('type',[...state.types].join(','));
  if(state.topics.size)p.set('topic',[...state.topics].join(','));
  if(state.starred)p.set('starred','1');
  history.replaceState(null,'',p.toString()?('?'+p):'/search.html');
}
function match(d){
  if(state.src.size && !state.src.has(d.src)) return false;
  if(state.types.size && !d.types.some(t=>state.types.has(t))) return false;
  if(state.topics.size && !d.topics.some(t=>state.topics.has(t))) return false;
  if(state.starred && !STARS.has(d.id)) return false;
  if(state.q){
    const toks=state.q.toLowerCase().split(/\s+/).filter(Boolean);
    if(!toks.every(t=>d.text.includes(t)||(d.docket||'').toLowerCase().includes(t))) return false;
  }
  return true;
}
function facetBlock(id,title,values,counts,vocab,active){
  return `<div class="facet"><h5>${title}</h5>${values.map(v=>{
    const on=active.has(v);
    return `<label><input type="checkbox" data-f="${id}" value="${esc(v)}" ${on?'checked':''}>${esc(vocab[v]||v)}<span class="n">${counts[v]||0}</span></label>`;
  }).join('')}</div>`;
}
function render(){
  saveState();
  const all=SHARD.docs;
  const counts={src:{},type:{},topic:{}};
  for(const d of all){
    counts.src[d.src]=(counts.src[d.src]||0)+1;
    d.types.forEach(t=>counts.type[t]=(counts.type[t]||0)+1);
    d.topics.forEach(t=>counts.topic[t]=(counts.topic[t]||0)+1);
  }
  const srcs=[...new Set(all.map(d=>d.src))];
  $('#facets').innerHTML =
    `<div class="facet"><h5>Following</h5><label><input type="checkbox" data-f="starred" ${state.starred?'checked':''}>Starred items<span class="n">${STARS.size()}</span></label></div>` +
    facetBlock('src','Source',srcs,counts.src,Object.fromEntries(all.map(d=>[d.src,d.src_name])),state.src) +
    facetBlock('type','Document type',Object.keys(SHARD.facets.types).filter(t=>counts.type[t]),counts.type,SHARD.facets.types,state.types) +
    facetBlock('topic','Topic',Object.keys(SHARD.facets.topics).filter(t=>counts.topic[t]),counts.topic,SHARD.facets.topics,state.topics) +
'';
  $('#facets').querySelectorAll('input').forEach(inp=>inp.onchange=()=>{
    const f=inp.dataset.f;
    if(f==='starred'){state.starred=inp.checked;}
    else if(f==='conf'){state.conf=inp.checked;}
    else{const set=f==='src'?state.src:f==='type'?state.types:state.topics;
         inp.checked?set.add(inp.value):set.delete(inp.value);}
    render();
  });
  const today=new Date().toISOString().slice(0,10);
  const hits=all.filter(match).sort((a,b)=>{
    const ak=(a.date||'')>today?0:1, bk=(b.date||'')>today?0:1;
    if(ak!==bk) return ak-bk;  // documents filed up to today first, future-dated meetings after
    return (b.date||'').localeCompare(a.date||'');
  });
  $('#rcount').textContent=`${hits.length.toLocaleString()} result${hits.length===1?'':'s'}`;
  const bits=[];
  if(state.q)bits.push(`matching "${state.q}"`);
  if(state.src.size)bits.push(`from ${[...state.src].join(', ')}`);
  $('#rq').textContent=bits.join(' ');
  const accOf=id=>id.startsWith('ferc:')?id.slice(5):null;
  const starBtn=d=>`<a href="#" class="star" data-star="${esc(d.id)}" title="${STARS.has(d.id)?'Unstar':'Star - keep this in Following'}">${STARS.has(d.id)?'★':'☆'}</a>`;
  $('#results').innerHTML = hits.length ? hits.slice(0,120).map(d=>{
    const acc=accOf(d.id);
    const art=acc&&ARTICLES.has(acc)?`<a href="/article.html?acc=${encodeURIComponent(acc)}">Analysis →</a>`:'';
    return `<div class="res">
      <div class="rline">${starBtn(d)}<span class="date">${esc(d.date||'undated')}</span>
        <span class="chip cls">${esc(d.src)}</span>
        ${d.docket?`<span class="chip">${esc(d.docket.replace(/-000$/,''))}</span>`:''}
        ${d.types.map(t=>`<span class="chip">${esc(SHARD.facets.types[t]||t)}</span>`).join('')}
        ${d.topics.filter(t=>t!=='general').map(t=>`<span class="chip cls">${esc(SHARD.facets.topics[t]||t)}</span>`).join('')}
        ${d.conf==='low'?`<span class="conf-low">REVIEW</span>`:''}</div>
      <h3><a href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.title)}</a></h3>
      ${d.party?`<div class="who">${d.kind==='iso'?'':'Filed by '}<b>${esc(d.party)}</b></div>`:''}
      ${d.caption&&d.caption!==d.title?`<div class="cap">${esc(d.caption)}</div>`:''}
      <div class="links">${art}<a href="${esc(d.url)}" target="_blank" rel="noopener" style="color:var(--ink3)">${d.src==='pjm'?'PJM document ↗':d.kind==='iso'?'Meeting page ↗':'Source docket ↗'}</a>
        ${d.local?`<a href="/${esc(d.local)}" style="color:var(--ink3)">Hosted PDF ↗</a>`:''}</div>
    </div>`;
  }).join('') + (hits.length>120?`<div class="empty">Showing the 120 newest of ${hits.length} - narrow with facets or search terms.</div>`:'')
    : `<div class="empty">${state.starred?'No starred items yet. Star any result to follow it here.':'Nothing matches that combination.<br>Try removing a facet or broadening the search.'}</div>`;
  document.querySelectorAll('[data-star]').forEach(a=>a.onclick=ev=>{
    ev.preventDefault(); STARS.toggle(a.dataset.star); render();
  });
}
(async()=>{
  loadState();
  const [s,f]=await Promise.all([
    fetch('data/search.json',{cache:'no-store'}).then(r=>r.json()),
    fetch('data/ferc.json',{cache:'no-store'}).then(r=>r.json()).catch(()=>null)]);
  SHARD=s; ARTICLES=new Set((f&&f.articles)||[]);
  $('#q').value=state.q;
  $('#stamp').textContent=`${SHARD.count.toLocaleString()} documents · shard built ${SHARD.built_at} · FERC/PUC/ISO nightly, PJM weekly`;
  let t; $('#q').addEventListener('input',e=>{clearTimeout(t);t=setTimeout(()=>{state.q=e.target.value.trim();render();},160);});
  render();
})();
