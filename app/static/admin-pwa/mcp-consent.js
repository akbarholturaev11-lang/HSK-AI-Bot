/* No token persistence or API calls. Only client-side UZ/RU/TJ catalog labels. */
(() => {
  'use strict';
  const catalog=window.HSKAI_ADMIN_I18N;
  if(!catalog) return;
  const select=document.getElementById('mcp-locale');
  let locale='uz';
  try {const saved=localStorage.getItem('hsk-admin-locale');if(['uz','ru','tj'].includes(saved))locale=saved;}catch(_){}
  function render(){
    document.documentElement.lang=locale==='tj'?'tg':locale;
    select.value=locale;
    document.querySelectorAll('[data-i18n]').forEach(el=>{
      const value=catalog[locale]?.[el.dataset.i18n];
      if(typeof value==='string')el.textContent=value;
    });
    select.setAttribute('aria-label',catalog[locale]?.language||'Language');
    document.title='HSK AI · '+(catalog[locale]?.[document.querySelector('h1')?.dataset.i18n]||'OAuth');
  }
  select.addEventListener('change',()=>{
    if(!['uz','ru','tj'].includes(select.value))return;
    locale=select.value;
    try{localStorage.setItem('hsk-admin-locale',locale);}catch(_){}
    render();
  });
  document.getElementById('mcp-retry')?.addEventListener('click',()=>location.reload());
  render();
})();
