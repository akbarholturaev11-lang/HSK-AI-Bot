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
download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v4h16v-4"/>',
chevron:'<path d="m9 5 7 7-7 7"/>',
gift:'<rect x="3" y="9" width="18" height="12" rx="2"/><path d="M12 9v12M3 13h18M12 9c-10 0-8-8-4-6 2 1 4 6 4 6Zm0 0c10 0 8-8 4-6-2 1-4 6-4 6Z"/>',
delete:'<path d="M3 6h18M8 6V4h8v2M6 6l1 15h10l1-15M10 10v7M14 10v7"/>',
device:'<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M11 18h2"/>',
sliders:'<path d="M4 5h16M4 12h16M4 19h16"/><circle cx="9" cy="5" r="2" fill="white"/><circle cx="16" cy="12" r="2" fill="white"/><circle cx="11" cy="19" r="2" fill="white"/>',
link:'<path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-2 2M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l2-2"/>'
};
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const telegramPreview = value => esc(value).replace(/&lt;(\/?)b&gt;/g, '<$1b>');
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${icons[name] || icons.folder}</svg>`;
let locale = 'uz';
try { const saved = localStorage.getItem('hsk-admin-locale'); if (['uz','ru','tj'].includes(saved)) locale = saved; } catch (_) {}
const t = key => window.HSKAI_ADMIN_I18N?.[locale]?.[key] ?? courseCopy?.[locale]?.[key] ?? '—';
const btn = (label, action, variant='', disabled=false) => `<button class="btn ${variant}" data-action="${action}" ${disabled?'disabled':''}>${esc(t(label))}</button>`;
const state = {actor:null, phase:'loading', route:'home', statsTab:'overview', courseTab:'tracks', period:'weekly', platform:'overall', rows:[], stats:null,
  query:'', segment:'all', status:'pending', cursor:null, previous:[], next:null, error:null, approval:null, enrollment:false, enrollmentOptions:null};
let epoch=0, view=0, drawerId=0, confirmation=null, receiptLoaded=false, reviewId=null, signing=null, busy=false;
let publicRegistration=null, installPrompt=null, returnFocus=null, revokeTarget=null, revoking=false, feedbackUserId=null, inboxNextCursor=null, inboxUpdating=false, inboxUnread=null, pushChanging=false, pushReady=null;
let inboxAttachment=null;
let drawerBack=null, backSwipeInProgress=false, backSwipeStart=null, blockSwipeClickUntil=0;
const sectionBackStack=[];
let automaticLoginAttempted=false, automaticLoginInProgress=false;
let freshLoginInProgress=false, biometricPromptInProgress=false, resumeAuthenticationRequired=false, biometricAbort=null;
let approvalWatchTimer=null, approvalChecking=false;
let statisticsDownload=null;
let userFilterOpen=false;
const USER_SEGMENTS=[['all','userFilterAll'],['active_today','userFilterActiveToday'],['paid','userFilterPaid'],['pending','userFilterPending'],['wants_pay','userFilterWantsPay'],['trial','userFilterTrial'],['free','userFilterFree'],['expired','userFilterExpired'],['blocked','userFilterBlocked'],['bot_blocked','userFilterBotBlocked']];
let managementDraft=null,managementReview=null,managementPreparing=false,preparingEditor=null;
let coursePolicyRevision=null,hsk30Baseline=null;
let courseData=null,courseLimitDraft=null,courseTrialDraft=null,courseLimitPlan='FREE';
let managementMediaPreviewUrl=null;
let feedbackLoadId=0;
const feedbackStats={source:'all',period:'weekly',data:null,loading:false,error:false};
class ApiError extends Error { constructor(code,status) { super(code);this.status=status; } }
function clearPrivate(phase) {
  stopApprovalWatch();
  cancelStatisticsDownload();feedbackLoadId++;
  feedbackStats.data=null;feedbackStats.loading=false;feedbackStats.error=false;
  epoch++;view++;closeDrawer();inboxUnread=null;pushReady=null;state.actor=null;state.rows=[];state.stats=null;state.approval=null;state.enrollment=false;state.enrollmentOptions=null;
  courseData=null;courseLimitDraft=null;courseTrialDraft=null;state.phase=phase;state.error=null;render();
}
function releaseManagementMediaPreview(){if(managementMediaPreviewUrl){URL.revokeObjectURL(managementMediaPreviewUrl);managementMediaPreviewUrl=null;}}
async function api(path, body, {publicAuth=false, method='POST',rawBody=null,extraHeaders={},timeoutMs=15000}={}) {
  const current=epoch, control=new AbortController(), timer=setTimeout(()=>control.abort(),timeoutMs);
  try {
    const headers=method==='POST'?{'Content-Type':rawBody?rawBody.type:'application/json',...extraHeaders}:extraHeaders;
    const response=await fetch('/api/admin/v1/'+path,{method, credentials:'same-origin',cache:'no-store',redirect:'error',
      headers,body:method==='POST'?(rawBody||JSON.stringify(body)):undefined,signal:control.signal});
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
let noticeTimer=null;
function clearNotice(){clearTimeout(noticeTimer);noticeTimer=null;$('notice')?.classList.remove('show');}
function showNotice(key) { clearNotice();$('notice').textContent=t(key);$('notice').classList.add('show');noticeTimer=setTimeout(clearNotice,6000); }
function errorKey(error) {
  if(error?.name==='NotAllowedError'||error?.name==='AbortError') return 'passkeyCancelled';
  return error?.status===409?'changed':'error';
}
function telegramApprovalUrl(approval) {
  const raw=approval?.telegram_url, requestId=approval?.request_id;
  if(typeof raw!=='string'||typeof requestId!=='string'||!/^[0-9a-f-]{36}$/.test(requestId))return null;
  try {
    const url=new URL(raw);
    if(url.protocol!=='https:'||url.hostname!=='t.me'||url.port||url.username||url.password||
       url.hash||Array.from(url.searchParams).length!==1||url.searchParams.get('start')!=='admin_pwa_'+requestId||
       !/^\/[A-Za-z][A-Za-z0-9_]{4,31}$/.test(url.pathname))return null;
    return url.href;
  }catch(_){return null;}
}
function stopApprovalWatch() {
  if(approvalWatchTimer!==null)clearTimeout(approvalWatchTimer);
  approvalWatchTimer=null;
}
function watchApproval() {
  stopApprovalWatch();
  if(state.phase!=='approval'||document.hidden||!navigator.onLine)return;
  // Only one outstanding read; never poll while Telegram is in the foreground.
  approvalWatchTimer=setTimeout(()=>{approvalWatchTimer=null;checkApproval().catch(()=>{});},10000);
}
function auth() {
  let content='';
  if(state.phase==='loading') content=`<h1>${esc(t('loading'))}</h1>`;
  else if(state.phase==='offline') content=`<h1>${esc(t('offline'))}</h1><p>${esc(t('offlineHint'))}</p>${btn('retry','boot','primary')}`;
  else if(state.phase==='error') content=`<h1>${esc(t('error'))}</h1>${btn('retry','boot','primary')}`;
  else if(state.phase==='approval') {
    const telegramUrl=telegramApprovalUrl(state.approval);
    const link=telegramUrl?`<a class="btn primary" href="${esc(telegramUrl)}" target="_blank" rel="noopener noreferrer">${icon('send')}${esc(t('openTelegram'))}</a>`:`<p role="status">${esc(t('telegramUnavailable'))}</p>`;
    content=`<h1>${esc(t('approval'))}</h1><p>${esc(t('approvalHint'))}</p><p class="pairing-code">${esc(state.approval?.pairing_code)}</p><div class="approval-actions">${link}${btn('checkApproval','approval','',busy)}</div>`;
  }
  else if(state.phase==='enroll') content=`<h1>${esc(t('enroll'))}</h1><p>${esc(t('enrollHint'))}</p>${btn('enroll','enroll','primary',busy)}${state.error?btn('googleStart','google','',busy):''}`;
  else content=`<h1>${esc(t('signInTitle'))}</h1><p>${esc(t('passkeyHint'))}</p>${btn('signIn','signin','primary',busy)}<details><summary>${esc(t('google'))}</summary><p>${esc(t('googleHint'))}</p>${btn('googleStart','google','',busy)}</details>`;
  return `<main class="auth-wrap"><section class="auth-panel">${languageSelect()}<div class="brand-logo"><img src="/admin/assets/icon.png" alt="HSK AI"></div>${state.error?`<p class="alert" role="alert">${esc(t(state.error))}</p>`:''}${content}</section></main>`;
}
const routes=[['home','home'],['stats','chart'],['users','users'],['payments','wallet'],['course','book'],['marketing','mega'],['system','settings']];
function pushQuickButton(){
  if(!state.actor?.push_available||!pushReady||pushReady.epoch!==epoch||Notification.permission==='denied')return '';
  return `<button type="button" class="btn push-quick-enable" data-action="pushEnable" aria-label="${esc(t('pushEnable'))}" title="${esc(t('pushEnable'))}">${icon('bell')}<span>${esc(t('pushEnable'))}</span></button>`;
}
function updatePushQuickButton(){
  const tools=document.querySelector('.header-tools');
  if(!tools)return;
  tools.querySelector('.push-quick-enable')?.remove();
  const bell=tools.querySelector('button[data-action="feedback"]');
  if(bell)bell.insertAdjacentHTML('beforebegin',pushQuickButton());
}
function render() {
  document.documentElement.lang=locale==='tj'?'tg':locale;document.title=t('appTitle');
  if(!state.actor) { $('root').innerHTML=auth();return; }
  const navButton=([route,glyph])=>`<button data-route="${route}" class="${state.route===route?'active':''}" ${state.route===route?'aria-current="page"':''}>${icon(glyph)}${esc(t(route))}</button>`;
  const navigation=routes.map(navButton).join('');
  const mobileNav=routes.slice(0,4).map(([route,glyph])=>`<button type="button" data-route="${route}" aria-label="${esc(t(route))}" title="${esc(t(route))}" class="${state.route===route?'active':''}" ${state.route===route?'aria-current="page"':''}>${icon(glyph)}</button>`).join('')
    +`<button type="button" data-action="more" aria-label="${esc(t('more'))}" title="${esc(t('more'))}" class="${['course','marketing','system'].includes(state.route)?'active':''}" ${busy?'disabled':''}>${icon('more')}</button>`;
  const disabled='';
  $('root').innerHTML=`<div class="app"><aside class="sidebar"><div class="brand"><div class="brand-logo"><img src="/admin/assets/icon.png" alt=""></div><div><div class="brand-title">HSK AI</div><div class="brand-sub">ADMIN</div></div></div><p class="nav-cap">${esc(t('sections'))}</p><nav class="nav">${navigation}${disabled}</nav><div class="side-foot"><p>${esc(t('account'))} · ${state.actor.user_id}</p>${languageSelect()}${state.actor.mcp_available?btn('mcpConnections','mcpConnections'):''}${state.actor.push_available?btn('pushTitle','pushSettings'):''}${btn('logout','logout')}</div></aside><div class="workspace"><header class="topbar"><div class="topbar-context"><h1 class="page-title">${esc(t(state.route==='home'?'workspace':state.route))}</h1></div><div class="header-tools">${['home','stats'].includes(state.route)?filters():''}${pushQuickButton()}<button class="top-icon-btn" data-action="feedback" aria-label="${esc(t('feedback'))}">${icon('bell')}${inboxUnread?.unread_count?`<span class="top-icon-badge" aria-hidden="true">${inboxUnread.capped?'99+':inboxUnread.unread_count}</span>`:''}</button></div></header><main class="main" id="content">${content()}</main></div></div><nav class="mobile-tabs" aria-label="${esc(t('sections'))}">${mobileNav}</nav>`;
  $('root').inert=!!$('overlay');
}
function filters() {
  return `<div class="header-dropdown"><button class="header-control period-control" data-action="period" data-menu-toggle="periodMenu" aria-controls="periodMenu" aria-haspopup="menu" aria-expanded="false">${icon('clock')}<strong>${esc(t(state.period))}</strong></button><div class="header-menu action-menu" id="periodMenu" role="menu" aria-label="${esc(t('period'))}" hidden>${['weekly','monthly','all_time'].map(id=>`<button role="menuitem" tabindex="-1" data-period="${id}">${esc(t(id))}</button>`).join('')}</div></div><div class="header-dropdown"><button class="header-control icon-control" data-action="platform" data-menu-toggle="platformMenu" aria-controls="platformMenu" aria-haspopup="menu" aria-expanded="false" aria-label="${esc(t('platform'))}">${icon('filter')}</button><div class="header-menu action-menu platform-menu" id="platformMenu" role="menu" aria-label="${esc(t('platform'))}" hidden>${[['overall',t('all')],['android','Android'],['telegram','Telegram Mini App'],['macos','macOS'],['windows','Windows'],['iphone_pwa','iPhone PWA']].map(([id,name])=>`<button role="menuitem" tabindex="-1" data-platform="${id}" class="${state.platform===id?'chosen':''}">${esc(name)}</button>`).join('')}</div></div>`;
}
function actionMenu(id,items,label='moreActions',download=false){
  return `<div class="action-disclosure"><button type="button" class="btn action-menu-trigger ${download?'download-trigger':'icon-only'}" data-menu-toggle="${id}" aria-controls="${id}" aria-haspopup="menu" aria-expanded="false" aria-label="${esc(t(label))}" ${download&&statisticsDownload?'disabled aria-busy="true"':''}>${icon(download?'download':'more')}${download?`<span>${esc(t(label))}</span>`:''}</button><div class="action-menu" id="${id}" role="menu" aria-label="${esc(t(label))}" hidden>${items}</div></div>`;
}
function exportMenu(dataset){
  const attribute=dataset==='feedback'?'data-feedback-export':'data-export-format';
  const items=['json','csv'].map(format=>`<button type="button" role="menuitem" tabindex="-1" ${attribute}="${format}" ${statisticsDownload?'disabled':''}>${esc(t(format==='json'?'exportJson':'exportCsv'))}</button>`).join('');
  return actionMenu(dataset==='feedback'?'feedbackExportMenu':'statisticsExportMenu',items,'download',true);
}
function closeActionMenus(restoreFocus=false){
  let trigger;
  document.querySelectorAll('.action-menu:not([hidden])').forEach(menu=>{
    const button=menu.parentElement.querySelector('[data-menu-toggle]');
    menu.hidden=true;button?.setAttribute('aria-expanded','false');trigger=button;
  });
  if(restoreFocus&&trigger?.isConnected)trigger.focus();
  return !!trigger;
}
function toggleActionMenu(button,last=false){
  const menu=$(button.dataset.menuToggle);if(!menu)return;
  const opening=menu.hidden;closeActionMenus();if(!opening)return;
  menu.classList.remove('opens-up');menu.hidden=false;button.setAttribute('aria-expanded','true');
  const bounds=menu.getBoundingClientRect(),anchor=button.getBoundingClientRect();
  const bottom=Math.min(innerHeight,button.closest('.drawer-content')?.getBoundingClientRect().bottom??innerHeight);
  if(bounds.bottom>bottom-8&&anchor.top>bounds.height+8)menu.classList.add('opens-up');
  const items=[...menu.querySelectorAll('button:not(:disabled)')];
  (last?items.at(-1):items[0])?.focus();
}
function filterSelect(id,label,value,options){
  return `<label class="compact-filter" for="${id}"><span>${esc(t(label))}</span><select id="${id}">${options.map(([key,text])=>`<option value="${key}" ${value===key?'selected':''}>${esc(t(text))}</option>`).join('')}</select></label>`;
}
function statePanel(key, hint='', retry=false) { return `<section class="state-panel"><h2>${esc(t(key))}</h2>${hint?`<p>${esc(t(hint))}</p>`:''}${retry?btn('retry','reload','primary'):''}</section>`; }
function metric(label,value,glyph='chart') { return `<div class="metric"><div class="metric-top"><span>${esc(t(label))}</span><span class="metric-icon">${icon(glyph)}</span></div><div class="metric-value">${esc(value ?? '—')}</div></div>`; }

const feedbackCategoryLabels={
  price:'feedbackCatPrice',limits:'feedbackCatLimits',unclear:'feedbackCatUnclear',
  pace:'feedbackCatPace',other:'feedbackCatOther',unclassified:'feedbackCatUnclassified',
  low_rating:'feedbackCatLow',neutral_rating:'feedbackCatNeutral',
  positive_rating:'feedbackCatPositive',unclassified_rating:'feedbackCatUnclassified',
  reported_issue:'feedbackCatAndroid'
};
function feedbackPanel(){
  if(state.route!=='stats')return '';
  const d=feedbackStats.data;
  let result='<section class="stat-detail feedback-analysis"><h2>'+esc(t('feedbackAnalysis'))+'</h2><div class="feedback-analysis-controls">';
  result+=filterSelect('feedbackPeriod','feedbackPeriod',feedbackStats.period,[['weekly','weekly'],['monthly','monthly']]);
  result+=filterSelect('feedbackSource','source',feedbackStats.source,[['all','all'],['bot','botFeedback'],['release','releaseFeedback'],['android','inboxAndroid']]);
  result+='</div>';
  if(feedbackStats.loading)result+='<p role="status">'+esc(t('loading'))+'</p>';
  else if(feedbackStats.error)result+='<p role="alert">'+esc(t('error'))+'</p><button class="btn" data-feedback-retry="1">'+esc(t('retry'))+'</button>';
  else if(d){
    result+='<div class="feedback-analysis-grid">';
    for(const source of d.sources){
      const label=source.source==='bot'?'botFeedback':source.source==='release'?'releaseFeedback':'inboxAndroid';
      result+='<section class="feedback-analysis-source"><h3>'+esc(t(label))+'</h3><p class="source-note">'+esc(t('feedbackScanned'))+': '+esc(source.records_scanned)+'</p>';
      if(!source.categories.length)result+='<p class="source-note">'+esc(t('empty'))+'</p>';
      else{
        result+='<ul class="feedback-analysis-list">';
        for(const row of source.categories)result+='<li><span>'+esc(t(feedbackCategoryLabels[row.category]||'feedbackCatUnclassified'))+'</span><strong>'+esc(row.count)+'</strong></li>';
        result+='</ul>';
      }
      if(source.truncated)result+='<p class="source-note">'+esc(t('feedbackTruncated'))+'</p>';
      result+='</section>';
    }
    result+='</div><p class="source-note">'+esc(t('feedbackSampled'))+' · '+esc(t('updated'))+': '+esc(date(d.generated_at))+'</p>';
    result+='<div class="feedback-analysis-download">'+exportMenu('feedback')+'</div>';
  }
  return result+'</section>';
}
function refreshFeedbackPanel(){
  // Feedback IO must not replace unrelated controls or close an export menu.
  const panel=document.querySelector('.feedback-analysis');
  if(panel&&state.route==='stats')panel.outerHTML=feedbackPanel();
}
async function loadFeedbackStats(){
  if(!state.actor||state.route!=='stats'||state.statsTab!=='report'||feedbackStats.loading)return;
  const id=++feedbackLoadId,at=epoch,seen=view;
  const source=feedbackStats.source,period=feedbackStats.period;
  feedbackStats.loading=true;feedbackStats.error=false;refreshFeedbackPanel();
  try{
    const d=await api('feedback/categories',{source,period});
    if(id!==feedbackLoadId||at!==epoch||seen!==view||state.route!=='stats'||!state.actor)return;
    if(d.schema!=='hskai_feedback_categories_v1'||!Array.isArray(d.sources))throw Error('invalid_feedback');
    feedbackStats.data=d;
  }catch(error){
    if(id!==feedbackLoadId||at!==epoch||seen!==view||state.route!=='stats'||!state.actor)return;
    feedbackStats.data=null;feedbackStats.error=true;
  }finally{
    if(id===feedbackLoadId&&at===epoch&&seen===view&&state.route==='stats'&&state.actor){
      feedbackStats.loading=false;refreshFeedbackPanel();
    }
  }
}

function statsCategoryNav(){
  const choices=[['overview','statsTabOverview'],['course','statsTabCourse'],['platform','statsTabPlatforms'],['funnel','statsTabConversion'],['money','statsTabFinance'],['sources','statsTabSources'],['report','statsTabReport']];
  const selectedPlatform={overall:t('all'),android:'Android',telegram:'Telegram Mini App',macos:'macOS',windows:'Windows',iphone_pwa:'iPhone PWA'}[state.platform]||state.platform;
  return `<div class="stats-top-row"><div class="subtabs stats-category-tabs" role="tablist" aria-label="${esc(t('stats'))}">${choices.map(([id,label])=>`<button type="button" role="tab" class="subtab ${state.statsTab===id?'active':''}" data-stats-tab="${id}" aria-selected="${state.statsTab===id}" tabindex="${state.statsTab===id?'0':'-1'}">${esc(t(label))}</button>`).join('')}</div><span class="stats-scope-chip">${icon('device')}${esc(selectedPlatform)}</span></div>`;
}

function statsCategorySection(title,fields,note){
  return `<section class="stat-detail stats-category-section"><h2>${esc(t(title))}</h2>${profileFields(fields)}${note?`<p class="source-note">${esc(t(note))}</p>`:''}</section>`;
}

function categorizedStatsView(){
  const data=state.stats;
  if(!data)return statePanel('loading');
  const nav=statsCategoryNav();
  const footer=`<p class="source-note stats-category-footnote">${esc(t('overlap'))}${data.scope?.period_filter_applied===false?' '+esc(t('rolling30')):''}</p><p class="source-note">${esc(t('updated'))}: ${esc(date(data.generated_at))}</p>`;
  if(!data.available)return nav+statePanel('unavailable')+(state.statsTab==='report'?feedbackPanel():'')+footer;
  const m=data.metrics;
  const tab=state.statsTab;
  if(data.platform!=='overall'&&tab!=='platform'&&tab!=='report')
    return nav+statePanel('unavailable', 'statsPlatformChoose')+footer;
  let content='';
  if(tab==='overview'){
    content=`<div class="grid metrics stats-category-metrics">${metric('usersTotal',m.users_total,'users')}${metric('newAccounts',m.new_accounts,'users')}${metric(state.period==='all_time'?'active30':'activeAccounts',m.active_accounts,'chart')}${metric('pending',m.payments_by_status.pending,'wallet')}</div>`;
    content+=statsCategorySection('payments', [['pending',m.payments_by_status.pending],['approved',m.payments_by_status.approved],['rejected',m.payments_by_status.rejected]],'currencyNote');
  }else if(tab==='course'){
    const c=m.course_engagement;
    content=`<div class="grid metrics stats-category-metrics">${metric('engagedAccounts',c.engaged_accounts,'users')}${metric('startedAccounts',c.started_accounts,'book')}${metric('completedAccounts',c.completed_accounts,'check')}</div>`;
    content+=statsCategorySection('courseEngagement',[['engagedAccounts',c.engaged_accounts],['startedAccounts',c.started_accounts],['completedAccounts',c.completed_accounts]],'courseMetricNote');
    if(c.unmatched_events)content+=`<p class="source-note">${esc(t('unmatchedEvents'))}: ${esc(c.unmatched_events)}</p>`;
  }else if(tab==='platform'){
    if(data.platform==='overall'){
      content=`<div class="grid metrics stats-category-metrics">${metric('usersTotal',m.users_total,'users')}${metric('activeAccounts',m.active_accounts,'chart')}</div><p class="source-note">${esc(t('statsPlatformChoose'))}</p>`;
    }else if(data.platform==='android'){
      content=`<div class="grid metrics stats-category-metrics">${metric('installedDevices',m.registry.installed_devices,'device')}${metric('installedUsers',m.registry.installed_users,'users')}${metric('active7',m.active.wau,'chart')}${metric('active30',m.active.mau,'chart')}</div>`;
    }else{
      content=`<div class="grid metrics stats-category-metrics">${metric('active30',m.active_users_30d,'chart')}${metric('firstOpen',m.verified_first_open_30d,'device')}</div>`;
    }
  }else if(tab==='funnel'){
    const r=m.registration_conversion;
    content=`<div class="grid metrics stats-category-metrics">${metric('conversion',r.percent===null?'—':r.percent+'%','target')}${metric('registeredCohort',r.registered_accounts,'users')}${metric('convertedAccounts',r.converted_accounts,'wallet')}</div>`;
    content+=statsCategorySection('registrationConversion',[['registeredCohort',r.registered_accounts],['convertedAccounts',r.converted_accounts],['conversion',r.percent===null?'—':r.percent+'%']],'conversionNote');
  }else if(tab==='money'){
    const ai=m.ai_usage;
    content=`<div class="grid metrics stats-category-metrics">${metric('estimatedCost',ai.estimated_cost_usd+' USD','spark')}${metric('recordedRequests',ai.recorded_requests,'chart')}${metric('tokens',ai.tokens,'chart')}</div>`;
    content+=statsCategorySection('aiSpend',[['estimatedCost',ai.estimated_cost_usd+' USD'],['recordedRequests',ai.recorded_requests],['tokens',ai.tokens]],'aiCostNote');
    content+=`<section class="stat-detail stats-category-section"><h2>${esc(t('approvedAmounts'))}</h2><div class="currency-rows">${m.approved_amounts_by_currency.map(row=>`<div class="currency-row">${esc(row.currency)}<strong>${esc(row.amount)}</strong></div>`).join('')||`<p>${esc(t('empty'))}</p>`}</div><p class="source-note">${esc(t('currencyNote'))}</p></section>`;
  }else if(tab==='sources'){
    content=statePanel('unavailable','statsSourcesUnavailable');
  }else if(tab==='report'){
    content=`<section class="stat-detail stats-category-section"><h2>${esc(t('statsTabReport'))}</h2>${profileFields([['source',data.source||'—'],['platform',data.platform],['period',t(data.period)],['updated',date(data.generated_at)]])}<p class="source-note">${esc(t('statsReportNote'))}</p><div class="statistics-export">${exportMenu('statistics')}</div></section>${feedbackPanel()}`;
  }
  return nav+`<div class="stats-category-content">${content}</div>`+footer;
}

function statsView() {
  if(state.route==='stats')return categorizedStatsView();
  const data=state.stats;if(!data) return statePanel('loading');
  const exports=state.route==='stats'?`<div class="statistics-export">${exportMenu('statistics')}</div>`:'';
  if(!data.available) return exports+statePanel('unavailable')+feedbackPanel();
  let cards='', extra='';const m=data.metrics;
  if(data.platform==='overall') {
    cards=metric('usersTotal',m.users_total,'users')+metric('newAccounts',m.new_accounts,'users')+metric(state.period==='all_time'?'active30':'activeAccounts',m.active_accounts)+metric('pending',m.payments_by_status.pending,'wallet');
    extra=`<h2 class="section-title">${esc(t('approvedAmounts'))}</h2><div class="currency-rows">${m.approved_amounts_by_currency.map(row=>`<div class="currency-row">${esc(row.currency)}<strong>${esc(row.amount)}</strong></div>`).join('')||`<p>${esc(t('empty'))}</p>`}</div><p class="source-note">${esc(t('currencyNote'))}</p>`;
    const ai=m.ai_usage,c=m.course_engagement,r=m.registration_conversion;
    extra+=`<div class="stats-details"><section class="stat-detail"><h2>${esc(t('aiSpend'))}</h2>${profileFields([['estimatedCost',ai.estimated_cost_usd+' USD'],['recordedRequests',ai.recorded_requests],['tokens',ai.tokens]])}<p class="source-note">${esc(t('aiCostNote'))}</p></section><section class="stat-detail"><h2>${esc(t('courseEngagement'))}</h2>${profileFields([['engagedAccounts',c.engaged_accounts],['startedAccounts',c.started_accounts],['completedAccounts',c.completed_accounts]])}<p class="source-note">${esc(t('courseMetricNote'))}${c.unmatched_events?' '+esc(t('unmatchedEvents'))+': '+c.unmatched_events:''}</p></section><section class="stat-detail"><h2>${esc(t('registrationConversion'))}</h2>${profileFields([['conversion',r.percent===null?'—':r.percent+'%'],['registeredCohort',r.registered_accounts],['convertedAccounts',r.converted_accounts]])}<p class="source-note">${esc(t('conversionNote'))}</p></section></div>`;
  } else if(data.platform==='android') cards=metric('installedDevices',m.registry.installed_devices,'device')+metric('installedUsers',m.registry.installed_users,'users')+metric('active7',m.active.wau)+metric('active30',m.active.mau);
  else cards=metric('active30',m.active_users_30d)+metric('firstOpen',m.verified_first_open_30d,'device');
  return `${exports}<div class="grid metrics">${cards}</div>${extra}<p class="source-note">${esc(t('overlap'))}${data.scope?.period_filter_applied===false?' '+esc(t('rolling30')):''}</p><p class="source-note">${esc(t('updated'))}: ${esc(date(data.generated_at))}</p>${feedbackPanel()}`;
}
function cancelStatisticsDownload(){
  const download=statisticsDownload;statisticsDownload=null;
  if(!download)return;
  download.control.abort();clearTimeout(download.timer);
  if(download.url)URL.revokeObjectURL(download.url);
  document.querySelectorAll('[data-export-format],[data-feedback-export],.download-trigger').forEach(button=>{button.disabled=false;button.removeAttribute('aria-busy');});
  if(document.activeElement===document.body&&download.focusTarget?.isConnected)download.focusTarget.focus();
}
async function exportStatistics(format,dataset='statistics'){
  if(!state.actor||state.phase!=='ready'||state.route!=='stats'||!['json','csv'].includes(format)||statisticsDownload||(dataset==='feedback'&&!feedbackStats.data))return;
  const current=view,at=epoch,language=locale,control=new AbortController();
  const download={control,url:null,timer:null};statisticsDownload=download;
  const active=()=>statisticsDownload===download&&current===view&&at===epoch&&language===locale&&!!state.actor;
  closeActionMenus(true);
  download.focusTarget=document.activeElement?.matches('.download-trigger')?document.activeElement:null;
  const buttons=[...document.querySelectorAll('[data-export-format],[data-feedback-export],.download-trigger')];
  buttons.forEach(button=>{button.disabled=true;button.setAttribute('aria-busy','true');});
  const timer=setTimeout(()=>control.abort(),15000),platform=state.platform;
  const source=feedbackStats.source,period=dataset==='feedback'?feedbackStats.period:state.period,feedbackId=feedbackLoadId;
  try{
    const endpoint=dataset==='feedback'?'/api/admin/v1/feedback/categories/export':'/api/admin/v1/statistics/export';
    const body=dataset==='feedback'?{source,period,format}:{platform,period,format};
    const response=await fetch(endpoint,{method:'POST',credentials:'same-origin',cache:'no-store',redirect:'error',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:control.signal});
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
    if(!active()||(dataset==='feedback'&&feedbackId!==feedbackLoadId))return;
    if(!size)throw Error('empty_export');
    download.url=URL.createObjectURL(new Blob(chunks,{type:mime}));
    const link=document.createElement('a');link.href=download.url;
    link.download=dataset==='feedback'?`hskai-feedback-categories-${source}-${period}.${format}`:`hskai-statistics-${platform}-${period}.${format}`;
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
function relativeLastActive(value, clock=Date.now()) {
  if(!value)return '—';
  const time=Date.parse(value);
  if(!Number.isFinite(time))return '—';
  const minutes=Math.max(0,Math.floor((clock-time)/60000));
  if(minutes<1)return t('relativeNow');
  let amount,unit,extra='';
  if(minutes<60){amount=minutes;unit='relativeMinute';}
  else if(minutes<1440){
    amount=Math.floor(minutes/60);unit='relativeHour';
    const remainder=minutes%60;
    if(remainder)extra=' '+remainder+' '+t('relativeMinute');
  }else if(minutes<43200){amount=Math.floor(minutes/1440);unit='relativeDay';}
  else if(minutes<525600){amount=Math.floor(minutes/43200);unit='relativeMonth';}
  else{amount=Math.floor(minutes/525600);unit='relativeYear';}
  return amount+' '+t(unit)+extra+' '+t('relativeAgo');
}
function displayPlan(value){if(!value)return '—';const label=t(value);return label==='—'?String(value):label;}
function pager() { return `<div class="pager">${btn('previous','previous','',state.previous.length===0)}${btn('next','next','',!state.next)}</div>`; }
function userSummary(row){
  const label=esc(row.name||'—'),handle=esc(row.username||'');
  const details=`<span class="person"><span class="mini-avatar" aria-hidden="true">${esc((row.name||'H').trim().charAt(0).toUpperCase())}</span><span class="directory-person"><strong>${label}</strong><small>${handle?handle+' · ':''}#${row.user_id}</small></span></span>`;
  const fields=[['level',row.level],['language',row.language],['lastActive',relativeLastActive(row.last_active_at)],['accessUntil',date(row.access_expires_at||(row.access_state==='EXPIRED'?row.end_date:null))]];
  const info=fields.map(([key,value])=>`<span class="u-mini-field"><small>${esc(t(key))}</small><b>${esc(value||'—')}</b></span>`).join('');
  const access=`<span class="pill">${esc(t(row.access_state))}</span>`;
  return {details,info,access};
}

