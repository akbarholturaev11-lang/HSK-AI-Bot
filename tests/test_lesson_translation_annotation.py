"""Pronunciation explanations must never become the graded translation."""
import json
from pathlib import Path

import pytest
from app.services.course_lesson_mistake_material_service import CourseLessonMistakeMaterialService as Materials
from scripts.seed_hsk1_lesson_01 import LESSON


@pytest.mark.parametrize('lang,answer,wrong', [('ru','привет','ты'),('uz','salom','sen'),('tj','салом','ту')])
def test_greeting_answer_and_server_material_share_clean_translation(lang, answer, wrong):
    lesson = json.loads(Path('app/static/course_v3_data/hsk1/lesson_01.json').read_text())
    section = next(s for s in lesson['sections'] if any(c.get('type') == 'reverse_builder' and c.get('zh') == '你好' for c in s['cards']))
    index, card = next((i,c) for i,c in enumerate(section['cards'],1) if c.get('type') == 'reverse_builder' and c.get('zh') == '你好')
    ref = Materials.material_ref('hsk1',1,section['section_no'],index)
    assert card['answer_tokens'][lang] == [answer]
    assert card['translation'][lang] == answer
    assert Materials.canonicalize_items(level='hsk1',lesson_order=1,lang=lang,items=[{'material_ref':ref,'selected_tokens':[answer]}]) == []
    mistakes = Materials.canonicalize_items(level='hsk1',lesson_order=1,lang=lang,items=[{'material_ref':ref,'selected_tokens':[wrong]}])
    assert len(mistakes) == 1
    assert mistakes[0]['correct_answer'] == answer
    assert mistakes[0]['material']['pinyin'] == 'nǐ hǎo → ní hǎo'
    assert mistakes[0]['material']['source']['card'] == index
    assert Materials.canonicalize_items(level='hsk1',lesson_order=1,lang=lang,items=[{'material_ref':ref,'selected_tokens':['nǐ']}]) == []


def test_seed_keeps_tone_note_out_of_translations_and_in_teaching_explanation():
    grammar=json.loads(LESSON['grammar_json'])
    rule=next(g for g in grammar if any(e.get('zh')=='你好' and '→' in e.get('pinyin','') for e in g.get('examples',[])))
    ex=rule['examples'][0]
    assert {lang:ex[lang] for lang in ('uz','ru','tj')} == {'uz':'salom','ru':'привет','tj':'салом'}
    assert 'пишется nǐ hǎo' in rule['rule_ru']


def test_generated_builder_prompt_uses_meaning_without_rewriting_tone_rule():
    from scripts.gen_course_v3_from_seed import make_builder_card, t3
    rule=json.loads(LESSON['grammar_json'])[-1]
    ex=rule['examples'][0]
    card=make_builder_card(ex['zh'], ex['pinyin'], t3(ex), ['你','好'], [])
    assert card['sentence'] == {'uz':'salom','ru':'привет','tj':'салом'}
    assert card['answer_tokens'] == ['你','好']
    assert card['explanation']['ru'] == '你好 — nǐ hǎo → ní hǎo'
