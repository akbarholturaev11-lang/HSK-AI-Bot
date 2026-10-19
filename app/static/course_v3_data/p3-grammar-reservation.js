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
  if(!Array.isArray(rows)||rows.length<1||rows.length>128||
     !Array.isArray(lesson.grammar)||!Array.isArray(lesson.sections))return lesson;
  /* A partial but otherwise valid patch must not silently localize half of
     a lesson. The expected slots come only from the already loaded lesson,
     not from a count claimed by the authenticated response. */
  var expected=Object.create(null);
  function expectBlank(path,ex){
    var t=ex&&ex.translation;
    if(ex&&typeof ex.zh==="string"&&t&&Object.keys(t).length===3&&
       ["uz","ru","tj"].every(function(lang){return t[lang]==="";}))expected[path]=true;
  }
  lesson.grammar.forEach(function(g,gi){
    if(g&&Array.isArray(g.examples))g.examples.forEach(function(ex,ei){
      expectBlank("/grammar/"+gi+"/examples/"+ei+"/translation",ex);
    });
  });
  lesson.sections.forEach(function(sec,si){
    if(sec&&Array.isArray(sec.cards))sec.cards.forEach(function(card,ci){
      if(card&&card.type==="_grammar"&&card.g&&Array.isArray(card.g.examples))
        card.g.examples.forEach(function(ex,ei){
          expectBlank("/sections/"+si+"/cards/"+ci+"/g/examples/"+ei+"/translation",ex);
        });
    });
  });
  if(rows.length!==Object.keys(expected).length)return lesson;
  var out=cloneJson(lesson),seen={};
  for(var i=0;i<rows.length;i++){
    var item=rows[i],p=item&&item.pointer;
    if(typeof p!=="string"||seen[p]||!Object.prototype.hasOwnProperty.call(expected,p)||
       !/^\/(?:grammar\/\d+\/examples\/\d+|sections\/\d+\/cards\/\d+\/g\/examples\/\d+)\/translation$/.test(p))return lesson;
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
  P3_RESERVED_GRAMMAR=null;
  return _apiPost("/api/v3/lesson/start",{lesson_id:l.n,review_only:true})
    .then(function(r){return r.json().catch(function(){return{}}).then(function(d){
      /* Only an explicit server grant authorizes completed-lesson review.
         HTTP errors and malformed replies must never become offline grants. */
      if(!r.ok||!d||d.ok!==true||d.allowed!==true){
        var err=new Error((d&&d.error)||"course_lesson_not_unlocked");
        err.data=d;err.status=r.status;err.lessonAccessDenied=true;
        throw err;
      }
      P3_RESERVED_GRAMMAR=d.p3_grammar||null;
      return {ok:true,allowed:true};
    })}).catch(function(err){
      if(err&&err.lessonAccessDenied)throw err;
      /* Only transport failures retain legacy offline completed-lesson access. */
      return {ok:true,allowed:true};
    });
}