function usersView(){
  const rows=state.rows.map(row=>{
    const {details,access}=userSummary(row);
    return `<tr class="user-row" tabindex="0" role="button" aria-label="${esc(t('openProfile'))}: ${esc(row.name||'—')}" data-user-row="${row.user_id}"><td><button type="button" class="directory-row-link" data-user-detail="${row.user_id}">${details}</button></td><td>${esc(row.level||'—')}</td><td>${esc(row.language||'—')}</td><td>${access}${row.has_pending_payment?`<small>${esc(t('pending'))}</small>`:''}</td><td>${esc(relativeLastActive(row.last_active_at))}</td><td>${esc(date(row.access_expires_at||(row.access_state==='EXPIRED'?row.end_date:null)))}</td></tr>`;
  }).join('');
  const cards=state.rows.map(row=>{
    const {details,info,access}=userSummary(row);
    return `<button type="button" class="user-card directory-user-card" data-user-detail="${row.user_id}"><span class="user-card-top">${details}${access}</span><span class="user-card-details">${info}</span>${row.has_pending_payment?`<span class="directory-pending">${esc(t('pending'))}</span>`:''}</button>`;
  }).join('');
  const search=`<form id="searchForm" class="data-toolbar user-search-toolbar"><label class="screen-reader" for="userQuery">${esc(t('search'))}</label><input id="userQuery" class="search-input" maxlength="80" value="${esc(state.query)}" placeholder="${esc(t('search'))}" autocomplete="off"><button type="submit" class="btn primary user-search-icon" aria-label="${esc(t('find'))}" title="${esc(t('find'))}">${icon('search')}</button><div class="user-filter-area"><button type="button" class="btn user-filter-icon ${state.segment!=='all'?'is-active':''}" data-user-filter-toggle aria-controls="userFilterPanel" aria-expanded="${userFilterOpen}" aria-label="${esc(t('filters'))}" title="${esc(t('filters'))}">${icon('filter')}${state.segment!=='all'?'<i aria-hidden="true"></i>':''}</button><div id="userFilterPanel" class="user-filter-panel" ${userFilterOpen?'':'hidden'}><div class="user-filter-title"><strong>${esc(t('filters'))}</strong><button type="button" data-user-segment="all">${esc(t('userFilterAll'))}</button></div><div class="user-filter-choices">${USER_SEGMENTS.map(([segment,key])=>`<button type="button" class="user-filter-choice ${state.segment===segment?'active':''}" aria-pressed="${state.segment===segment}" data-user-segment="${segment}">${esc(t(key))}${state.segment===segment?icon('check'):''}</button>`).join('')}</div></div></div></form>`;
  const table=`<div class="table-wrap user-table-wrap"><table class="data-table user-table directory-table"><thead><tr>${['name','level','language','status','lastActive','accessUntil'].map(key=>`<th>${esc(t(key))}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`;
  return search+(state.rows.length?table+`<div class="user-cards">${cards}</div>`:statePanel('empty'))+pager();
}

function paymentsView(){
  const reviewButton=row=>row.status==='pending'?`<button type="button" class="btn small" data-review="${row.payment_id}">${esc(t('review'))}</button>`:'—';
  const head=state.rows.map(row=>`<tr class="payment-row"><td><strong>${esc(row.name||'—')}</strong><small>${esc(t('account'))}: #${esc(row.user_id??'—')} · #${row.payment_id}</small></td><td>${esc(t(row.plan_type))}<small>${esc(row.payment_method||'—')}</small></td><td><strong>${esc(row.amount)} ${esc(row.currency)}</strong></td><td>${esc(row.source||'—')}</td><td><span class="pill">${esc(t(row.status))}</span></td><td>${esc(date(row.submitted_at))}</td><td>${reviewButton(row)}</td></tr>`).join('');
  const cards=state.rows.map(row=>`<article class="payment-card"><div class="payment-card-top"><div><strong>${esc(row.name||'—')}</strong><small>#${row.payment_id} · ${esc(t('account'))}: #${esc(row.user_id??'—')}</small></div><span class="pill">${esc(t(row.status))}</span></div><div class="payment-card-amount">${esc(row.amount)} ${esc(row.currency)}</div><div class="user-card-details"><span class="u-mini-field"><small>${esc(t('plan'))}</small><b>${esc(t(row.plan_type))}</b></span><span class="u-mini-field"><small>${esc(t('method'))}</small><b>${esc(row.payment_method||'—')}</b></span><span class="u-mini-field"><small>${esc(t('source'))}</small><b>${esc(row.source||'—')}</b></span><span class="u-mini-field"><small>${esc(t('submitted'))}</small><b>${esc(date(row.submitted_at))}</b></span></div>${row.status==='pending'?`<button type="button" class="btn primary payment-card-review" data-review="${row.payment_id}">${esc(t('review'))}</button>`:''}</article>`).join('');
  return `<div class="data-toolbar payment-status-filters">${['pending','approved','rejected'].map(status=>`<button class="btn ${state.status===status?'primary':''}" data-status="${status}">${esc(t(status))}</button>`).join('')}</div>${state.rows.length?`<div class="table-wrap payment-table-wrap"><table class="data-table payment-table directory-table"><thead><tr>${['name','plan','amount','source','status','submitted','review'].map(key=>`<th>${esc(t(key))}</th>`).join('')}</tr></thead><tbody>${head}</tbody></table></div><div class="payment-cards">${cards}</div>`:statePanel('empty')}${pager()}`;
}
function managementRow(label,attributes,glyph='settings'){
  return `<button class="management-row" ${attributes}><span class="management-row-icon">${icon(glyph)}</span><strong>${esc(label)}</strong>${icon('chevron')}</button>`;
}

const courseCopy={
uz:{tracks:'HSK 2.0 / 3.0',access:'Кириш ва лимитлар',trial:'Pro синови',experiment:'Сотув A/B',trackTitle:'HSK 3.0 курс',unlock:'Бир марталик очиш тўлови',active:'Фаол',inactive:'Ўчирилган',yes:'Ёқилган',no:'Ўчирилган',enabled:'Курс ҳолати',levels:'Фаол даражалар',price:'Бир марталик нарх',paid:'Тўлов талаб қилинади',free:'Бепул очилади',edit:'Таҳрирлаш',courseAccess:'Курсга кириш режими',courseAccessMode:'Кириш шарти',subscription:'Pro обуна талаб қилинади',freeUntil:'Маълум муддат бепул',until:'Бепул муддат тугайди',limits:'Free ва Trial лимитлари',plan:'Режа',freePlan:'Бепул (FREE)',trialPlan:'Pro синови (TRIAL_ACTIVE)',limitValue:'Миқдор',limitWindow:'Давр',daily:'Кунлик',lifetime:'Бир умр',save:'Сақлаш',note:'0 = функция ёпиқ. 1–10000 = рухсат этилган миқдор. Фақат кунлик ёки бир умр режими.',trialDays:'Муддат (кун)',trialReason:'Ўчириш сабаби',trialState:'Синов ҳолати',experimentNote:'Сотув тажрибаси ҳозирги хавфсиз бошқарув орқали созланади.',trialNote:'Trial AI бюджети ва бошқа қоидалар ўзгартирилмайди.',browse:'Кўриш ва бошқариш',courseStats:'Курс фаолияти',courseStatsHint:'Ҳақиқий статистика «Таҳлиллар → Курс ва фаоллик» бўлимида.',statsOpen:'Статистикани очиш',count:'Қоида',limitSaving:'Сақланаётган ўзгаришлар',trialSaving:'Синов созламаларини сақлаш',unchanged:'Ўзгариш киритилмаган',saved:'Сақланди'},
ru:{tracks:'HSK 2.0 / 3.0',access:'Доступ и лимиты',trial:'Пробный Pro',experiment:'Продажи A/B',trackTitle:'Курс HSK 3.0',unlock:'Разовая разблокировка',active:'Активно',inactive:'Отключено',yes:'Включено',no:'Отключено',enabled:'Состояние курса',levels:'Открытые уровни',price:'Разовая цена',paid:'Платный доступ',free:'Бесплатный доступ',edit:'Изменить',courseAccess:'Режим доступа',courseAccessMode:'Условие доступа',subscription:'Требуется Pro',freeUntil:'Бесплатно до даты',until:'Действует до',limits:'Лимиты Free и Trial',plan:'Тариф',freePlan:'Бесплатный (FREE)',trialPlan:'Пробный Pro (TRIAL_ACTIVE)',limitValue:'Количество',limitWindow:'Период',daily:'В день',lifetime:'За всё время',save:'Сохранить',note:'0 = функция отключена. 1–10000 = разрешённое количество. Только дневной или пожизненный период.',trialDays:'Срок (дни)',trialReason:'Причина отключения',trialState:'Статус пробного периода',experimentNote:'Продажи A/B настраиваются через существующий защищённый редактор.',trialNote:'Бюджет AI и другие правила Trial не изменяются.',browse:'Открыть редактор',courseStats:'Активность курса',courseStatsHint:'Актуальные данные в «Аналитика → Курс и активность».',statsOpen:'Открыть аналитику',count:'Правило',limitSaving:'Сохраняемые изменения',trialSaving:'Сохранить Trial',unchanged:'Нет изменений',saved:'Сохранено'},
tj:{tracks:'HSK 2.0 / 3.0',access:'Дастрасӣ ва маҳдудият',trial:'Санҷиши Pro',experiment:'Фурӯши A/B',trackTitle:'Курси HSK 3.0',unlock:'Кушодани якдафъаина',active:'Фаъол',inactive:'Хомӯш',yes:'Фаъол',no:'Хомӯш',enabled:'Ҳолати курс',levels:'Сатҳҳои фаъол',price:'Нархи якдафъаина',paid:'Бо пардохт',free:'Ройгон',edit:'Тағйир',courseAccess:'Реҷаи дастрасии курс',courseAccessMode:'Шарти дастрасӣ',subscription:'Обунаи Pro лозим',freeUntil:'То муҳлат ройгон',until:'То сана',limits:'Маҳдудияти Free ва Trial',plan:'Нақша',freePlan:'Ройгон (FREE)',trialPlan:'Санҷиши Pro (TRIAL_ACTIVE)',limitValue:'Миқдор',limitWindow:'Давра',daily:'Ҳар рӯз',lifetime:'Барои тамоми умр',save:'Сабт',note:'0 = ғайрифаъол. 1–10000 = миқдори иҷозат. Танҳо ҳаррӯз ё тамоми умр.',trialDays:'Муҳлат (рӯз)',trialReason:'Сабаби хомӯшкунӣ',trialState:'Ҳолати санҷиш',experimentNote:'Фурӯши A/B аз муҳаррири амн идора мешавад.',trialNote:'Буҷаи AI ва қоидаҳои дигари Trial тағйир намеёбанд.',browse:'Кушодани идоракунӣ',courseStats:'Фаъолияти курс',courseStatsHint:'Омори воқеӣ дар «Таҳлилҳо → Курс ва фаъолият».',statsOpen:'Кушодани омор',count:'Қоида',limitSaving:'Тағйироти сабтшаванда',trialSaving:'Сабти Trial',unchanged:'Тағйире нест',saved:'Сабт шуд'}
};
const cx=key=>courseCopy[locale]?.[key]||courseCopy.uz[key]||key;
const courseLimitTitles={'lesson.start':'Дарс бошлаш','ai.text':'AI матн','ai.photo':'AI расм','ai.voice':'AI овоз','speaking.session':'Speaking','practice.*':'Машқлар','practice.placement':'Даража тести','study.quiz':'Тест','study.audio':'Аудио','study.flashcard_translate':'Карточкалар'};
const courseCard=(heading,body)=>`<section class="panel course-panel"><div class="panel-title"><h2>${esc(heading)}</h2></div>${body}</section>`;
const courseMetric=(label,value,note)=>`<div class="metric"><div class="metric-top">${esc(label)}</div><div class="metric-value">${esc(value)}</div><div class="metric-note">${esc(note||'')}</div></div>`;
function renderCourseView(){
  const tabs=[['tracks','tracks'],['access','access'],['trial','trial'],['experiment','experiment']];
  const tabBar=`<div class="subtabs course-subtabs" role="tablist" aria-label="${esc(t('course'))}">${tabs.map(([id,key])=>`<button type="button" role="tab" aria-selected="${state.courseTab===id}" class="subtab ${state.courseTab===id?'active':''}" data-course-tab="${id}">${esc(cx(key))}</button>`).join('')}</div>`;
  if(!courseData)return tabBar+statePanel('loading');
  const h=courseData.hsk30,a=courseData.course_access,limits=courseData.limits;
  let body='';
  if(state.courseTab==='tracks'){
    const shown=(h.live_levels||[]).map(s=>s.toUpperCase()).join(' · ')||'—';
    body=`<div class="grid stat-cards course-stats">${courseMetric(cx('enabled'),cx(h.enabled?'yes':'no'),'HSK 3.0')}${courseMetric(cx('levels'),String(h.live_levels?.length||0),shown)}${courseMetric(cx('price'),String(h.unlock_price_tjs)+' TJS',cx(h.unlock_payment_enabled?'paid':'free'))}</div>
    <div class="v6-two">${courseCard(cx('trackTitle'),`<div class="switchline"><div><strong>${esc(cx('enabled'))}</strong><small>${esc(cx(h.enabled?'yes':'no'))}</small></div><span class="pill ${h.enabled?'green':'gray'}">${esc(cx(h.enabled?'active':'inactive'))}</span></div><div class="course-levels">${(h.available_levels||[]).map(l=>`<span class="v6-check ${h.live_levels.includes(l)?'chosen':''}">${esc(l.toUpperCase())}</span>`).join('')}</div><div class="v6-buttons"><button type="button" class="btn primary" data-action="hsk30Settings">${esc(cx('edit'))}</button></div>`)}
    ${courseCard(cx('unlock'),`<div class="switchline"><div><strong>${esc(cx('paid'))}</strong><small>${esc(cx(h.unlock_payment_enabled?'paid':'free'))}</small></div><span class="pill ${h.unlock_payment_enabled?'amber':'green'}">${esc(cx(h.unlock_payment_enabled?'yes':'no'))}</span></div><div class="course-price">${esc(String(h.unlock_price_tjs))} TJS</div><div class="v6-buttons"><button type="button" class="btn primary" data-action="hsk30Settings">${esc(cx('edit'))}</button></div>`)}</div>
    <div class="course-spacer"></div>${courseCard(cx('courseStats'),`<p class="secondary-note">${esc(cx('courseStatsHint'))}</p><button type="button" class="btn" data-course-stats>${esc(cx('statsOpen'))}</button>`)}`;
  } else if(state.courseTab==='access'){
    const rules=courseLimitDraft?.[courseLimitPlan]||{};
    const options=Object.entries(rules).filter(([,rule])=>Number.isInteger(rule.limit));
    body=`<div class="v6-two">
    ${courseCard(cx('courseAccess'),`<div class="form-field"><label class="form-label">${esc(cx('courseAccessMode'))}</label><div class="course-mode-value">${esc(cx(a.mode==='free_until'?'freeUntil':'subscription'))}</div></div>${a.mode==='free_until'?`<div class="form-field"><label class="form-label">${esc(cx('until'))}</label><strong>${esc(date(a.free_until))}</strong></div>`:''}<div class="v6-buttons"><button class="btn primary" type="button" data-action="courseSettings">${esc(cx('edit'))}</button></div>`)}
    ${courseCard(cx('limits'),`<div class="form-field"><label class="form-label" for="courseLimitPlan">${esc(cx('plan'))}</label><select id="courseLimitPlan" class="input"><option value="FREE" ${courseLimitPlan==='FREE'?'selected':''}>${esc(cx('freePlan'))}</option><option value="TRIAL_ACTIVE" ${courseLimitPlan==='TRIAL_ACTIVE'?'selected':''}>${esc(cx('trialPlan'))}</option></select></div><div class="course-limits-rows">${options.map(([key,rule])=>`<div class="v6-limit-row"><span><strong>${esc(courseLimitTitles[key]||key)}</strong><small>${esc(key)}</small></span><label><span class="screen-reader">${esc(cx('limitValue'))}</span><input class="input" type="number" min="0" max="10000" step="1" required data-course-limit="${esc(key)}" value="${esc(rule.limit)}"></label><label><span class="screen-reader">${esc(cx('limitWindow'))}</span><select class="input" data-course-window="${esc(key)}"><option value="daily" ${rule.window!=='lifetime'?'selected':''}>${esc(cx('daily'))}</option><option value="lifetime" ${rule.window==='lifetime'?'selected':''}>${esc(cx('lifetime'))}</option></select></label></div>`).join('')}</div><p class="form-hint">${esc(cx('note'))}</p><div class="v6-buttons"><button type="button" id="courseLimitSave" class="btn primary" data-action="limitsPrepare" ${courseLimitDirty()?'':'disabled'}>${esc(cx('save'))}</button></div>`)}</div>`;
  } else if(state.courseTab==='trial'){
    const draft=courseTrialDraft||limits.trial;
    body=`<div class="v6-two">
    ${courseCard(cx('trial'),`<div class="switchline"><div><strong>${esc(cx('trialState'))}</strong></div><input id="courseTrialEnabled" type="checkbox" class="switch" aria-label="${esc(cx('trialState'))}" ${draft.enabled?'checked':''}></div><div class="form-field"><label class="form-label" for="courseTrialDays">${esc(cx('trialDays'))}</label><input id="courseTrialDays" class="input" type="number" min="1" max="90" step="1" required value="${esc(draft.days)}"></div><div class="form-field"><label class="form-label" for="courseTrialReason">${esc(cx('trialReason'))}</label><input id="courseTrialReason" class="input" maxlength="200" value="${esc(draft.disabled_reason||'')}"></div><div class="v6-buttons"><button type="button" id="courseTrialSave" data-action="trialPrepare" class="btn primary" ${courseTrialDirty()?'':'disabled'}>${esc(cx('save'))}</button></div>`)}
    ${courseCard(cx('trialState'),`<p class="secondary-note">${esc(cx('trialNote'))}</p><div class="profile-kv"><span class="kv-key">AI budget</span><strong class="kv-value">${esc(limits.trial.ai_budget_usd)} USD</strong><span class="kv-key">Min. account age</span><strong class="kv-value">${esc(limits.trial.min_account_age_hours)} h</strong></div>`)}</div>`;
  } else {
    body=`<div class="v6-two">${courseCard(cx('experiment'),`<p class="secondary-note">${esc(cx('experimentNote'))}</p><button type="button" class="btn primary" data-marketing-kind="sales_experiment">${esc(cx('browse'))}</button>`)}
    ${courseCard(cx('courseStats'),`<p class="secondary-note">${esc(cx('courseStatsHint'))}</p><button type="button" class="btn" data-course-stats>${esc(cx('statsOpen'))}</button>`)}</div>`;
  }
  return `<div class="course-dashboard">${tabBar}<div class="course-content">${body}</div></div>`;
}
function courseLimitDirty(){
  const plan=courseLimitPlan,original=courseData?.limits?.plans?.[plan],draft=courseLimitDraft?.[plan];
  if(!original||!draft)return false;
  return Object.keys(draft).some(key=>draft[key].limit!==original[key]?.limit||(draft[key].window!=='lifetime'?'daily':'lifetime')!==(original[key]?.window==='lifetime'?'lifetime':'daily'));
}
function courseTrialDirty(){
  if(!courseTrialDraft||!courseData?.limits)return false;
  const a=courseData.limits.trial,b=courseTrialDraft;
  return b.enabled!==a.enabled||b.days!==a.days||b.disabled_reason!==a.disabled_reason;
}
function keepCourseEdits(){
  if(state.route!=='course'||!courseData)return;
  if(state.courseTab==='access'){
    for(const input of document.querySelectorAll('[data-course-limit]')){
      const rule=courseLimitDraft?.[courseLimitPlan]?.[input.dataset.courseLimit];
      if(rule)rule.limit=input.value===''?null:Number(input.value);
    }
    for(const input of document.querySelectorAll('[data-course-window]')){
      const rule=courseLimitDraft?.[courseLimitPlan]?.[input.dataset.courseWindow];
      if(rule)rule.window=input.value;
    }
    const b=$('courseLimitSave');if(b)b.disabled=!courseLimitDirty();
  }
  if(state.courseTab==='trial'){
    if(!courseTrialDraft)return;
    if($('courseTrialEnabled'))courseTrialDraft.enabled=$('courseTrialEnabled').checked;
    if($('courseTrialDays'))courseTrialDraft.days=$('courseTrialDays').value===''?null:Number($('courseTrialDays').value);
    if($('courseTrialReason'))courseTrialDraft.disabled_reason=$('courseTrialReason').value;
    const b=$('courseTrialSave');if(b)b.disabled=!courseTrialDirty();
  }
}
async function loadCourseData(){
  const current=++view,at=epoch;
  state.phase='loading';state.error=null;render();
  try {
    const [hsk,access,limit]=await Promise.all([
      api('hsk30/read',{}),api('course-access/read',{}),api('limits/read',{})
    ]);
    if(current!==view||at!==epoch||state.route!=='course'||!state.actor)return;
    courseData={hsk30:hsk.hsk30,course_access:access.course_access,limits:limit.limits,limitsRevision:limit.revision_hash};
    courseLimitDraft={FREE:structuredClone(limit.limits.plans.FREE),TRIAL_ACTIVE:structuredClone(limit.limits.plans.TRIAL_ACTIVE)};
    courseTrialDraft={enabled:limit.limits.trial.enabled,days:limit.limits.trial.days,disabled_reason:limit.limits.trial.disabled_reason||''};
    state.phase='ready';render();
  }catch(error){
    if(current!==view||at!==epoch||state.route!=='course'||!state.actor)return;
    state.phase='ready';state.error='error';render();
  }
}
async function prepareCourseLimits(trial=false){
  keepCourseEdits();
  if(!courseData||!state.actor||signing)return;
  if(!(trial?courseTrialDirty():courseLimitDirty()))return;
  const change=trial?{trial:courseTrialDraft}:{plan:courseLimitPlan,rules:courseLimitDraft[courseLimitPlan]};
  if(!trial){
    for(const rule of Object.values(change.rules)){
      if(!Number.isInteger(rule.limit)||rule.limit<0||rule.limit>10000||!['daily','lifetime'].includes(rule.window)){
        document.querySelector('[data-course-limit]:invalid')?.reportValidity();return;
      }
    }
  }else if(!Number.isInteger(change.trial.days)||change.trial.days<1||change.trial.days>90||change.trial.disabled_reason.length>200){
    $('courseTrialDays')?.reportValidity();return;
  }
  if(!supportsPasskey()){showNotice('passkeyUnsupported');return;}
  const current=drawerId,at=epoch;
  drawer(trial?'trialSaving':'limitSaving',statePanel('loading'));
  try{
    const prepared=await api('limits/prepare',change);
    if(current!==drawerId||at!==epoch||!state.actor)return;
    if(prepared.operation?.action!=='limits.update'||prepared.operation?.target!=='global'
       ||prepared.operation.payload.expected_hash!==courseData.limitsRevision)throw new ApiError('confirmation_changed',409);
    confirmation=Object.freeze(structuredClone(prepared.operation));
    await saveCourseLimits();
  }catch(error){
    if(at!==epoch||!state.actor)return;
    confirmation=null;
    drawer(trial?'trialSaving':'limitSaving',statePanel(errorKey(error)),btn('close','close')+btn('reload','reload','primary'));
  }
}
async function saveCourseLimits(){
  if(confirmation?.action!=='limits.update'||!supportsPasskey()||signing)return;
  const operation=structuredClone(confirmation),current=drawerId,at=epoch,control=new AbortController();
  signing=control;let submitted=false;
  try {
    const options=await api('auth/step-up/options',operation);
    if(current!==drawerId||at!==epoch)return;
    const credential=await navigator.credentials.get({publicKey:publicKey(options.publicKey),signal:control.signal});
    if(current!==drawerId||at!==epoch)return;
    await api('auth/step-up/verify',{step_up_id:options.step_up_id,credential:serialize(credential)});
    if(current!==drawerId||at!==epoch)return;
    submitted=true;
    await api('limits/save',{...operation.payload,step_up_id:options.step_up_id});
    if(current!==drawerId||at!==epoch)return;
    confirmation=null;closeDrawer();await loadCourseData();showNotice('saved');
  }catch(error){
    if(current!==drawerId||at!==epoch)return;
    confirmation=null;
    if(!submitted&&['NotAllowedError','AbortError'].includes(error.name)){closeDrawer();showNotice('passkeyCancelled');return;}
    const rejected=[400,403,404,409].includes(error.status);
    drawer('limitSaving',statePanel(error.status===409?'changed':submitted&&!rejected?'uncertain':errorKey(error)),btn('close','close')+btn('reload','reload','primary'));
  }finally{if(signing===control)signing=null;}
}

