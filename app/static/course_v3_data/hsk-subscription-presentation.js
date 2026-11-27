/* Shared presentation-only subscription helpers. No checkout requests or price mutations. */
(function(root){
"use strict";
function inferPaymentRegion(zone,locale,language){
  const tz=String(zone||"");
  let zoneRegion="";
  if(tz==="Asia/Dushanbe")zoneRegion="tj";
  else if(["Asia/Tashkent","Asia/Samarkand"].includes(tz))zoneRegion="uz";
  else if(["Asia/Shanghai","Asia/Urumqi","Asia/Chongqing","Asia/Harbin","Asia/Kashgar","PRC"].includes(tz))zoneRegion="cn";
  else if(["Europe/Moscow","Europe/Kaliningrad","Europe/Samara","Europe/Volgograd","Europe/Kirov","Europe/Astrakhan","Europe/Saratov","Europe/Ulyanovsk","Asia/Yekaterinburg","Asia/Omsk","Asia/Novosibirsk","Asia/Barnaul","Asia/Tomsk","Asia/Novokuznetsk","Asia/Krasnoyarsk","Asia/Irkutsk","Asia/Chita","Asia/Yakutsk","Asia/Khandyga","Asia/Vladivostok","Asia/Ust-Nera","Asia/Magadan","Asia/Sakhalin","Asia/Srednekolymsk","Asia/Kamchatka","Asia/Anadyr","W-SU"].includes(tz))zoneRegion="ru";
  else if(tz.includes("/")&&!tz.startsWith("Etc/"))zoneRegion="other";
  const match=String(locale||"").match(/^[a-z]{2,3}(?:-[a-z]{4})?-([a-z]{2})(?:-|$)/i);
  const code=match?match[1].toLowerCase():"";
  const localeRegion=code?(["tj","uz","ru","cn"].includes(code)?code:"other"):"";
  if(zoneRegion&&localeRegion&&zoneRegion!==localeRegion)return "other";
  return zoneRegion||localeRegion||(["tj","uz","ru"].includes(language)?language:"other");
}
function localPaymentRegion(language){
  let zone="";
  try{zone=Intl.DateTimeFormat().resolvedOptions().timeZone||""}catch(e){}
  return inferPaymentRegion(zone,typeof navigator==="undefined"?"":navigator.language,language);
}
function regionalProviderPlans(info,currency){
  const rows=info?.plans_by_currency?.[currency]||(info?.currency===currency?info.plans:[]);
  return (Array.isArray(rows)?rows:[]).filter(plan=>plan&&plan.plan_type&&plan.currency===currency&&plan.amount!=null&&Number(plan.amount)>0);
}
function regionalRoute(region,mode,manualAvailable,currencies,defaultCurrency,forcedPath){
  const desired=region==="ru"?"RUB":"USD";
  const exact=currencies.includes(desired);
  const alternate=exact?desired:(currencies.includes(defaultCurrency)?defaultCurrency:(currencies[0]||""));
  if(mode==="manual_only")return {path:"manual",currency:""};
  if(mode==="lava_only")return {path:"lava",currency:alternate};
  if(forcedPath==="manual"&&manualAvailable)return {path:"manual",currency:""};
  if(forcedPath==="lava"&&alternate)return {path:"lava",currency:alternate};
  if(manualAvailable&&(["tj","cn"].includes(region)||!exact))return {path:"manual",currency:""};
  return {path:"lava",currency:alternate};
}
  function relativePrice(value) {
    var n=Number(value);
    if (!Number.isFinite(n)||n<=0) return null;
    // UI-only roughly +30% comparison, rounded to the nearest .99.
    // It is NOT a historical price and NEVER sent to the payment API.
    var result=Math.round(n*1.3-0.99)+0.99;
    if(result<=n)result=Math.ceil(n-0.99+1e-9)+0.99;
    return result.toFixed(2);
  }

function regionalLabel(lang,key){
  const messages=root.HSKAI_MINIAPP_I18N;
  const id="ui.subscription.regional."+key;
  return messages?.[lang]?.[id]||messages?.ru?.[id]||"";
}
/* Only server-supplied local amounts are eligible; never estimate payable amounts. */
function manualRegionalPlans(data,region){
  const prices=data?.prices||{};
  const methods=region==="cn"?["alipay","wechat"]:["visa"];
  const terms=["1_month","10_days","3_months"];
  const method=methods.find(m=>terms.some(t=>prices[m]?.[t]));
  if(!method)return [];
  const rows=terms.filter(t=>prices[method]?.[t]).map(t=>{
    const base=prices[method][t];
    const local=method==="visa"&&region!=="tj"?data?.card_prices?.[region]?.[t]:base;
    if(!local?.currency||local.final_amount==null||!Number.isFinite(Number(local.final_amount))||Number(local.final_amount)<=0)return null;
    return {plan_type:t,currency:local.currency,amount:local.final_amount,base_amount:local.base_amount,discount_percent:base.discount_applied?Number(base.discount_percent)||0:0};
  });
  return rows.every(Boolean)?rows:[];
}
root.HSKSubscriptionPresentation=Object.freeze({manualRegionalPlans,regionalLabel,inferPaymentRegion,localPaymentRegion,regionalProviderPlans,regionalRoute,relativePrice});
})(globalThis);
