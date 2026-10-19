/* Authenticated P3 display-only grammar patch; no anonymous text pack. */
var P3_RESERVED_GRAMMAR=null;
function applyReservedP3Grammar(lesson,level,number){
  var patch=P3_RESERVED_GRAMMAR;
  P3_RESERVED_GRAMMAR=null;
  if(!patch||patch.version!==1||normalizeLevel(level)!=="nhsk2"||
     patch.level!=="nhsk2"||patch.lesson_order!==Number(number)||
     !lesson||lesson.level!=="nhsk2"||lesson.lesson_id!==Number(number)||
     !/^[0-9a-f]{40}$/.test(String(patch.source_git_blob_sha1||"")))return lesson;
  var rows=patch.display_translations;
  if(!Array.isArray(rows)||rows.length<1||rows.length>128)return lesson;
  var out=cloneJson(lesson),seen={};
  for(var i=0;i<rows.length;i++){
    var item=rows[i],p=item&&item.pointer;
    if(typeof p!=="string"||seen[p]||!/^\/(?:grammar\/\d+\/examples\/\d+|sections\/\d+\/cards\/\d+\/g\/examples\/\d+)\/translation$/.test(p))return lesson;
    seen[p]=true;
    var v=item.values;
    if(!v||Object.keys(v).length!==3||!["uz","ru","tj"].every(function(lang){
      return typeof v[lang]==="string"&&v[lang].trim()===v[lang]&&v[lang].length>0;
    }))return lesson;
    var parts=p.split("/").slice(1,-1),ex=out;
    for(var j=0;j<parts.length;j++){
      var token=parts[j],key=Array.isArray(ex)?Number(token):token;
      if(!ex||!Object.prototype.hasOwnProperty.call(ex,key))return lesson;
      ex=ex[key];
    }
    if(!ex||ex.zh!==item.zh||String(ex.pinyin||"")!==String(item.pinyin||"")||
       !ex.translation||Object.keys(ex.translation).length!==3||
       !["uz","ru","tj"].every(function(lang){return ex.translation[lang]==="";}))return lesson;
    ex.translation={uz:v.uz,ru:v.ru,tj:v.tj};
  }
  return out;
}

/* Read-only grammar copy for already COMPLETED lessons only. Server checks
   signed Telegram initData and completed progress; no limit consumption. */
function reserveCompletedP3Grammar(l){
  return _apiPost("/api/v3/lesson/start",{lesson_id:l.n,review_only:true})
    .then(function(r){return r.json().catch(function(){return{}}).then(function(d){
      /* An explicit server access rejection is authoritative even when the
         cached Mini App lists this lesson as completed. Never turn 401/403
         or allowed:false into the legacy offline fallback. */
      if(r.status===401||r.status===403||d.allowed===false){
        var err=new Error(d.error||"course_lesson_not_unlocked");
        err.data=d;err.status=r.status;err.lessonAccessDenied=true;
        throw err;
      }
      if(r.ok&&d.ok&&d.allowed===true)P3_RESERVED_GRAMMAR=d.p3_grammar||null;
      return {ok:true,allowed:true};
    })}).catch(function(err){
      if(err&&err.lessonAccessDenied)throw err;
      /* Network failures must not break old completed offline lessons. */
      return {ok:true,allowed:true};
    });
}