function managementView(){
  const group=(label,rows)=>`<section class="management-section"><h2>${esc(t(label))}</h2><div class="management-list">${rows}</div></section>`;
  if(state.route==='course')return renderCourseView();
  if(state.route==='marketing')return `<div class="management-page">${group('marketing',managementRow(t('messages'),'data-action="messageList"','mega')+managementRow(t('adCampaigns'),'data-campaign-list="ad"','mega')+managementRow(t('releaseCampaigns'),'data-campaign-list="release"','bell')+managementRow(t('discountCampaigns'),'data-campaign-list="discount"','wallet')+managementRow(t('desktopPromo'),'data-marketing-kind="desktop_promo"','device')+managementRow(t('courseAds'),'data-marketing-kind="course_ad"','mega')+managementRow(t('partners'),'data-action="partnerList"','users')+managementRow(t('partnerPayouts'),'data-action="payoutList"','wallet'))}</div>`;
  return `<div class="management-page">${group('payments',managementRow(t('subscriptionPrices'),'data-action="priceSettings"','wallet')+managementRow(t('ledger'),'data-action="portfolioHistory"','wallet')+managementRow(t('deliveryQueue'),'data-action="deliveryList"','bell')+managementRow('DC City','data-setting-kind="payment_details" data-bank="dc_city"','credit')+managementRow('Alif','data-setting-kind="payment_details" data-bank="alif"','credit'))}${group('notices',managementRow(t('notices'),'data-action="noticeList"','bell'))}${group('aiModel',managementRow(t('aiModel'),'data-setting-kind="ai_model"','spark'))}${group('requiredChannels',managementRow(t('requiredChannels'),'data-channels-kind="list"','link')+managementRow(t('channelMode'),'data-channels-kind="mode"','shield'))}${group('helpSettings',managementRow(t('helpContact'),'data-setting-kind="help_contact"','link')+managementRow(t('helpVideos'),'data-setting-kind="help_video"','book'))}</div>`;
}
function content() { if(state.error) return statePanel(state.error,'',true);if(state.phase==='loading') return statePanel('loading');return ['course','system','marketing'].includes(state.route)?managementView():['home','stats'].includes(state.route)?statsView():state.route==='users'?usersView():paymentsView(); }
async function load() {
  cancelStatisticsDownload();feedbackLoadId++;feedbackStats.loading=false;feedbackStats.data=null;
  if(!state.actor) return;const current=++view, authEpoch=epoch;state.phase='loading';state.error=null;render();
  if(state.route==='course'){await loadCourseData();return;}
   if(['system','marketing'].includes(state.route)){state.phase='ready';render();return;}
  try {
    const data=await api(['home','stats'].includes(state.route)?'statistics':state.route==='users'?'users/search':'payments/list',
      ['home','stats'].includes(state.route)?{period:state.period,platform:state.platform}:state.route==='users'?{query:state.query,segment:state.segment,before_id:state.cursor,limit:30}:{status:state.status,before_id:state.cursor,limit:30});
    if(current!==view||authEpoch!==epoch) return;
    if(['home','stats'].includes(state.route)) state.stats=data; else {state.rows=data.items;state.next=data.next_before_id;}
    state.phase='ready';render();
    if(state.route==='stats'&&state.statsTab==='report'&&!feedbackStats.data&&!feedbackStats.loading)loadFeedbackStats();
  } catch(error) {if(current!==view||authEpoch!==epoch||!state.actor) return;state.phase='ready';state.error='error';render();}
}
async function boot() {
  if(!navigator.onLine){clearPrivate('offline');return;}
  clearPrivate('loading');const current=epoch;
  try {state.actor=await api('me',null,{method:'GET',publicAuth:true});if(current!==epoch)return;state.phase='ready';
    // Warm dashboard metrics and inbox independently after the biometric gate:
    // a slow unread query must never block the main dashboard from loading.
    // Never block the dashboard or raise a permission prompt during sign-in.
    void restorePushAfterLogin().catch(()=>{});
    await Promise.all([load(),refreshInboxUnread()]);
    if(current===epoch&&state.actor&&location.pathname==='/admin/'&&location.search==='?inbox=1'){
      history.replaceState(null,'','/admin/');
      await inbox(); // Only after current passkey Admin PWA login is verified.
    }}
  catch(error) {
    if(current!==epoch)return;
    if(error.status!==401){state.phase='error';render();return;}
    try {await checkApproval();} catch(_) {state.phase='signin';render();}
    if(state.phase==='signin')await tryAutomaticPasskeyLogin();
  }
}
async function lockAndRequirePasskey() {
  // Every fresh load and foreground resume must pass a NEW WebAuthn assertion.
  // Revocation happens server-side, including for a still-valid cookie; never
  // rely on a client-only lock in front of a usable admin session.
  if(freshLoginInProgress)return;
  freshLoginInProgress=true;
  resumeAuthenticationRequired=false;
  automaticLoginAttempted=false;
  clearPrivate('loading');
  try {
    if(!navigator.onLine){clearPrivate('offline');return;}
    await api('auth/logout',{}, {publicAuth:true});
    if(!document.hidden)await boot();
  }catch(error){
    if(error.message!=='stale')clearPrivate(navigator.onLine?'error':'offline');
  }finally{
    freshLoginInProgress=false;
    if(resumeAuthenticationRequired&&!document.hidden&&!biometricPromptInProgress){
      lockAndRequirePasskey();
    }
  }
}
async function tryAutomaticPasskeyLogin() {
  // Try the modal ceremony once per foreground visit. Safari/WebKit can reject
  // an invocation without user activation; the existing manual button remains
  // the fallback. Never treat a rejected or cancelled ceremony as a login.
  if(automaticLoginAttempted||automaticLoginInProgress||document.hidden||
     !navigator.onLine||!supportsPasskey())return;
  automaticLoginAttempted=true;
  automaticLoginInProgress=true;
  state.phase='loading';state.error=null;render();
  try {await login();}
  catch(error){
    if(error.message==='stale')return;
    state.phase='signin';state.error=null;render();
  }finally{automaticLoginInProgress=false;}
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
  const loginEpoch=epoch, control=new AbortController();
  biometricAbort=control;
  biometricPromptInProgress=true;
  let credential;
  try {
    credential=await navigator.credentials.get({publicKey:publicKey(options.publicKey),signal:control.signal});
  }finally{
    biometricPromptInProgress=false;
    if(biometricAbort===control)biometricAbort=null;
  }
  if(loginEpoch!==epoch)throw new ApiError('stale',0);
  await api('auth/passkey/login/verify',{credential:serialize(credential)},{publicAuth:true});await boot();
}
async function checkApproval() {
  if(approvalChecking)return;
  approvalChecking=true;stopApprovalWatch();
  try {
    const data=await api('auth/telegram/status',null,{method:'GET',publicAuth:true});
    if(!['pending','approved'].includes(data.status)){
      state.approval=null;state.phase='signin';state.error='authFailed';render();
      throw new Error('approval_expired');
    }
    state.approval=data;state.phase=data.status==='approved'?'enroll':'approval';render();
  } finally {approvalChecking=false;watchApproval();}
}
async function enroll() {
  if(!supportsPasskey()){state.error='passkeyUnsupported';render();return;}
  if(!state.enrollment){await api('auth/telegram/complete',{request_id:state.approval.request_id},{publicAuth:true});state.enrollment=true;}
  const options=state.enrollmentOptions || await api('auth/passkey/register/options',{}, {publicAuth:true});
  state.enrollmentOptions=options;
  const credential=await navigator.credentials.create({publicKey:publicKey(options.publicKey,true)});
  await api('auth/passkey/register/verify',{credential:serialize(credential)},{publicAuth:true});state.enrollment=false;state.enrollmentOptions=null;state.phase='signin';state.error=null;render();
}
function closeDrawer() {clearNotice();managementPreparing=false;preparingEditor=null;drawerBack=null;closeActionMenus();closeInboxAttachment();releaseManagementMediaPreview();managementDraft=null;managementReview=null;feedbackUserId=null;revokeTarget=null;drawerId++;signing?.abort();signing=null;confirmation=null;receiptLoaded=false;reviewId=null;$('dialogs').innerHTML='';$('root').inert=false;if(returnFocus?.isConnected)returnFocus.focus();returnFocus=null;}
function drawer(title,body,foot='',className='') {
  if(!$('overlay'))returnFocus=document.activeElement;
  $('dialogs').innerHTML=`<div class="canvas-overlay show" id="overlay"><section class="drawer ${className}" role="dialog" aria-modal="true" aria-labelledby="drawerTitle"><div class="drawer-top"><h2 id="drawerTitle">${esc(t(title))}</h2><button class="drawer-close" data-action="close" aria-label="${esc(t('close'))}">×</button></div><div class="drawer-content" id="drawerContent">${body}</div><div class="drawer-foot" id="drawerFoot">${foot||btn('close','close')}</div></section></div>`;
  $('root').inert=true;document.querySelector('.drawer-close')?.focus();
  updateManagementAction();
}
function lockEditor(){
  const panel=document.querySelector('.drawer'),fields=[...document.querySelectorAll('#drawerContent input,#drawerContent select,#drawerContent textarea,#drawerContent button,#drawerFoot button')].map(input=>[input,input.disabled]);
  if(panel)panel.setAttribute('aria-busy','true');
  fields.forEach(([input])=>input.disabled=true);
  return ()=>{fields.forEach(([input,disabled])=>{if(input.isConnected)input.disabled=disabled;});if(panel?.isConnected)panel.removeAttribute('aria-busy');};
}
async function singleEditorAction(task){
  if(managementPreparing||signing||!state.actor)return;
  if(!supportsPasskey()){showNotice('passkeyUnsupported');return;}
  const restore=lockEditor(),token={};preparingEditor=token;managementPreparing=true;
  try{await task();}finally{restore();if(preparingEditor===token){managementPreparing=false;preparingEditor=null;}}
}
function updateManagementAction(){
  const button=document.querySelector('[data-action="managementPrepare"]'),d=managementDraft;
  if(!button||!d)return;
  let label='saveChanges',danger=false;
  if(d.type==='campaign'){label=['ad_send','release_create'].includes(d.kind)?'sendMessage':d.kind==='discount_create'?'createItem':'saveChanges';}
  else if(d.type==='user'){label=userOperationLabels[d.userOperation];danger=d.userOperation==='delete';}
  else if(d.type==='message')label=!d.userId&&$('messageKind')?.value==='test'?'sendTestMessage':'sendMessage';
  else if(d.type==='message_control')label=d.controlOperation==='resume'?'messageResume':'messageStop';
  else if(d.type==='payout')label=payoutOperationLabels[$('payoutOperation')?.value]||'saveChanges';
  else if(d.type==='partner')label={approve:'acceptPartner',reject:'rejectPartner',block:'partnerBlock',unblock:'partnerUnblock'}[$('partnerOperation')?.value]||'saveChanges';
  else if(d.type==='delivery')label='recordResult';
  else if(d.type==='portfolio')label='addLedgerEntry';
  else if(d.type==='payment_qr')label='replaceMedia';
  else if(d.type==='channel'){label=d.kind==='add'?'addItem':$('channelOperation')?.value==='delete'?'deleteItem':'saveChanges';danger=label==='deleteItem';}
  else if(d.type==='marketing'){label=d.kind==='campaign_draft'?'createCampaign':d.kind==='course_ad_create'?'createItem':d.kind==='course_ad'?({delete:'deleteItem',replace_image:'replaceMedia',replace_video:'replaceMedia'}[$('adOperation')?.value]||'saveChanges'):'saveChanges';danger=label==='deleteItem';}
  button.textContent=t(label);button.classList.toggle('danger',danger);button.classList.toggle('primary',!danger);
}
function managementCurrentUnchanged(d,result,payload){
  let before=d.current;
  if(['payout','payout_completion'].includes(d.type))return result.operation.payload.expected_hash===d.payoutRevision;
  if(d.type==='price')before=d.prices.find(row=>row.method===payload.method&&row.plan===payload.plan);
  if(d.type==='marketing')before=d.kind==='course_ad'?d.ad:d.data?.[d.kind];
  if(d.type==='notice')before=d.template;
  if(d.type==='channel')before=d.kind==='mode'?{enabled:d.data.enabled}:d.current;
  if(d.type==='setting'){
    const s=d.data.settings,c=payload.change;
    before=d.kind==='payment_details'?{kind:d.kind,bank:d.bank,value:s.payment_details[d.bank]}:
      d.kind==='help_video'?{kind:d.kind,...s.help_videos.find(row=>row.key===c.key&&row.lang===c.lang)}:{kind:d.kind,...s[d.kind]};
  }
  if(!before)return true;
  if(before.revision_hash)return before.revision_hash===result.operation.payload.expected_hash;
  return Object.entries(before).filter(([key])=>Object.hasOwn(result.current||{},key)).every(([key,value])=>JSON.stringify(value)===JSON.stringify(result.current[key]));
}
function profileFields(fields) {
  return `<dl class="review-summary">${fields.map(([key,value])=>`<dt>${esc(t(key))}</dt><dd>${esc(value??'—')}</dd>`).join('')}</dl>`;
}
function profilePayments(data,userId) {
  return `${data.items.map(row=>`<article class="feedback-item"><strong>#${row.payment_id} · ${esc(row.amount)} ${esc(row.currency)}</strong><p>${esc(displayPlan(row.plan_type))} · ${esc(t(row.status))} · ${esc(row.payment_method||'—')}</p><small>${esc(row.source)} · ${esc(date(row.reviewed_at||row.submitted_at))}</small></article>`).join('')||`<p class="source-note">${esc(t('empty'))}</p>`}${data.next_before_id?`<button class="btn" data-profile-payments="${userId}" data-before="${data.next_before_id}">${esc(t('next'))}</button>`:''}`;
}
async function userProfile(userId) {
  closeDrawer();const current=drawerId;drawer('userProfile',statePanel('loading'));
  try {
    const data=await api('users/detail',{user_id:userId});
    if(current!==drawerId||!state.actor)return;
    const u=data.user,c=data.course,r=data.referral,blocked=String(data.user.status||'').trim().toLowerCase()==='blocked';
    const section=(key,body)=>`<section class="profile-section"><h3>${esc(t(key))}</h3>${body}</section>`;
    drawer('userProfile',`<div class="profile-heading"><h3>${esc(u.name||'—')}</h3><p>#${u.user_id} · ${esc(u.username||'—')}</p><span class="pill">${esc(t(u.access_state))}</span></div>`+
      profileFields([['language',u.language],['level',u.level],['created',date(u.created_at)],['lastActive',relativeLastActive(u.last_active_at)],['userSelectedPlan',displayPlan(u.selected_plan_type)],['userSelectedMethod',u.selected_payment_method||'—'],['accessUntil',date(u.access_expires_at)]])+
      section('course',(c.progress?profileFields([['level',c.progress.level],['completedLessons',c.progress.completed_lessons],['lastLesson',date(c.progress.last_completed_at)]]):`<p class="source-note">${esc(t('empty'))}</p>`)+c.tracks.map(row=>`<p class="source-note">${esc(row.track==='hsk30'?'HSK 3.0':'HSK 2.0')} · ${esc(row.level)} · ${esc(t('completedLessons'))}: ${row.completed_lessons}${row.unlocked_at?' · '+esc(t('unlocked'))+' '+esc(date(row.unlocked_at)):''}</p>`).join(''))+
      section('referrals',profileFields([['invitedTotal',r.invited_total],['invitedActive',r.invited_active],['discountQualified',r.discount_qualified]]))+
      section('devices',data.devices.map(row=>`<article class="feedback-item"><strong>${esc(row.platform)}</strong>${profileFields([['linkedTotal',row.linked+' / '+row.total],['lastContact',date(row.last_contact_at)]])}</article>`).join('')||`<p class="source-note">${esc(t('empty'))}</p>`)+
      (data.miniapp_presence.length?section('miniappOpens',data.miniapp_presence.map(row=>`<p class="source-note">${esc(row.platform)} · ${esc(date(row.last_opened_at))}</p>`).join('')):'')+
      section('feedback',profileFields([['botFeedback',data.feedback_counts.bot],['releaseFeedback',data.feedback_counts.release]])+`<button class="btn" data-user-feedback="${userId}">${esc(t('openFeedback'))}</button>`)+
      section('paymentHistory',`<div id="profilePayments">${profilePayments(data.payments,userId)}</div>`)+
      section('userActions',`<div class="profile-access-editor">
        <h4>${esc(t('grantAccess'))}</h4>
        <label for="accessDays">${esc(t('durationDays'))}</label>
        <input class="input" id="accessDays" type="number" min="1" max="365" value="30" step="1" required>
        <div class="profile-day-presets">${[10,30,90].map(days=>`<button type="button" class="profile-day-preset ${days===30?'selected':''}" data-user-days="${days}">${days} ${esc(t('relativeDay'))}</button>`).join('')}</div>
        <p class="source-note">${esc(t('manualGrantHint'))}</p>
        <button type="button" class="btn primary profile-main-action" data-prepare-access="${userId}" ${blocked?'disabled':''}>${esc(t('grantAccess'))}</button>
      </div>${userId===state.actor.user_id?'':`<button type="button" class="btn profile-block-action" data-user-management="${userId}" data-user-operation="${blocked?'unblock':'block'}">${icon('shield')}${esc(t(blocked?'unblockAccount':'blockAccount'))}</button>
      <details class="profile-more-actions"><summary>${esc(t('userMoreActions'))}</summary>
      <div class="profile-extra-buttons">
        <button type="button" data-message-user="${userId}">${icon('send')}${esc(t('directMessage'))}</button>
        <button type="button" data-user-discount="${userId}">${icon('gift')}${esc(t('userDiscount'))}</button>
        <button type="button" class="profile-delete-action" data-user-management="${userId}" data-user-operation="delete">${icon('delete')}${esc(t('deleteAccount'))}</button>
      </div></details>`}`)+`<p class="source-note">${esc(t('updated'))}: ${esc(date(data.generated_at))}</p>`, 
      '', 'user-profile-drawer');
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
    btn('cancel','close')+`<button class="btn primary" data-prepare-access="${userId}">${esc(t('grantAccess'))}</button>`);
}
async function prepareAccess(userId){
  if(!$('accessDays')?.reportValidity())return;
  await singleEditorAction(()=>prepareAccessCommand(userId));
}
async function prepareAccessCommand(userId){
  const input=$('accessDays');if(!input?.reportValidity())return;
  const days=Number(input.value);if(!Number.isInteger(days)||days<1||days>365)return;
  const current=drawerId,at=epoch;$('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=true);
  try{
    const operation=await api('users/prepare-access',{user_id:userId,duration_days:days});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    confirmation=Object.freeze(structuredClone(operation));
    await executeAccess();
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
    if(!submitted&&['NotAllowedError','AbortError'].includes(error.name)){showNotice('passkeyCancelled');return;}
    const rejected=[400,403,404,409].includes(error.status);
    drawer('grantAccess',statePanel(error.status===409?'changed':submitted&&!rejected?'uncertain':errorKey(error)),btn('close','close')+`<button class="btn" data-user-detail="${operation.payload.user_id}">${esc(t('openProfile'))}</button>`);
    if(submitted)await load();
  }finally{if(signing===control)signing=null;}
}

const settingLabels={payment_details:'paymentDetails',ai_model:'aiModel',help_contact:'helpContact',help_video:'helpVideos'};
const helpVideoLabels={course_hsk:'course',qa_mode:'questionAnswer',voice_translator:'voiceTranslator',subscription:'subscriptionHelp'};
const userOperationLabels={block:'blockAccount',unblock:'unblockAccount',delete:'deleteAccount'};
function userManagementEditor(userId,operation){
  if(!Number.isSafeInteger(userId)||userId<1||!Object.hasOwn(userOperationLabels,operation))return;
  closeDrawer();managementDraft={type:'user',userId,userOperation:operation};
  const confirmation=operation==='delete'?`<p class="alert">${esc(t('deleteAccountHint'))}</p><div class="form-field"><label for="manageConfirm">${esc(t('confirmAccountId'))}</label><input class="input" id="manageConfirm" inputmode="numeric" pattern="${userId}" maxlength="10" required autocomplete="off"></div>`:'';
  drawer(userOperationLabels[operation],`<form id="managementForm">${profileFields([['account',userId],['operation',t(userOperationLabels[operation])]])}${confirmation}</form>`,btn('cancel','close')+btn('saveChanges','managementPrepare','primary'));
}
const marketingLabels={sales_experiment:'salesExperiment',desktop_promo:'desktopPromo',course_ad:'courseAds'};
const courseAdTypeLabels={odiy:'adTypeStandard',hamkorlik:'adTypePartner',bot:'adTypeBot',dars_yakuni:'adTypeLessonEnd'};
const salesModes={off:'salesOff',shadow:'salesShadow',ab:'salesAB',treatment:'salesTreatment'};
const promoLabels={home_prompt:'promoHome',lesson_end_promo:'promoLesson',ad_promo:'promoAd',macos:'macOS',windows:'Windows',android:'Android',ios:'iOS'};
function managementNamespace(type){return type==='campaign'?'campaigns':['message','message_control'].includes(type)?'messages':type==='delivery'?'payment-deliveries':type==='payout'?'partner-payouts':type==='partner'?'partners':type==='notice'?'notifications':type==='portfolio'?'portfolio':type==='channel'?'channels':type==='user'?'users':type==='price'?'subscription-prices':type==='payment_qr'?'payment-qr':type==='marketing'?'marketing':'settings';}
function managementEndpoint(type,phase){if(type==='payout_completion')return 'partner-payouts/'+(phase==='prepare'?'prepare-completion':'complete');return type==='message_control'?'messages/'+(phase==='prepare'?'prepare-control':'control'):type==='user'?'users/'+(phase==='prepare'?'prepare-management':'manage'):managementNamespace(type)+'/'+phase;}
function managementAction(type,operation){return type==='campaign'?'marketing.update':type==='message'?'broadcast.send':type==='message_control'?'broadcast.control':type==='delivery'?'payments.delivery_reconcile':['payout','payout_completion'].includes(type)?'partners.payout':type==='partner'?'partners.update':type==='notice'?'notifications.update':type==='portfolio'?'portfolio.add':type==='channel'?'channels.update':type==='user'?(operation==='delete'?'users.delete':'users.block'):type==='price'?'subscription.prices':type==='payment_qr'?'subscription.qr_media':type==='marketing'?'marketing.update':'settings.update';}
const messageKindLabels={direct:'directMessage',broadcast:'broadcastMessage',test:'testMessage'};
const messageJobLabels={ready:'messageReady',running:'messageRunning',complete:'messageComplete',closed:'messageClosed'};
const messageCountLabels={pending:'messagePending',attempting:'messageAttempting',attempted:'messageAttempted',uncertain:'messageUncertain',skipped:'messageSkipped',removed:'messageRemoved'};
async function messageList(before=null){
  closeDrawer();const current=drawerId,at=epoch;drawer('messages',statePanel('loading'));
  try{
    const data=await api('messages/read',before?{before_id:before}:{});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    const rows=data.items.map(row=>managementRow(t(messageKindLabels[row.kind])+' · '+row.audience_count+' · '+t(messageJobLabels[row.status]),`data-message-job="${esc(row.job_id)}"`,'mega')).join('');
    drawer('messages',(rows?`<div class="management-list">${rows}</div>`:statePanel('empty'))+(data.next_before_id?`<button class="btn" data-message-next="${esc(data.next_before_id)}">${esc(t('next'))}</button>`:''),btn('close','close')+btn('newMessage','messageEditor','primary'));
  }catch(error){if(current===drawerId&&at===epoch&&state.actor)drawer('messages',statePanel(errorKey(error)),btn('close','close')+btn('readCurrent','messageList'));}
}
async function messageJob(id){
  closeDrawer();const current=drawerId,at=epoch;drawer('messages',statePanel('loading'));
  try{
    const data=await api('messages/read',{job_id:id});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    const job=data.job;
    const refresh=`<button class="btn" data-message-job="${esc(id)}">${esc(t('readCurrent'))}</button>`;
    const pending=job.counts.pending>0;
    const run=pending&&job.status==='ready'&&job.session_current?`<button class="btn primary" data-message-run="${esc(id)}">${esc(t('messageNextBatch'))}</button>`:pending&&job.can_control?`<button class="btn primary" data-message-control="resume" data-job-id="${esc(id)}">${esc(t('messageResume'))}</button>`:'';
    const stop=job.can_stop?actionMenu('messageControlMenu',`<button role="menuitem" data-message-stop="${esc(id)}">${esc(t('messageStop'))}</button>`):'';
    drawer('messages',`<p class="source-note">${esc(t('messageAttemptHint'))}</p>${managementFields(job,'message')}${stop}`,refresh+run);
  }catch(error){if(current===drawerId&&at===epoch&&state.actor)drawer('messages',statePanel(errorKey(error)),btn('close','close')+btn('readCurrent','messageList'));}
}
async function runMessage(id){
  const current=drawerId,at=epoch;$('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=true);
  try{await api('messages/run',{job_id:id});}catch(error){if(current===drawerId&&at===epoch&&state.actor)showNotice(errorKey(error));}
  if(current===drawerId&&at===epoch&&state.actor)await messageJob(id);
}
async function confirmMessageStop(id){await stopMessage(id);}
async function stopMessage(id){
  const current=drawerId,at=epoch;$('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=true);
  try{await api('messages/stop',{job_id:id});}catch(error){if(current===drawerId&&at===epoch&&state.actor)showNotice(errorKey(error));}
  if(current===drawerId&&at===epoch&&state.actor)await messageJob(id);
}
function messageControlEditor(id,operation){
  if(!['resume','close'].includes(operation))return;
  closeDrawer();managementDraft={type:'message_control',jobId:id,controlOperation:operation};
  drawer(operation==='resume'?'messageResume':'messageStop',`<form id="managementForm"><p class="source-note">${esc(t('messageControlHint'))}</p></form>`,btn('cancel','close')+btn('saveChanges','managementPrepare','primary'));
}
const messageFilterConfig={
  status:['status',[['free','FREE'],['trial','messageTrial'],['active','accountActive'],['expired','messageExpired']]],
  track:['messageTrack',[['hsk20','HSK 2.0'],['hsk30','HSK 3.0']]],
  level:['level',[['beginner','messageBeginner'],...['hsk1','hsk2','hsk3','hsk4','nhsk1','nhsk2','nhsk3'].map(value=>[value,(value.startsWith('nhsk')?'HSK 3.0 · ':'HSK 2.0 · ')+value.at(-1)])]],
  mode:['messageMode',[['qa','questionAnswer'],['course','course']]],
  payment_status:['messagePaymentStatus',[['none','messageNoPayment'],['pending','pending'],['approved','approved'],['rejected','rejected']]],
  payment_method:['method',[['visa','Visa'],['alipay','Alipay'],['wechat','WeChat']]],
  plan:['plan',[['10_days','10_days'],['1_month','1_month'],['3_months','3_months']]],
  discount:['discount',[['eligible','messageDiscountEligible'],['used','messageDiscountUsed'],['none','messageNoDiscount']]],
  course_promo:['messagePromo',[['sent','messagePromoSent'],['not_sent','messagePromoNotSent']]],
  activity:['messageActivity',[['active_7d','messageActive7d'],['inactive_7d','messageInactive7d'],['new_7d','messageNew7d']]]
};
function messageEditor(userId=null){
  closeDrawer();managementDraft={type:'message',userId,textLanguage:locale,texts:{uz:'',ru:'',tj:''}};
  const select=(id,label,options)=>`<div class="form-field"><label for="${id}">${esc(t(label))}</label><select class="input" id="${id}">${options.map(([value,text])=>`<option value="${value}">${esc(t(text))}</option>`).join('')}</select></div>`;
  let body=userId?profileFields([['account',userId]]):select('messageKind','operation',[['broadcast','broadcastMessage'],['test','testMessage']]);
  body+=`<p class="source-note">${esc(t(userId?'directMessageHint':'messageEditorHint'))}</p>`;
  if(!userId)body+=select('messageLanguage','language',[['uz','UZ'],['ru','RU'],['tj','TJ']]);
  body+=`<div class="form-field"><label for="messageText">${esc(t('noticeText'))}</label><textarea class="input setting-value" id="messageText" maxlength="3500" minlength="2" required></textarea></div>`;
  if(!userId)body+=`<details class="profile-section notice-languages" id="messageFilters"><summary>${esc(t('filters'))}</summary><fieldset class="form-field"><legend>${esc(t('language'))}</legend>${['uz','ru','tj'].map(lang=>`<label class="management-check"><input type="checkbox" data-message-language="${lang}">${lang.toUpperCase()}</label>`).join('')}</fieldset>${Object.entries(messageFilterConfig).map(([key,[label,options]])=>select('messageFilter-'+key,label,[['','all'],...options])).join('')}</details>`;
  body+='<p id="messageValidation" class="alert" role="alert" hidden></p>';
  drawer(userId?'directMessage':'newMessage',`<form id="managementForm">${body}</form>`,btn('cancel','close')+btn('saveChanges','managementPrepare','primary'));
  if(!userId)$('messageLanguage').value=locale;
}
function updateMessageLanguage(){
  const draft=managementDraft,next=$('messageLanguage')?.value;
  if(draft?.type!=='message'||!['uz','ru','tj'].includes(next))return;
  draft.texts[draft.textLanguage]=$('messageText').value;draft.textLanguage=next;$('messageText').value=draft.texts[next];
}
const deliveryStatusLabels={pending:'pending',attempting:'deliveryAttempting',attempted:'deliveryAttempted',uncertain:'deliveryUncertain'};
const deliveryResolutionLabels={observed:'deliveryObserved',no_retry:'deliveryNoRetry'};
async function deliveryEditor(id=null,before=null){
  closeDrawer();const current=drawerId,at=epoch;drawer('deliveryQueue',statePanel('loading'));
  try{
    const data=await api('payment-deliveries/read',id?{review_id:id}:before?{before_id:before}:{});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    if(!id){
      const rows=data.items.map(row=>managementRow(`#${row.payment_id} · ${t(deliveryStatusLabels[row.delivery_status])}`,`data-delivery-id="${esc(row.review_id)}"`,'bell')).join('');
      drawer('deliveryQueue',(rows?`<div class="management-list">${rows}</div>`:statePanel('empty'))+(data.next_before_id?`<button class="btn" data-delivery-next="${esc(data.next_before_id)}">${esc(t('next'))}</button>`:''),btn('close','close'));return;
    }
    const row=data.delivery;managementDraft={type:'delivery',deliveryId:id,current:row};
    const form=row.eligible&&!row.resolution?`<div class="form-field"><label for="deliveryResolution">${esc(t('operation'))}</label><select class="input" id="deliveryResolution">${Object.entries(deliveryResolutionLabels).map(([value,label])=>`<option value="${value}">${esc(t(label))}</option>`).join('')}</select></div><div class="form-field"><label for="deliveryReason">${esc(t('deliveryReason'))}</label><textarea class="input setting-value" id="deliveryReason" minlength="5" maxlength="300" required></textarea></div>`:'';
    drawer('deliveryQueue',`<p class="source-note">${esc(t('deliveryReconcileHint'))}</p><form id="managementForm">${managementFields(row,'delivery')}${form}</form>`,btn('close','close')+(form?btn('saveChanges','managementPrepare','primary'):''));
  }catch(error){if(current===drawerId&&at===epoch&&state.actor)drawer('deliveryQueue',statePanel(errorKey(error)),btn('close','close')+btn('readCurrent','deliveryList'));}
}
const payoutStatusLabels={pending:'pending',deadline_set:'payoutDeadlineSet',processing:'payoutReserved',paid:'payoutPaid',rejected:'rejected'};
const payoutOperationLabels={deadline:'payoutDeadline',reject:'reject',claim:'payoutClaim',release:'payoutRelease',complete:'payoutComplete'};
async function payoutEditor(id=null,before=null){
  closeDrawer();const current=drawerId,at=epoch;drawer('partnerPayouts',statePanel('loading'));
  try{
    const data=await api('partner-payouts/read',id?{payout_id:id}:before?{before_id:before}:{});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    if(!id){
      const rows=data.items.map(row=>managementRow(`#${row.id} · ${row.local_amount} ${row.local_currency} · ${t(payoutStatusLabels[row.status])}`,`data-payout-id="${Number(row.id)}"`,'wallet')).join('');
      drawer('partnerPayouts',(rows?`<div class="management-list">${rows}</div>`:statePanel('empty'))+(data.next_before_id?`<button class="btn" data-payout-next="${data.next_before_id}">${esc(t('next'))}</button>`:''),btn('close','close'));return;
    }
    const row=data.payout,operations=(row.owned_reservation?['complete',...row.operations]:row.operations).filter(op=>Object.hasOwn(payoutOperationLabels,op));
    managementDraft={type:'payout',payoutId:id,payoutRevision:row.revision_hash};
    const selection=operations.length?`<div class="form-field"><label for="payoutOperation">${esc(t('operation'))}</label><select class="input" id="payoutOperation">${operations.map(op=>`<option value="${op}">${esc(t(payoutOperationLabels[op]))}</option>`).join('')}</select></div><div class="form-field" id="payoutDaysField" ${operations[0]==='deadline'?'':'hidden'}><label for="payoutDays">${esc(t('durationDays'))}</label><select class="input" id="payoutDays">${[1,3,7].map(days=>`<option>${days}</option>`).join('')}</select></div>`:'';
    drawer('partnerPayouts',`<form id="managementForm"><p class="source-note">${esc(t('payoutReserveHint'))}</p>${managementFields(row,'payout')}${selection}${row.owned_reservation?`<div class="form-field" id="payoutProofField"><label for="payoutProofFile">${esc(t('payoutProofFile'))}</label><input class="input" id="payoutProofFile" type="file" accept="image/jpeg,image/png,image/webp" required><p class="source-note">${esc(t('payoutProofUploadHint'))}</p><div id="payoutProofPreview" aria-live="polite"></div></div>`:''}</form>`,btn('close','close')+(operations.length?btn('saveChanges','managementPrepare','primary',row.owned_reservation):''));
  }catch(error){if(current===drawerId&&at===epoch&&state.actor)drawer('partnerPayouts',statePanel(errorKey(error)),btn('close','close')+btn('readCurrent','payoutList'));}
}
async function stagePayoutProof(file){
  const draft=managementDraft,current=drawerId,at=epoch;
  if(draft?.type!=='payout'||!$('payoutProofPreview'))return;
  draft.proofId=null;draft.proofLoaded=false;
  const confirm=document.querySelector('[data-action=managementPrepare]');if(confirm)confirm.disabled=true;
  $('payoutProofPreview').textContent=t('loading');
  draft.uploadVersion=(draft.uploadVersion||0)+1;const version=draft.uploadVersion;
  if(!file||file.size>2*1024*1024||!['image/jpeg','image/png','image/webp'].includes(file.type)){$('payoutProofPreview').textContent=t('payoutProofInvalid');return;}
  try{
    const staged=await api('partner-payouts/'+draft.payoutId+'/proof',null,{rawBody:file});
    if(current!==drawerId||at!==epoch||draft!==managementDraft||version!==draft.uploadVersion)return;
    draft.proofId=staged.proof_id;
    const image=new Image();image.className='inbox-attachment-image';image.alt=t('payoutProofFile');
    image.addEventListener('load',()=>{
      if(current!==drawerId||at!==epoch||draft!==managementDraft||version!==draft.uploadVersion)return;
      draft.proofLoaded=image.naturalWidth>0;
      if(confirm)confirm.disabled=managementPreparing||!!signing||$('payoutOperation')?.value==='complete'&&!draft.proofLoaded;
    },{once:true});
    image.addEventListener('error',()=>{if(current===drawerId&&at===epoch&&version===draft.uploadVersion)$('payoutProofPreview').textContent=t('error');},{once:true});
    image.src='/api/admin/v1/payout-proofs/'+encodeURIComponent(staged.proof_id);
    const hint=document.createElement('p');hint.className='source-note';hint.textContent=t('payoutProofReviewHint');
    $('payoutProofPreview').replaceChildren(image,hint);
  }catch(error){if(current===drawerId&&at===epoch&&draft===managementDraft&&version===draft.uploadVersion){$('payoutProofPreview').textContent=t('payoutProofInvalid');$('payoutProofFile').value='';}}
}
const partnerStatusLabels={pending:'pending',active:'accountActive',blocked:'BLOCKED',rejected:'rejected'};
const partnerOperationLabels={approve:'approve',reject:'reject',block:'partnerBlock',unblock:'partnerUnblock'};
async function partnerEditor(id=null,before=null){
  closeDrawer();const current=drawerId,at=epoch;drawer('partners',statePanel('loading'));
  try{
    const data=await api('partners/read',id?{partner_id:id}:before?{before_id:before}:{});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    if(!id){
      const rows=data.items.map(row=>managementRow(`#${row.id} · ${row.contact_username} · ${t(partnerStatusLabels[row.status])}`,`data-partner-id="${Number(row.id)}"`,'users')).join('');
      drawer('partners',(rows?`<div class="management-list">${rows}</div>`:statePanel('empty'))+(data.next_before_id?`<button class="btn" data-partner-next="${data.next_before_id}">${esc(t('next'))}</button>`:''),btn('close','close'));return;
    }
    const row=data.partner,operations={pending:['approve','reject'],active:['block'],blocked:['unblock'],rejected:[]}[row.status]||[];
    managementDraft={type:'partner',partnerId:id,current:row};
    const form=`<form id="managementForm">${managementFields(row,'partner')}${operations.length?`<div class="form-field"><label for="partnerOperation">${esc(t('operation'))}</label><select class="input" id="partnerOperation">${operations.map(op=>`<option value="${op}">${esc(t(partnerOperationLabels[op]))}</option>`).join('')}</select></div>`:''}</form>`;
    drawer('partners',form,btn('close','close')+(operations.length?btn('saveChanges','managementPrepare','primary'):''));
  }catch(error){if(current===drawerId&&at===epoch&&state.actor)drawer('partners',statePanel(errorKey(error)),btn('close','close')+btn('readCurrent','partnerList'));}
}
const noticeLabels={rating_overtaken:'noticeRating',lesson_unfinished:'noticeLesson',d1_lesson_recovery:'noticeD1',daily_goal:'noticeDaily',streak_risk:'noticeStreak'};
async function noticeEditor(key=null){
  if(key!==null&&!Object.hasOwn(noticeLabels,key))return;
  closeDrawer();const current=drawerId,at=epoch;drawer('notices',statePanel('loading'));
  try{
    const data=await api('notifications/read',key?{key}:{});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    if(!key){
      const rows=data.items.filter(item=>Object.hasOwn(noticeLabels,item.key)).map(item=>managementRow(t(noticeLabels[item.key])+' · '+t(item.enabled?'hsk30On':'hsk30Off'),`data-notice-key="${item.key}"`,'bell')).join('');
      drawer('notices',`<div class="management-list">${rows}</div>`,btn('close','close'));return;
    }
    const template=data.template;
    managementDraft={type:'notice',noticeKey:key,template,texts:{...template.custom_texts},textLanguage:locale};
    const body=boolSelect('noticeEnabled','status',template.enabled)+`<p class="source-note">${esc(t('noticeDefaultHint'))}</p><p class="source-note">${esc(t('noticePlaceholders'))}: ${template.placeholders.map(esc).join(' ')}</p><div class="form-field"><label for="noticeLanguage">${esc(t('language'))}</label><select class="input" id="noticeLanguage">${['uz','ru','tj'].map(lang=>`<option value="${lang}" ${lang===locale?'selected':''}>${lang.toUpperCase()}</option>`).join('')}</select></div><div class="form-field"><label for="noticeText">${esc(t('noticeText'))}</label><textarea class="input setting-value" id="noticeText" maxlength="${template.text_max}">${esc(template.custom_texts[locale])}</textarea></div><p id="noticeValidation" class="alert" role="alert" hidden></p>`;
    drawer(noticeLabels[key],`<form id="managementForm">${body}</form>`,btn('cancel','close')+btn('saveChanges','managementPrepare','primary'));
    $('noticeText').placeholder=template.defaults[locale];
  }catch(error){if(current===drawerId&&at===epoch&&state.actor)drawer('notices',statePanel(errorKey(error)),btn('close','close')+btn('readCurrent','noticeList'));}
}
function updateNoticeLanguage(){
  const draft=managementDraft,next=$('noticeLanguage')?.value;
  if(draft?.type!=='notice'||!['uz','ru','tj'].includes(next))return;
  draft.texts[draft.textLanguage]=$('noticeText').value;draft.textLanguage=next;
  $('noticeText').value=draft.texts[next];$('noticeText').placeholder=draft.template.defaults[next];
}
async function portfolioHistory(before=null){
  closeDrawer();const current=drawerId,at=epoch;drawer('ledger',statePanel('loading'));
  try{
    const data=await api('portfolio/read',before?{before_id:before}:{});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    const rows=data.items.map(row=>`<article class="feedback-item"><strong>#${Number(row.id)} · ${esc(t({profit:'ledgerProfit',expense:'ledgerExpense'}[row.transaction_type]))} · ${esc(row.amount??'—')} ${esc(row.currency)}</strong><p>${esc(row.note)}${row.note_truncated?'…':''}</p><small>${esc(t('ledgerUSD'))}: ${esc(row.amount_usd??'—')} USD · ${esc(date(row.created_at))}</small></article>`).join('');
    drawer('ledger',`<p class="source-note">${esc(t('ledgerRateHint'))}</p>`+(rows||statePanel('empty'))+(data.next_before_id?`<button class="btn" data-portfolio-next="${data.next_before_id}">${esc(t('next'))}</button>`:''),btn('close','close')+btn('newLedgerEntry','portfolioEditor','primary'));
  }catch(error){if(current===drawerId&&at===epoch&&state.actor)drawer('ledger',statePanel(errorKey(error)),btn('close','close')+btn('readCurrent','portfolioHistory'));}
}
function portfolioEditor(){
  closeDrawer();managementDraft={type:'portfolio'};
  const body=`<p class="source-note">${esc(t('ledgerHint'))}</p><div class="form-field"><label for="portfolioType">${esc(t('ledgerType'))}</label><select class="input" id="portfolioType"><option value="profit">${esc(t('ledgerProfit'))}</option><option value="expense">${esc(t('ledgerExpense'))}</option></select></div><div class="form-field"><label for="portfolioCurrency">${esc(t('ledgerCurrency'))}</label><select class="input" id="portfolioCurrency">${['USD','TJS','CNY'].map(code=>`<option>${code}</option>`).join('')}</select></div><div class="form-field"><label for="portfolioAmount">${esc(t('amount'))}</label><input class="input" id="portfolioAmount" type="number" min="0.01" max="1000000" step="0.01" required></div><div class="form-field"><label for="portfolioNote">${esc(t('ledgerNote'))}</label><textarea class="input setting-value" id="portfolioNote" minlength="2" maxlength="300" required></textarea></div>`;
  drawer('newLedgerEntry',`<form id="managementForm">${body}</form>`,btn('cancel','close')+btn('saveChanges','managementPrepare','primary'));
}
async function channelEditor(kind,before=null){
  if(!['mode','list','add'].includes(kind))return;
  closeDrawer();const current=drawerId,at=epoch;
  drawer('requiredChannels',statePanel('loading'));
  try{
    const data=kind==='add'?null:await api('channels/read',before?{before_id:before}:{});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    managementDraft={type:'channel',kind,data};
    if(kind==='list'){
      const rows=data.items.map(row=>managementRow(`${row.title} · ${row.chat_id}`,`data-channel-id="${Number(row.id)}"`,'link')).join('');
      const next=data.next_before_id?`<button class="btn" data-channels-next="${data.next_before_id}">${esc(t('next'))}</button>`:'';
      drawer('requiredChannels',profileFields([['channelMode',t(data.enabled?'hsk30On':'hsk30Off')]])+(rows?`<div class="management-list">${rows}</div>`:statePanel('empty'))+next,btn('close','close')+`<button class="btn primary" data-channels-kind="add">${esc(t('addChannel'))}</button>`);
      return;
    }
    const field=(id,label,max,type='text',required=true)=>`<div class="form-field"><label for="${id}">${esc(t(label))}</label><input class="input" type="${type}" id="${id}" maxlength="${max}" ${required?'required':''}></div>`;
    const body=kind==='mode'?boolSelect('channelEnabled','channelMode',data.enabled):field('channelChat','channelChatId',40)+field('channelTitle','name',180)+field('channelInvite','channelInvite',300,'url',false);
    drawer(kind==='mode'?'channelMode':'addChannel',`<form id="managementForm">${body}</form>`,btn('cancel','close')+btn('saveChanges','managementPrepare','primary'));
  }catch(error){if(current===drawerId&&at===epoch&&state.actor)drawer('requiredChannels',statePanel(errorKey(error)),btn('close','close')+managementReread({type:'channel',kind}));}
}
function editChannel(id){
  const row=managementDraft?.data?.items?.find(row=>row.id===id);
  if(managementDraft?.type!=='channel'||!row)return;
  managementDraft={...managementDraft,kind:'state',channelId:id,current:row};
  const body=profileFields([['channelChatId',row.chat_id],['name',row.title]])+`<div class="form-field"><label for="channelOperation">${esc(t('operation'))}</label><select class="input" id="channelOperation"><option value="state">${esc(t('changeStatus'))}</option><option value="delete">${esc(t('deleteItem'))}</option></select></div><div id="channelActiveField">${boolSelect('channelActive','status',row.is_active)}</div>`;
  drawer('requiredChannels',`<form id="managementForm">${body}</form>`,btn('cancel','close')+btn('saveChanges','managementPrepare','primary'));
}
function marketingFields(value){
  const yes=value=>t(value?'hsk30On':'hsk30Off');
  if(value.kind==='campaign_draft'){
    const fields=[];
    if(value.id)fields.push(['campaignId',value.id]);
    if(value.title)fields.push(['campaignTitle',value.title]);
    fields.push(['status',t(value.status==='paused_draft'?'campaignDraftStatus':'newCampaign')]);
    if(value.languages)fields.push(['targetLanguages',value.languages.map(language=>language.toUpperCase()).join(', ')]);
    if(value.track)fields.push(['campaignTrack',value.track==='hsk20'?'HSK 2.0':'HSK 3.0']);
    if(value.duration_hours)fields.push(['campaignDurationHours',value.duration_hours]);
    if(value.include_active_subscribers!==undefined)fields.push(['includeActiveSubscribers',t(value.include_active_subscribers?'hsk30On':'hsk30Off')]);
    if(value.texts)return profileFields(fields)+['uz','ru','tj'].map(language=>`<details class="profile-section notice-languages" ${language===locale?'open':''}><summary>${language.toUpperCase()}</summary><p class="notice-preview">${esc(value.texts[language])}</p></details>`).join('');
    return profileFields(fields);
  }
  if(value.kind==='sales_experiment')return profileFields([['salesMode',t(salesModes[value.mode])],['salesPercent',value.treatment_percent+'%']]);
  if(value.kind==='desktop_promo')return profileFields([['status',yes(value.enabled)],['dailyLimit',value.daily_limit],['requireProgress',yes(value.require_learning_progress)],
    ['promoPlacements',Object.entries(value.placements||{}).filter(([,enabled])=>enabled).map(([key])=>t(promoLabels[key])).join(', ')||'—'],
    ['platform',Object.entries(value.platforms||{}).filter(([,enabled])=>enabled).map(([key])=>promoLabels[key]).join(', ')||'—'],
    ['promoMedia',value.media_sha256?(value.media_name||t('mediaSelected')):t(value.clear_media?'notSet':value.has_media?'mediaAttached':'notSet')]]);
  if(value.deleted_id)return profileFields([['courseAdId',value.deleted_id],['status',t('deleted')]]);
  const fields=[['courseAdId',value.ad_id||value.id]];
  if(value.title)fields.push(['courseAdTitle',value.title]);
  if(value.media_name||value.media_type)fields.push(['courseAdMedia',value.media_name
    ?`${value.media_name} · ${Number(value.media_size||0).toLocaleString()} B`
    :t(value.media_type==='photo'?'courseAdPhoto':'courseAdVideo')]);
  fields.push([value.operation?'operation':'status',value.operation==='delete'?t('deleteItem'):value.operation==='replace_image'?t('courseAdReplaceImage'):value.operation==='replace_video'?t('courseAdReplaceVideo'):yes(value.is_active)]);
  return profileFields(fields);
}
function boolSelect(id,label,value){return `<div class="form-field"><label for="${id}">${esc(t(label))}</label><select class="input" id="${id}"><option value="true" ${value?'selected':''}>${esc(t('hsk30On'))}</option><option value="false" ${!value?'selected':''}>${esc(t('hsk30Off'))}</option></select></div>`;}
function courseAdCreateEditor(){
  closeDrawer();managementDraft={type:'marketing',kind:'course_ad_create',mediaFile:null};
  const select=(id,label,options)=>`<div class="form-field"><label for="${id}">${esc(t(label))}</label><select id="${id}" class="input">${options.map(([value,label])=>`<option value="${value}">${esc(['UZ','RU','TJ'].includes(label)?label:t(label))}</option>`).join('')}</select></div>`;
  const copies=['uz','ru','tj'].map(lang=>`<details class="profile-section notice-languages" id="newAdCopy-${lang}" open><summary>${lang.toUpperCase()}</summary><div class="form-field"><label for="newAdTitle-${lang}">${esc(t('courseAdTitle'))}</label><input id="newAdTitle-${lang}" class="input" maxlength="120" required></div><div class="form-field"><label for="newAdButton-${lang}">${esc(t('courseAdButton'))}</label><input id="newAdButton-${lang}" class="input" maxlength="64"></div></details>`).join('');
  const body=select('newAdLanguage','language',[['uz','UZ'],['ru','RU'],['tj','TJ'],['all','allLanguages']])+`<p class="form-hint">${esc(t('courseAdCopiesHint'))}</p>${copies}`
    +select('newAdType','courseAdKind',Object.entries(courseAdTypeLabels))
    +`<fieldset class="form-field"><legend>${esc(t('promoPlacements'))}</legend>${[['screen_center','courseAdScreenCenter'],['lesson_end','courseAdLessonEnd']].map(([value,label])=>`<label class="management-check"><input type="checkbox" data-course-ad-placement="${value}" ${value==='screen_center'?'checked':''}>${esc(t(label))}</label>`).join('')}</fieldset>`
    +`<div class="form-field"><label for="newAdDuration">${esc(t('durationSeconds'))}</label><input id="newAdDuration" type="number" class="input" min="5" max="120" step="1" value="7" required></div><div class="form-field"><label for="newAdLink">${esc(t('courseAdLink'))}</label><input id="newAdLink" type="text" class="input" maxlength="512" placeholder="https://…"></div>`
    +boolSelect('newAdActive','status',false)+select('newAdMediaType','courseAdMedia',[['photo','courseAdPhoto'],['video','courseAdVideo']])
    +`<div class="form-field"><label for="courseAdMediaFile">${esc(t('courseAdMedia'))}</label><input class="input" id="courseAdMediaFile" type="file" accept="image/jpeg,image/png,image/webp"><p class="form-hint" id="courseAdMediaHint">${esc(t('courseAdMediaHint'))}</p><div id="courseAdMediaPreview" aria-live="polite"></div><p class="alert" id="courseAdMediaValidation" role="alert" hidden></p></div><p class="alert" id="courseAdCreateValidation" role="alert" hidden>${esc(t('courseAdCreateValidation'))}</p>`;
  drawer('newCourseAd',`<form id="managementForm">${body}</form>`,btn('cancel','close')+btn('createItem','managementPrepare','primary'));
  $('newAdLanguage').value=locale;updateCourseAdCreateLanguage();
}
function updateCourseAdCreateLanguage(){
  if(managementDraft?.kind!=='course_ad_create')return;
  const selected=$('newAdLanguage').value;
  for(const lang of ['uz','ru','tj']){
    const active=selected==='all'||selected===lang,section=$('newAdCopy-'+lang);
    section.hidden=!active;section.open=selected!=='all'||lang===locale;
    for(const input of section.querySelectorAll('input'))input.disabled=!active;
  }
}
function updateCourseAdCreateMedia(){
  if(managementDraft?.kind!=='course_ad_create')return;
  const video=$('newAdMediaType').value==='video',input=$('courseAdMediaFile');
  input.value='';input.accept=video?'video/mp4,video/quicktime,video/webm,video/x-m4v':'image/jpeg,image/png,image/webp';
  $('courseAdMediaHint').textContent=t(video?'courseAdVideoHint':'courseAdMediaHint');
  managementDraft={...managementDraft,mediaFile:null};releaseManagementMediaPreview();
  $('courseAdMediaPreview').innerHTML='';$('courseAdMediaValidation').hidden=true;
}
const campaignLabels={ad:'adCampaigns',release:'releaseCampaigns',discount:'discountCampaigns'};
const campaignFeatureLabels={general:'all',qa:'questionAnswer',image:'releaseFeatureImage',course:'course',profile:'userProfile',subscription:'subscriptionPrices',android_subscription:'releaseFeatureAndroid'};
function campaignSelect(id,label,options,selected=''){
  return `<div class="form-field"><label for="${id}">${esc(t(label))}</label><select class="input" id="${id}">${options.map(([value,text])=>`<option value="${esc(value)}" ${value===selected?'selected':''}>${esc(t(text))}</option>`).join('')}</select></div>`;
}
function campaignFields(row){
  const fields=[['campaignId',row.id],['campaignTitle',row.title],['status',t(({active:'hsk30On',paused:'campaignDraftStatus',sending:'messageRunning',sent:'messageComplete',stopped:'messageClosed',scheduled:'messageReady'})[row.status]||'unavailable')]];
  if(row.ends_at)fields.push(['campaignExpiry',date(row.ends_at)]);
  if(row.percent)fields.push(['discount',row.percent+'%']);
  if(row.target_user_id)fields.push(['account',row.target_user_id]);
  if(row.quota_total)fields.push(['discountQuota',row.quota_total]);
  if(row.repeat_interval_days)fields.push(['discountRepeatDays',row.repeat_interval_days]);
  if(row.sent_count!==undefined)fields.push(['messageAttempted',row.sent_count],['messageUncertain',row.failed_count]);
  const copies=row.texts?['uz','ru','tj'].map(lang=>`<details class="profile-section notice-languages" ${lang===locale?'open':''}><summary>${lang.toUpperCase()}</summary><p class="notice-preview">${esc(row.texts[lang])}</p></details>`).join(''):row.copies?['uz','ru','tj'].map(lang=>`<details class="profile-section notice-languages" ${lang===locale?'open':''}><summary>${lang.toUpperCase()}</summary><strong>${esc(row.copies[lang].title)}</strong><p class="notice-preview">${esc(row.copies[lang].reason)}</p></details>`).join(''):'';
  return profileFields(fields)+copies;
}
async function campaignList(kind,before=null){
  if(!Object.hasOwn(campaignLabels,kind))return;
  closeDrawer();const current=drawerId,at=epoch;drawer(campaignLabels[kind],statePanel('loading'));
  try{
    const data=await api('campaigns/read',{kind,...(before?{before_id:before}:{})});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    if(!Array.isArray(data.items)||data.items.length>30)throw Error('invalid_campaigns');
    const rows=data.items.map(row=>managementRow(`#${row.id} · ${row.title}`,`data-campaign-detail="${Number(row.id)}" data-campaign-kind="${kind}"`,'mega')).join('');
    const next=data.next_before_id?`<button class="btn" data-campaign-list="${kind}" data-before="${Number(data.next_before_id)}">${esc(t('next'))}</button>`:'';
    const create=kind==='ad'?`<button class="btn primary" data-marketing-kind="campaign_draft">${esc(t('createCampaign'))}</button>`:`<button class="btn primary" data-campaign-create="${kind}">${esc(t(kind==='release'?'newReleaseCampaign':'newDiscountCampaign'))}</button>`;
    drawer(campaignLabels[kind],(rows?`<div class="management-list">${rows}</div>`:statePanel('empty'))+next,btn('close','close')+create);
  }catch(error){if(current===drawerId&&at===epoch&&state.actor)drawer(campaignLabels[kind],statePanel(errorKey(error)),btn('close','close'));}
}
async function campaignDetail(kind,id){
  if(!Object.hasOwn(campaignLabels,kind))return;
  closeDrawer();const current=drawerId,at=epoch;drawer(campaignLabels[kind],statePanel('loading'));
  try{
    const data=await api('campaigns/read',{kind,campaign_id:id});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    const row=data.campaign;
    if(row.id!==id||row.kind!==kind)throw Error('invalid_campaign');
    const editable=kind==='ad'&&row.can_send||kind==='discount'&&(row.can_activate||row.is_active);
    managementDraft=editable?{type:'campaign',kind:kind==='ad'?'ad_send':'discount_state',campaignKind:kind,campaignId:id,current:row}:null;
    const selection=kind==='discount'&&editable?campaignSelect('campaignActive','status',row.can_activate?[['false','hsk30Off'],['true','hsk30On']]:[['false','hsk30Off']],String(row.is_active)):'';
    const hint=kind==='ad'?`<p class="source-note">${esc(t(row.can_send?'campaignSendHint':'campaignReadOnly'))}</p>`:kind==='discount'?`<p class="source-note">${esc(t('discountNoNotificationHint'))}</p>`:'';
    drawer(campaignLabels[kind],`<form id="managementForm">${campaignFields(row)}${hint}${selection}<p class="alert" id="campaignCommandValidation" role="alert" hidden></p></form>`,btn('close','close')+(editable?btn('saveChanges','managementPrepare','primary'):''));
  }catch(error){if(current===drawerId&&at===epoch&&state.actor)drawer(campaignLabels[kind],statePanel(errorKey(error)),btn('close','close'));}
}
function campaignCreate(kind,userId=null){
  if(!['release','discount'].includes(kind))return;
  closeDrawer();managementDraft={type:'campaign',kind:kind+'_create',campaignKind:kind};
  const input=(id,label,max,extra='')=>`<div class="form-field"><label for="${id}">${esc(t(label))}</label><input class="input" id="${id}" maxlength="${max}" ${extra}></div>`;
  let body='';
  if(kind==='release'){
    body=`<p class="source-note">${esc(t('releaseCampaignHint'))}</p>`+input('releaseTitle','campaignTitle',120,'required');
    body+=['uz','ru','tj'].map(lang=>`<details class="profile-section notice-languages" ${lang===locale?'open':''}><summary>${lang.toUpperCase()}</summary><div class="form-field"><label for="releaseText-${lang}">${esc(t('campaignCopy'))}</label><textarea class="input setting-value" id="releaseText-${lang}" maxlength="3500" rows="5" required></textarea></div></details>`).join('');
    body+=campaignSelect('releaseFeature','releaseFeature',Object.entries(campaignFeatureLabels));
    body+=`<details class="profile-section"><summary>${esc(t('filters'))}</summary><fieldset class="form-field"><legend>${esc(t('targetLanguages'))}</legend>${['uz','ru','tj'].map(lang=>`<label class="management-check"><input type="checkbox" data-release-language="${lang}" checked>${lang.toUpperCase()}</label>`).join('')}</fieldset><div class="management-form-pair">${Object.entries(messageFilterConfig).map(([key,[label,options]])=>campaignSelect('releaseFilter-'+key,label,[['','all'],...options])).join('')}</div></details>`;
  }else{
    body=`<p class="source-note">${esc(t('discountNoNotificationHint'))}</p>`;
    body+=['uz','ru','tj'].map(lang=>`<details class="profile-section notice-languages" ${lang===locale?'open':''}><summary>${lang.toUpperCase()}</summary>${input('discountTitle-'+lang,'campaignTitle',120,'required')}<div class="form-field"><label for="discountReason-${lang}">${esc(t('discountReason'))}</label><textarea class="input setting-value" id="discountReason-${lang}" maxlength="500" rows="3"></textarea></div></details>`).join('');
    body+=`<div class="management-form-pair">${input('discountPercent','discountPercent',2,'type="number" min="1" max="90" step="1" value="20" required')}${input('discountHours','campaignDurationHours',3,'type="number" min="1" max="720" step="1" value="24" required')}</div>`;
    body+=input('discountTarget','discountTarget',12,'type="number" min="1" step="1"');
    body+=`<div class="management-form-pair" id="discountSegment">${campaignSelect('discountStatus','status',[['','all'],...messageFilterConfig.status[1]])}${campaignSelect('discountLanguage','language',[['','all'],['uz','UZ'],['ru','RU'],['tj','TJ']])}${campaignSelect('discountLevel','level',[['','all'],...messageFilterConfig.level[1]])}</div>`;
    body+=`<div class="management-form-pair">${campaignSelect('discountMethod','method',[['','all'],...messageFilterConfig.payment_method[1]])}${campaignSelect('discountPlan','plan',[['','all'],...messageFilterConfig.plan[1].filter(([plan])=>plan!=='3_months')])}${input('discountQuota','discountQuota',6,'type="number" min="1" max="100000" step="1"')}${input('discountRepeat','discountRepeatDays',3,'type="number" min="1" max="365" step="1"')}</div>`;
    body+=campaignSelect('campaignActive','status',[['false','hsk30Off'],['true','hsk30On']]);
  }
  body+='<p class="alert" id="campaignCommandValidation" role="alert" hidden></p>';
  drawer(kind==='release'?'newReleaseCampaign':'newDiscountCampaign',`<form id="managementForm">${body}</form>`,btn('cancel','close')+btn('saveChanges','managementPrepare','primary'));
  if(kind==='discount'&&Number.isSafeInteger(userId)&&userId>0&&$('discountTarget')){
    $('discountTarget').value=String(userId);
    if($('discountSegment'))$('discountSegment').hidden=true;
  }
}
function campaignChange(draft){
  if(draft.kind==='ad_send')return {kind:draft.kind,campaign_id:draft.campaignId};
  if(draft.kind==='discount_state')return {kind:draft.kind,campaign_id:draft.campaignId,is_active:$('campaignActive').value==='true'};
  if(draft.kind==='release_create'){
    const filters={languages:[...document.querySelectorAll('[data-release-language]:checked')].map(input=>input.dataset.releaseLanguage)};
    for(const key of Object.keys(messageFilterConfig))if($('releaseFilter-'+key).value)filters[key]=$('releaseFilter-'+key).value;
    return {kind:draft.kind,title:$('releaseTitle').value,texts:Object.fromEntries(['uz','ru','tj'].map(lang=>[lang,$('releaseText-'+lang).value])),feature_key:$('releaseFeature').value,filters};
  }
  const target=Number($('discountTarget').value)||null;
  return {kind:draft.kind,copies:Object.fromEntries(['uz','ru','tj'].map(lang=>[lang,{title:$('discountTitle-'+lang).value,reason:$('discountReason-'+lang).value}])),
    percent:Number($('discountPercent').value),duration_hours:Number($('discountHours').value),target_user_id:target,
    audience_status:target?null:$('discountStatus').value||null,audience_language:target?null:$('discountLanguage').value||null,audience_level:target?null:$('discountLevel').value||null,
    payment_method:$('discountMethod').value||null,plan_type:$('discountPlan').value||null,quota_total:Number($('discountQuota').value)||null,repeat_interval_days:Number($('discountRepeat').value)||null,is_active:$('campaignActive').value==='true'};
}
async function marketingEditor(kind,before=null){
  if(kind==='course_ad_create'){courseAdCreateEditor();return;}
  if(kind==='campaign_draft'){
    closeDrawer();managementDraft={type:'marketing',kind};
    const copy=['uz','ru','tj'].map(language=>`<details class="profile-section notice-languages campaign-locale-copy" ${language===locale?'open':''}><summary>${language.toUpperCase()}</summary><div class="form-field"><label for="campaignText-${language}">${esc(t('campaignCopy'))}</label><textarea class="input setting-value" id="campaignText-${language}" maxlength="3500" rows="5" required></textarea></div></details>`).join('');
    const languages=['uz','ru','tj'].map(language=>`<label class="management-check"><input type="checkbox" data-campaign-language="${language}">${language.toUpperCase()}</label>`).join('');
    const body=`<p class="source-note campaign-paused-note">${esc(t('campaignPausedHint'))}</p><div class="form-field"><label for="campaignTitle">${esc(t('campaignTitle'))}</label><input class="input" id="campaignTitle" maxlength="120" required></div>${copy}<fieldset class="form-field"><legend>${esc(t('targetLanguages'))}</legend><div class="v6-toggles">${languages}</div></fieldset><div class="management-form-pair"><div class="form-field"><label for="campaignTrack">${esc(t('campaignTrack'))}</label><select class="input" id="campaignTrack"><option value="">${esc(t('all'))}</option><option value="hsk20">HSK 2.0</option><option value="hsk30">HSK 3.0</option></select></div><div class="form-field"><label for="campaignDuration">${esc(t('campaignDurationHours'))}</label><input class="input" id="campaignDuration" type="number" min="1" max="720" step="1" value="24" required></div></div><label class="management-check"><input type="checkbox" id="campaignSubscribers">${esc(t('includeActiveSubscribers'))}</label><p class="alert" id="campaignValidation" hidden>${esc(t('campaignValidation'))}</p>`;
    drawer('createCampaign',`<form id="managementForm">${body}</form>`,btn('cancel','close')+btn('saveChanges','managementPrepare','primary'));
    return;
  }
  if(!Object.hasOwn(marketingLabels,kind))return;
  closeDrawer();const current=drawerId,at=epoch;
  drawer(marketingLabels[kind],statePanel('loading'));
  try{
    const data=await api('marketing/read',before?{before_id:before}:{});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    managementDraft={type:'marketing',kind,data,mediaFile:null,clearMedia:false};
    if(kind==='course_ad'){
      const page=data.course_ads;
      if(!Array.isArray(page?.items)||page.items.length>30)throw Error('invalid_ads');
      const rows=page.items.map(ad=>managementRow(`#${ad.id} · ${ad.title}`,`data-course-ad="${Number(ad.id)}"`,'mega')).join('');
      drawer('courseAds',(rows?`<div class="management-list">${rows}</div>`:statePanel('empty'))+(page.next_before_id?`<button class="btn" data-marketing-next="${page.next_before_id}">${esc(t('next'))}</button>`:''),btn('close','close')+`<button class="btn primary" data-marketing-kind="course_ad_create">${esc(t('newCourseAd'))}</button>`);
      return;
    }
    const value=data[kind];let body;
    if(kind==='sales_experiment')body=`<div class="form-field"><label for="salesMode">${esc(t('salesMode'))}</label><select id="salesMode" class="input">${Object.entries(salesModes).map(([mode,label])=>`<option value="${mode}" ${value.mode===mode?'selected':''}>${esc(t(label))}</option>`).join('')}</select></div><div class="form-field"><label for="salesPercent">${esc(t('salesPercent'))}</label><select id="salesPercent" class="input">${[0,50,90,100].map(percent=>`<option value="${percent}" ${value.treatment_percent===percent?'selected':''}>${percent}%</option>`).join('')}</select></div>`;
    else{
      const check=(key,value,label)=>`<label class="management-check"><input type="checkbox" id="promo-${key}" ${value?'checked':''}>${esc(label)}</label>`;
      body=boolSelect('promoEnabled','status',value.enabled)+`<div class="form-field"><label for="promoLimit">${esc(t('dailyLimit'))}</label><input class="input" id="promoLimit" type="number" min="1" max="3" step="1" value="${esc(value.daily_limit)}" required></div><label class="management-check"><input id="promoProgress" type="checkbox" ${value.require_learning_progress?'checked':''}>${esc(t('requireProgress'))}</label><fieldset class="form-field"><legend>${esc(t('promoPlacements'))}</legend>${['home_prompt','lesson_end_promo','ad_promo'].map(key=>check(key,value.placements?.[key],t(promoLabels[key]))).join('')}</fieldset><fieldset class="form-field"><legend>${esc(t('platform'))}</legend>${['macos','windows','android','ios'].map(key=>check(key,value.platforms?.[key],promoLabels[key])).join('')}</fieldset><div class="form-field"><label for="promoMediaFile">${esc(t('promoMedia'))}</label><input class="input" id="promoMediaFile" type="file" accept="image/jpeg,image/png,image/webp"><p class="form-hint">${esc(t('promoMediaHint'))}</p><div id="promoMediaPreview" aria-live="polite"></div><p class="alert" id="promoMediaValidation" hidden>${esc(t('promoMediaValidation'))}</p></div>${value.has_media?`<label class="management-check"><input id="promoMediaClear" type="checkbox">${esc(t('promoMediaRemove'))}</label>`:''}`;
    }
    drawer(marketingLabels[kind],`<form id="managementForm">${body}</form>`,btn('cancel','close')+btn('saveChanges','managementPrepare','primary'));
  }catch(error){if(current===drawerId&&at===epoch&&state.actor)drawer(marketingLabels[kind],statePanel(errorKey(error)),btn('close','close')+managementReread({type:'marketing',kind}));}
}
function editCourseAd(id){
  const ad=managementDraft?.data?.course_ads?.items?.find(row=>row.id===id);
  if(!ad||managementDraft.kind!=='course_ad')return;
  managementDraft={...managementDraft,ad};
  const form=`<form id="managementForm">${profileFields([['courseAdId',ad.id],['courseAdTitle',ad.title],['language',ad.language],['courseAdMedia',t(ad.media_type==='photo'?'courseAdPhoto':'courseAdVideo')]])}<div class="form-field"><label for="adOperation">${esc(t('operation'))}</label><select id="adOperation" class="input"><option value="set_active">${esc(t('changeStatus'))}</option><option value="replace_image">${esc(t('courseAdReplaceImage'))}</option><option value="replace_video">${esc(t('courseAdReplaceVideo'))}</option><option value="delete">${esc(t('deleteItem'))}</option></select></div><div id="adActiveField">${boolSelect('adActive','status',ad.is_active)}</div><div class="form-field" id="adMediaField" hidden><label for="courseAdMediaFile">${esc(t('courseAdMedia'))}</label><input class="input" id="courseAdMediaFile" type="file" accept="image/jpeg,image/png,image/webp" disabled><p class="form-hint" id="courseAdMediaHint">${esc(t('courseAdMediaHint'))}</p><div id="courseAdMediaPreview" aria-live="polite"></div><p class="alert" id="courseAdMediaValidation" role="alert" hidden></p></div><p class="alert" id="adDeleteHint" hidden>${esc(t('deleteAdHint'))}</p></form>`;
  drawer('courseAds',form,btn('cancel','close')+btn('saveChanges','managementPrepare','primary'));
}
function managementFields(value,type){
  if(['message','message_control'].includes(type)){
    const fields=[['operation',t(messageKindLabels[value.kind])],['messageAudience',value.audience_count]];
    if(value.user_id)fields.push(['account',value.user_id]);
    if(value.filters){
      if(value.filters.languages?.length)fields.push(['language',value.filters.languages.join(', ').toUpperCase()]);
      for(const [key,[label,options]] of Object.entries(messageFilterConfig))if(value.filters[key])fields.push([label,t(options.find(item=>item[0]===value.filters[key])?.[1]||value.filters[key])]);
    }
    if(value.status)fields.push(['status',t(value.stale?'messageStale':messageJobLabels[value.status])]);
    if(value.operation)fields.push(['operation',t(value.operation==='resume'?'messageResume':'messageStop')]);
    if(value.expires_at)fields.push(['messageExpiry',date(value.expires_at)]);
    for(const [key,label] of Object.entries(messageCountLabels))if(value.counts)fields.push([label,value.counts[key]||0]);
    return profileFields(fields)+['uz','ru','tj'].map(lang=>`<details class="profile-section notice-languages" ${lang===locale?'open':''}><summary>${lang.toUpperCase()}</summary><p class="notice-preview">${esc(value.texts[lang])}</p></details>`).join('');
  }
  if(type==='delivery'){
    const fields=[['paymentId',value.payment_id],['reviewDecision',t(value.decision==='approve'?'approved':'rejected')],['deliveryStatus',t(deliveryStatusLabels[value.delivery_status])]];
    if(value.resolution)fields.push(['deliveryResolution',t(deliveryResolutionLabels[value.resolution])]);
    if(value.reason)fields.push(['deliveryReason',value.reason]);
    if(value.attempted_at)fields.push(['deliveryAttemptTime',date(value.attempted_at)]);
    if(value.reconciled_at)fields.push(['deliveryReconciledTime',date(value.reconciled_at)]);
    return profileFields(fields);
  }
  if(['payout','payout_completion'].includes(type)){
    const fields=[['payoutId',value.id],['partnerId',value.partner_id],['status',value.previous_status?t(payoutStatusLabels[value.previous_status])+' → '+t(payoutStatusLabels[value.status]):t(payoutStatusLabels[value.status])],['amount',value.local_amount+' '+value.local_currency],['ledgerUSD',value.amount_usd+' USD']];
    if(value.operation)fields.push(['operation',t(payoutOperationLabels[value.operation])]);
    fields.push(['method',value.bank_name||value.payment_method]);
    if(value.holder_name)fields.push(['payoutHolder',value.holder_name]);
    fields.push(['payoutAccount',value.account_details]);
    if(value.deadline_at)fields.push(['payoutDueAt',date(value.deadline_at)]);
    if(value.note)fields.push(['ledgerNote',value.note]);
    if(value.notice_count!==undefined)fields.push(['messageAudience',value.notice_count]);
    if(value.notice_user_id)fields.push(['account',value.notice_user_id]);
    const proof=value.proof_id?`<p class="source-note">${esc(t('payoutProofReviewHint'))}</p><img class="inbox-attachment-image" src="/api/admin/v1/payout-proofs/${esc(value.proof_id)}" alt="${esc(t('payoutProofFile'))}">`:'';
    const notice=value.notice_texts?['uz','ru','tj'].map(lang=>`<details class="profile-section notice-languages"><summary>${lang.toUpperCase()}</summary><p class="notice-preview">${telegramPreview(value.notice_texts[lang])}</p></details>`).join(''):'';
    return proof+profileFields(fields)+notice;
  }
  if(type==='partner'){
    const fields=[['partnerId',value.id],['status',t(partnerStatusLabels[value.status])]];
    if(value.operation)fields.push(['operation',t(partnerOperationLabels[value.operation])]);
    if(value.contact_username)fields.push(['partnerContact',value.contact_username]);
    if(value.promotion_channel)fields.push(['partnerPromotion',value.promotion_channel]);
    if(value.audience_size)fields.push(['partnerAudience',value.audience_size]);
    if(value.signup_bonus_usd!==undefined)fields.push(['partnerBonus',value.signup_bonus_usd+' USD']);
    if(value.notice_count!==undefined)fields.push(['messageAudience',value.notice_count]);
    const notice=value.notice_texts?`<p class="source-note">${esc(t('messageAttemptHint'))}</p>`+['uz','ru','tj'].map(lang=>`<details class="profile-section notice-languages" ${lang===locale?'open':''}><summary>${lang.toUpperCase()}</summary><p class="notice-preview">${telegramPreview(value.notice_texts[lang])}</p></details>`).join(''):'';
    return notice+profileFields(fields);
  }
  if(type==='notice')return profileFields([['status',t(value.enabled?'hsk30On':'hsk30Off')]])+['uz','ru','tj'].map(lang=>`<details class="profile-section notice-languages" ${lang===locale?'open':''}><summary>${lang.toUpperCase()}</summary><p class="notice-preview">${esc(value.effective_texts[lang])}</p></details>`).join('');
  if(type==='portfolio')return profileFields([['ledgerType',t(value.transaction_type==='profit'?'ledgerProfit':'ledgerExpense')],['amount',(value.amount_minor/100).toFixed(2)+' '+value.currency],['ledgerUSD',(value.expected_usd||value.amount_usd)+' USD'],['ledgerNote',value.note]]);
  if(type==='channel'){
    if(Object.hasOwn(value,'enabled'))return profileFields([['channelMode',t(value.enabled?'hsk30On':'hsk30Off')]]);
    const fields=[];const id=value.id||value.channel_id||value.deleted_id;
    if(id)fields.push(['channelId',id]);
    if(value.chat_id)fields.push(['channelChatId',value.chat_id]);
    if(value.title)fields.push(['name',value.title]);
    if(value.invite_link)fields.push(['channelInvite',value.invite_link]);
    fields.push(['status',value.kind==='delete'||value.deleted_id?t('deleteItem'):value.exists===false?t('notSet'):t(value.is_active===false?'hsk30Off':'hsk30On')]);
    return profileFields(fields);
  }
  if(type==='user'){
    const fields=[['account',value.user_id]];
    if(value.name)fields.push(['name',value.name]);
    if(value.operation)fields.push(['operation',t(userOperationLabels[value.operation])]);
    if(value.deleted)fields.push(['status',t('deleted')]);
    else if(value.status)fields.push(['status',t({free:'FREE',active:'accountActive',blocked:'BLOCKED'}[value.status])]);
    return profileFields(fields);
  }
  if(type==='campaign')return campaignFields(value);
  if(type==='marketing')return marketingFields(value);
  if(type==='price')return profileFields([['method',value.method],['plan',t(value.plan)],['amount',value.amount+' '+value.currency]]);
  if(type==='payment_qr')return profileFields([
    ['method',value.method],['plan',t(value.plan)],['amount',value.amount+' '+value.currency],
    ['paymentQrStatus',t(value.qr_set?'paymentQrSet':'paymentQrMissing')],
    ...(value.media_name?[["paymentQrImage",`${value.media_name} · ${Number(value.media_size||0).toLocaleString()} B`]]:[]),
  ]);
  if(value.kind==='payment_details')return profileFields([['method',value.bank==='dc_city'?'DC City':'Alif'],['paymentDetails',value.value||t('notSet')]]);
  if(value.kind==='ai_model')return profileFields([['aiModel',value.model]]);
  if(value.kind==='help_contact')return profileFields([['helpContact',value.value||t('notSet')]]);
  if(value.kind==='help_video')return profileFields([['videoTopic',t(helpVideoLabels[value.key])],['language',value.lang.toUpperCase()],['videoLink',value.value||t('notSet')]]);
  throw Error('invalid_settings');
}
function managementReread(draft){
  if(draft.type==='message')return btn('readCurrent','messageList');
  if(draft.type==='message_control')return `<button class="btn" data-message-job="${esc(draft.jobId)}">${esc(t('readCurrent'))}</button>`;
  if(draft.type==='delivery')return `<button class="btn" data-delivery-id="${esc(draft.deliveryId)}">${esc(t('readCurrent'))}</button>`;
  if(['payout','payout_completion'].includes(draft.type))return `<button class="btn" data-payout-id="${draft.payoutId}">${esc(t('readCurrent'))}</button>`;
  if(draft.type==='partner')return `<button class="btn" data-partner-id="${draft.partnerId}">${esc(t('readCurrent'))}</button>`;
  if(draft.type==='notice')return `<button class="btn" data-notice-key="${esc(draft.noticeKey)}">${esc(t('readCurrent'))}</button>`;
  if(draft.type==='portfolio')return btn('readCurrent','portfolioHistory');
  if(draft.type==='campaign')return `<button class="btn" data-campaign-list="${esc(draft.campaignKind||({ad_send:'ad',release_create:'release',discount_create:'discount',discount_state:'discount'}[draft.kind]))}">${esc(t('readCurrent'))}</button>`;
  if(draft.type==='channel')return `<button class="btn" data-channels-kind="${draft.kind==='mode'?'mode':'list'}">${esc(t('readCurrent'))}</button>`;
  if(draft.type==='user')return `<button class="btn" data-user-detail="${draft.userId}">${esc(t('readCurrent'))}</button>`;
  if(draft.type==='marketing')return `<button class="btn" data-marketing-kind="${esc(draft.kind==='course_ad_create'?'course_ad':draft.kind)}">${esc(t('readCurrent'))}</button>`;
  if(draft.type==='payment_qr')return `<button class="btn" data-payment-qr-target="${esc(draft.method+'-'+draft.plan)}">${esc(t('readCurrent'))}</button>`;
  return draft.type==='price'?btn('readCurrent','priceSettings'):`<button class="btn" data-setting-kind="${draft.kind}" ${draft.bank?`data-bank="${draft.bank}"`:''}>${esc(t('readCurrent'))}</button>`;
}
function updatePriceFields(){
  if(managementDraft?.type!=='price')return;
  const row=managementDraft.prices.find(row=>row.method===$('priceMethod')?.value&&row.plan===$('pricePlan')?.value);
  if(!row)return;
  $('priceAmount').value=row.amount;$('priceCurrency').textContent=row.currency;
  const qrButton=$('priceQrAction');
  const qrField=$('priceQrField');
  if(qrButton)qrButton.hidden=!['alipay','wechat'].includes(row.method);
  if(qrField)qrField.hidden=!['alipay','wechat'].includes(row.method);
}
async function priceSettings(){
  closeDrawer();const current=drawerId,at=epoch;
  drawer('subscriptionPrices',statePanel('loading'));
  try{
    const data=await api('subscription-prices/read',{});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    if(!Array.isArray(data.prices)||data.prices.length!==9)throw Error('invalid_prices');
    managementDraft={type:'price',prices:data.prices};
    const select=(id,label,options)=>`<div class="form-field"><label for="${id}">${esc(t(label))}</label><select id="${id}" class="input">${options.map(([key,text])=>`<option value="${key}">${esc(text)}</option>`).join('')}</select></div>`;
    const body=`<form id="managementForm">${select('priceMethod','method',[['visa','Visa'],['alipay','Alipay'],['wechat','WeChat']])}${select('pricePlan','plan',[['10_days',t('10_days')],['1_month',t('1_month')],['3_months',t('3_months')]])}<div class="form-field"><label for="priceAmount">${esc(t('amount'))} · <span id="priceCurrency"></span></label><input id="priceAmount" class="input" type="number" min="1" max="1000000" step="1" required></div><div class="form-field" id="priceQrField"><button type="button" class="btn" id="priceQrAction" data-action="priceQrSettings">${esc(t('paymentQrManage'))}</button></div></form>`;
    drawer('subscriptionPrices',body,btn('cancel','close')+btn('saveChanges','managementPrepare','primary'));
    updatePriceFields();
  }catch(error){
    if(current===drawerId&&at===epoch&&state.actor)drawer('subscriptionPrices',statePanel(errorKey(error)),btn('close','close')+btn('retry','priceSettings','primary'));
  }
}
async function priceQrSettings(method=null,plan=null){
  method=method||$('priceMethod')?.value;plan=plan||$('pricePlan')?.value;
  if(!['alipay','wechat'].includes(method)||!['10_days','1_month','3_months'].includes(plan))return;
  closeDrawer();const current=drawerId,at=epoch;
  drawer('paymentQrTitle',statePanel('loading'));
  try{
    const data=await api('payment-qr/read',{method,plan});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    const qr=data.qr;
    if(!qr||qr.method!==method||qr.plan!==plan)throw Error('invalid_payment_qr');
    managementDraft={type:'payment_qr',method,plan,current:qr,mediaFile:null};
    const body=`<form id="managementForm"><p class="source-note">${esc(t('paymentQrPrivateNote'))}</p>${managementFields(qr,'payment_qr')}<div class="form-field"><label for="paymentQrMediaFile">${esc(t('paymentQrImage'))}</label><input class="input" id="paymentQrMediaFile" type="file" accept="image/jpeg,image/png,image/webp"><p class="form-hint">${esc(t('paymentQrMediaHint'))}</p><div id="paymentQrMediaPreview" aria-live="polite"></div><p class="alert" id="paymentQrMediaValidation" role="alert" hidden></p></div></form>`;
    drawer('paymentQrTitle',body,btn('cancel','priceSettings')+btn('saveChanges','managementPrepare','primary'));
  }catch(error){
    if(current===drawerId&&at===epoch&&state.actor)drawer('paymentQrTitle',statePanel(errorKey(error)),btn('close','close')+`<button class="btn" data-payment-qr-target="${esc(method+'-'+plan)}">${esc(t('readCurrent'))}</button>`);
  }
}
function updateHelpVideoField(){
  if(managementDraft?.kind!=='help_video')return;
  const row=managementDraft.data.settings.help_videos.find(row=>row.key===$('helpVideoKey')?.value&&row.lang===$('helpVideoLanguage')?.value);
  if($('settingValue'))$('settingValue').value=row?.value||'';
}
async function editSetting(kind,bank=null){
  if(!Object.hasOwn(settingLabels,kind)||(kind==='payment_details'&&!['dc_city','alif'].includes(bank)))return;
  closeDrawer();const current=drawerId,at=epoch,label=settingLabels[kind];
  drawer(label,statePanel('loading'));
  try{
    const data=await api('settings/read',{});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    if(!data.settings||!data.options)throw Error('invalid_settings');
    managementDraft={type:'setting',kind,bank,data};
    const s=data.settings,o=data.options;let body='';
    if(kind==='ai_model')body=`<div class="form-field"><label for="settingModel">${esc(t(label))}</label><select id="settingModel" class="input">${o.ai_models.map(model=>`<option value="${esc(model)}" ${s.ai_model.model===model?'selected':''}>${esc(model)}</option>`).join('')}</select></div>`;
    else{
      let value='',maximum=512;
      if(kind==='payment_details'){value=s.payment_details[bank];maximum=1500;body=`<p class="setting-target">${bank==='dc_city'?'DC City':'Alif'}</p>`;}
      if(kind==='help_contact')value=s.help_contact.value;
      if(kind==='help_video'){
        maximum=2048;
        body=`<div class="management-form-pair"><div class="form-field"><label for="helpVideoKey">${esc(t('videoTopic'))}</label><select id="helpVideoKey" class="input">${o.help_video_keys.filter(key=>Object.hasOwn(helpVideoLabels,key)).map(key=>`<option value="${key}">${esc(t(helpVideoLabels[key]))}</option>`).join('')}</select></div><div class="form-field"><label for="helpVideoLanguage">${esc(t('language'))}</label><select id="helpVideoLanguage" class="input">${o.help_languages.filter(lang=>['uz','ru','tj'].includes(lang)).map(lang=>`<option value="${lang}" ${lang===locale?'selected':''}>${lang.toUpperCase()}</option>`).join('')}</select></div></div>`;
      }
      body+=`<div class="form-field"><label for="settingValue">${esc(t(kind==='help_video'?'videoLink':label))}</label><textarea id="settingValue" class="input setting-value" rows="${kind==='payment_details'?5:3}" maxlength="${maximum}" ${kind==='payment_details'?'required':''}>${esc(value)}</textarea></div>`;
    }
    drawer(label,`<form id="managementForm">${body}</form>`,btn('cancel','close')+btn('saveChanges','managementPrepare','primary'));
    if(kind==='help_video')updateHelpVideoField();
  }catch(error){
    if(current===drawerId&&at===epoch&&state.actor)drawer(label,statePanel(errorKey(error)),btn('close','close')+managementReread({type:'setting',kind,bank}));
  }
}
async function prepareManagement(){
  if(managementPreparing||!state.actor||signing||!managementDraft)return;
  const form=$('managementForm');
  if(!form)return;
  const invalid=form.querySelector(':invalid');
  if(invalid){for(let parent=invalid.parentElement;parent&&parent!==form;parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;}
  if(!form.reportValidity())return;
  if(!supportsPasskey()){showNotice('passkeyUnsupported');return;}
  const current=drawerId,at=epoch;
  await singleEditorAction(()=>prepareManagementCommand(current,at));
}
async function prepareManagementCommand(current,at){
  const draft={...managementDraft};let payload;
  if(draft.type==='campaign'){payload={change:campaignChange(draft)};}
  else if(draft.type==='message'){
    const kind=draft.userId?'direct':$('messageKind').value;
    if(draft.userId)draft.texts={uz:$('messageText').value,ru:$('messageText').value,tj:$('messageText').value};
    else draft.texts[draft.textLanguage]=$('messageText').value;
    const filters={};
    if(kind==='broadcast'){
      filters.languages=[...document.querySelectorAll('[data-message-language]:checked')].map(input=>input.dataset.messageLanguage);
      for(const key of Object.keys(messageFilterConfig))if($('messageFilter-'+key).value)filters[key]=$('messageFilter-'+key).value;
    }
    payload={kind,user_id:draft.userId||null,texts:{...draft.texts},filters};
  }else if(draft.type==='message_control'){
    payload={job_id:draft.jobId,operation:draft.controlOperation};
  }else if(draft.type==='delivery'){
    payload={review_id:draft.deliveryId,resolution:$('deliveryResolution').value,reason:$('deliveryReason').value};
  }else if(draft.type==='payout'){
    if($('payoutOperation').value==='complete'){draft.type='payout_completion';payload={payout_id:draft.payoutId};}
    else payload={payout_id:draft.payoutId,operation:$('payoutOperation').value,days:$('payoutOperation').value==='deadline'?Number($('payoutDays').value):null};
  }else if(draft.type==='partner'){
    payload={partner_id:draft.partnerId,operation:$('partnerOperation').value};
  }else if(draft.type==='notice'){
    draft.texts[draft.textLanguage]=$('noticeText').value;
    payload={key:draft.noticeKey,enabled:$('noticeEnabled').value==='true',...Object.fromEntries(['uz','ru','tj'].map(lang=>['text_'+lang,draft.texts[lang]]))};
  }else if(draft.type==='portfolio'){
    const raw=$('portfolioAmount').value;
    if(!/^(?:0|[1-9][0-9]{0,6})(?:\.[0-9]{1,2})?$/.test(raw))return;
    const [whole,fraction='']=raw.split('.'),minor=Number(whole)*100+Number(fraction.padEnd(2,'0'));
    payload={transaction_type:$('portfolioType').value,amount_minor:minor,currency:$('portfolioCurrency').value,note:$('portfolioNote').value};
  }else if(draft.type==='channel'){
    let change;
    if(draft.kind==='mode')change={kind:'mode',enabled:$('channelEnabled').value==='true'};
    else if(draft.kind==='add')change={kind:'add',chat_id:$('channelChat').value,title:$('channelTitle').value,invite_link:$('channelInvite').value||null};
    else change=$('channelOperation').value==='delete'?{kind:'delete',channel_id:draft.channelId}:{kind:'state',channel_id:draft.channelId,is_active:$('channelActive').value==='true'};
    payload={change};
  }else if(draft.type==='user'){
    payload={user_id:draft.userId,operation:draft.userOperation,confirm_user_id:draft.userOperation==='delete'?Number($('manageConfirm').value):null};
  }else if(draft.type==='price'){
    const amount=Number($('priceAmount').value);
    if(!Number.isSafeInteger(amount)||amount<1||amount>1000000)return;
    payload={method:$('priceMethod').value,plan:$('pricePlan').value,amount};
  }else if(draft.type==='payment_qr'){
    const file=draft.mediaFile,validation=$('paymentQrMediaValidation');
    if(!file){if(validation){validation.textContent=t('paymentQrRequired');validation.hidden=false;}return;}
    if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size<1||file.size>1024*1024){
      if(validation){validation.textContent=t(file.size>1024*1024?'paymentQrTooLarge':'paymentQrValidation');validation.hidden=false;}return;
    }
    const digest=await crypto.subtle.digest('SHA-256',await file.arrayBuffer());
    payload={method:draft.method,plan:draft.plan,media_sha256:[...new Uint8Array(digest)].map(byte=>byte.toString(16).padStart(2,'0')).join(''),media_size:file.size};
  }else if(draft.type==='marketing'){
    const change={kind:draft.kind};
    if(draft.kind==='course_ad_create'){
      const language=$('newAdLanguage').value,mediaType=$('newAdMediaType').value,file=draft.mediaFile;
      const placements=[...document.querySelectorAll('[data-course-ad-placement]:checked')].map(input=>input.dataset.courseAdPlacement);
      if(!placements.length){$('courseAdCreateValidation').hidden=false;return;}
      if(!file){$('courseAdMediaValidation').textContent=t('courseAdMediaRequired');$('courseAdMediaValidation').hidden=false;return;}
      const video=mediaType==='video',maxBytes=video?25*1024*1024:1024*1024;
      const allowed=video?['video/mp4','video/quicktime','video/webm','video/x-m4v']:['image/jpeg','image/png','image/webp'];
      if(!allowed.includes(file.type)||file.size<1||file.size>maxBytes){$('courseAdMediaValidation').textContent=t(file.size>maxBytes?(video?'courseAdVideoTooLarge':'courseAdMediaTooLarge'):(video?'courseAdVideoValidation':'courseAdMediaValidation'));$('courseAdMediaValidation').hidden=false;return;}
      const digest=await crypto.subtle.digest('SHA-256',await file.arrayBuffer());
      Object.assign(change,{language,copies:Object.fromEntries(['uz','ru','tj'].map(lang=>[lang,language==='all'||language===lang?{title:$('newAdTitle-'+lang).value,button_text:$('newAdButton-'+lang).value}:null])),
        ad_type:$('newAdType').value,placements,duration_seconds:Number($('newAdDuration').value),link_url:$('newAdLink').value||null,is_active:$('newAdActive').value==='true',media_type:mediaType,
        media_sha256:[...new Uint8Array(digest)].map(byte=>byte.toString(16).padStart(2,'0')).join(''),media_size:file.size});
    }
    if(draft.kind==='campaign_draft'){
      const languages=[...document.querySelectorAll('[data-campaign-language]:checked')].map(input=>input.dataset.campaignLanguage);
      if(!languages.length){$('campaignValidation').hidden=false;return;}
      Object.assign(change,{title:$('campaignTitle').value,texts:Object.fromEntries(['uz','ru','tj'].map(language=>[language,$('campaignText-'+language).value])),
        languages,track:$('campaignTrack').value||null,duration_hours:Number($('campaignDuration').value),include_active_subscribers:$('campaignSubscribers').checked});
    }
    if(draft.kind==='sales_experiment')Object.assign(change,{mode:$('salesMode').value,treatment_percent:Number($('salesPercent').value)});
    if(draft.kind==='desktop_promo')Object.assign(change,{enabled:$('promoEnabled').value==='true',daily_limit:Number($('promoLimit').value),require_learning_progress:$('promoProgress').checked,
      placements:Object.fromEntries(['home_prompt','lesson_end_promo','ad_promo'].map(key=>[key,$('promo-'+key).checked])),
      platforms:Object.fromEntries(['macos','windows','android','ios'].map(key=>[key,$('promo-'+key).checked]))});
    if(draft.kind==='desktop_promo'){
      const file=draft.mediaFile,clearMedia=$('promoMediaClear')?.checked===true;
      change.clear_media=clearMedia;
      if(file){
        const digest=await crypto.subtle.digest('SHA-256',await file.arrayBuffer());
        change.media_sha256=[...new Uint8Array(digest)].map(byte=>byte.toString(16).padStart(2,'0')).join('');
        change.media_size=file.size;
      }
    }
    if(draft.kind==='course_ad'){
      const operation=$('adOperation').value;
      Object.assign(change,{ad_id:draft.ad.id,operation,is_active:operation==='set_active'?$('adActive').value==='true':null});
      if(operation==='replace_image'||operation==='replace_video'){
        const file=draft.mediaFile;
        if(!file){const validation=$('courseAdMediaValidation');validation.textContent=t('courseAdMediaRequired');validation.hidden=false;return;}
        const isVideo=operation==='replace_video';
        const allowed=isVideo?['video/mp4','video/quicktime','video/webm','video/x-m4v']:['image/jpeg','image/png','image/webp'];
        const maxBytes=isVideo?25*1024*1024:1024*1024;
        if(!allowed.includes(file.type)||file.size<1||file.size>maxBytes){
          const validation=$('courseAdMediaValidation');validation.textContent=t(file.size>maxBytes?(isVideo?'courseAdVideoTooLarge':'courseAdMediaTooLarge'):(isVideo?'courseAdVideoValidation':'courseAdMediaValidation'));validation.hidden=false;return;
        }
        const digest=await crypto.subtle.digest('SHA-256',await file.arrayBuffer());
        change.media_sha256=[...new Uint8Array(digest)].map(byte=>byte.toString(16).padStart(2,'0')).join('');
        change.media_size=file.size;
      }
    }
    payload={change};
  }else{
    const change={kind:draft.kind};
    if(draft.kind==='payment_details')Object.assign(change,{bank:draft.bank,value:$('settingValue').value});
    if(draft.kind==='ai_model')change.model=$('settingModel').value;
    if(draft.kind==='help_contact')change.value=$('settingValue').value;
    if(draft.kind==='help_video')Object.assign(change,{key:$('helpVideoKey').value,lang:$('helpVideoLanguage').value,value:$('settingValue').value});
    payload={change};
  }
  if(current!==drawerId||at!==epoch||!state.actor)return;
  try{
    if(draft.type==='payout_completion'){
      if(!draft.proofId||!draft.proofLoaded)throw new ApiError('admin_pwa_proof_invalid',400);
      payload.proof_id=draft.proofId;
    }
    const result=await api(managementEndpoint(draft.type,'prepare'),payload);
    if(current!==drawerId||at!==epoch||!state.actor)return;
    const operation=structuredClone(result.operation);
    if(operation?.action!==managementAction(draft.type,draft.userOperation)||!operation.target||!operation.payload)throw Error('invalid_operation');
    managementReview=Object.freeze({type:draft.type,kind:draft.kind,bank:draft.bank,method:draft.method,plan:draft.plan,userId:draft.userId,userOperation:draft.userOperation,noticeKey:draft.noticeKey,partnerId:draft.partnerId,payoutId:draft.payoutId,deliveryId:draft.deliveryId,jobId:draft.jobId,mediaFile:draft.mediaFile||null,executePayload:structuredClone(result.execute_payload||operation.payload),operation:Object.freeze(operation)});
    if(!managementCurrentUnchanged(draft,result,payload))throw new ApiError('confirmation_changed',409);
    await executeManagement();
  }catch(error){
    managementReview=null;
    if(current===drawerId&&at===epoch&&state.actor){
      if(draft.type==='campaign'&&[400,409].includes(error.status)&&$('campaignCommandValidation')){
        $('campaignCommandValidation').textContent=t(error.message==='admin_pwa_message_too_many_targets'?'messageTooMany':error.message==='admin_pwa_message_no_targets'?'messageNoTargets':'campaignValidation');$('campaignCommandValidation').hidden=false;
      }else if(draft.type==='message'&&[400,409].includes(error.status)&&$('messageValidation')){
        const key=error.message==='admin_pwa_message_no_targets'?'messageNoTargets':error.message==='admin_pwa_message_too_many_targets'?'messageTooMany':'messageInvalid';
        $('messageValidation').textContent=t(key);$('messageValidation').hidden=false;
        $('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=false);
      }else if(draft.type==='notice'&&error.status===400&&$('noticeValidation')){
        $('noticeValidation').textContent=t(error.message==='admin_pwa_notice_too_long'?'noticeTooLong':'noticeInvalid');$('noticeValidation').hidden=false;
        $('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=false);
      }else if(draft.type==='marketing'&&draft.kind==='campaign_draft'&&error.status===400&&$('campaignValidation')){
        $('campaignValidation').textContent=t('campaignValidation');$('campaignValidation').hidden=false;
        $('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=false);
      }else if(draft.type==='marketing'&&draft.kind==='course_ad_create'&&error.status===400&&$('courseAdCreateValidation')){
        $('courseAdCreateValidation').hidden=false;
        $('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=false);
      }else if(draft.type==='marketing'&&draft.kind==='desktop_promo'&&error.status===400&&$('promoMediaValidation')){
        $('promoMediaValidation').textContent=t(error.message==='admin_pwa_media_too_large'?'promoMediaTooLarge':'promoMediaValidation');$('promoMediaValidation').hidden=false;
        $('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=false);
      }else if(draft.type==='marketing'&&draft.kind==='course_ad'&&error.status===400&&$('courseAdMediaValidation')){
        $('courseAdMediaValidation').textContent=t('courseAdMediaValidation');$('courseAdMediaValidation').hidden=false;
        $('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=false);
      }else if(draft.type==='payment_qr'&&[400,413].includes(error.status)&&$('paymentQrMediaValidation')){
        $('paymentQrMediaValidation').textContent=t(error.status===413||error.message==='admin_pwa_media_too_large'?'paymentQrTooLarge':'paymentQrValidation');$('paymentQrMediaValidation').hidden=false;
        $('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=false);
      }else drawer('operationResult',statePanel(error.status===409?'configChanged':errorKey(error)),btn('close','close')+managementReread(draft));
    }
  }
}
async function executeManagement(){
  if(!managementReview||signing||!state.actor)return;
  if(!supportsPasskey()){showNotice('passkeyUnsupported');return;}
  const review=managementReview,operation=structuredClone(review.operation),current=drawerId,at=epoch,control=new AbortController();
  if(operation.action!==managementAction(review.type,review.userOperation))return;
  signing=control;let submitted=false;
  $('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=true);
  try{
    const options=await api('auth/step-up/options',operation);
    if(current!==drawerId||at!==epoch||!state.actor)return;
    const credential=await navigator.credentials.get({publicKey:publicKey(options.publicKey),signal:control.signal});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    await api('auth/step-up/verify',{step_up_id:options.step_up_id,credential:serialize(credential)});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    submitted=true;
    const command={...review.executePayload,step_up_id:options.step_up_id};
    const result=review.type==='payment_qr'&&review.mediaFile
      ?await api('payment-qr/media/save',null,{rawBody:review.mediaFile,extraHeaders:{'X-Admin-PWA-Command':JSON.stringify(command)}})
      :review.type==='marketing'&&['desktop_promo','course_ad','course_ad_create'].includes(review.kind)&&review.mediaFile
      ?await api('marketing/media/save',null,{rawBody:review.mediaFile,extraHeaders:{'X-Admin-PWA-Command':encode(new TextEncoder().encode(JSON.stringify(command))),'X-Admin-PWA-Command-Encoding':'base64url'},timeoutMs:review.executePayload?.change?.operation==='replace_video'||review.executePayload?.change?.media_type==='video'?150000:15000})
      :await api(managementEndpoint(review.type,'save'),command);
    if(current!==drawerId||at!==epoch||!state.actor)return;
    managementReview=null;managementDraft=null;
    if(['message','message_control'].includes(review.type)){await messageJob(result.job.job_id);return;}
    if(review.type==='campaign'&&result.job_id){await messageJob(result.job_id);return;}
    const saved=review.type==='campaign'?result.campaign:review.type==='delivery'?result.delivery:['payout','payout_completion'].includes(review.type)?result.payout:review.type==='partner'?result.partner:review.type==='notice'?result.template:review.type==='price'?result.price:review.type==='payment_qr'?result.qr:review.type==='marketing'?{kind:review.kind,...result.result}:review.type==='channel'?result.channel:review.type==='portfolio'?result.transaction:review.type==='user'?result:result.setting;
    if(review.type==='user'&&result.deleted){state.rows=state.rows.filter(row=>row.user_id!==result.user_id);render();}
    drawer('changesSaved',managementFields(saved,review.type),btn('close','close')+(result.deleted?'':managementReread(review))+(result.job_id?`<button class="btn" data-message-job="${esc(result.job_id)}">${esc(t('messages'))}</button>`:''));
  }catch(error){
    if(current!==drawerId||at!==epoch||!state.actor)return;
    managementReview=null;
    if(!submitted&&['NotAllowedError','AbortError'].includes(error.name)){
      $('drawerFoot').querySelectorAll('button').forEach(button=>button.disabled=false);showNotice('passkeyCancelled');return;
    }
    managementDraft=null;
    releaseManagementMediaPreview();
    const rejected=[400,403,404,409,413,422,429].includes(error.status)||['course_ad_video_unavailable','course_ad_video_busy'].includes(error.message);
    const adMediaKind=review.type==='marketing'&&['course_ad','course_ad_create'].includes(review.kind),adVideo=review.executePayload?.change?.operation==='replace_video'||review.executePayload?.change?.media_type==='video';
    const failureKey=review.type==='marketing'&&review.kind==='desktop_promo'&&error.status===413
      ?'promoMediaTooLarge':review.type==='marketing'&&review.kind==='desktop_promo'&&error.status===400
        ?'promoMediaValidation':adMediaKind&&error.status===413
          ?(adVideo?'courseAdVideoTooLarge':'courseAdMediaTooLarge'):adMediaKind&&error.status===422
          ?'courseAdVideoInvalid':adMediaKind&&error.message==='course_ad_video_unavailable'
            ?'courseAdVideoUnavailable':adMediaKind&&error.message==='course_ad_video_busy'
              ?'courseAdVideoBusy':adMediaKind&&error.status===400
          ?(adVideo?'courseAdVideoValidation':'courseAdMediaValidation'):review.type==='payment_qr'&&error.status===413
            ?'paymentQrTooLarge':review.type==='payment_qr'&&error.status===400
              ?'paymentQrValidation':review.type==='payment_qr'&&error.status===502
                ?'paymentQrUploadFailed':error.status===409?'configChanged':submitted&&!rejected?'configUncertain':errorKey(error);
    drawer('operationResult',statePanel(failureKey),btn('close','close')+managementReread(review));
  }finally{if(signing===control)signing=null;}
}

function localCourseDate(value){
  const d=value?new Date(value):new Date(Date.now()+3*86400000);
  if(!Number.isFinite(d.getTime()))return '';
  return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);
}
async function courseSettings(){
  closeDrawer();const current=drawerId,at=epoch;
  drawer('courseAccess',statePanel('loading'));
  try{
    const data=await api('course-access/read',{});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    coursePolicyRevision=data.revision_hash;
    const policy=data.course_access,selected=policy.mode==='free_until'?'free_until':'subscription';
    const body='<p class="source-note">'+esc(t('courseHint'))+'</p>'
      +'<div class="form-field"><label for="courseMode">'+esc(t('courseMode'))+'</label>'
      +'<select class="input" id="courseMode"><option value="subscription" '+(selected==='subscription'?'selected':'')+'>'+esc(t('courseSubscription'))+'</option>'
      +'<option value="free_until" '+(selected==='free_until'?'selected':'')+'>'+esc(t('courseFreeUntil'))+'</option></select></div>'
      +'<div class="form-field" id="courseUntilField" '+(selected!=='free_until'?'hidden':'')+'>'
      +'<label for="courseUntil">'+esc(t('courseUntil'))+'</label>'
      +'<input class="input" type="datetime-local" id="courseUntil" value="'+esc(localCourseDate(policy.free_until))+'"></div>'
      +'<p class="source-note">'+esc(t('updated'))+': '+esc(date(policy.saved_at))+'</p>';
    drawer('courseAccess',body,btn('cancel','close')+btn('saveChanges','coursePrepare','primary'));
  }catch(error){
    if(current!==drawerId||at!==epoch||!state.actor)return;
    drawer('courseAccess',statePanel(errorKey(error)),btn('close','close')+btn('retry','courseSettings','primary'));
  }
}
async function prepareCoursePolicy(){await singleEditorAction(prepareCoursePolicyCommand);}
async function prepareCoursePolicyCommand(){
  if(!state.actor||signing)return;
  const mode=$('courseMode')?.value,input=$('courseUntil');
  if(!['subscription','free_until'].includes(mode))return;
  let freeUntil=null;
  if(mode==='free_until'){
    if(!input?.value)return;
    const parsed=new Date(input.value),now=Date.now();
    if(!Number.isFinite(parsed.getTime())||parsed.getTime()<=now||parsed.getTime()>now+365*86400000){showNotice('error');return;}
    freeUntil=parsed.toISOString();
  }
  const current=drawerId,at=epoch;
  $('drawerFoot')?.querySelectorAll('button').forEach(b=>b.disabled=true);
  try{
    const data=await api('course-access/prepare',{mode,free_until:freeUntil});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    confirmation=Object.freeze(structuredClone(data.operation));
    if(confirmation.action!=='course.access_policy'||confirmation.target!=='global')throw Error('invalid_policy');
    if(confirmation.payload.expected_hash!==coursePolicyRevision)throw new ApiError('confirmation_changed',409);
    await executeCoursePolicy();
  }catch(error){
    if(current!==drawerId||at!==epoch||!state.actor)return;
    confirmation=null;
    drawer('courseAccess',statePanel(error.status===409?'changed':errorKey(error)),
      btn('close','close')+btn('retry','courseSettings','primary'));
  }
}
async function executeCoursePolicy(){
  if(confirmation?.action!=='course.access_policy'||!supportsPasskey()||signing)return;
  const operation=structuredClone(confirmation),current=drawerId,at=epoch,control=new AbortController();
  signing=control;let submitted=false;
  $('drawerFoot')?.querySelectorAll('button').forEach(b=>b.disabled=true);
  try{
    const options=await api('auth/step-up/options',operation);
    if(current!==drawerId||at!==epoch)return;
    const credential=await navigator.credentials.get({publicKey:publicKey(options.publicKey),signal:control.signal});
    if(current!==drawerId||at!==epoch)return;
    await api('auth/step-up/verify',{step_up_id:options.step_up_id,credential:serialize(credential)});
    if(current!==drawerId||at!==epoch)return;
    submitted=true;
    const result=await api('course-access/save',{...operation.payload,step_up_id:options.step_up_id});
    if(current!==drawerId||at!==epoch)return;
    confirmation=null;
    const policy=result.course_access;
    if(courseData&&state.route==='course')courseData.course_access=structuredClone(policy);
    drawer('courseSaved',profileFields([['courseMode',t(policy.mode==='free_until'?'courseFreeUntil':'courseSubscription')],
      ['courseUntil',date(policy.free_until)]]),btn('close','close'));
  }catch(error){
    if(current!==drawerId||at!==epoch)return;
    confirmation=null;
    if(!submitted&&['NotAllowedError','AbortError'].includes(error.name)){showNotice('passkeyCancelled');return;}
    const rejected=[400,403,404,409].includes(error.status);
    drawer('courseAccess',statePanel(error.status===409?'changed':submitted&&!rejected?'uncertain':errorKey(error)),
      btn('close','close')+btn('courseAccess','courseSettings','primary'));
  }finally{if(signing===control)signing=null;}
}


async function hsk30Settings(){
  closeDrawer();const current=drawerId,at=epoch;
  drawer('hsk30Settings',statePanel('loading'));
  try{
    const data=await api('hsk30/read',{});
    if(current!==drawerId||at!==epoch||!state.actor)return;
    const policy=data.hsk30;hsk30Baseline=structuredClone(policy);
    if(!Array.isArray(policy.available_levels)||!Array.isArray(policy.live_levels))throw Error('invalid_hsk30');
    const pick=(id,value,label)=>'<div class="form-field"><label for="'+id+'">'+esc(t(label))+'</label><select id="'+id+'" class="input"><option value="true" '+(value?'selected':'')+'>'+esc(t('hsk30On'))+'</option><option value="false" '+(!value?'selected':'')+'>'+esc(t('hsk30Off'))+'</option></select></div>';
    const levels=policy.available_levels.map(level=>'<label class="hsk30-level-option"><input type="checkbox" data-hsk30-level="'+esc(level)+'" '+(policy.live_levels.includes(level)?'checked':'')+'> '+esc(level.toUpperCase())+'</label>').join('');
    const body='<p class="source-note">'+esc(t('hsk30Note'))+'</p>'
      +pick('hsk30Enabled',policy.enabled,'hsk30Enabled')
      +pick('hsk30Pay',policy.unlock_payment_enabled,'hsk30PaymentEnabled')
      +'<div class="form-field"><label for="hsk30Price">'+esc(t('hsk30Price'))+'</label>'
      +'<input class="input" id="hsk30Price" type="number" min="1" max="10000" step="1" value="'+esc(policy.unlock_price_tjs)+'" required></div>'
      +'<fieldset class="form-field"><legend>'+esc(t('hsk30Levels'))+'</legend>'+levels+'</fieldset>';
    drawer('hsk30Settings',body,btn('cancel','close')+btn('saveChanges','hsk30Prepare','primary'));
  }catch(error){
    if(current!==drawerId||at!==epoch||!state.actor)return;
    drawer('hsk30Settings',statePanel(errorKey(error)),btn('close','close')+btn('retry','hsk30Settings','primary'));
  }
}
async function prepareHsk30Settings(){
  if(!$('hsk30Price')?.reportValidity())return;
  await singleEditorAction(prepareHsk30SettingsCommand);
}
async function prepareHsk30SettingsCommand(){
  if(!state.actor||signing)return;
  const priceInput=$('hsk30Price');
  if(!priceInput?.reportValidity())return;
  const price=Number(priceInput.value);
  if(!Number.isInteger(price)||price<1||price>10000)return;
  const levels=[...document.querySelectorAll('[data-hsk30-level]')].filter(x=>x.checked).map(x=>x.dataset.hsk30Level);
  const policy={enabled:$('hsk30Enabled')?.value==='true',
    unlock_payment_enabled:$('hsk30Pay')?.value==='true',
    unlock_price_tjs:price,live_levels:levels};
  const current=drawerId,at=epoch;
  $('drawerFoot')?.querySelectorAll('button').forEach(b=>b.disabled=true);
  try{
    const response=await api('hsk30/prepare',policy);
    if(current!==drawerId||at!==epoch||!state.actor)return;
    confirmation=Object.freeze(structuredClone(response.operation));
    if(confirmation.action!=='hsk30.settings'||confirmation.target!=='global')throw Error('invalid_hsk30');
    if(JSON.stringify(response.current)!==JSON.stringify(hsk30Baseline))throw new ApiError('confirmation_changed',409);
    await executeHsk30Settings();
  }catch(error){
    if(current!==drawerId||at!==epoch||!state.actor)return;
    confirmation=null;
    drawer('hsk30Settings',statePanel(error.status===409?'changed':errorKey(error)),
      btn('close','close')+btn('retry','hsk30Settings','primary'));
  }
}
async function executeHsk30Settings(){
  if(confirmation?.action!=='hsk30.settings'||!supportsPasskey()||signing)return;
  const operation=structuredClone(confirmation),current=drawerId,at=epoch,control=new AbortController();
  signing=control;let submitted=false;
  $('drawerFoot')?.querySelectorAll('button').forEach(b=>b.disabled=true);
  try{
    const options=await api('auth/step-up/options',operation);
    if(current!==drawerId||at!==epoch)return;
    const credential=await navigator.credentials.get({publicKey:publicKey(options.publicKey),signal:control.signal});
    if(current!==drawerId||at!==epoch)return;
    await api('auth/step-up/verify',{step_up_id:options.step_up_id,credential:serialize(credential)});
    if(current!==drawerId||at!==epoch)return;
    submitted=true;
    const result=await api('hsk30/save',{...operation.payload,step_up_id:options.step_up_id});
    if(current!==drawerId||at!==epoch)return;
    confirmation=null;
    const p=result.hsk30;
    if(courseData&&state.route==='course')courseData.hsk30=structuredClone(p);
    drawer('hsk30Saved',profileFields([
      ['hsk30Enabled',t(p.enabled?'hsk30On':'hsk30Off')],
      ['hsk30PaymentEnabled',t(p.unlock_payment_enabled?'hsk30On':'hsk30Off')],
      ['hsk30Price',String(p.unlock_price_tjs)+' TJS'],
      ['hsk30Levels',p.live_levels.join(', ')||'—']
    ]),btn('close','close'));
  }catch(error){
    if(current!==drawerId||at!==epoch)return;
    confirmation=null;
    if(!submitted&&['NotAllowedError','AbortError'].includes(error.name)){showNotice('passkeyCancelled');return;}
    const rejected=[400,403,404,409].includes(error.status);
    drawer('hsk30Settings',statePanel(error.status===409?'changed':submitted&&!rejected?'uncertain':errorKey(error)),
      btn('close','close')+btn('hsk30Settings','hsk30Settings','primary'));
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
    drawer('review',summary(operation)+`<p class="alert" id="receiptStatus">${esc(t('receiptMissing'))}</p>${fingerprint?`<img class="receipt-image" id="receiptImage" alt="${esc(t('receipt'))}">`:''}<div class="form-field"><label for="rejectReason">${esc(t('reason'))}</label><textarea id="rejectReason" class="input textarea" maxlength="300"></textarea></div>`,btn('rejectPayment','reject','danger',true)+btn('acceptPayment','approve','primary',true));
    if(fingerprint) {
      const image=$('receiptImage');image.onload=()=>{if(current!==drawerId)return;receiptLoaded=true;$('receiptStatus').hidden=true;document.querySelectorAll('[data-action="approve"],[data-action="reject"]').forEach(button=>button.disabled=false);};
      image.onerror=()=>{if(current===drawerId)receiptLoaded=false;};
      image.src=`/api/admin/v1/payments/${paymentId}/receipt?receipt_sha256=${encodeURIComponent(fingerprint)}`;
    }
  } catch(error){if(current===drawerId&&state.actor)drawer('review',statePanel(error.status===409?'changed':'error'));}
}
async function prepareDecision(decision){
  if(decision==='reject'&&!$('rejectReason')?.value.trim()){$('rejectReason')?.focus();return;}
  await singleEditorAction(()=>prepareDecisionCommand(decision));
}
async function prepareDecisionCommand(decision) {
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
  await execute();
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
    if(!submitted&&['NotAllowedError','AbortError'].includes(error.name)){showNotice('passkeyCancelled');return;}
    confirmation=null;receiptLoaded=false;
    drawer('review',statePanel(submitted?'uncertain':errorKey(error)));
    if(submitted)await load();
  } finally {if(signing===control)signing=null;}
}

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
const autoImportantSources=new Set(['payment','android','technical']);
function inboxTitle(row){
  const label=row.source==='payment'?'inboxPaymentReceipt':row.source==='android'?'inboxAndroid':row.source==='technical'?'inboxTechnical':row.source==='release'?'releaseFeedback':'botFeedback';
  return t(label)+(row.user_id?' · '+t('account')+' '+row.user_id:'');
}
function inboxEntry(row){
  const unread=row.triage_status==='new', important=autoImportantSources.has(row.source);
  if(!['bot','release','android','payment','technical'].includes(row.source)||
     !Number.isSafeInteger(row.source_id)||row.source_id<1)return '';
  return `<button type="button" class="inbox-minimal-row ${unread?'is-unread':'is-read'} ${important?'is-important':''}"
    data-inbox-open="${row.source}:${row.source_id}" aria-label="${esc(inboxTitle(row))}">
      <span class="inbox-row-dot" aria-hidden="true"></span>
      <span class="inbox-row-title">${esc(inboxTitle(row))}</span>
      ${icon('chevron')}
    </button>`;
}
function inboxDetails(row) {
  const source=row.source,id=row.source_id;
  const canView=(source==='android'?row.has_attachment:['bot','release'].includes(source)&&row.image_preview_available===true)
    &&Number.isSafeInteger(id)&&id>0&&id<=2147483647;
  const attachmentId=`inboxAttachment-${source}-${id}`;
  return `<div class="inbox-details">
    <button class="inbox-back" data-action="inboxBack" type="button">${icon('chevron')}${esc(t('feedback'))}</button>
    <h2>${esc(inboxTitle(row))}</h2>
    <time>${esc(date(row.created_at))}</time>
    ${row.message?`<p class="inbox-details-text">${esc(row.message)}</p>`:''}
    ${row.rating?`<p>${esc(row.rating)}/5</p>`:''}
    ${row.app_version?`<p>${esc(row.app_version)}</p>`:''}
    ${row.screen?`<p>${esc(row.screen)}</p>`:''}
    ${canView?`<button type="button" class="btn" data-inbox-attachment="${id}"
      data-attachment-source="${source}" aria-controls="${attachmentId}" aria-expanded="false">${esc(t('viewAttachment'))}</button>
      <div class="inbox-attachment" id="${attachmentId}" aria-live="polite" hidden></div>`:''}
  </div>`;
}
let currentInboxRows=[];
async function openInbox(source,id) {
  if(inboxUpdating||!state.actor)return;
  const row=currentInboxRows.find(item=>item.source===source&&item.source_id===id);
  if(!row)return;
  const current=drawerId,at=epoch;
  inboxUpdating=true;
  try {
    if(row.triage_status==='new'){
      // Persist read before presenting details; a payment receipt is not approved.
      await api('inbox/triage',{source,source_id:id,operation:'mark_read',expected_revision:row.triage_revision});
      if(current!==drawerId||at!==epoch||!state.actor)return;
      row.triage_status='read';row.triage_revision++;
      await refreshInboxUnread();
    }
    if(current!==drawerId||at!==epoch||!state.actor)return;
    const originatingUser=feedbackUserId;
    if(source==='payment'){
      await review(id);
      if(state.actor&&$('overlay'))drawerBack=()=>inbox(null,originatingUser);
      return;
    }
    drawer('feedback',inboxDetails(row),null,'inbox-drawer');
    drawerBack=()=>inbox(null,originatingUser);
  }catch(error){
    if(current!==drawerId||at!==epoch||!state.actor)return;
    showNotice(error.status===409?'inboxChanged':'inboxActionError');
    await inbox(null,feedbackUserId);
  }finally{inboxUpdating=false;}
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
  closeDrawer();feedbackUserId=userId;inboxNextCursor=null;currentInboxRows=[];const current=drawerId;
  drawer('feedback',statePanel('loading'),null,'inbox-drawer');
  try {
    const data=await api('inbox/list',{source:'all',priority:'all',status:'all',period:'all_time',
      search:null,user_id:userId,before,limit:30});
    if(current!==drawerId||!state.actor)return;
    inboxNextCursor=data.next_before;currentInboxRows=data.items;
    const body=`<div class="inbox-shell inbox-minimal">
      ${userId?`<p class="inbox-account">${esc(t('account'))} #${esc(userId)}</p>`:''}
      <div class="inbox-minimal-list">${data.items.map(inboxEntry).join('')||statePanel('empty')}</div>
      ${inboxNextCursor?`<button type="button" class="btn inbox-more" data-feedback-next="1">${esc(t('next'))}</button>`:''}
    </div>`;
    drawer('feedback',body,null,'inbox-drawer');
  }catch(error){if(current===drawerId&&state.actor)drawer('feedback',statePanel('error'),null,'inbox-drawer');}
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
async function registerPushSubscription(subscription,platform){
  const payload=subscription.toJSON(),keys=payload.keys||{};
  if(!payload.endpoint||!keys.p256dh||!keys.auth)throw Error('invalid_push_subscription');
  return api('push/subscribe',{platform,endpoint:payload.endpoint,
    keys:{p256dh:keys.p256dh,auth:keys.auth}});
}
async function restorePushAfterLogin(){
  const platform=applePushPlatform(),at=epoch;
  if(!state.actor?.push_available||!platform||!pushInstallReady(platform)||document.hidden||
     !('Notification' in window)||Notification.permission==='denied'||
     !('serviceWorker' in navigator)||!('PushManager' in window))return;
  try{
    const registration=await navigator.serviceWorker.ready;
    const data=await api('push/list',{});
    if(at!==epoch||!state.actor)return;
    const existing=await registration.pushManager.getSubscription();
    if(at!==epoch||!state.actor)return;
    const prepared={registration,key:decode(data.vapid_public_key),previous:!!existing,epoch:at};
    if(Notification.permission==='granted'){
      try{
        // Permission was already granted: repair/register silently on each
        // authenticated app launch. Never show another OS permission prompt.
        const subscription=existing||await registration.pushManager.subscribe({
          userVisibleOnly:true,applicationServerKey:prepared.key
        });
        if(at!==epoch||!state.actor)return;
        await registerPushSubscription(subscription,platform);
        return;
      }catch(_){ /* Some WebKit versions still require a fresh tap. */ }
    }
    if(at!==epoch||!state.actor)return;
    pushReady=prepared;updatePushQuickButton();
  }catch(_){ /* Fail closed; settings still shows the server error. */ }
}
async function pushSettings(){
  if(!state.actor?.push_available)return;
  closeDrawer();pushReady=null;updatePushQuickButton();const current=drawerId,at=epoch;
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
      updatePushQuickButton();
    }
    const rows=data.subscriptions||[];
    const devices=rows.map(row=>`<article class="feedback-item settings-device-row"><div><strong>${esc(row.platform==='iphone'?'iPhone':'Mac')}</strong><small>${esc(date(row.created_at))}</small></div><button class="btn quiet-action danger" data-push-revoke="${esc(row.id)}">${esc(t('pushRevoke'))}</button></article>`).join('')||statePanel('empty');
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
    try{
      await registerPushSubscription(subscription,applePushPlatform());
    }catch(error){
      if(!prepared.previous)await subscription.unsubscribe().catch(()=>{});
      throw error;
    }
    if(at!==epoch||current!==drawerId||!state.actor)return;
    const settingsOpen=!!document.querySelector('.push-settings');
    pushReady=null;updatePushQuickButton();showNotice('pushSaved');
    if(settingsOpen)await pushSettings();
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
    drawer('mcpConnections',`<p class="source-note">${esc(t('mcpLifecycle'))}</p><div class="mcp-history">${rows.map(row=>`<article class="feedback-item"><strong class="mcp-client-name">${esc(row.client_id)}</strong><p>${esc(t('mcpPermission'))}</p><p class="pill">${esc(t(mcpStateKey(row)))}</p><p><small>${esc(date(row.created_at))}${row.access_expires_at?' · '+esc(t('mcpAccessUntil'))+' '+esc(date(row.access_expires_at)):''}</small></p>${['pending','approved','redeemed'].includes(row.status)?`<button class="btn quiet-action danger" data-mcp-revoke="${esc(row.id)}">${esc(t('mcpRevoke'))}</button>`:''}</article>`).join('')||statePanel('empty')}</div>`);
  }catch(error){
    if(current!==drawerId||!state.actor)return;
    drawer('mcpConnections',statePanel(error.status===404?'notReady':error.status===403?'authFailed':navigator.onLine?'error':'offline'),btn('close','close')+btn('retry','mcpConnections','primary'));
  }
}
async function confirmMcpRevoke(id,label){
  if(!/^[0-9a-f-]{36}$/.test(id)||!state.actor?.mcp_available)return;
  revokeTarget=id;await revokeMcp();
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
      if(name==='logout'){await api('auth/logout',{});automaticLoginAttempted=true;clearPrivate('signin');}
    }catch(error){if(error.message!=='stale'){state.error=['signin','enroll'].includes(name)?errorKey(error):'authFailed';render();}}
    finally{busy=false;render();}return;
  }
  if(name==='close'){closeDrawer();if(state.route==='course'&&courseData)render();return;}
  if(name==='boot'){await lockAndRequirePasskey();return;}
  if(name==='reload'){await load();return;}
  if(name==='mcpConnections'){await mcpConnections();return;}
  if(name==='pushSettings'){await pushSettings();return;}
  if(name==='courseSettings'){await courseSettings();return;}
  if(name==='limitsPrepare'){await prepareCourseLimits();return;}
  if(name==='trialPrepare'){await prepareCourseLimits(true);return;}
  if(name==='priceSettings'){await priceSettings();return;}
  if(name==='priceQrSettings'){await priceQrSettings();return;}
  if(name==='messageList'){await messageList();return;}
  if(name==='messageEditor'){messageEditor();return;}
  if(name==='deliveryList'){await deliveryEditor();return;}
  if(name==='payoutList'){await payoutEditor();return;}
  if(name==='partnerList'){await partnerEditor();return;}
  if(name==='noticeList'){await noticeEditor();return;}
  if(name==='portfolioHistory'){await portfolioHistory();return;}
  if(name==='portfolioEditor'){portfolioEditor();return;}
  if(name==='managementPrepare'){await prepareManagement();return;}
  if(name==='hsk30Settings'){await hsk30Settings();return;}
  if(name==='hsk30Prepare'){await prepareHsk30Settings();return;}
  if(name==='coursePrepare'){await prepareCoursePolicy();return;}
  if(name==='pushEnable'){await enablePush();return;}
  if(name==='mcpRevokeConfirm'){await revokeMcp();return;}
  if(name==='feedback'){await inbox();return;}
  if(name==='inboxBack'){await inbox(null,feedbackUserId);return;}
  if(name==='approve'||name==='reject'){await prepareDecision(name);return;}
  if(name==='more'){
    const sections=['course','marketing','system'].map(route=>managementRow(t(route),'data-route="'+route+'"',{course:'book',marketing:'mega',system:'settings'}[route])).join('');
    const extras=(state.actor.mcp_available?btn('mcpConnections','mcpConnections'):'')+(state.actor.push_available?btn('pushTitle','pushSettings'):'');
    drawer('more',`<div class="more-sheet-content"><div class="more-sheet-list">${sections}</div><div class="more-sheet-extras">${extras}${languageSelect('drawerLocale')}</div></div>`,btn('install','install')+btn('logout','logout'),'more-drawer');return;
  }

  if(name==='install'){if(installPrompt){await installPrompt.prompt();installPrompt=null;}else showNotice('installHint');return;}
  if(name==='update'){publicRegistration?.waiting?.postMessage('ACTIVATE_PUBLIC_SHELL');return;}
  if(name==='next'&&state.next){state.previous.push(state.cursor);state.cursor=state.next;await load();}
  if(name==='previous'&&state.previous.length){state.cursor=state.previous.pop();await load();}
  if(name==='period'||name==='platform'){const menu=$(name+'Menu');menu.hidden=!menu.hidden;document.querySelector(`[data-action="${name}"]`).setAttribute('aria-expanded',String(!menu.hidden));}
}
// iPhone PWA: one-step right swipe from the left 30% of the screen.
// Native Safari owns the extreme left edge when this is not a standalone PWA.
function canSwipeBack(target) {
  if(!state.actor||state.phase!=='ready'||busy||managementPreparing||signing||inboxUpdating||backSwipeInProgress||
     document.querySelector('.canvas-overlay .confirmation[aria-busy="true"]'))return false;
  if(target.closest('input,textarea,select,[contenteditable],.mobile-tabs,[role="slider"]'))return false;
  for(let node=target;node&&node!==document.body;node=node.parentElement){
    if(node.scrollWidth>node.clientWidth+8&&
       ['auto','scroll'].includes(getComputedStyle(node).overflowX))return false;
  }
  return Boolean($('overlay')||state.route!=='home'||sectionBackStack.length);
}
async function oneStepBack() {
  if(backSwipeInProgress)return;
  backSwipeInProgress=true;
  try{
    if($('overlay')){
      const previous=drawerBack;
      drawerBack=null;
      if(previous)await previous();
      else closeDrawer();
    }else if(state.actor){
      const previous=sectionBackStack.pop();
      if(previous||state.route!=='home'){
        state.route=previous||'home';state.cursor=null;state.previous=[];state.query='';
        await load();
      }
    }
  }finally{backSwipeInProgress=false;}
}
const iosTouchDevice=/iPhone|iPad|iPod/.test(navigator.userAgent||'')||
  (/Macintosh/.test(navigator.userAgent||'')&&navigator.maxTouchPoints>1);
if(iosTouchDevice){
  document.addEventListener('touchstart',event=>{
    backSwipeStart=null;
    if(event.touches.length!==1||!canSwipeBack(event.target))return;
    const touch=event.touches[0],standalone=navigator.standalone===true||
      window.matchMedia?.('(display-mode: standalone)').matches===true;
    if(touch.clientX>window.innerWidth*0.30||(!standalone&&touch.clientX<24))return;
    backSwipeStart={x:touch.clientX,y:touch.clientY,id:touch.identifier,at:Date.now()};
  },{passive:true});
  document.addEventListener('touchcancel',()=>{backSwipeStart=null;},{passive:true});
  document.addEventListener('touchend',event=>{
    const start=backSwipeStart;backSwipeStart=null;
    if(!start||event.touches.length||event.changedTouches.length!==1||!canSwipeBack(event.target))return;
    const touch=event.changedTouches[0];
    if(touch.identifier!==start.id||Date.now()-start.at>900)return;
    const dx=touch.clientX-start.x,dy=Math.abs(touch.clientY-start.y);
    if(dx<Math.max(72,window.innerWidth*0.28)||dy>Math.max(35,dx*0.35))return;
    blockSwipeClickUntil=Date.now()+400;
    oneStepBack().catch(()=>showNotice('error'));
  },{passive:true});
  // A completed swipe must never also activate a button beneath the finger.
  document.addEventListener('click',event=>{
    if(Date.now()<blockSwipeClickUntil){event.preventDefault();event.stopImmediatePropagation();}
  },true);
}
document.addEventListener('keydown',event=>{
  const row=event.target.closest('tr[data-user-row]');
  if(row&&event.target===row&&(event.key==='Enter'||event.key===' ')){
    event.preventDefault();userProfile(Number(row.dataset.userRow));
  }
});
document.addEventListener('click',event=>{
  if(!event.target.closest('.action-disclosure,.header-dropdown'))closeActionMenus();
  if(userFilterOpen&&!event.target.closest('.user-filter-area')){
    userFilterOpen=false;const panel=$('userFilterPanel');if(panel)panel.hidden=true;
    document.querySelector('[data-user-filter-toggle]')?.setAttribute('aria-expanded','false');
  }
  const button=event.target.closest('button');
  if(!button){const row=event.target.closest('tr[data-user-row]');if(row){userProfile(Number(row.dataset.userRow));return;}}
  if(!button||button.disabled)return;
  const run=async()=>{
    if(button.hasAttribute('data-user-filter-toggle')){
      userFilterOpen=!userFilterOpen;
      const panel=$('userFilterPanel');
      if(panel)panel.hidden=!userFilterOpen;
      button.setAttribute('aria-expanded',String(userFilterOpen));
    }
    else if(button.dataset.userSegment){
      // Applying a segment must also include unsent text currently in the box.
      // Otherwise the rerender discards the user's query and uses the old one.
      if($('userQuery'))state.query=$('userQuery').value;
      userFilterOpen=false;state.segment=button.dataset.userSegment;state.cursor=null;state.previous=[];await load();
    }
    else if(button.dataset.userDays){
      const input=$('accessDays');if(input){input.value=button.dataset.userDays;
        document.querySelectorAll('[data-user-days]').forEach(item=>item.classList.toggle('selected',item===button));}
    }
    else if(button.dataset.userDiscount){campaignCreate('discount',Number(button.dataset.userDiscount));}
    else if(button.dataset.menuToggle){toggleActionMenu(button);}
    else if(button.dataset.route){
      if(state.route!==button.dataset.route)sectionBackStack.push(state.route);
      cancelStatisticsDownload();feedbackLoadId++;feedbackStats.data=null;feedbackStats.loading=false;
      closeDrawer();state.route=button.dataset.route;state.cursor=null;state.previous=[];state.query='';state.segment='all';userFilterOpen=false;await load();
    }
    else if(button.dataset.campaignList){await campaignList(button.dataset.campaignList,Number(button.dataset.before)||null);}
    else if(button.dataset.campaignDetail){await campaignDetail(button.dataset.campaignKind,Number(button.dataset.campaignDetail));}
    else if(button.dataset.campaignCreate){campaignCreate(button.dataset.campaignCreate);}
    else if(button.dataset.marketingKind){await marketingEditor(button.dataset.marketingKind);}
    else if(button.dataset.paymentQrTarget){
      const match=/^(alipay|wechat)-(10_days|1_month|3_months)$/.exec(button.dataset.paymentQrTarget);
      if(match)await priceQrSettings(match[1],match[2]);
    }
    else if(button.dataset.marketingNext){await marketingEditor('course_ad',Number(button.dataset.marketingNext));}
    else if(button.dataset.courseAd){editCourseAd(Number(button.dataset.courseAd));}
    else if(button.dataset.userManagement){userManagementEditor(Number(button.dataset.userManagement),button.dataset.userOperation);}
    else if(button.dataset.channelsKind){await channelEditor(button.dataset.channelsKind);}
    else if(button.dataset.channelsNext){await channelEditor('list',Number(button.dataset.channelsNext));}
    else if(button.dataset.channelId){editChannel(Number(button.dataset.channelId));}
    else if(button.dataset.messageUser){messageEditor(Number(button.dataset.messageUser));}
    else if(button.dataset.messageNext){await messageList(button.dataset.messageNext);}
    else if(button.dataset.messageJob){await messageJob(button.dataset.messageJob);}
    else if(button.dataset.messageRun){await runMessage(button.dataset.messageRun);}
    else if(button.dataset.messageStop){await confirmMessageStop(button.dataset.messageStop);}
    else if(button.dataset.messageStopConfirm){await stopMessage(button.dataset.messageStopConfirm);}
    else if(button.dataset.messageControl){messageControlEditor(button.dataset.jobId,button.dataset.messageControl);}
    else if(button.dataset.deliveryId){await deliveryEditor(button.dataset.deliveryId);}
    else if(button.dataset.deliveryNext){await deliveryEditor(null,button.dataset.deliveryNext);}
    else if(button.dataset.payoutId){await payoutEditor(Number(button.dataset.payoutId));}
    else if(button.dataset.payoutNext){await payoutEditor(null,Number(button.dataset.payoutNext));}
    else if(button.dataset.partnerId){await partnerEditor(Number(button.dataset.partnerId));}
    else if(button.dataset.partnerNext){await partnerEditor(null,Number(button.dataset.partnerNext));}
    else if(button.dataset.noticeKey){await noticeEditor(button.dataset.noticeKey);}
    else if(button.dataset.portfolioNext){await portfolioHistory(Number(button.dataset.portfolioNext));}
    else if(button.dataset.courseTab){keepCourseEdits();state.courseTab=button.dataset.courseTab;render();}
    else if(button.dataset.courseStats){state.route='stats';state.statsTab='course';await load();}
    else if(button.dataset.statsTab){
      const next=button.dataset.statsTab;
      if(['overview','course','platform','funnel','money','sources','report'].includes(next)&&state.route==='stats'){
        const left=button.closest('.stats-category-tabs')?.scrollLeft||0;
        state.statsTab=next;render();const tabs=document.querySelector('.stats-category-tabs');if(tabs)tabs.scrollLeft=left;
        if(next==='report'&&!feedbackStats.data&&!feedbackStats.loading)loadFeedbackStats();
      }
    }
    else if(button.dataset.period){state.period=button.dataset.period;await load();}
    else if(button.dataset.platform){state.platform=button.dataset.platform;if(state.route==='stats'&&state.platform!=='overall')state.statsTab='platform';await load();}
    else if(button.dataset.exportFormat){await exportStatistics(button.dataset.exportFormat);}
    else if(button.dataset.feedbackExport){await exportStatistics(button.dataset.feedbackExport,'feedback');}
    else if(button.dataset.feedbackPeriod||button.dataset.feedbackSource||button.dataset.feedbackRetry){
      cancelStatisticsDownload();feedbackLoadId++;feedbackStats.data=null;feedbackStats.loading=false;
      if(button.dataset.feedbackPeriod)feedbackStats.period=button.dataset.feedbackPeriod;
      if(button.dataset.feedbackSource)feedbackStats.source=button.dataset.feedbackSource;
      await loadFeedbackStats();
    }
    else if(button.dataset.status){state.status=button.dataset.status;state.cursor=null;state.previous=[];await load();}
    else if(button.dataset.review){await review(Number(button.dataset.review));}
    else if(button.dataset.userDetail){await userProfile(Number(button.dataset.userDetail));}
    else if(button.dataset.accessUser){accessGrantForm(Number(button.dataset.accessUser));}
    else if(button.dataset.settingKind){await editSetting(button.dataset.settingKind,button.dataset.bank||null);}
    else if(button.dataset.prepareAccess){await prepareAccess(Number(button.dataset.prepareAccess));}
    else if(button.dataset.profilePayments){await moreUserPayments(Number(button.dataset.profilePayments),Number(button.dataset.before),button);}
    else if(button.dataset.userFeedback){await inbox(null,Number(button.dataset.userFeedback));}
    else if(button.dataset.inboxOpen){
      const match=/^(bot|release|android|payment|technical):([1-9][0-9]*)$/.exec(button.dataset.inboxOpen);
      if(match)await openInbox(match[1],Number(match[2]));
    }
    else if(button.dataset.inboxAttachment){await viewInboxAttachment(button);}
    else if(button.dataset.feedbackNext&&inboxNextCursor){await inbox(inboxNextCursor,feedbackUserId);}
    else if(button.dataset.pushRevoke){await revokePush(button.dataset.pushRevoke);}
    else if(button.dataset.mcpRevoke){await confirmMcpRevoke(button.dataset.mcpRevoke,button.closest('article').querySelector('strong').textContent);}
    else if(button.dataset.action){await action(button.dataset.action);}
  };run().catch(error=>{if(error.message!=='stale')showNotice(errorKey(error));});
});
document.addEventListener('input',event=>{if(event.target.matches('[data-course-limit],#courseTrialDays,#courseTrialReason'))keepCourseEdits();});
document.addEventListener('change',event=>{
  if(event.target.id==='courseLimitPlan'){keepCourseEdits();courseLimitPlan=event.target.value;render();return;}
  if(event.target.matches('[data-course-window],#courseTrialEnabled')){keepCourseEdits();return;}
  if(event.target.id==='discountTarget'&&$('discountSegment'))$('discountSegment').hidden=Boolean(event.target.value);
  if(event.target.id==='newAdLanguage')updateCourseAdCreateLanguage();
  if(event.target.id==='newAdMediaType'){updateCourseAdCreateMedia();return;}
  if(['messageKind','payoutOperation','partnerOperation','channelOperation','adOperation'].includes(event.target.id))updateManagementAction();
  if(event.target.id==='messageLanguage')updateMessageLanguage();
  if(event.target.id==='messageKind'&&$('messageFilters'))$('messageFilters').hidden=event.target.value==='test';
  if(event.target.id==='payoutProofFile'){void stagePayoutProof(event.target.files[0]);return;}
  if(['promoMediaFile','courseAdMediaFile','paymentQrMediaFile'].includes(event.target.id)){
    const isCourseAd=event.target.id==='courseAdMediaFile',isPaymentQr=event.target.id==='paymentQrMediaFile';
    const isCourseAdVideo=isCourseAd&&($('adOperation')?.value==='replace_video'||managementDraft?.kind==='course_ad_create'&&$('newAdMediaType')?.value==='video');
    const file=event.target.files?.[0]||null,allowed=isCourseAdVideo?['video/mp4','video/quicktime','video/webm','video/x-m4v']:['image/jpeg','image/png','image/webp'];
    const maxBytes=isCourseAdVideo?25*1024*1024:isCourseAd||isPaymentQr?1024*1024:2*1024*1024;
    const previewId=isCourseAd?'courseAdMediaPreview':isPaymentQr?'paymentQrMediaPreview':'promoMediaPreview';
    const validationId=isCourseAd?'courseAdMediaValidation':isPaymentQr?'paymentQrMediaValidation':'promoMediaValidation';
    const invalid=file&&(!allowed.includes(file.type)||file.size<1||file.size>maxBytes);
    const validation=$(validationId);
    if(validation){validation.hidden=!invalid;if(invalid&&(isCourseAd||isPaymentQr))validation.textContent=t(file.size>maxBytes?(isPaymentQr?'paymentQrTooLarge':isCourseAdVideo?'courseAdVideoTooLarge':'courseAdMediaTooLarge'):(isPaymentQr?'paymentQrValidation':isCourseAdVideo?'courseAdVideoValidation':'courseAdMediaValidation'));}
    if(invalid){event.target.value='';if($('promoMediaClear'))$('promoMediaClear').checked=false;
      managementDraft={...managementDraft,mediaFile:null,clearMedia:false};releaseManagementMediaPreview();
      if($(previewId))$(previewId).innerHTML='';return;}
    releaseManagementMediaPreview();
    managementDraft={...managementDraft,mediaFile:file,clearMedia:false};
    if($('promoMediaClear'))$('promoMediaClear').checked=false;
    if(file){managementMediaPreviewUrl=URL.createObjectURL(file);
      if($(previewId))$(previewId).innerHTML=`<figure class="management-media-preview">${isCourseAdVideo?`<video src="${esc(managementMediaPreviewUrl)}" controls playsinline preload="metadata" aria-label="${esc(t('courseAdVideo'))}"></video>`:`<img src="${esc(managementMediaPreviewUrl)}" alt="${esc(t(isPaymentQr?'paymentQrImage':isCourseAd?'courseAdMedia':'promoMedia'))}">`}<figcaption>${esc(String(file.name||'').slice(0,120))} · ${file.size.toLocaleString()} B</figcaption></figure>`;}
    else if($(previewId))$(previewId).innerHTML='';
    return;
  }
  if(event.target.id==='promoMediaClear'){
    if(event.target.checked){const input=$('promoMediaFile');if(input)input.value='';releaseManagementMediaPreview();
      if($('promoMediaPreview'))$('promoMediaPreview').innerHTML='';}
    managementDraft={...managementDraft,mediaFile:null,clearMedia:event.target.checked};return;
  }
  if(event.target.id==='payoutOperation'){
    if($('payoutDaysField'))$('payoutDaysField').hidden=event.target.value!=='deadline';
    if($('payoutProofField')){
      $('payoutProofField').hidden=event.target.value!=='complete';$('payoutProofFile').disabled=event.target.value!=='complete';
      const confirm=document.querySelector('[data-action=managementPrepare]');
      if(confirm)confirm.disabled=event.target.value==='complete'&&!managementDraft?.proofLoaded;
    }
  }
  if(event.target.id==='noticeLanguage')updateNoticeLanguage();
  if(event.target.id==='channelOperation'&&$('channelActiveField'))$('channelActiveField').hidden=event.target.value==='delete';
  if(event.target.id==='adOperation'){
    const deleting=event.target.value==='delete';
    const replacing=['replace_image','replace_video'].includes(event.target.value);
    const video=event.target.value==='replace_video';
    if($('adActiveField'))$('adActiveField').hidden=!['set_active'].includes(event.target.value);
    if($('adDeleteHint'))$('adDeleteHint').hidden=!deleting;
    const mediaField=$('adMediaField'),mediaInput=$('courseAdMediaFile');
    if(mediaField)mediaField.hidden=!replacing;
    if(mediaInput){mediaInput.disabled=!replacing;mediaInput.required=replacing;mediaInput.accept=video?'video/mp4,video/quicktime,video/webm,video/x-m4v':'image/jpeg,image/png,image/webp';
      if(!replacing){mediaInput.value='';managementDraft={...managementDraft,mediaFile:null};releaseManagementMediaPreview();
        if($('courseAdMediaPreview'))$('courseAdMediaPreview').innerHTML='';}
      if(replacing&&managementDraft?.mediaFile){mediaInput.value='';managementDraft={...managementDraft,mediaFile:null};releaseManagementMediaPreview();if($('courseAdMediaPreview'))$('courseAdMediaPreview').innerHTML='';}}
    if($('courseAdMediaHint'))$('courseAdMediaHint').textContent=t(video?'courseAdVideoHint':'courseAdMediaHint');
    if(!replacing&&$('courseAdMediaValidation'))$('courseAdMediaValidation').hidden=true;
  }
  if(['priceMethod','pricePlan'].includes(event.target.id))updatePriceFields();
  if(['helpVideoKey','helpVideoLanguage'].includes(event.target.id))updateHelpVideoField();
  if(['feedbackPeriod','feedbackSource'].includes(event.target.id)){
    const period=event.target.id==='feedbackPeriod',value=event.target.value;
    if(!(period?['weekly','monthly']:['all','bot','release','android']).includes(value))return;
    cancelStatisticsDownload();feedbackLoadId++;feedbackStats.data=null;feedbackStats.loading=false;
    if(period)feedbackStats.period=value;else feedbackStats.source=value;
    loadFeedbackStats().catch(()=>showNotice('error'));
  }
  if(event.target.id==='courseMode'){
    const field=$('courseUntilField');
    if(field)field.hidden=event.target.value!=='free_until';
  }
  if(['locale','drawerLocale'].includes(event.target.id)&&['uz','ru','tj'].includes(event.target.value)){
    cancelStatisticsDownload();feedbackLoadId++;
    feedbackStats.loading=false;feedbackStats.data=null;
    locale=event.target.value;try{localStorage.setItem('hsk-admin-locale',locale);}catch(_){}
    closeDrawer();render();
    if(state.route==='stats'&&state.actor)loadFeedbackStats();
  }
});
document.addEventListener('submit',event=>{
  if(event.target.id==='managementForm'){event.preventDefault();prepareManagement();}
  else if(event.target.id==='searchForm'){event.preventDefault();state.query=$('userQuery').value;state.cursor=null;state.previous=[];load();}

});
document.addEventListener('keydown',event=>{
  const statsTab=event.target.closest?.('[data-stats-tab]');
  if(statsTab&&['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){
    const tabs=[...statsTab.closest('.stats-category-tabs').querySelectorAll('[data-stats-tab]')];
    const index=tabs.indexOf(statsTab),n=tabs.length;
    if(index>=0&&n){
      event.preventDefault();
      const target=tabs[event.key==='Home'?0:event.key==='End'?n-1:
        (index+(event.key==='ArrowRight'?1:-1)+n)%n];
      const next=target.dataset.statsTab;
      target.click();
      document.querySelector('[data-stats-tab="'+next+'"]')?.focus();
      return;
    }
  }
  if(event.key==='Escape'){
    if(closeActionMenus(true)){event.preventDefault();return;}
    closeDrawer();for(const id of ['periodMenu','platformMenu'])if($(id)){$(id).hidden=true;document.querySelector(`[data-action="${id==='periodMenu'?'period':'platform'}"]`)?.setAttribute('aria-expanded','false');}
  }
  const trigger=event.target.closest('[data-menu-toggle]');
  if(trigger&&['ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();toggleActionMenu(trigger,event.key==='ArrowUp');return;}
  const menu=event.target.closest('.action-menu');
  if(menu&&['ArrowDown','ArrowUp','Home','End'].includes(event.key)){
    event.preventDefault();
    const items=[...menu.querySelectorAll('button:not(:disabled)')],index=items.indexOf(document.activeElement);
    const next=event.key==='Home'?0:event.key==='End'?items.length-1:(index+(event.key==='ArrowDown'?1:-1)+items.length)%items.length;
    items[next]?.focus();return;
  }
  if(event.key==='Tab'&&$('overlay')){
    const controls=[...$('overlay').querySelectorAll('button:not(:disabled),input,select,textarea')].filter(el=>el.getClientRects().length);
    if(!controls.length)return;const first=controls[0],last=controls.at(-1);
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
  }
});
document.addEventListener('focusin',event=>{
  const open=document.querySelector('.action-menu:not([hidden])');
  if(open&&!open.parentElement.contains(event.target))closeActionMenus();
});
window.addEventListener('offline',()=>clearPrivate('offline'));
window.addEventListener('online',()=>{if(!document.hidden)lockAndRequirePasskey();});
window.addEventListener('pagehide',()=>{
  resumeAuthenticationRequired=true;
  biometricAbort?.abort();
  clearPrivate('loading');
});
window.addEventListener('pageshow',event=>{
  if(event.persisted){resumeAuthenticationRequired=true;lockAndRequirePasskey();}
});
document.addEventListener('visibilitychange',()=>{
  if(document.hidden){
    stopApprovalWatch();
    // A native Face ID / Touch ID sheet can briefly hide a PWA. Do not cancel
    // that same WebAuthn ceremony or accidentally start a second prompt.
    if(biometricPromptInProgress||signing)return;
    resumeAuthenticationRequired=true;
    clearPrivate('loading');
    return;
  }
  if(biometricPromptInProgress||signing)return;
  if(resumeAuthenticationRequired)lockAndRequirePasskey();
  else if(state.phase==='approval')checkApproval().catch(()=>{});
});
window.addEventListener('focus',()=>{if(state.phase==='approval')checkApproval().catch(()=>{});});
window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();installPrompt=event;});
if('serviceWorker' in navigator){
  navigator.serviceWorker.register('/admin/sw.js',{scope:'/admin/',updateViaCache:'none'}).then(registration=>{
    publicRegistration=registration;
    const update=()=>{if(registration.waiting&&navigator.serviceWorker.controller){const button=document.createElement('button');button.className='btn primary shell-update';button.textContent=t('update');button.dataset.action='update';document.body.append(button);}};
    update();registration.addEventListener('updatefound',()=>registration.installing?.addEventListener('statechange',update));
  }).catch(()=>{});
  navigator.serviceWorker.addEventListener('controllerchange',()=>location.reload());
}
lockAndRequirePasskey();
})();
