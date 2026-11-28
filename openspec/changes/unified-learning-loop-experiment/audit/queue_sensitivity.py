"""Read-only sensitivity, actual planner; all output /tmp."""
import json,collections as C,copy,sys
from pathlib import Path
from app.services import course_lesson_plan_service as P
root=Path('app/static/course_v3_data');out=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/hsk-learning-queue-audit');audit=json.loads((out/'audit.json').read_text());records=json.loads((out/'planner-records.json').read_text());parts=[]
for level in ['hsk1','hsk2','hsk3','hsk4','nhsk1','nhsk2','nhsk3']:
 for f in sorted((root/level).glob('lesson_*.json'),key=lambda x:int(x.stem.split('_')[1])):
  d=json.loads(f.read_text());cs=[(s['section_no'],i,c,s['section_purpose']) for s in d['sections'] for i,c in enumerate(s['cards'],1)];pics=P.learned_picture_words(level,d['lesson_id'],d['source_lesson']);parts.append((d,cs,pics))
profiles=[(g,(g,),f) for g in P.GOAL_SKILL_WEIGHTS for f in P.FOCUS_TO_SKILL]+[('travel',('travel','hsk_exam'),None),('hsk_exam',('hsk_exam','travel'),None),('travel',('travel',)+tuple(g for g in P.GOAL_SKILL_WEIGHTS if g!='travel'),None)]
summaries=[]
for goal,goals,focus in profiles:
 stat=C.Counter();types=C.Counter();counterBefore=C.Counter();counterAfter=C.Counter();omitraw=C.Counter()
 for d,cs,pics in parts:
  level=d['level'];n=d['lesson_id'];plan=P.build_lesson_plan(d,level=level,lesson_order=n,minutes=5,goal=goal,goals=goals,focus=focus,seed='synthetic-account-1',picture_words=pics);omit={(o['section_no'],o['card_no']) for o in (plan or {}).get('omit',[])};kept=[(sn,cn,c,p) for sn,cn,c,p in cs if (sn,cn) not in omit];pr=((plan or {}).get('picture_review') or {});anchor=pr.get('anchor') or {};pw=pr.get('words') or [];qt=[c['type'] for c in d.get('basics',[])]
  for s in d['sections']:
   sn=s['section_no'];ispic=bool(pw) and anchor.get('section_no')==sn
   if ispic and anchor.get('position')=='start':qt.append('_picture_review')
   qt.extend(c['type'] for xs,cn,c,p in kept if xs==sn)
   if ispic and anchor.get('position')!='start':qt.append('_picture_review')
  qt.extend(c['type'] for c in (d.get('exit_ticket') or {}).get('cards',[]))
  refs=[[f'lesson:{level}:{n}:section:{sn}:card:{cn}',c['type']] for sn,cn,c,p in kept]
  records.append({'level':level,'n':n,'minutes':5,'goal':goal,'goals':list(goals),'focus':focus,'plan':plan,'expected_ref_types':refs,'expected_types':qt})
  optional=[(sn,cn,c,p) for sn,cn,c,p in cs if p in P.TRIMMABLE_PURPOSES and c['type'] in P.CARD_SKILL and not P._protected(c)]
  opa=[c['type'] for sn,cn,c,p in optional if (sn,cn) not in omit]
  protected=len(cs)-len(optional)+len((d.get('exit_ticket') or {}).get('cards',[]));stat['overflow']+=protected>P.budget_units(5,goal,goals);stat['no_optional']+=not opa;stat['omitted']+=len(omit);stat['picture_parts']+=bool(pw);stat['optional_diversity_sum']+=len(set(opa));types.update(opa)
 summaries.append({'goal':goal,'goals':goals,'focus':focus,**stat,'optional_types':dict(types)})
# Explicit feature-OFF baseline actual-queue checks.
for d,cs,pics in parts:
 types=[c['type'] for c in d.get('basics',[])]+[c['type'] for sn,cn,c,p in cs]+[c['type'] for c in (d.get('exit_ticket') or {}).get('cards',[])];refs=[[f'lesson:{d["level"]}:{d["lesson_id"]}:section:{sn}:card:{cn}',c['type']] for sn,cn,c,p in cs]
 records.append({'level':d['level'],'n':d['lesson_id'],'minutes':'OFF','goal':'OFF','plan':None,'expected_ref_types':refs,'expected_types':types})
(out/'sensitivity.json').write_text(json.dumps(summaries,indent=2));(out/'planner-records.json').write_text(json.dumps(records,separators=(',',':')));print('additional_profiles',len(profiles),'planner_calls',len(parts)*len(profiles),'off_checks',len(parts)*3)
