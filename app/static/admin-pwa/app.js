/* Admin PWA: public shell, in-memory private data, server-owned decisions. */
(() => {
'use strict';
const icons={
home:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M9 21v-8h6v8"/>',
chart:'<rect x="3" y="11" width="4" height="10" rx="1"/><rect x="10" y="6" width="4" height="15" rx="1"/><rect x="17" y="3" width="4" height="18" rx="1"/>',
users:'<circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M17 5a3 3 0 0 1 0 6m4 10v-3a6 6 0 0 0-4-5.65"/>',
wallet:'<rect x="3" y="6" width="18" height="15" rx="2"/><path d="M3 10h18M7 3h12"/><circle cx="17" cy="15" r="1"/>',
book:'<path d="M4 4h7a3 3 0 0 1 3 3v14a3 3 0 0 0-3-3H4zM20 4h-3a3 3 0 0 0-3 3v14a3 3 0 0 1 3-3h3z"/>',
mega:'<path d="M3 10v4h4l11 5V5L7 10zM7 14l2 6M21 9v6"/>',
settings:'<circle cx="12" cy="12" r="3"/><path d="M9 3h6l.6 2.3 2 .9 2.1-1.2 3 5.2-1.7 1.7v2.2l1.7 1.7-3 5.2-2.1-1.2-2 .9L15 23H9l-.6-2.3-2-.9-2.1 1.2-3-5.2L3 14.1v-2.2l-1.7-1.7 3-5.2 2.1 1.2 2-.9z"/>',
search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
bell:'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 8-3 9h18c0-1-3-2-3-9M10 21h4"/>',
check:'<path d="m5 12 5 5L20 7"/>',
clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
filter:'<path d="M3 5h18M6 12h12M9 19h6"/>',
plus:'<path d="M12 4v16M4 12h16"/>',
send:'<path d="M22 2 11 13M22 2l-7 20-4-9-9-4z"/>',
spark:'<path d="m3 16 5-5 4 4 9-10M15 5h6v6"/>',
target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
folder:'<path d="M3 5h6l2 3h10v12H3z"/>',
credit:'<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M2 10h20"/>',
shield:'<path d="M12 2 3 6v6c0 6 4 9 9 10 5-1 9-4 9-10V6z"/><path d="m8 12 3 3 5-6"/>',
globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 0 0 18M12 3a15 15 0 0 1 0 18"/>',
menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
more:'<path d="M12 5h.01M12 12h.01M12 19h.01"/>',
gift:'<rect x="3" y="9" width="18" height="12" rx="2"/><path d="M12 9v12M3 13h18M12 9c-10 0-8-8-4-6 2 1 4 6 4 6Zm0 0c10 0 8-8 4-6-2 1-4 6-4 6Z"/>',
device:'<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M11 18h2"/>',
sliders:'<path d="M4 5h16M4 12h16M4 19h16"/><circle cx="9" cy="5" r="2" fill="white"/><circle cx="16" cy="12" r="2" fill="white"/><circle cx="11" cy="19" r="2" fill="white"/>',
link:'<path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-2 2M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l2-2"/>'
};
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${icons[name] || icons.folder}</svg>`;
let locale = 'uz';
try { const saved = localStorage.getItem('hsk-admin-locale'); if (['uz','ru','tj'].includes(saved)) locale = saved; } catch (_) {}
const t = key => window.HSKAI_ADMIN_I18N?.[locale]?.[key] ?? '—';
const btn = (label, action, variant='', disabled=false) => `<button class="btn ${variant}" data-action="${action}" ${disabled?'disabled':''}>${esc(t(label))}</button>`;
const state = {actor:null, phase:'loading', route:'home', period:'weekly', platform:'overall', rows:[], stats:null,
  query:'', status:'pending', source:'all', inboxPriority:'all', inboxSearch:'', cursor:null, previous:[], next:null, error:null, approval:null, enrollment:false, enrollmentOptions:null};
let epoch=0, view=0, drawerId=0, confirmation=null, receiptLoaded=false, reviewId=null, signing=null, busy=false;
let publicRegistration=null, installPrompt=null, returnFocus=null, revokeTarget=null, revoking=false, feedbackUserId=null, inboxNextCursor=null, inboxUpdating=false, inboxUnread=null, pushChanging=false, pushReady=null;
let inboxAttachment=null;
let statisticsDownload=null;
class ApiError extends Error { constructor(code,status) { super(code);this.status=status; } }
function clearPrivate(phase) {
  cancelStatisticsDownload();
  epoch++;view++;closeDrawer();inboxUnread=null;pushReady=null;state.inboxSearch='';state.actor=null;state.rows=[];state.stats=null;state.approval=null;state.enrollment=false;state.enrollmentOptions=null;
  state.phase=phase;state.error=null;render();
}
async function api(path, body, {publicAuth=false, method='POST'}={}) {
  const current=epoch, control=new AbortController(), timer=setTimeout(()=>control.abort(),15000);
  try {
    const response=await fetch('/api/admin/v1/'+path,{method, credentials:'same-origin',cache:'no-store',redirect:'error',
      headers:method==='POST'?{'Content-Type':'application/json'}:{},body:method==='POST'?JSON.stringify(body):undefined,signal:control.signal});
    const data=await response.json();
    if (epoch!==current) throw new ApiError('stale',0);
    if (!response.ok || data.ok!==true) {
      if(response.status===401 && !publicAuth) { clearPrivate('signin');state.error='authExpired';render(); }
      throw new ApiError(data.error || 'error',response.status);
    }
    const {ok,...result}=data;return result;
  } catch(error) {
    if (epoch!==current) throw new ApiError('stale',0);
    throw error;
  } finally { clearTimeout(timer); }
}
function languageSelect(id='locale') { return `<select class="locale-select" id="${id}" aria-label="${esc(t('language'))}">${[['uz','O‘zbekcha'],['ru','Русский'],['tj','Тоҷикӣ']].map(([id,name])=>`<option value="${id}" ${locale===id?'selected':''}>${name}</option>`).join('')}</select>`; }
function showNotice(key) { $('notice').textContent=t(key);$('notice').classList.add('show');setTimeout(()=>$('notice').classList.remove('show'),6000); }
function errorKey(error) {
  if(error?.name==='NotAllowedError'||error?.name==='AbortError') return 'passkeyCancelled';
  return error?.status===409?'changed':'error';
}
function auth() {
  let content='';
  if(state.phase==='loading') content=`<h1>${esc(t('loading'))}</h1>`;
  else if(state.phase==='offline') content=`<h1>${esc(t('offline'))}</h1><p>${esc(t('offlineHint'))}</p>${btn('retry','boot','primary')}`;
  else if(state.phase==='error') content=`<h1>${esc(t('error'))}</h1>${btn('retry','boot','primary')}`;
  else if(state.phase==='approval') content=`<h1>${esc(t('approval'))}</h1><p>${esc(t('approvalHint'))}</p><p class="pairing-code">${esc(state.approval?.pairing_code)}</p>${btn('checkApproval','approval','primary',busy)}`;
  else if(state.phase==='enroll') content=`<h1>${esc(t('enroll'))}</h1><p>${esc(t('enrollHint'))}</p>${btn('enroll','enroll','primary',busy)}${state.error?btn('googleStart','google','',busy):''}`;
  else content=`<h1>${esc(t('signInTitle'))}</h1><p>${esc(t('passkeyHint'))}</p>${btn('signIn','signin','primary',busy)}<details><summary>${esc(t('google'))}</summary><p>${esc(t('googleHint'))}</p>${btn('googleStart','google','',busy)}</details>`;
  return `<main class="auth-wrap"><section class="auth-panel">${languageSelect()}<div class="brand-logo"><img src="/admin/assets/icon.png" alt="HSK AI"></div>${state.error?`<p class="alert" role="alert">${esc(t(state.error))}</p>`:''}${content}</section></main>`;
}
const routes=[['home','home'],['stats','chart'],['users','users'],['payments','wallet']];
function render() {
  document.documentElement.lang=locale==='tj'?'tg':locale;document.title=t('appTitle');
  if(!state.actor) { $('root').innerHTML=auth();return; }
  const navigation=routes.map(([route,glyph])=>`<button data-route="${route}" class="${state.route===route?'active':''}" ${state.route===route?'aria-current="page"':''}>${icon(glyph)}${esc(t(route))}</button>`).join('');
  const disabled=['course','marketing','system'].map(route=>`<button disabled title="${esc(t('notReady'))}">${icon(route==='course'?'book':route==='marketing'?'mega':'settings')}${esc(t(route))}</button>`).join('');
  $('root').innerHTML=`<div class="app"><aside class="sidebar"><div class="brand"><div class="brand-logo"><img src="/admin/assets/icon.png" alt=""></div><div><div class="brand-title">HSK AI</div><div class="brand-sub">ADMIN</div></div></div><p class="nav-cap">${esc(t('sections'))}</p><nav class="nav">${navigation}${disabled}</nav><div class="side-foot"><p>${esc(t('account'))} · ${state.actor.user_id}</p>${languageSelect()}${state.actor.mcp_available?btn('mcpConnections','mcpConnections'):''}${state.actor.push_available?btn('pushTitle','pushSettings'):''}${btn('logout','logout')}</div></aside><div class="workspace"><header class="topbar"><div class="topbar-context"><h1 class="page-title">${esc(t(state.route==='home'?'workspace':state.route))}</h1></div><div class="header-tools">${['home','stats'].includes(state.route)?filters():''}<button class="top-icon-btn" data-action="feedback" aria-label="${esc(t('feedback'))}">${icon('bell')}${inboxUnread?.unread_count?`<span class="top-icon-badge" aria-hidden="true">${inboxUnread.capped?'99+':inboxUnread.unread_count}</span>`:''}</button><button class="top-icon-btn mobile-only" data-action="more" aria-label="${esc(t('more'))}" ${busy?'disabled':''}>${icon('more')}</button></div></header><main class="main" id="content">${content()}</main></div></div><nav class="mobile-tabs" aria-label="${esc(t('sections'))}">${navigation}</nav>`;
  $('root').inert=!!$('overlay');
}
function filters() {
  return `<div class="header-dropdown"><button class="header-control period-control" data-action="period" aria-haspopup="true" aria-expanded="false">${icon('clock')}<strong>${esc(t(state.period))}</strong></button><div class="header-menu" id="periodMenu" hidden>${['weekly','monthly','all_time'].map(id=>`<button data-period="${id}">${esc(t(id))}</button>`).join('')}</div></div><div class="header-dropdown"><button class="header-control icon-control" data-action="platform" aria-haspopup="true" aria-expanded="false" aria-label="${esc(t('platform'))}">${icon('filter')}</button><div class="header-menu platform-menu" id="platformMenu" hidden>${[['overall',t('all')],['android','Android'],['telegram','Telegram Mini App'],['macos','macOS'],['windows','Windows'],['iphone_pwa','iPhone PWA']].map(([id,name])=>`<button data-platform="${id}" class="${state.platform===id?'chosen':''}">${esc(name)}</button>`).join('')}</div></div>`;
}
function statePanel(key, hint='', retry=false) { return `<section class="state-panel"><h2>${esc(t(key))}</h2>${hint?`<p>${esc(t(hint))}</p>`:''}${retry?btn('retry','reload','primary'):''}</section>`; }
function metric(label,value,glyph='chart') { return `<div class="metric"><div class="metric-top"><span>${esc(t(label))}</span><span class="metric-icon">${icon(glyph)}</span></div><div class="metric-value">${esc(value ?? '—')}</div></div>`; }
function statsView() {
  const data=state.stats;if(!data) return statePanel('loading');
  const exports=state.route==='stats'?`<div class="data-toolbar statistics-export"><button class="btn" data-export-format="json" ${statisticsDownload?'disabled aria-busy="true"':''}>${esc(t('exportJson'))}</button><button class="btn" data-export-format="csv" ${statisticsDownload?'disabled aria-busy="true"':''}>${esc(t('exportCsv'))}</button></div>`:'';
  if(!data.available) return exports+statePanel('unavailable');
  let cards='', extra='';const m=data.metrics;
  if(data.platform==='overall') {
    cards=metric('usersTotal',m.users_total,'users')+metric('newAccounts',m.new_accounts,'users')+metric(state.period==='all_time'?'active30':'activeAccounts',m.active_accounts)+metric('pending',m.payments_by_status.pending,'wallet');
    extra=`<h2 class="section-title">${esc(t('approvedAmounts'))}</h2><div class="currency-rows">${m.approved_amounts_by_currency.map(row=>`<div class="currency-row">${esc(row.currency)}<strong>${esc(row.amount)}</strong></div>`).join('')||`<p>${esc(t('empty'))}</p>`}</div><p class="source-note">${esc(t('currencyNote'))}</p>`;
    const ai=m.ai_usage,c=m.course_engagement,r=m.registration_conversion;
    extra+=`<div class="stats-details"><section class="stat-detail"><h2>${esc(t('aiSpend'))}</h2>${profileFields([['estimatedCost',ai.estimated_cost_usd+' USD'],['recordedRequests',ai.recorded_requests],['tokens',ai.tokens]])}<p class="source-note">${esc(t('aiCostNote'))}</p></section><section class="stat-detail"><h2>${esc(t('courseEngagement'))}</h2>${profileFields([['engagedAccounts',c.engaged_accounts],['startedAccounts',c.started_accounts],['completedAccounts',c.completed_accounts]])}<p class="source-note">${esc(t('courseMetricNote'))}${c.unmatched_events?' '+esc(t('unmatchedEvents'))+': '+c.unmatched_events:''}</p></section><section class="stat-detail"><h2>${esc(t('registrationConversion'))}</h2>${profileFields([['conversion',r.percent===null?'—':r.percent+'%'],['registeredCohort',r.registered_accounts],['convertedAccounts',r.converted_accounts]])}<p class="source-note">${esc(t('conversionNote'))}</p></section></div>`;
  } else if(data.platform==='android') cards=metric('installedDevices',m.registry.installed_devices,'device')+metric('installedUsers',m.registry.installed_users,'users')+metric('active7',m.active.wau)+metric('active30',m.active.mau);
  else cards=metric('active30',m.active_users_30d)+metric('firstOpen',m.verified_first_open_30d,'device');
  return `${exports}<div class="grid metrics">${cards}</div>${extra}<p class="source-note">${esc(t('overlap'))}${data.scope?.period_filter_applied===false?' '+esc(t('rolling30')):''}</p><p class="source-note">${esc(t('updated'))}: ${esc(date(data.generated_at))}</p>`;
}
function cancelStatisticsDownload(){
  const download=statisticsDownload;statisticsDownload=null;
  if(!download)return;
  download.control.abort();clearTimeout(download.timer);
  if(download.url)URL.revokeObjectURL(download.url);
  document.querySelectorAll('[data-export-format]').forEach(button=>{button.disabled=false;button.removeAttribute('aria-busy');});
}
async function exportStatistics(format){
  if(!state.actor||state.phase!=='ready'||state.route!=='stats'||!['json','csv'].includes(format)||statisticsDownload)return;
  const current=view,at=epoch,language=locale,control=new AbortController();
  const download={control,url:null,timer:null};statisticsDownload=download;
  const active=()=>statisticsDownload===download&&current===view&&at===epoch&&language===locale&&!!state.actor;
  const buttons=[...document.querySelectorAll('[data-export-format]')];
  buttons.forEach(button=>{button.disabled=true;button.setAttribute('aria-busy','true');});
  const timer=setTimeout(()=>control.abort(),15000),platform=state.platform,period=state.period;
  try{
    const response=await fetch('/api/admin/v1/statistics/export',{method:'POST',credentials:'same-origin',cache:'no-store',redirect:'error',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({platform,period,format}),signal:control.signal});
    if(!active())return;
    if(response.status===401){clearPrivate('signin');state.error='authExpired';render();return;}
    const mime=format==='json'?'application/json':'text/csv';
    if(!response.ok||response.headers.get('content-type')?.split(';')[0]!==mime||!response.body)throw Error('export_failed');
    const reader=response.body.getReader(),chunks=[];let size=0;
    try{
      while(true){
        const {done,value}=await reader.read();if(done)break;
        size+=value.byteLength;
        if(size>128*1024){await reader.cancel();throw Error('export_too_large');}
        chunks.push(value);
      }
    }finally{reader.releaseLock();}
    if(!active())return;
    if(!size)throw Error('empty_export');
    download.url=URL.createObjectURL(new Blob(chunks,{type:mime}));
    const link=document.createElement('a');link.href=download.url;link.download=`hskai-statistics-${platform}-${period}.${format}`;
    link.hidden=true;document.body.append(link);link.click();link.remove();
    // Give the browser time to consume the explicit download, then release it.
    download.timer=setTimeout(()=>{if(statisticsDownload===download)cancelStatisticsDownload();},1000);
  }catch(error){if(active())showNotice('error');}
  finally{
    clearTimeout(timer);
    if(statisticsDownload===download&&!download.timer)cancelStatisticsDownload();
  }
}
function date(value) { if(!value) return '—';const d=new Date(value);return Number.isNaN(d.valueOf())?'—':d.toLocaleString(locale==='tj'?'tg':locale,{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}); }
function pager() { return `<div class="pager">${btn('previous','previous','',state.previous.length===0)}${btn('next','next','',!state.next)}</div>`; }
function usersView() {
  const rows=state.rows.map(row=>`<tr><td><button class="profile-link" data-user-detail="${row.user_id}">${esc(row.name||'—')}</button><small>${esc(row.username||'')} · #${row.user_id}</small></td><td>${esc(row.level||'—')}</td><td>${esc(row.language||'—')}</td><td>${esc(t(row.access_state))}</td><td>${esc(date(row.last_active_at))}</td></tr>`).join('');
  const cards=state.rows.map(row=>`<article class="user-card"><div class="user-card-top"><div class="user-card-head"><strong>${esc(row.name||'—')}</strong><small>#${row.user_id} · ${esc(row.username||'')}</small></div><span class="pill">${esc(t(row.access_state))}</span></div><div class="user-card-details"><div class="u-mini-field"><small>${esc(t('level'))}</small><b>${esc(row.level||'—')}</b></div><div class="u-mini-field"><small>${esc(t('lastActive'))}</small><b>${esc(date(row.last_active_at))}</b></div></div><button class="btn small" data-user-detail="${row.user_id}">${esc(t('openProfile'))}</button></article>`).join('');
  return `<form id="searchForm" class="data-toolbar"><label class="screen-reader" for="userQuery">${esc(t('search'))}</label><input id="userQuery" class="search-input" maxlength="80" value="${esc(state.query)}" placeholder="${esc(t('search'))}"><button class="btn primary">${esc(t('find'))}</button></form>${state.rows.length?`<div class="table-wrap user-table-wrap"><table class="data-table user-table"><thead><tr>${['name','level','language','status','lastActive'].map(key=>`<th>${esc(t(key))}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div><div class="user-cards">${cards}</div>`:statePanel('empty')}${pager()}`;
}
function paymentsView() {
  return `<div class="data-toolbar">${['pending','approved','rejected'].map(status=>`<button class="btn ${state.status===status?'primary':''}" data-status="${status}">${esc(t(status))}</button>`).join('')}</div>${state.rows.length?`<div class="table-wrap"><table class="data-table"><thead><tr>${['name','plan','amount','status','review'].map(key=>`<th>${esc(t(key))}</th>`).join('')}</tr></thead><tbody>${state.rows.map(row=>`<tr><td>${esc(row.name||'—')}<small>${esc(t('account'))}: ${esc(row.user_id??'—')} · #${row.payment_id}</small></td><td>${esc(t(row.plan_type))}<small>${esc(row.payment_method)}</small></td><td><strong>${esc(row.amount)} ${esc(row.currency)}</strong></td><td>${esc(t(row.status))}</td><td>${row.status==='pending'?`<button class="btn small" data-review="${row.payment_id}">${esc(t('review'))}</button>`:'—'}</td></tr>`).join('')}</tbody></table></div>`:statePanel('empty')}${pager()}`;
}
function content() { if(state.error) return statePanel(state.error,'',true);if(state.phase==='loading') return statePanel('loading');return ['home','stats'].includes(state.route)?statsView():state.route==='users'?usersView():paymentsView(); }
async function load() {
  cancelStatisticsDownload();
  if(!state.actor) return;const current=++view, authEpoch=epoch;state.phase='loading';state.error=null;render();
  try {
    const data=await api(['home','stats'].includes(state.route)?'statistics':state.route==='users'?'users/search':'payments/list',
      ['home','stats'].includes(state.route)?{period:state.period,platform:state.platform}:state.route==='users'?{query:state.query,before_id:state.cursor,limit:30}:{status:state.status,before_id:state.cursor,limit:30});
    if(current!==view||authEpoch!==epoch) return;
    if(['home','stats'].includes(state.route)) state.stats=data; else {state.rows=data.items;state.next=data.next_before_id;}
    state.phase='ready';render();
  } catch(error) {if(current!==view||authEpoch!==epoch||!state.actor) return;state.phase='ready';state.error='error';render();}
}
async function boot() {
  if(!navigator.onLine){clearPrivate('offline');return;}
  clearPrivate('loading');const current=epoch;
  try {state.actor=await api('me',null,{method:'GET',publicAuth:true});if(current!==epoch)return;state.phase='ready';await load();await refreshInboxUnread();
    if(current===epoch&&state.actor&&location.pathname==='/admin/'&&location.search==='?inbox=1'){
      history.replaceState(null,'','/admin/');
      await inbox(); // Only after current passkey Admin PWA login is verified.
    }}
  catch(error) {
    if(current!==epoch)return;
    if(error.status!==401){state.phase='error';render();return;}
    try {await checkApproval();} catch(_) {state.phase='signin';render();}
  }
}
function decode(value) { const normalized=value.replace(/-/g,'+').replace(/_/g,'/');return Uint8Array.from(atob(normalized+'='.repeat((4-normalized.length%4)%4)),ch=>ch.charCodeAt(0)); }
function encode(buffer) { if(buffer==null)return null;let s='';for(const b of new Uint8Array(buffer))s+=String.fromCharCode(b);return btoa(s).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''); }
function publicKey(options,registration=false) {
  const copy=structuredClone(options);copy.challenge=decode(copy.challenge);
  for(const field of ['allowCredentials','excludeCredentials']) if(copy[field]) copy[field]=copy[field].map(row=>({...row,id:decode(row.id)}));
  if(registration) copy.user.id=decode(copy.user.id);return copy;
}
function serialize(credential) {
  if(!credential) throw new Error('missing_credential');const response={clientDataJSON:encode(credential.response.clientDataJSON)};
  for(const name of ['authenticatorData','signature','userHandle','attestationObject']) if(name in credential.response)response[name]=encode(credential.response[name]);
  if(credential.response.getTransports)response.transports=credential.response.getTransports();
  return {id:credential.id,rawId:encode(credential.rawId),type:credential.type,response,clientExtensionResults:credential.getClientExtensionResults()};
}
function supportsPasskey() { return !!(window.PublicKeyCredential&&navigator.credentials&&window.isSecureContext); }
async function login() {
  if(!supportsPasskey()){state.error='passkeyUnsupported';render();return;}
  const options=await api('auth/passkey/login/options',{}, {publicAuth:true});
  const credential=await navigator.credentials.get({publicKey:publicKey(options.publicKey)});
  await api('auth/passkey/login/verify',{credential:serialize(credential)},{publicAuth:true});await boot();
}
async function checkApproval() {
  const data=await api('auth/telegram/status',null,{method:'GET',publicAuth:true});
  if(!['pending','approved'].includes(data.status)){state.approval=null;state.phase='signin';throw new Error('approval_expired');}
  state.approval=data;state.phase=data.status==='approved'?'enroll':'approval';render();
}
async function enroll() {
  if(!supportsPasskey()){state.error='passkeyUnsupported';render();return;}
  if(!state.enrollment){await api('auth/telegram/complete',{request_id:state.approval.request_id},{publicAuth:true});state.enrollment=true;}
  const options=state.enrollmentOptions || await api('auth/passkey/register/options',{}, {publicAuth:true});
  state.enrollmentOptions=options;
  const credential=await navigator.credentials.create({publicKey:publicKey(options.publicKey,true)});
  await api('auth/passkey/register/verify',{credential:serialize(credential)},{publicAuth:true});state.enrollment=false;state.enrollmentOptions=null;state.phase='signin';state.error=null;render();
}
function closeDrawer() {closeInboxAttachment();feedbackUserId=null;revokeTarget=null;drawerId++;signing?.abort();signing=null;confirmation=null;receiptLoaded=false;reviewId=null;$('dialogs').innerHTML='';$('root').inert=false;if(returnFocus?.isConnected)returnFocus.focus();returnFocus=null;}
function drawer(title,body,foot='',className='') {
  if(!$('overlay'))returnFocus=document.activeElement;
  $('dialogs').innerHTML=`<div class="canvas-overlay show" id="overlay"><section class="drawer ${className}" role="dialog" aria-modal="true" aria-labelledby="drawerTitle"><div class="drawer-top"><h2 id="drawerTitle">${esc(t(title))}</h2><button class="drawer-close" data-action="close" aria-label="${esc(t('close'))}">×</button></div><div class="drawer-content" id="drawerContent">${body}</div><div class="drawer-foot" id="drawerFoot">${foot||btn('close','close')}</div></section></div>`;
  $('root').inert=true;document.querySelector('.drawer-close')?.focus();
}
function profileFields(fields) {
  return `<dl class="review-summary">${fields.map(([key,value])=>`<dt>${esc(t(key))}</dt><dd>${esc(value??'—')}</dd>`).join('')}</dl>`;
}
function profilePayments(data,userId) {
  return `${data.items.map(row=>`<article class="feedback-item"><strong>#${row.payment_id} · ${esc(row.amount)} ${esc(row.currency)}</strong><p>${esc(t(row.plan_type))} · ${esc(t(row.status))}</p><small>${esc(row.source)} · ${esc(date(row.reviewed_at||row.submitted_at))}</small></article>`).join('')||`<p class="source-note">${esc(t('empty'))}</p>`}${data.next_before_id?`<button class="btn" data-profile-payments="${userId}" data-before="${data.next_before_id}">${esc(t('next'))}</button>`:''}`;
}
async function userProfile(userId) {
  closeDrawer();const current=drawerId;drawer('userProfile',statePanel('loading'));
  try {
    const data=await api('users/detail',{user_id:userId});
    if(current!==drawerId||!state.actor)return;
    const u=data.user,c=data.course,r=data.referral;
    const section=(key,body)=>`<section class="profile-section"><h3>${esc(t(key))}</h3>${body}</section>`;
    drawer('userProfile',`<div class="profile-heading"><h3>${esc(u.name||'—')}</h3><p>#${u.user_id} · ${esc(u.username||'—')}</p><span class="pill">${esc(t(u.access_state))}</span></div>`+
      profileFields([['language',u.language],['level',u.level],['created',date(u.created_at)],['lastActive',date(u.last_active_at)],['plan',t(u.selected_plan_type)],['accessUntil',date(u.access_expires_at)]])+
      section('course',(c.progress?profileFields([['level',c.progress.level],['completedLessons',c.progress.completed_lessons],['lastLesson',date(c.progress.last_completed_at)]]):`<p class="source-note">${esc(t('empty'))}</p>`)+c.tracks.map(row=>`<p class="source-note">${esc(row.track==='hsk30'?'HSK 3.0':'HSK 2.0')} · ${esc(row.level)} · ${esc(t('completedLessons'))}: ${row.completed_lessons}${row.unlocked_at?' · '+esc(t('unlocked'))+' '+esc(date(row.unlocked_at)):''}</p>`).join(''))+
      section('referrals',profileFields([['invitedTotal',r.invited_total],['invitedActive',r.invited_active],['discountQualified',r.discount_qualified]]))+
      section('devices',data.devices.map(row=>`<article class="feedback-item"><strong>${esc(row.platform)}</strong>${profileFields([['linkedTotal',row.linked+' / '+row.total],['lastContact',date(row.last_contact_at)]])}</article>`).join('')||`<p class="source-note">${esc(t('empty'))}</p>`)+
      (data.miniapp_presence.length?section('miniappOpens',data.miniapp_presence.map(row=>`<p class="source-note">${esc(row.platform)} · ${esc(date(row.last_opened_at))}</p>`).join('')):'')+
      section('feedback',profileFields([['botFeedback',data.feedback_counts.bot],['releaseFeedback',data.feedback_counts.release]])+`<button class="btn" data-user-feedback="${userId}">${esc(t('openFeedback'))}</button>`)+
      section('paymentHistory',`<div id="profilePayments">${profilePayments(data.payments,userId)}</div>`)+`<p class="source-note">${esc(t('updated'))}: ${esc(date(data.generated_at))}</p>`,
      btn('close','close')+`<button class="btn primary" data-access-user="${userId}" ${u.status==='blocked'?'disabled':''}>${esc(t('grantAccess'))}</button>`);
  }catch(error){if(current===drawerId&&state.actor)drawer('userProfile',statePanel(error.status===404?'userMissing':'error'),btn('close','close')+`<button class="btn" data-user-detail="${userId}">${esc(t('retry'))}</button>`);}
}
async function moreUserPayments(userId,before,button) {
  const current=drawerId;button.disabled=true;
  try {
    const data=await api('users/payments',{user_id:userId,before_id:before,limit:10});
    if(current===drawerId&&state.actor&&$('profilePayments'))$('profilePayments').innerHTML=profilePayments(data,userId);
  }catch(error){if(current===drawerId&&state.actor)showNotice('error');}
  finally{if(button.isConnected)button.disabled=false;}
}
function accessGrantForm(userId){
  closeDrawer();
  if(!state.actor||!Number.isSafeInteger(userId)||userId<1)return;
  drawer('grantAccess',`<p>${esc(t('account'))}: #${userId}</p><p class="source-note">${esc(t('manualGrantHint'))}</p><div class="form-field"><label for="accessDays">${esc(t('durationDays'))}</label><input class="input" id="accessDays" type="number" min="1" max="365" step="1" value="30" required></div>`,
    btn('cancel','close')+`<button class="btn primary" data-prepare-access="${userId}">${esc(t('next'))}</button>`);
}
async function prepareAccess(userId){
  const input=$('accessDays');if(!input?.reportValidity())return;
  const days=Number(input.value);if(!Number.isInteger(days)||days<1||days>365)return;
  const current=drawerId,at=epoch;$('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=true);
  try{
    const operation=await api('users/prepare-access',{user_id:userId,duration_days:days});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    confirmation=Object.freeze(structuredClone(operation));
    drawer('confirmAccess',`<p class="alert">${esc(t('manualGrantHint'))}</p>`+profileFields([
      ['account','#'+operation.payload.user_id],['durationDays',operation.payload.duration_days],
      ['accessUntil',date(operation.payload.expected.end_date)]]),btn('cancel','close')+btn('confirmPasskey','executeAccess','primary'),'confirmation');
  }catch(error){if(current===drawerId&&at===epoch&&state.actor)drawer('grantAccess',statePanel(error.status===409?'changed':'error'));}
}
async function executeAccess(){
  if(confirmation?.action!=='users.grant_access'||!supportsPasskey()||signing)return;
  const operation=structuredClone(confirmation),current=drawerId,at=epoch,control=new AbortController();signing=control;
  $('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=true);let submitted=false;
  try{
    const options=await api('auth/step-up/options',operation);
    if(current!==drawerId||at!==epoch)return;
    const credential=await navigator.credentials.get({publicKey:publicKey(options.publicKey),signal:control.signal});
    if(current!==drawerId||at!==epoch)return;
    await api('auth/step-up/verify',{step_up_id:options.step_up_id,credential:serialize(credential)});
    if(current!==drawerId||at!==epoch)return;
    submitted=true;
    const result=await api('users/grant-access',{...operation.payload,step_up_id:options.step_up_id});
    if(current!==drawerId||at!==epoch)return;
    confirmation=null;
    drawer('accessGranted',profileFields([['account','#'+result.user_id],['durationDays',result.duration_days],['accessUntil',date(result.after.end_date)]]));
    await load();
  }catch(error){
    if(current!==drawerId||at!==epoch)return;
    confirmation=null;
    const rejected=[400,403,404,409].includes(error.status);
    drawer('grantAccess',statePanel(error.status===409?'changed':submitted&&!rejected?'uncertain':errorKey(error)),btn('close','close')+`<button class="btn" data-user-detail="${operation.payload.user_id}">${esc(t('openProfile'))}</button>`);
    if(submitted)await load();
  }finally{if(signing===control)signing=null;}
}
function summary(operation) {
  const p=operation.payload,s=p.expected;
  const fields=[['payment','#'+p.payment_id],['account',s.user_id],['plan',t(s.plan_type)],['amount',s.amount+' '+s.currency],['method',s.payment_method],['source',s.source],['submitted',date(s.submitted_at)]];
  if(s.local_amount)fields.push(['localAmount',s.local_amount+' '+(s.local_currency||'')]);
  if(s.discount_percent)fields.push(['discount',s.discount_percent+'% · '+s.discount_source]);
  if(p.reason)fields.push(['reason',p.reason]);
  return `<dl class="review-summary">${fields.map(([key,value])=>`<dt>${esc(t(key))}</dt><dd ${key==='amount'?'class="amount-value"':''}>${esc(value??'—')}</dd>`).join('')}</dl>`;
}
async function review(paymentId) {
  closeDrawer();const current=drawerId;reviewId=paymentId;drawer('review',statePanel('loading'));
  try {
    const operation=await api('payments/prepare-review',{payment_id:paymentId,decision:'approve',reason:null});
    if(current!==drawerId||!state.actor)return;
    confirmation=operation;receiptLoaded=false;
    const fingerprint=operation.payload.expected.receipt_sha256;
    drawer('review',summary(operation)+`<p class="alert" id="receiptStatus">${esc(t('receiptMissing'))}</p>${fingerprint?`<img class="receipt-image" id="receiptImage" alt="${esc(t('receipt'))}">`:''}<div class="form-field"><label for="rejectReason">${esc(t('reason'))}</label><textarea id="rejectReason" class="input textarea" maxlength="300"></textarea></div>`,btn('reject','reject','danger',true)+btn('approve','approve','primary',true));
    if(fingerprint) {
      const image=$('receiptImage');image.onload=()=>{if(current!==drawerId)return;receiptLoaded=true;$('receiptStatus').hidden=true;document.querySelectorAll('[data-action="approve"],[data-action="reject"]').forEach(button=>button.disabled=false);};
      image.onerror=()=>{if(current===drawerId)receiptLoaded=false;};
      image.src=`/api/admin/v1/payments/${paymentId}/receipt?receipt_sha256=${encodeURIComponent(fingerprint)}`;
    }
  } catch(error){if(current===drawerId&&state.actor)drawer('review',statePanel(error.status===409?'changed':'error'));}
}
async function prepareDecision(decision) {
  if(!receiptLoaded||!confirmation)return;
  const previous=confirmation, paymentId=reviewId, current=drawerId;
  const reason=decision==='reject'?$('rejectReason').value.trim():null;
  if(decision==='reject'&&!reason){$('rejectReason').focus();return;}
  document.querySelectorAll('[data-action="approve"],[data-action="reject"]').forEach(button=>button.disabled=true);
  let actual;
  try {actual=await api('payments/prepare-review',{payment_id:paymentId,decision,reason});}
  catch(error){if(current===drawerId&&state.actor)drawer('review',statePanel(error.status===409?'changed':'error'));return;}
  if(current!==drawerId||!state.actor)return;
  if(JSON.stringify(actual.payload.expected)!==JSON.stringify(previous.payload.expected)){showNotice('changed');await review(paymentId);return;}
  confirmation=Object.freeze(structuredClone(actual));
  drawer('confirmPayment',`<p class="alert">${esc(t('confirmHint'))}</p><h3>${esc(t(decision))}</h3>${summary(actual)}`,btn('cancel','close')+btn('confirmPasskey','execute',decision==='reject'?'danger':'primary'),'confirmation');
}
async function execute() {
  if(!confirmation||!receiptLoaded||!supportsPasskey())return;
  const operation=structuredClone(confirmation), current=drawerId, authEpoch=epoch;
  $('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=true);const control=new AbortController();signing=control;
  let submitted=false;
  try {
    const options=await api('auth/step-up/options',operation);
    if(current!==drawerId||authEpoch!==epoch)return;
    const credential=await navigator.credentials.get({publicKey:publicKey(options.publicKey),signal:control.signal});
    if(current!==drawerId||authEpoch!==epoch)return;
    await api('auth/step-up/verify',{step_up_id:options.step_up_id,credential:serialize(credential)});
    if(current!==drawerId||authEpoch!==epoch)return;
    submitted=true;
    const result=await api('payments/review',{...operation.payload,step_up_id:options.step_up_id});
    if(current!==drawerId||authEpoch!==epoch)return;
    confirmation=null;receiptLoaded=false;
    drawer('decisionSaved',`<div class="state-panel"><h2>${esc(t(result.status))}</h2><p>#${esc(operation.payload.payment_id)}</p>${['uncertain','attempting','unconfirmed'].includes(result.delivery_status)?`<p>${esc(t('deliveryUncertain'))}</p>`:''}</div>`);
    await load();
  } catch(error) {
    if(current!==drawerId||authEpoch!==epoch)return;
    confirmation=null;receiptLoaded=false;
    drawer('confirmPayment',statePanel(submitted?'uncertain':errorKey(error)));
    if(submitted)await load();
  } finally {if(signing===control)signing=null;}
}

const inboxStatusLabels={new:'inboxStatusNew',read:'inboxStatusRead',assigned:'inboxStatusAssigned',resolved:'inboxStatusResolved'};
function closeInboxAttachment(){
  const preview=inboxAttachment;inboxAttachment=null;
  if(!preview)return;
  preview.control.abort();
  if(preview.url)URL.revokeObjectURL(preview.url);
  preview.host.replaceChildren();preview.host.hidden=true;preview.host.removeAttribute('aria-busy');
  preview.button.setAttribute('aria-expanded','false');preview.button.textContent=t('viewAttachment');
}
async function viewInboxAttachment(button){
  if(inboxAttachment?.button===button){closeInboxAttachment();return;}
  closeInboxAttachment();
  const source=button.dataset.attachmentSource,id=Number(button.dataset.inboxAttachment);
  if(!['android','bot','release'].includes(source))return;
  const host=$(`inboxAttachment-${source}-${id}`);
  if(!state.actor||!Number.isSafeInteger(id)||id<1||id>2147483647||!host)return;
  const mediaTypes=source==='android'?['image/jpeg']:['image/jpeg','image/png','image/webp'];
  const maxBytes=source==='android'?550*1024:8*1024*1024;
  const current=drawerId,at=epoch,control=new AbortController();
  const preview={button,host,control,url:null};inboxAttachment=preview;
  const active=()=>inboxAttachment===preview&&current===drawerId&&at===epoch&&!!state.actor;
  host.hidden=false;host.setAttribute('aria-busy','true');host.innerHTML=`<p role="status">${esc(t('loading'))}</p>`;
  button.setAttribute('aria-expanded','true');button.textContent=t('hideAttachment');
  const timer=setTimeout(()=>control.abort(),15000);
  try{
    // Allowlisted first-party source only; never an attachment URL from a record.
    const response=await fetch(`/api/admin/v1/inbox/${source}/${id}/attachment`,{
      credentials:'same-origin',cache:'no-store',redirect:'error',headers:{Accept:mediaTypes.join(',')},signal:control.signal});
    if(!active())return;
    if(response.status===401){clearPrivate('signin');state.error='authExpired';render();return;}
    if(!response.ok||!mediaTypes.includes(response.headers.get('content-type')))throw new Error('unavailable');
    const blob=await response.blob();
    if(!active())return;
    if(!blob.size||blob.size>maxBytes)throw new Error('unavailable');
    const image=new Image();image.className='inbox-attachment-image';image.alt=t('inboxAttachment');
    image.onload=()=>{if(active()){host.setAttribute('aria-busy','false');image.scrollIntoView({block:'nearest'});}};
    image.onerror=()=>{
      if(!active())return;
      URL.revokeObjectURL(preview.url);preview.url=null;
      host.setAttribute('aria-busy','false');host.innerHTML=`<p role="status">${esc(t('unavailable'))}</p>`;
    };
    preview.url=URL.createObjectURL(blob);image.src=preview.url;host.replaceChildren(image);
  }catch(error){
    if(active()){host.setAttribute('aria-busy','false');host.innerHTML=`<p role="status">${esc(t('unavailable'))}</p>`;}
  }finally{clearTimeout(timer);}
}
function inboxControl(row,operation,key){
  if(!['bot','release','android','payment'].includes(row.source)||!Number.isSafeInteger(row.source_id)||!Number.isSafeInteger(row.triage_revision))return '';
  return `<button class="btn small" data-inbox-op="${operation}" data-inbox-source="${row.source}" data-inbox-id="${row.source_id}" data-inbox-revision="${row.triage_revision}">${esc(t(key))}</button>`;
}
function inboxEntry(row){
  const status=inboxStatusLabels[row.triage_status]||'inboxStatusNew';
  const origin=row.source==='bot'?'botFeedback':row.source==='release'?'releaseFeedback':row.source==='payment'?'inboxPaymentReceipt':'inboxAndroid';
  const flags=`<span class="inbox-state">${esc(t(status))}</span>${row.triage_priority==='important'?`<span class="inbox-state inbox-state-important">${esc(t('inboxImportant'))}</span>`:''}${row.triage_assigned_to===state.actor?.user_id?`<span class="inbox-state">${esc(t('inboxMine'))}</span>`:''}`;
  const actions=[];
  const canView=(row.source==='android'?row.has_attachment:['bot','release'].includes(row.source)&&row.image_preview_available===true)&&Number.isSafeInteger(row.source_id)&&row.source_id>0&&row.source_id<=2147483647;
  const attachmentId=`inboxAttachment-${row.source}-${row.source_id}`;
  if(canView)actions.push(`<button class="btn small" data-inbox-attachment="${row.source_id}" data-attachment-source="${row.source}" aria-controls="${attachmentId}" aria-expanded="false">${esc(t('viewAttachment'))}</button>`);
  if(row.triage_status==='new')actions.push(inboxControl(row,'mark_read','inboxMarkRead'));
  if(row.source==='payment'){
    // Opening Payments is NOT the same as approving an unverified receipt.
    actions.push(`<button class="btn small" data-route="payments">${esc(t('payments'))}</button>`);
  }else{
    if(row.triage_status!=='resolved'&&row.triage_assigned_to!==state.actor?.user_id)actions.push(inboxControl(row,'assign_self','inboxAssignSelf'));
    actions.push(row.triage_status==='resolved'?inboxControl(row,'reopen','inboxReopen'):inboxControl(row,'resolve','inboxResolve'));
    actions.push(row.triage_priority==='important'?inboxControl(row,'clear_important','inboxClearImportant'):inboxControl(row,'mark_important','inboxMarkImportant'));
  }
  return `<article class="feedback-item inbox-feedback-item"><div class="inbox-entry-head"><strong>${esc(t(origin))} · ${esc(row.user_id?t('account')+' '+row.user_id:'—')}${row.rating?' · '+esc(row.rating)+'/5':''}</strong><small>${esc(date(row.created_at))}</small></div><div class="inbox-states">${flags}</div><p>${esc(row.message||'—')}</p>${row.has_attachment&&!canView?`<p class="source-note">${esc(t('hasAttachment'))}</p>`:''}<div class="inbox-entry-actions">${actions.join('')}</div>${canView?`<div class="inbox-attachment" id="${attachmentId}" aria-live="polite" hidden></div>`:''}</article>`;
}
async function refreshInboxUnread() {
  if(!state.actor)return;
  const id=state.actor.user_id,current=epoch;
  try{
    const data=await api('inbox/unread-count',{});
    if(current!==epoch||state.actor?.user_id!==id)return;
    if(!Number.isSafeInteger(data.unread_count)||data.unread_count<0||typeof data.capped!=='boolean')return;
    inboxUnread={unread_count:data.unread_count,capped:data.capped};
    // Apple Home Screen/Dock badge: only after the user explicitly opted in.
    // Never clear or replace the badge when the authoritative read failed.
    if(state.actor.push_available&&'Notification' in window&&Notification.permission==='granted'){
      if(data.unread_count&&typeof navigator.setAppBadge==='function'){
        navigator.setAppBadge(data.unread_count).catch(()=>{});
      }else if(!data.unread_count&&typeof navigator.clearAppBadge==='function'){
        navigator.clearAppBadge().catch(()=>{});
      }
    }
    const bell=document.querySelector('button[data-action="feedback"]');
    if(!bell)return;
    bell.querySelector('.top-icon-badge')?.remove();
    if(data.unread_count){
      const badge=document.createElement('span');badge.className='top-icon-badge';badge.setAttribute('aria-hidden','true');
      badge.textContent=data.capped?'99+':String(data.unread_count);bell.append(badge);
    }
    bell.setAttribute('aria-label',t('feedback')+' · '+t('inboxUnread')+': '+(data.capped?'99+':data.unread_count));
  }catch(_){/* Never invent a zero badge on an unavailable private read. */}
}
async function inbox(before=null,userId=null) {
  closeDrawer();feedbackUserId=userId;inboxNextCursor=null;const current=drawerId;
  drawer('feedback',statePanel('loading'),'','inbox-drawer');
  try {
    const data=await api('inbox/list',{source:state.source,priority:state.inboxPriority,search:state.inboxSearch||null,user_id:userId,before,limit:30});
    if(current!==drawerId||!state.actor)return;
    inboxNextCursor=data.next_before;
    const options=[['all','all'],['payment','inboxPaymentReceipt'],['android','inboxAndroid'],['bot','botFeedback'],['release','releaseFeedback']];
    const searchUI=`<form id="inboxSearchForm" class="inbox-search-form" role="search"><input class="input" id="inboxSearchQuery" type="search" value="${esc(state.inboxSearch)}" minlength="3" maxlength="80" autocomplete="off" spellcheck="false" aria-label="${esc(t('find'))}" placeholder="${esc(t('find'))}"><button type="submit" class="btn primary">${esc(t('find'))}</button></form>${state.inboxSearch?`<p class="source-note">${esc(t('monthly'))}</p>`:''}`;
    const body=`<div class="inbox-shell">${searchUI}${userId?`<p class="source-note">${esc(t('account'))}: #${esc(userId)}</p>`:''}<div class="data-toolbar">${options.map(([source,key])=>`<button class="btn ${state.source===source?'primary':''}" data-source="${source}" aria-pressed="${state.source===source}">${esc(t(key))}</button>`).join('')}</div><div class="inbox-priority-filter"><button class="btn small ${state.inboxPriority==='all'?'primary':''}" data-inbox-priority="all" aria-pressed="${state.inboxPriority==='all'}">${esc(t('all'))}</button><button class="btn small ${state.inboxPriority==='important'?'primary':''}" data-inbox-priority="important" aria-pressed="${state.inboxPriority==='important'}">${esc(t('inboxImportant'))}</button></div><p class="source-note">${esc(t('inboxHistoryNote'))}</p>${data.items.map(inboxEntry).join('')||statePanel('empty')}${inboxNextCursor?`<button class="btn" data-feedback-next="1">${esc(t('next'))}</button>`:''}</div>`;
    drawer('feedback',body,'','inbox-drawer');
  }catch(error){if(current===drawerId&&state.actor)drawer('feedback',statePanel('error'));}
}
async function mutateInbox(button){
  if(inboxUpdating||!state.actor)return;
  const source=button.dataset.inboxSource,operation=button.dataset.inboxOp;
  const source_id=Number(button.dataset.inboxId),expected_revision=Number(button.dataset.inboxRevision);
  if(!['bot','release','android','payment'].includes(source)||!Number.isSafeInteger(source_id)||source_id<1||!Number.isSafeInteger(expected_revision))return;
  const prevDrawer=drawerId,prevEpoch=epoch,account=feedbackUserId;
  inboxUpdating=true;
  const controls=[...document.querySelectorAll('.inbox-drawer button')];
  controls.forEach(el=>el.disabled=true);
  try{
    await api('inbox/triage',{source,source_id,operation,expected_revision});
    if(prevEpoch!==epoch||prevDrawer!==drawerId||!state.actor)return;
    showNotice('inboxSaved');
    await inbox(null,account);
    await refreshInboxUnread();
  }catch(error){
    if(prevEpoch!==epoch||prevDrawer!==drawerId||!state.actor)return;
    if(error.status===409){
      showNotice('inboxChanged');
      await inbox(null,account);
      await refreshInboxUnread();
    }else{
      showNotice('inboxActionError');
      controls.forEach(el=>{if(el.isConnected)el.disabled=false;});
    }
  }finally{inboxUpdating=false;}
}

// Apple-first Web Push opt-in; actual sending requires an independent server kill switch.
function applePushPlatform() {
  const ua=navigator.userAgent||'';
  if(/iPhone/i.test(ua))return 'iphone';
  if(/Macintosh|Mac OS X/i.test(ua))return 'mac';
  return null;
}
function pushInstallReady(platform) {
  if(platform!=='iphone')return true;
  return navigator.standalone===true||window.matchMedia?.('(display-mode: standalone)').matches===true;
}
async function pushSettings(){
  if(!state.actor?.push_available)return;
  closeDrawer();pushReady=null;const current=drawerId,at=epoch;
  drawer('pushTitle',statePanel('loading'));
  try{
    const data=await api('push/list',{});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    const platform=applePushPlatform();
    const eligible=platform&&pushInstallReady(platform)&&'Notification' in window&&
                   'serviceWorker' in navigator&&'PushManager' in window&&
                   Notification.permission!=='denied';
    if(eligible){
      // No permission prompt here. Prepare public VAPID and active worker
      // before the opt-in click so subscribe() can begin with user activation.
      const registration=await navigator.serviceWorker.ready;
      const previous=await registration.pushManager.getSubscription();
      if(current!==drawerId||at!==epoch||!state.actor)return;
      pushReady={registration,key:decode(data.vapid_public_key),previous:!!previous,epoch:at};
    }
    const rows=data.subscriptions||[];
    const devices=rows.map(row=>`<article class="feedback-item"><strong>${esc(row.platform==='iphone'?'iPhone':'Mac')}</strong><small>${esc(date(row.created_at))}</small><div class="inbox-entry-actions"><button class="btn small danger" data-push-revoke="${esc(row.id)}">${esc(t('pushRevoke'))}</button></div></article>`).join('')||statePanel('empty');
    const note=!platform?t('pushAppleOnly'):!pushInstallReady(platform)?t('pushInstallFirst'):t('pushConsentHint');
    const deliveryNote=data.sending_enabled===true?'':`<p class="source-note">${esc(t('pushNotSending'))}</p>`;
    drawer('pushTitle',`<div class="push-settings"><p class="source-note">${esc(note)}</p>${deliveryNote}${devices}</div>`,
      pushReady?btn('pushEnable','pushEnable','primary')+btn('close','close'):btn('close','close'));
  }catch(error){
    if(current!==drawerId||at!==epoch||!state.actor)return;
    pushReady=null;
    drawer('pushTitle',statePanel(error.status===404?'notReady':'error'),btn('close','close')+btn('retry','pushSettings'));
  }
}
async function enablePush(){
  if(pushChanging||!state.actor?.push_available||!pushReady||pushReady.epoch!==epoch||
     !['iphone','mac'].includes(applePushPlatform())||!pushInstallReady(applePushPlatform()))return;
  if(Notification.permission==='denied'){showNotice('pushPermissionDenied');return;}
  pushChanging=true;
  const prepared=pushReady;
  // Apple Web Push: call subscribe() in this direct tap callback, BEFORE
  // any await/fetch. A deferred request loses iPhone's user activation.
  let subscriptionPromise;
  try{
    subscriptionPromise=prepared.registration.pushManager.subscribe({
      userVisibleOnly:true,applicationServerKey:prepared.key
    });
  }catch(_){pushChanging=false;showNotice('pushSaveError');return;}
  const current=drawerId,at=epoch;
  document.querySelectorAll('#drawerFoot button').forEach(el=>el.disabled=true);
  try{
    const subscription=await subscriptionPromise;
    if(at!==epoch||current!==drawerId||!state.actor)return;
    const payload=subscription.toJSON(),keys=payload.keys||{};
    if(!payload.endpoint||!keys.p256dh||!keys.auth)throw Error('invalid_push_subscription');
    try{
      await api('push/subscribe',{platform:applePushPlatform(),endpoint:payload.endpoint,
        keys:{p256dh:keys.p256dh,auth:keys.auth}});
    }catch(error){
      if(!prepared.previous)await subscription.unsubscribe().catch(()=>{});
      throw error;
    }
    if(at!==epoch||current!==drawerId||!state.actor)return;
    showNotice('pushSaved');await pushSettings();
  }catch(error){
    if(at===epoch&&state.actor)showNotice(Notification.permission==='denied'?'pushPermissionDenied':'pushSaveError');
  }finally{
    pushChanging=false;
    document.querySelectorAll('#drawerFoot button').forEach(el=>el.disabled=false);
  }
}

async function revokePush(id){
  if(pushChanging||!state.actor?.push_available||!/^[0-9a-f-]{36}$/.test(id))return;
  const current=drawerId,at=epoch;
  pushChanging=true;
  document.querySelectorAll('.push-settings button').forEach(el=>el.disabled=true);
  try{
    await api('push/revoke',{subscription_id:id});
    if(at!==epoch||current!==drawerId||!state.actor)return;
    showNotice('pushRevoked');await pushSettings();
  }catch(error){
    if(at!==epoch||current!==drawerId||!state.actor)return;
    // A lost response may follow a committed revocation: re-read authoritative list.
    showNotice('pushReviewStatus');await pushSettings();
  }finally{pushChanging=false;}
}

function mcpStateKey(row) {
  if(row.status==='revoked')return 'mcpRevoked';
  if(row.status==='denied')return 'mcpDenied';
  if(row.active_access)return 'mcpActive';
  return row.status==='pending'||row.status==='approved'?'mcpPending':'mcpExpired';
}
async function mcpConnections() {
  closeDrawer();const current=drawerId;
  drawer('mcpConnections',statePanel('loading'));
  try {
    const data=await api('mcp/authorizations',null,{method:'GET'});
    if(current!==drawerId||!state.actor)return;
    const rows=data.authorizations;
    drawer('mcpConnections',`<p class="source-note">${esc(t('mcpLifecycle'))}</p><div class="mcp-history">${rows.map(row=>`<article class="feedback-item"><strong class="mcp-client-name">${esc(row.client_id)}</strong><p>${esc(t('mcpPermission'))}</p><p class="pill">${esc(t(mcpStateKey(row)))}</p><p><small>${esc(date(row.created_at))}${row.access_expires_at?' · '+esc(t('mcpAccessUntil'))+' '+esc(date(row.access_expires_at)):''}</small></p>${['pending','approved','redeemed'].includes(row.status)?`<button class="btn danger" data-mcp-revoke="${esc(row.id)}">${esc(t('mcpRevoke'))}</button>`:''}</article>`).join('')||statePanel('empty')}</div>`);
  }catch(error){
    if(current!==drawerId||!state.actor)return;
    drawer('mcpConnections',statePanel(error.status===404?'notReady':error.status===403?'authFailed':navigator.onLine?'error':'offline'),btn('close','close')+btn('retry','mcpConnections','primary'));
  }
}
function confirmMcpRevoke(id, label) {
  if(!/^[0-9a-f-]{36}$/.test(id)||!state.actor?.mcp_available)return;
  revokeTarget=id;
  drawer('mcpRevoke',`<p class="alert">${esc(t('mcpRevokeHint'))}</p><p class="mcp-client-name">${esc(label)}</p>`,btn('cancel','mcpConnections')+btn('mcpRevoke','mcpRevokeConfirm','danger'));
}
async function revokeMcp() {
  if(!revokeTarget||revoking)return;
  const id=revokeTarget,current=drawerId;revoking=true;
  $('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=true);
  try {
    await api('mcp/authorizations/revoke',{authorization_id:id});
    if(current!==drawerId||!state.actor)return;
    showNotice('mcpRevoked');await mcpConnections();
  }catch(error){
    if(current!==drawerId||!state.actor)return;
    // The response may be lost after a committed revocation. Re-read history.
    drawer('mcpConnections',statePanel('uncertain'),btn('close','close')+btn('retry','mcpConnections','primary'));
  }finally{revoking=false;}
}
async function action(name) {
  if(busy&&name!=='close')return;
  if(['signin','google','approval','enroll','logout'].includes(name)){
    busy=true;state.error=null;render();
    try {
      if(name==='signin')await login();
      if(name==='approval')await checkApproval();
      if(name==='enroll')await enroll();
      if(name==='google'){const data=await api('auth/google/start',{}, {publicAuth:true});const url=new URL(data.authorize_url);if(url.protocol!=='https:'||url.hostname!=='accounts.google.com')throw Error('invalid_authorize_url');location.assign(url.href);}
      if(name==='logout'){await api('auth/logout',{});clearPrivate('signin');}
    }catch(error){if(error.message!=='stale'){state.error=['signin','enroll'].includes(name)?errorKey(error):'authFailed';render();}}
    finally{busy=false;render();}return;
  }
  if(name==='close'){closeDrawer();return;}
  if(name==='boot'){await boot();return;}
  if(name==='reload'){await load();return;}
  if(name==='mcpConnections'){await mcpConnections();return;}
  if(name==='pushSettings'){await pushSettings();return;}
  if(name==='pushEnable'){await enablePush();return;}
  if(name==='mcpRevokeConfirm'){await revokeMcp();return;}
  if(name==='feedback'){state.inboxSearch='';await inbox();return;}
  if(name==='approve'||name==='reject'){await prepareDecision(name);return;}
  if(name==='execute'){if(!signing)await execute();return;}
  if(name==='executeAccess'){await executeAccess();return;}
  if(name==='more'){drawer('more',languageSelect('drawerLocale')+(state.actor.mcp_available?btn('mcpConnections','mcpConnections'):'')+(state.actor.push_available?btn('pushTitle','pushSettings'):''),btn('install','install')+btn('logout','logout'));return;}
  if(name==='install'){if(installPrompt){await installPrompt.prompt();installPrompt=null;}else showNotice('installHint');return;}
  if(name==='update'){publicRegistration?.waiting?.postMessage('ACTIVATE_PUBLIC_SHELL');return;}
  if(name==='next'&&state.next){state.previous.push(state.cursor);state.cursor=state.next;await load();}
  if(name==='previous'&&state.previous.length){state.cursor=state.previous.pop();await load();}
  if(name==='period'||name==='platform'){const menu=$(name+'Menu');menu.hidden=!menu.hidden;document.querySelector(`[data-action="${name}"]`).setAttribute('aria-expanded',String(!menu.hidden));}
}
document.addEventListener('click',event=>{
  const button=event.target.closest('button');if(!button||button.disabled)return;
  const run=async()=>{
    if(button.dataset.route){closeDrawer();state.route=button.dataset.route;state.cursor=null;state.previous=[];state.query='';await load();}
    else if(button.dataset.period){state.period=button.dataset.period;await load();}
    else if(button.dataset.platform){state.platform=button.dataset.platform;await load();}
    else if(button.dataset.exportFormat){await exportStatistics(button.dataset.exportFormat);}
    else if(button.dataset.status){state.status=button.dataset.status;state.cursor=null;state.previous=[];await load();}
    else if(button.dataset.review){await review(Number(button.dataset.review));}
    else if(button.dataset.userDetail){await userProfile(Number(button.dataset.userDetail));}
    else if(button.dataset.accessUser){accessGrantForm(Number(button.dataset.accessUser));}
    else if(button.dataset.prepareAccess){await prepareAccess(Number(button.dataset.prepareAccess));}
    else if(button.dataset.profilePayments){await moreUserPayments(Number(button.dataset.profilePayments),Number(button.dataset.before),button);}
    else if(button.dataset.userFeedback){state.inboxSearch='';await inbox(null,Number(button.dataset.userFeedback));}
    else if(button.dataset.source){state.source=button.dataset.source;await inbox(null,feedbackUserId);}
    else if(button.dataset.inboxPriority){state.inboxPriority=button.dataset.inboxPriority;await inbox(null,feedbackUserId);}
    else if(button.dataset.inboxAttachment){await viewInboxAttachment(button);}
    else if(button.dataset.inboxOp){await mutateInbox(button);}
    else if(button.dataset.feedbackNext&&inboxNextCursor){await inbox(inboxNextCursor,feedbackUserId);}
    else if(button.dataset.pushRevoke){await revokePush(button.dataset.pushRevoke);}
    else if(button.dataset.mcpRevoke){confirmMcpRevoke(button.dataset.mcpRevoke,button.closest('article').querySelector('strong').textContent);}
    else if(button.dataset.action){await action(button.dataset.action);}
  };run().catch(error=>{if(error.message!=='stale')showNotice(errorKey(error));});
});
document.addEventListener('change',event=>{
  if(['locale','drawerLocale'].includes(event.target.id)&&['uz','ru','tj'].includes(event.target.value)){
    cancelStatisticsDownload();
    locale=event.target.value;try{localStorage.setItem('hsk-admin-locale',locale);}catch(_){}
    closeDrawer();render();
  }
});
document.addEventListener('submit',event=>{
  if(event.target.id==='searchForm'){event.preventDefault();state.query=$('userQuery').value;state.cursor=null;state.previous=[];load();}
  else if(event.target.id==='inboxSearchForm'){
    event.preventDefault();
    const value=$('inboxSearchQuery').value.trim();
    if(value&&(value.length<3||value.length>80))return;
    state.inboxSearch=value;
    inbox(null,feedbackUserId).catch(()=>showNotice('error'));
  }
});
document.addEventListener('keydown',event=>{
  if(event.key==='Escape'){closeDrawer();for(const id of ['periodMenu','platformMenu'])if($(id))$(id).hidden=true;}
  if(event.key==='Tab'&&$('overlay')){
    const controls=[...$('overlay').querySelectorAll('button:not(:disabled),input,select,textarea')];
    if(!controls.length)return;const first=controls[0],last=controls.at(-1);
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
  }
});
window.addEventListener('offline',()=>clearPrivate('offline'));
window.addEventListener('online',()=>boot());
window.addEventListener('pagehide',()=>clearPrivate('loading'));
window.addEventListener('pageshow',event=>{if(event.persisted)boot();});
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&state.actor&&!signing)boot();});
window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();installPrompt=event;});
if('serviceWorker' in navigator){
  navigator.serviceWorker.register('/admin/sw.js',{scope:'/admin/',updateViaCache:'none'}).then(registration=>{
    publicRegistration=registration;
    const update=()=>{if(registration.waiting&&navigator.serviceWorker.controller){const button=document.createElement('button');button.className='btn primary shell-update';button.textContent=t('update');button.dataset.action='update';document.body.append(button);}};
    update();registration.addEventListener('updatefound',()=>registration.installing?.addEventListener('statechange',update));
  }).catch(()=>{});
  navigator.serviceWorker.addEventListener('controllerchange',()=>location.reload());
}
boot();
})();
