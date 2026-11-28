"""Read-only actual planner audit. Run from the audited project root using its env.
Writes only local audit artifacts. No database query, provider call or app startup.
"""
import collections as C,copy,json,statistics,hashlib,subprocess,sys
from pathlib import Path
from app.services import course_lesson_plan_service as P
ROOT=Path.cwd(); OUT=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/hsk-learning-queue-audit');OUT.mkdir(exist_ok=True)
LEVELS=['hsk1','hsk2','hsk3','hsk4','nhsk1','nhsk2','nhsk3'];MINUTES=[5,10,15,20,30];GOALS=list(P.GOAL_SKILL_WEIGHTS)
LANGS=['uz','ru','tj']
NONINTERACTIVE={'active_word','_grammar','_basics'}
FAMILY={'active_word':'teaching','_grammar':'teaching','_basics':'teaching','pronunciation':'speaking','_picture_review':'picture_speaking','listening_choice':'listening_choice','sentence_builder':'tile_production','reverse_builder':'translation_tiles','match_pairs':'matching','dialog_cloze':'dialogue_choice','gap_fill':'gap_choice','meaning_guess':'word_choice','hanzi_choice':'word_choice','pinyin_choice':'pinyin_choice','translation_choice':'word_choice','quick_quiz':'quiz_choice'}
def fam(t):return FAMILY.get(t,t)
def mean(xs):return round(statistics.mean(xs),3) if xs else None
def describe(xs):return {'min':min(xs),'median':statistics.median(xs),'mean':mean(xs),'max':max(xs)} if xs else None
allparts=[]
for level in LEVELS:
 for f in sorted((ROOT/'app/static/course_v3_data'/level).glob('lesson_*.json'),key=lambda x:int(x.stem.split('_')[1])):
  d=json.loads(f.read_text());cards=[]
  for s in d['sections']:
   sn=s['section_no'];purpose=s['section_purpose']
   for cn,c in enumerate(s['cards'],1):
    optional=purpose in P.TRIMMABLE_PURPOSES and c['type'] in P.CARD_SKILL and not P._protected(c)
    cards.append({'ref':f'lesson:{level}:{d["lesson_id"]}:section:{sn}:card:{cn}','sn':sn,'cn':cn,'type':c['type'],'purpose':purpose,'optional':optional})
  pictures=P.learned_picture_words(level,d['lesson_id'],int(d.get('source_lesson') or 0))
  allparts.append({'id':f'{level}/{d["lesson_id"]}','level':level,'n':d['lesson_id'],'d':d,'cards':cards,'pictures':pictures})
base_stats={};planned={};records=[];examples=[];before=C.Counter();all_hashes={p['id']:hashlib.sha256(json.dumps(p['d'],sort_keys=True,ensure_ascii=False).encode()).hexdigest() for p in allparts}
for p in allparts:
 before.update(c['type'] for c in p['cards'])
