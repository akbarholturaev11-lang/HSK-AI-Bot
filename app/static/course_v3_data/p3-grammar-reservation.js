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
