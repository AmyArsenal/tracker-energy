/* tracker.energy - battery fleet dashboard + dotted map */
const $ = s => document.querySelector(s);
const GW = mw => (mw/1000).toLocaleString(undefined,{maximumFractionDigits:1});
const N0 = n => n==null?'—':Number(n).toLocaleString();
const esc = s => String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function load(p){ const r = await fetch(p,{cache:'no-store'}); if(!r.ok) throw new Error(p+' '+r.status); return r.json(); }

/* ---------- dotted map ---------- */
function renderMap(m){
  const cv = $('#map'), ctx = cv.getContext('2d');
  const DPR = Math.min(window.devicePixelRatio||1, 2);
  cv.width = m.w*DPR; cv.height = m.h*DPR; ctx.scale(DPR,DPR);
  ctx.fillStyle = '#deded9';
  for(const [x,y] of m.dots){ ctx.fillRect(x-0.9, y-0.9, 1.8, 1.8); }
  const draw = (pts, color, glow) => {
    for(const p of pts){
      const r = Math.max(1.6, Math.min(6, 1.2 + Math.sqrt(p[2])/7));
      ctx.beginPath(); ctx.arc(p[0], p[1], r, 0, 7);
      ctx.fillStyle = color; ctx.globalAlpha = .92; ctx.fill();
      if(glow && p[2] >= 200){
        ctx.beginPath(); ctx.arc(p[0], p[1], r+3.5, 0, 7);
        ctx.fillStyle = color; ctx.globalAlpha = .16; ctx.fill();
      }
    }
    ctx.globalAlpha = 1;
  };
  draw(m.plants.filter(p=>p[5]==='pipeline'), '#a8a8a2', false);
  draw(m.plants.filter(p=>p[5]==='operating'), '#356ff2', true);
  // hover tooltip
  const tip = $('#maptip');
  cv.addEventListener('mousemove', e=>{
    const box = cv.getBoundingClientRect();
    const mx = (e.clientX-box.left) * (m.w/box.width), my = (e.clientY-box.top) * (m.h/box.height);
    let best=null, bd=14*14;
    for(const p of m.plants){
      const dx=p[0]-mx, dy=p[1]-my, d=dx*dx+dy*dy;
      if(d<bd){ bd=d; best=p; }
    }
    if(best){
      tip.innerHTML = `<b>${esc(best[3])}</b><br><span class="mm">${N0(best[2])} MW</span> · ${esc(best[4])} · ${best[5]==='operating'?'Operating':'Planned'}`;
      tip.style.left = Math.min(e.clientX-box.left+14, box.width-190)+'px';
      tip.style.top  = (e.clientY-box.top-10)+'px';
      tip.style.opacity = 1;
    } else tip.style.opacity = 0;
  });
  cv.addEventListener('mouseleave', ()=> tip.style.opacity = 0);
}