for minutes in MINUTES:
 for goal in GOALS:
  key=f'{minutes}:{goal}';rows=[];total=C.Counter();optionalBefore=C.Counter();optionalAfter=C.Counter();omitted=C.Counter();familiesBefore=C.Counter();familiesAfter=C.Counter()
  for p in allparts:
   d=p['d'];cards=p['cards'];budget=P.budget_units(minutes,goal,())
   plan=P.build_lesson_plan(d,level=p['level'],lesson_order=p['n'],minutes=minutes,goal=goal,seed='synthetic-account-1',picture_words=p['pictures'])
   omit={(x['section_no'],x['card_no']) for x in (plan or {}).get('omit',[])}
   kept=[c for c in cards if (c['sn'],c['cn']) not in omit];optBefore=[c for c in cards if c['optional']];optAfter=[c for c in kept if c['optional']]
   bad=[c['ref'] for c in cards if not c['optional'] and (c['sn'],c['cn']) in omit]
   if bad:raise AssertionError(bad)
   pics=((plan or {}).get('picture_review') or {}).get('words') or []
   protected=sum(not c['optional'] for c in cards)+len((d.get('exit_ticket') or {}).get('cards') or [])
   allBefore=[c['type'] for c in d.get('basics',[])]+[c['type'] for c in cards]+[c['type'] for c in (d.get('exit_ticket') or {}).get('cards',[])]
   types=[c['type'] for c in d.get('basics',[])]
   anchor=((plan or {}).get('picture_review') or {}).get('anchor') or {}
   for section in d['sections']:
    sn=section['section_no']; has_picture=bool(pics) and anchor.get('section_no')==sn
    if has_picture and anchor.get('position')=='start':types.append('_picture_review')
    types.extend(c['type'] for c in kept if c['sn']==sn)
    if has_picture and anchor.get('position')!='start':types.append('_picture_review')
   types.extend(c['type'] for c in (d.get('exit_ticket') or {}).get('cards',[]))
   optTypes=[c['type'] for c in optAfter];beforeOpt=[c['type'] for c in optBefore]
   row={'id':p['id'],'level':p['level'],'n':p['n'],'checkpoint':d['checkpoint'],'budget_units':budget,'protected':protected,'overflow_units':max(0,protected-budget),'before_count':len(allBefore),'after_count':len(types),'omitted':len(omit),'picture_count':len(pics),'optional_before_count':len(optBefore),'optional_after_count':len(optAfter),'optional_before_types':beforeOpt,'optional_after_types':optTypes,'before_types':allBefore,'after_types':types,'before_families':[fam(t) for t in allBefore],'after_families':[fam(t) for t in types],'omitted_refs':[c['ref'] for c in cards if (c['sn'],c['cn']) in omit],'retained_optional_refs':[c['ref'] for c in optAfter],'picture_ref':f'lesson:{p["level"]}:{p["n"]}:picture_review' if pics else None,'interactive_diversity_before':len(set(allBefore)-NONINTERACTIVE),'interactive_diversity_after':len(set(types)-NONINTERACTIVE),'after_cost_units':protected+len(optAfter)+0.5*len(pics)}
   rows.append(row);total.update(types);optionalBefore.update(beforeOpt);optionalAfter.update(optTypes);omitted.update(c['type'] for c in cards if (c['sn'],c['cn']) in omit);familiesBefore.update(fam(t) for t in allBefore);familiesAfter.update(fam(t) for t in types)
   records.append({'level':p['level'],'n':p['n'],'minutes':minutes,'goal':goal,'plan':plan,'expected_ref_types':[[c['ref'],c['type']] for c in kept],'expected_types':types})
  adj=[]
  for a,b in zip(rows,rows[1:]):
   if a['level']!=b['level']:continue
   adj.append({'same_full_sequence':a['after_types']==b['after_types'],'same_optional_sequence':a['optional_after_types']==b['optional_after_types'],'same_optional_nonempty_sequence':bool(a['optional_after_types']) and a['optional_after_types']==b['optional_after_types'],'same_optional_before':a['optional_before_types']==b['optional_before_types'],'same_full_before':a['before_types']==b['before_types'],'optional_sets_equal':set(a['optional_after_types'])==set(b['optional_after_types']),'full_sets_equal':set(a['after_types'])==set(b['after_types'])})
  summary={'parts':len(rows),'omitted_cards':sum(x['omitted'] for x in rows),'parts_trimmed':sum(bool(x['omitted']) for x in rows),'parts_with_pictures':sum(bool(x['picture_count']) for x in rows),'picture_words':sum(x['picture_count'] for x in rows),'protected_overflow_parts':sum(x['overflow_units']>0 for x in rows),'no_remaining_optional_parts':sum(not x['optional_after_count'] for x in rows),'optional_raw_diversity_before':describe([len(set(x['optional_before_types'])) for x in rows]),'optional_raw_diversity_after':describe([len(set(x['optional_after_types'])) for x in rows]),'interactive_diversity_before':describe([x['interactive_diversity_before'] for x in rows]),'interactive_diversity_after':describe([x['interactive_diversity_after'] for x in rows]),'parts_interactive_diversity_reduced':sum(x['interactive_diversity_after']<x['interactive_diversity_before'] for x in rows),'protected_units':describe([x['protected'] for x in rows]),'display_steps':describe([x['after_count'] for x in rows]),'units_spent':describe([x['after_cost_units'] for x in rows]),'types':dict(total),'optional_before':dict(optionalBefore),'optional_after':dict(optionalAfter),'omitted_types':dict(omitted),'family_before':dict(familiesBefore),'family_after':dict(familiesAfter),'adjacent_pairs':len(adj),'adjacent_counts':{k:sum(a[k] for a in adj) for k in adj[0]}}
  planned[key]={'summary':summary,'rows':rows}
for p in allparts:
 assert all_hashes[p['id']]==hashlib.sha256(json.dumps(p['d'],sort_keys=True,ensure_ascii=False).encode()).hexdigest(),p['id']
# Because goal/minutes/planner do not take language, verify actual queue in all 3 locales separately with Node.
(OUT/'planner-records.json').write_text(json.dumps(records,separators=(',',':'),ensure_ascii=False))
(OUT/'audit.json').write_text(json.dumps({'sha':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'method':{'minutes':MINUTES,'goals':GOALS,'languages':LANGS,'planner':'actual imported build_lesson_plan + learned_picture_words; flag-enabled synthetic profiles only; no history/mistake evidence invented','family_mapping':FAMILY},'source_parts':len(allparts),'source_section_types':dict(before),'configs':planned},ensure_ascii=False))
print(json.dumps({'sha':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source_parts':len(allparts),'planner_calls':len(records),'planned_summary':{k:v['summary'] for k,v in planned.items() if k.startswith('5:')},'output_dir':str(OUT)},indent=2))
