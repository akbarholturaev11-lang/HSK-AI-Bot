/* Browser-only referral share UI. No Telegram Mini App requirements. */
(function(root){
  "use strict";
  if(!root.location||root.location.pathname!=="/iphone-pwa/course")return;
  var current=null;
  function esc(value){return String(value||"").replace(/[&<>"']/g,function(c){
    return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];
  })}
  function copy(key,fallback){return typeof root.courseMessage==="function"?root.courseMessage(key,fallback):fallback}
  function safeUrl(value){
    try{
      var url=new URL(String(value||""),root.location.origin);
      if(url.protocol!=="https:")return "";
      return url.href;
    }catch(_){return ""}
  }
  function open(data){
    var link=safeUrl(data&&data.link);
    if(!link)return;
    var prompt=copy("rating.inviteFallbackShare","");
    var title=copy("rating.inviteTitle","");
    var button=copy("rating.inviteSend","");
    current={link:link,text:prompt};
    var joined=Number(data.joined_count||0),active=Number(data.active_count||0);
    var required=Number(data.required||0);
    var stat=Number.isFinite(joined)&&Number.isFinite(active)&&Number.isFinite(required)
      ? '<div class="sst"><div><b>'+Math.max(0,joined)+'</b><small>'+
        esc(copy("rating.referralJoined",""))+'</small></div><div><b>'+
        Math.max(0,active)+' / '+Math.max(0,required)+'</b><small>'+
        esc(copy("rating.referralActive",""))+'</small></div></div>' : "";
    root.App.openSheet('<div class="shead"><div class="zh han" style="font-size:34px">友</div>'+
      '<div class="tr" style="font-size:16px;color:var(--ink);margin-top:8px">'+esc(title)+'</div>'+
      '<div class="tr">'+esc(prompt)+'</div></div>'+stat+
      '<div class="tmpl">'+esc(prompt+" "+link)+'</div>'+
      '<button class="scta" type="button" onclick="window.HskPwaInvite.share()"><i class="ti ti-share"></i> '+
      esc(button)+'</button>');
  }
  function share(){
    var d=current;if(!d)return;
    if(root.navigator.share){
      root.navigator.share({title:"HSK AI",text:d.text,url:d.link}).catch(function(){});
      return;
    }
    if(root.navigator.clipboard&&root.navigator.clipboard.writeText){
      root.navigator.clipboard.writeText((d.text+" "+d.link).trim()).then(function(){
        if(typeof root.toast==="function")root.toast(copy("rating.copiedToast",""),2100);
      }).catch(function(){});
    }
  }
  root.HskPwaInvite=Object.freeze({open:open,share:share});
})(window);
