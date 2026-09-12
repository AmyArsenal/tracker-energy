/* ISO stakeholder month calendar */
const $ = s => document.querySelector(s);
const esc = s => String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let DATA = null;
const now = new Date();
const state = {iso:'ALL',topic:'ALL',month:new Date(now.getFullYear(),now.getMonth(),1),day:null};
const TOPIC_ORDER = ['large load / data centers','interconnection','planning / transmission','capacity / resource adequacy','markets','reliability / operations','governance','general'];
function dayKey(e){return (e.start||'').slice(0,10)}
function fmtClock(raw,e){
  const tail=(raw||'').replace(/^\d{4}-\d{2}-\d{2}T?/,'').replace(/([+-]\d{2}:\d{2}|Z)$/,'');
  if(!tail)return '';
  if(/\d{1,2}:\d{2}\s*(AM|PM)/i.test(tail))return tail.toUpperCase()+(e.tz==='US/Central'?' CT':e.tz==='US/Eastern'?' ET':e.iso==='CAISO'?' PT':'');
  const m=tail.match(/^(\d{1,2}):(\d{2})/); if(!m)return tail;
  let h=+m[1]; const ap=h>=12?'PM':'AM'; h=h%12||12;
  return `${h}:${m[2]} ${ap}`+(e.tz==='US/Central'?' CT':e.tz==='US/Eastern'?' ET':e.iso==='CAISO'?' PT':'');
}
const longDay=d=>new Date(d+'T12:00:00').toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'});
const monthLabel=d=>d.toLocaleDateString('en-US',{month:'long',year:'numeric'});
function visible(){return DATA.events.filter(e=>(state.iso==='ALL'||e.iso===state.iso)&&(state.topic==='ALL'||e.topics.includes(state.topic)))}
function allTopics(){const x=new Set();DATA.events.forEach(e=>(e.topics||[]).forEach(t=>x.add(t)));return TOPIC_ORDER.filter(t=>x.has(t))}
function renderFilters(){
  const isos=['ALL',...DATA.coverage.live];
  $('#isoFilters').innerHTML='<span class="lbl">ISO</span>'+isos.map(i=>`<button class="fbtn ${state.iso===i?'on':''}" data-iso="${i}">${i==='ALL'?'All':i}</button>`).join('');
  $('#topicFilters').innerHTML='<span class="lbl">Topic</span>'+['ALL',...allTopics()].map(t=>`<button class="fbtn ${state.topic===t?'on':''}" data-topic="${esc(t)}">${t==='ALL'?'All topics':esc(t)}</button>`).join('');
  document.querySelectorAll('[data-iso]').forEach(b=>b.onclick=()=>{state.iso=b.dataset.iso;state.day=null;renderFilters();renderCalendar()});
  document.querySelectorAll('[data-topic]').forEach(b=>b.onclick=()=>{state.topic=b.dataset.topic;state.day=null;renderFilters();renderCalendar()});
}
function renderCalendar(){
  const evs=visible(), y=state.month.getFullYear(), m=state.month.getMonth();
  $('#monthLabel').textContent=monthLabel(state.month);
  const byDay={}; evs.forEach(e=>{const k=dayKey(e);if(k)(byDay[k]=byDay[k]||[]).push(e)});
  const first=new Date(y,m,1), lead=first.getDay(), days=new Date(y,m+1,0).getDate();
  const prevDays=new Date(y,m,0).getDate(), cells=[];
  for(let i=0;i<42;i++){
    let d,other=false;
    if(i<lead){d=new Date(y,m-1,prevDays-lead+i+1);other=true}
    else if(i>=lead+days){d=new Date(y,m+1,i-lead-days+1);other=true}
    else d=new Date(y,m,i-lead+1);
    const k=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
    const list=byDay[k]||[], dots=list.slice(0,4).map(e=>`<i class="dot ${e.iso}" title="${esc(e.iso)}"></i>`).join('');
    cells.push(`<button class="calday${other?' other':''}${state.day===k?' selected':''}${k===new Date().toISOString().slice(0,10)?' today':''}" data-day="${k}" aria-label="${longDay(k)}, ${list.length} meeting${list.length===1?'':'s'}"><span class="dn">${d.getDate()}</span>${list.length?`<span class="dots">${dots}${list.length>4?`<b>+${list.length-4}</b>`:''}</span><span class="daycount">${list.length}</span>`:''}</button>`);
  }
  $('#monthGrid').innerHTML=cells.join('');
  document.querySelectorAll('[data-day]').forEach(b=>b.onclick=()=>{
    const d=new Date(b.dataset.day+'T12:00:00');
    if(d.getMonth()!==state.month.getMonth()){state.month=new Date(d.getFullYear(),d.getMonth(),1)}
    state.day=state.day===b.dataset.day?null:b.dataset.day;renderCalendar();
  });
  renderAgenda(evs);
}
function renderAgenda(evs){
  const a=`${state.month.getFullYear()}-${String(state.month.getMonth()+1).padStart(2,'0')}`;
  let list=evs.filter(e=>dayKey(e).startsWith(a));
  if(state.day) list=list.filter(e=>dayKey(e)===state.day);
  list.sort((x,y)=>(x.start||'').localeCompare(y.start||''));
  $('#agendaTitle').innerHTML=state.day?`${longDay(state.day)} <small>${list.length} meeting${list.length===1?'':'s'} · <button id="clearDay">show whole month</button></small>`:`${monthLabel(state.month)} agenda <small>${list.length} meeting${list.length===1?'':'s'}</small>`;
  if(state.day)$('#clearDay').onclick=()=>{state.day=null;renderCalendar()};
  if(!list.length){$('#agenda').innerHTML='<div class="empty">No meetings match this date and these filters.</div>';return}
  const groups={};list.forEach(e=>(groups[dayKey(e)]=groups[dayKey(e)]||[]).push(e));
  $('#agenda').innerHTML=Object.keys(groups).sort().map(d=>`<h3 class="agday">${longDay(d)}</h3>`+groups[d].map(e=>`<article class="mtg"><span class="isob ${e.iso}">${e.iso}</span><div class="tm">${esc(fmtClock(e.start,e))}</div><div class="bd"><h3><a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.name)}</a></h3><div class="meta">${[e.group,e.location].filter(Boolean).map(esc).join(' · ')}</div><div class="tags">${(e.topics||[]).map(t=>`<span class="tg ${t==='large load / data centers'||t==='interconnection'?'hl':''}">${esc(t)}</span>`).join('')}</div></div></article>`).join('')).join('');
}
function renderHeader(){
  const n=DATA.events.length, today=new Date().toISOString().slice(0,10), end=new Date(Date.now()+7*864e5).toISOString().slice(0,10);
  const next7=DATA.events.filter(e=>dayKey(e)>=today&&dayKey(e)<=end).length;
  const ll=DATA.events.filter(e=>(e.topics||[]).includes('large load / data centers')).length;
  const ic=DATA.events.filter(e=>(e.topics||[]).includes('interconnection')).length;
  $('#stats').innerHTML=`<div class="st"><b>${n}</b><span>meetings tracked</span></div><div class="st"><b>${next7}</b><span>next 7 days</span></div><div class="st"><b>${ll}</b><span>large load / DC</span></div><div class="st"><b>${ic}</b><span>interconnection</span></div>`;
  $('#cov').innerHTML=DATA.coverage.live.map(i=>`<span class="c on">${i} · live</span>`).join('')+DATA.coverage.coming.map(i=>`<span class="c">${i} · coming</span>`).join('');
  $('#fresh').textContent=`${DATA.source} · refreshed ${DATA.refreshed_at.replace('T',' ').replace('Z',' UTC')}`;
}
const TOPIC_MAP={'large-load':'large load / data centers','interconnection':'interconnection','transmission':'planning / transmission','capacity':'capacity / resource adequacy','markets':'markets','reliability':'reliability / operations','governance':'governance','general':'general'};
function pjmMeetings(pjm){
  const by={}; (pjm.documents||[]).forEach(d=>{if(!d.date)return;const k=d.committee+'|'+d.date;(by[k]=by[k]||[]).push(d)});
  return Object.values(by).map(ds=>{ds.sort((a,b)=>(a.label==='agenda'?-1:b.label==='agenda'?1:0));const x=ds[0],topics=[...new Set(ds.flatMap(d=>(d.topics||[]).map(t=>TOPIC_MAP[t]).filter(Boolean)))];return{iso:'PJM',name:x.committee_name,start:x.date,tz:'US/Eastern',url:x.url,group:x.committee_name,topics:topics.length?topics:['general']}});
}
$('#prevMonth').onclick=()=>{state.month=new Date(state.month.getFullYear(),state.month.getMonth()-1,1);state.day=null;renderCalendar()};
$('#nextMonth').onclick=()=>{state.month=new Date(state.month.getFullYear(),state.month.getMonth()+1,1);state.day=null;renderCalendar()};
Promise.all([fetch('data/iso.json').then(r=>r.json()),fetch('data/pjm.json').then(r=>r.json()).catch(()=>null),fetch('data/miso.json').then(r=>r.json()).catch(()=>null)]).then(([d,pjm,miso])=>{
 DATA=d;if(pjm?.documents){DATA.events=DATA.events.concat(pjmMeetings(pjm));if(!DATA.coverage.live.includes('PJM'))DATA.coverage.live.push('PJM');DATA.coverage.coming=DATA.coverage.coming.filter(i=>i!=='PJM')}
 if(miso?.events){DATA.events=DATA.events.concat(miso.events);if(!DATA.coverage.live.includes('MISO'))DATA.coverage.live.push('MISO');DATA.coverage.coming=DATA.coverage.coming.filter(i=>i!=='MISO');DATA.source+=' + MISO official calendar API'}
 renderHeader();renderFilters();renderCalendar();
}).catch(()=>{$('#agenda').innerHTML='<div class="empty">Meeting data failed to load.</div>'});