/* ---------- fleet dashboard ---------- */
let DATA=null, rows=[], sort={k:'mw',dir:-1}, shown=100;
function kpi(cls,v,unit,l,d){return `<div class="kpi ${cls}"><div class="v">${v}<small>${unit||''}</small></div><div class="l">${l}</div><div class="d">${d||''}</div></div>`;}
function renderKpis(t){
  $('#kpis').innerHTML =
    kpi('g',N0(t.operating_mwh),' MWh','Energy storage live',`${GW(t.operating_mw)} GW operating capacity`) +
    kpi('',N0(t.operating_units),'','Generating units',`across ${N0(t.operating_plants)} plants`) +
    kpi('b',N0(t.pipeline_plants),'','Projects in the pipeline',`${GW(t.pipeline_mw)} GW planned`) +
    kpi('',N0(t.states),'','States + DC with batteries','incl. Puerto Rico');
  const hs=$('#hstats'); if(hs) hs.innerHTML =
    `<div class="hstat"><div class="v">${GW(t.operating_mw)}<small> GW</small></div><div class="l">Operating</div></div>
     <div class="hstat"><div class="v">${N0(t.operating_plants)}</div><div class="l">Plants live</div></div>
     <div class="hstat"><div class="v">${GW(t.pipeline_mw)}<small> GW</small></div><div class="l">In the pipeline</div></div>`;
}
function bars(el, items, max){
  el.innerHTML = items.map(it=>{
    const w=v=>Math.max(0.4,(v/max)*100);
    return `<div class="barrow"><div class="nm" title="${esc(it.label)}">${esc(it.label)}</div>
      <div class="track"><div class="fill" style="width:${w(it.op)}%"></div><div class="fill pipe" style="left:${w(it.op)}%;width:${w(it.pipe)}%"></div></div>
      <div class="val">${GW(it.op)} + ${GW(it.pipe)} GW</div></div>`;
  }).join('');
}
function renderStateChart(d){
  const items = d.by_state.slice(0,12).map(s=>({label:s.state, op:s.mw, pipe:s.pipeline_mw}));
  bars($('#ch-state'), items, Math.max(...items.map(i=>i.op+i.pipe)));
}
function renderBAChart(d){
  const items = d.by_ba.slice(0,10).map(s=>({label:s.ba, op:s.mw, pipe:s.pipeline_mw}));
  bars($('#ch-ba'), items, Math.max(...items.map(i=>i.op+i.pipe)));
}
function renderYearChart(d){
  const ys = d.by_year.filter(y=>y.year>=2015);
  const max = Math.max(...ys.map(y=>y.mw_added));
  $('#ch-year').innerHTML =
    `<div class="cols">`+ ys.map(y=>
      `<div class="col" title="${y.year}: ${N0(y.mw_added)} MW added, ${GW(y.cumulative_mw)} GW cumulative">
        <div class="bar" style="height:${Math.max(1.5,(y.mw_added/max)*100)}%"></div></div>`).join('') +
    `</div><div class="colx">`+ ys.map(y=>`<div>${String(y.year).slice(2)}</div>`).join('') +
    `</div><div class="tip">hover bars for detail · cumulative fleet now ${GW(d.totals.operating_mw)} GW</div>`;
}
function statusPill(p){
  const s=(p.status||'').toLowerCase();
  if(p.kind==='operating' && s.startsWith('operating')) return `<span class="pill op">Operating</span>`;
  if(s.includes('under construction')||s.startsWith('construction complete')) return `<span class="pill con">Construction</span>`;
  if(s.includes('approv')||s.includes('planned')||s.includes('permits')) return `<span class="pill plan">Planned</span>`;
  return `<span class="pill oth">${esc((p.status||'other').split('.')[0].slice(0,28))}</span>`;
}
function applyFilters(){
  const q=$('#f-q').value.trim().toLowerCase(), st=$('#f-state').value,
        ba=$('#f-ba').value, kind=$('#f-kind').value, min=+$('#f-min').value;
  rows = DATA.projects.filter(p=>
    (!q || (p.name+' '+(p.developer||'')).toLowerCase().includes(q)) &&
    (!st || p.state===st) && (!ba || p.ba===ba) && (!kind || p.kind===kind) && p.mw>=min);
  rows.sort((a,b)=>{const k=sort.k; let x=a[k],y=b[k];
    if(x==null)return 1; if(y==null)return -1;
    return (typeof x==='string'? x.localeCompare(y): x-y)*sort.dir;});
  shown=100; renderTable();
}
function renderTable(){
  $('#tbody').innerHTML = rows.slice(0,shown).map(p=>`<tr>
    <td><div class="proj">${esc(p.name)}</div><div class="dev">${esc(p.developer||'')}${p.county?' · '+esc(p.county):''}</div></td>
    <td>${esc(p.state||'')}</td><td>${esc(p.ba||'')}</td>
    <td class="num">${N0(p.mw)}</td><td class="num">${p.mwh?N0(p.mwh):'—'}</td>
    <td>${statusPill(p)}</td><td class="num">${p.year||''}</td></tr>`).join('');
  $('#f-count').textContent = `${N0(rows.length)} projects · ${GW(rows.reduce((s,p)=>s+p.mw,0))} GW`;
  $('#more').style.display = rows.length>shown ? 'block':'none';
}
function initTable(d){
  $('#f-state').innerHTML += [...new Set(d.projects.map(p=>p.state).filter(Boolean))].sort().map(s=>`<option>${s}</option>`).join('');
  $('#f-ba').innerHTML += [...new Set(d.projects.map(p=>p.ba).filter(Boolean))].sort().map(s=>`<option>${s}</option>`).join('');
  ['f-q','f-state','f-ba','f-kind','f-min'].forEach(id=>$('#'+id).addEventListener('input',applyFilters));
  $('#more').addEventListener('click',()=>{shown+=150;renderTable();});
  document.querySelectorAll('#tbl th').forEach(th=>th.addEventListener('click',()=>{
    const k=th.dataset.k; if(sort.k===k) sort.dir*=-1; else sort={k,dir:k==='name'?1:-1};
    applyFilters();
  }));
}

/* ---------- boot ---------- */
(async()=>{
  try{
    const [meta,b,m] = await Promise.all([load('data/meta.json'),load('data/battery.json'),load('data/map.json')]);
    DATA=b;
    $('#stamp').innerHTML = `SOURCE EIA-860M ${esc(meta.eia_file_month).toUpperCase()} · UPDATED ${esc(meta.generated_at_utc).toUpperCase()}`;
    renderMap(m);
    renderKpis(b.totals); renderStateChart(b); renderBAChart(b); renderYearChart(b);
    initTable(b); applyFilters();
  }catch(e){
    document.querySelector('.hero .wrap').insertAdjacentHTML('afterbegin',
      `<div class="err">Data failed to load: ${esc(e.message)} - the nightly refresh may still be running.</div>`);
  }
})();
