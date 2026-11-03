"""Offline diagnostics use genuine rule evaluation, synthetic as-of facts and no DB."""
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from datetime import datetime, time, timedelta, timezone
from hashlib import sha256
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from app.services.smart_reminder_offline import (
    CircularNeighbors, Dataset, OfflineError, Snapshot, VERSION, _sample, clock_error, evaluate_dataset,
)
from app.services.smart_reminder_policy import PolicyContext, VerifiedStudy
from scripts import smart_reminder_offline_eval as cli

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026,11,3,12,tzinfo=timezone.utc)


def key(value):
    return sha256(value.encode()).hexdigest()


def row(owner, days, *, now=NOW, target=time(21), habit=time(20), platform='android', locale='uz', zone='Etc/UTC'):
    day=(now-timedelta(days=days)).astimezone(ZoneInfo(zone)).date()
    observed=datetime.combine(day,time(0),ZoneInfo(zone))
    studies=tuple(VerifiedStudy(key(f'{owner}-{day}-history-{i}'),'lesson',
        datetime.combine(day-timedelta(days=i+1),habit,ZoneInfo(zone)),
        (day-timedelta(days=i+1)).isoformat(),1) for i in range(5))
    context=PolicyContext(observed_at=observed,level='hsk1',progress_level='hsk1',expected_level='hsk1',
        completed_parts=5,total_parts=100,target_allowed=True,foundation_required=False,
        revision=2,grant_epoch=1,master_enabled=True,permitted_channels=('android',),
        timezone_name=zone,course_day=day.isoformat(),daily_goal_xp=20,plan_completed=False,
        studies=studies,saved_time=time(14))
    outcome=VerifiedStudy(key(f'{owner}-{day}-outcome'),'lesson',datetime.combine(day,target,ZoneInfo(zone)),day.isoformat(),1)
    return Snapshot(learner_key=key(owner),platform=platform,locale=locale,context=context,
        history_available_at={s.reference:s.accepted_at+timedelta(seconds=2) for s in studies},
        outcome=outcome,outcome_available_at=outcome.accepted_at+timedelta(seconds=2))


def dataset(*rows,now=NOW):
    return Dataset(version=VERSION,data_kind='synthetic',generated_at=now,snapshots=rows)


def run(data,now=NOW,**options):
    return evaluate_dataset(data,cutoff=now-timedelta(days=10),minimum_accounts=2,now=now,**options)


def comparison(now=NOW):
    return dataset(row('train-a',20,now=now),row('train-b',19,now=now),
                   row('test-a',5,now=now),row('test-b',4,now=now),now=now)


class OfflineModelTests(unittest.TestCase):
    def test_shared_model_actually_learns_and_compares_with_existing_habit_rules(self):
        report=run(comparison())
        self.assertEqual(report['overall']['rules_mae_minutes'],60)
        self.assertEqual(report['overall']['model_mae_minutes'],0)
        self.assertEqual(report['overall']['model_minus_rules_minutes'],-60)
        self.assertEqual(report['habit_version'],'smart-habit-interval-v1')
        self.assertEqual(report['cohorts']['learner_history']['unseen']['accounts'],2)
        self.assertFalse(report['ml_ready']);self.assertFalse(report['dispatch_allowed'])
        self.assertIn('unavailable',report['learning_benefit'])

    def test_personal_features_select_different_learned_clocks_for_unseen_accounts(self):
        data=dataset(row('train-night',20),row('train-morning',19,habit=time(8),target=time(9)),
            row('new-night',6),row('new-morning',5,habit=time(8),target=time(9)))
        report=run(data,neighbors=1)
        self.assertEqual(report['overall']['rules_mae_minutes'],60)
        self.assertEqual(report['overall']['model_mae_minutes'],0)
        self.assertEqual(report['cohorts']['learner_history']['unseen']['accounts'],2)

    def test_future_decisions_and_test_labels_never_enter_training(self):
        data=comparison()
        before=run(data)
        altered=tuple(r.model_copy(update={'outcome':replace(r.outcome,accepted_at=r.outcome.accepted_at+timedelta(hours=1)),
            'outcome_available_at':r.outcome_available_at+timedelta(hours=1)}) for r in data.snapshots[2:])
        after=run(data.model_copy(update={'snapshots':data.snapshots[:2]+altered}))
        self.assertEqual(before['training_observations'],after['training_observations'])
        self.assertEqual(after['overall']['model_mae_minutes'],60)
        a,_=_sample(data.snapshots[2],NOW,NOW);b,_=_sample(altered[0],NOW,NOW)
        self.assertEqual(a.features,b.features)
        self.assertEqual(CircularNeighbors([_sample(r,NOW,NOW)[0] for r in data.snapshots[:2]],5).predict(a.features),1260)

    def test_training_label_must_have_been_available_before_cutoff(self):
        data=comparison()
        delayed=tuple(r.model_copy(update={'outcome_available_at':NOW-timedelta(days=9)}) for r in data.snapshots[:2])
        report=run(data.model_copy(update={'snapshots':delayed+data.snapshots[2:]}))
        self.assertEqual(report['training_observations'],0)
        self.assertEqual(report['excluded']['training_label_not_available'],2)
        self.assertIsNone(report['overall']['model_mae_minutes'])

    def test_late_original_proof_and_unknown_availability_do_not_leak_into_features(self):
        for available in (None,NOW-timedelta(days=3)):
            original=row('test-a',5)
            history=dict(original.history_available_at);history[original.context.studies[0].reference]=available
            report=run(dataset(original.model_copy(update={'history_available_at':history})))
            self.assertEqual(report['excluded'],{'history_not_available_at_decision':1})
            self.assertEqual(report['test_observations'],0)

    def test_existing_product_guards_and_manual_locks_are_preserved(self):
        cases=[('master_off',{'master_enabled':False}),('target_inaccessible',{'target_allowed':False}),
            ('foundation_required',{'foundation_required':True}),('consent_or_permission_unavailable',{'permitted_channels':()}),
            ('plan_completed',{'plan_completed':True}),('paused',{'pause_until':NOW}),
            ('course_context_changed',{'progress_level':'hsk2'}),
            ('personal_quiet',{'quiet_start':time(19),'quiet_end':time(22)}),
            ('manual_or_unknown_time',{'time_mode':'manual_locked','manual_time':time(2)}),
            ('history_coverage_limited',{'coverage_limits':('source_partial',)})]
        for expected,changes in cases:
            with self.subTest(expected=expected):
                original=row('test-a',5)
                report=run(dataset(original.model_copy(update={'context':replace(original.context,**changes)})))
                self.assertEqual(report['excluded'],{expected:1})
                self.assertEqual(report['test_observations'],0)

    def test_goal_completed_context_cannot_be_model_eligible(self):
        original=row('test-a',5)
        study=VerifiedStudy(key('today-original'),'lesson',original.context.observed_at+timedelta(minutes=30),
            original.context.course_day,20)
        context=replace(original.context,observed_at=original.context.observed_at+timedelta(hours=1),
            studies=(*original.context.studies,study))
        report=run(dataset(original.model_copy(update={'context':context,
            'history_available_at':original.history_available_at|{study.reference:study.accepted_at}})))
        self.assertEqual(report['excluded'],{'goal_completed':1})

    def test_positive_outcomes_only_never_infer_negative_learning(self):
        original=row('test-a',5)
        for outcome,ready in ((None,None),(replace(original.outcome,xp=0),original.outcome_available_at),
                (replace(original.outcome,activity_type='reward'),original.outcome_available_at),
                (replace(original.outcome,accepted_at=original.outcome.accepted_at+timedelta(days=1)),NOW)):
            report=run(dataset(original.model_copy(update={'outcome':outcome,'outcome_available_at':ready})))
            self.assertEqual(report['test_observations'],0)
            self.assertIsNone(report['overall']['model_mae_minutes'])

    def test_small_absent_and_underrepresented_platform_locale_cohorts_are_null(self):
        data=comparison();report=run(data)
        self.assertIsNone(report['cohorts']['locale']['ru']['model_mae_minutes'])
        self.assertEqual(report['cohorts']['locale']['ru']['accounts'],0)
        unsupported=tuple(r.model_copy(update={'platform':'telegram','locale':'ru'}) for r in data.snapshots[2:])
        report=run(data.model_copy(update={'snapshots':data.snapshots[:2]+unsupported}))
        self.assertEqual(report['cohorts']['platform_locale']['telegram/ru']['training_accounts'],0)
        self.assertIsNone(report['cohorts']['platform_locale']['telegram/ru']['model_mae_minutes'])
        one=run(dataset(data.snapshots[0],data.snapshots[2]))
        self.assertIsNone(one['overall']['model_mae_minutes'])

    def test_metric_is_account_balanced_and_seen_learners_are_separate(self):
        data=comparison()
        tests=(row('train-a',5),row('train-a',4),row('train-b',5,target=time(22)))
        report=run(dataset(*data.snapshots[:2],*tests))
        self.assertEqual(report['overall']['observations'],3)
        self.assertEqual(report['overall']['accounts'],2)
        self.assertEqual(report['overall']['rules_mae_minutes'],90)
        self.assertEqual(report['cohorts']['learner_history']['seen']['accounts'],2)
        self.assertIsNone(report['cohorts']['learner_history']['unseen']['rules_mae_minutes'])

    def test_midnight_circular_regression_ties_are_order_independent_and_ambiguous_falls_back(self):
        sample,_=_sample(row('a',20),NOW,NOW)
        samples=[replace(sample,target_clock=t) for t in (1439,1)]
        for values in (samples,list(reversed(samples))):
            self.assertLess(clock_error(CircularNeighbors(values,1).predict(sample.features),0),1e-6)
        model=CircularNeighbors([replace(sample,target_clock=0),replace(sample,target_clock=720)],2)
        self.assertIsNone(model.predict(sample.features))
        self.assertEqual(clock_error(1439,1),2)

    def test_ambiguous_shared_model_falls_back_without_improving_reported_errors(self):
        data=dataset(row('train-a',20,target=time(6)),row('train-b',19,target=time(18)),
            row('test-a',5),row('test-b',4))
        report=run(data)
        self.assertEqual(report['overall']['model_fallbacks'],2)
        self.assertEqual(report['overall']['model_mae_minutes'],report['overall']['rules_mae_minutes'])
        self.assertFalse(report['ml_ready'])

    def test_empty_data_and_bad_configuration_never_invent_readiness(self):
        report=run(dataset())
        self.assertEqual(report['overall']['accounts'],0)
        self.assertIsNone(report['overall']['rules_mae_minutes'])
        for overrides in ({'minimum_accounts':1},{'minimum_accounts':True},{'neighbors':0},{'neighbors':65}):
            with self.assertRaises(OfflineError):
                evaluate_dataset(dataset(),**(dict(cutoff=NOW-timedelta(days=10),minimum_accounts=2,now=NOW)|overrides))

    def test_dst_gap_and_fold_keep_real_rule_refusals(self):
        for now,days,clock,expected in (
                (datetime(2026,11,3,12,tzinfo=timezone.utc),2,time(1,30),'local_time_ambiguous'),
                (datetime(2026,3,10,12,tzinfo=timezone.utc),2,time(2,30),'local_time_nonexistent')):
            original=row('test',days,now=now,zone='America/New_York',target=time(4))
            context=replace(original.context,studies=(),saved_time=clock)
            data=dataset(original.model_copy(update={'context':context,'history_available_at':{}}),now=now)
            self.assertEqual(run(data,now=now)['excluded'],{expected:1})

    def test_expiry_future_snapshots_and_conflicting_account_day_or_outcome(self):
        original=row('a',5)
        for data in (dataset(original,original.model_copy(update={'platform':'telegram'})),
                dataset(original,row('a',4).model_copy(update={'outcome':original.outcome}))):
            with self.assertRaises(OfflineError):run(data)
        for original in (row('a',91),row('a',86),row('a',-1)):
            report=run(dataset(original))
            self.assertEqual(report['test_observations']+report['training_observations'],0)
        for generated in (NOW+timedelta(seconds=1),NOW-timedelta(days=91)):
            with self.assertRaises(OfflineError):run(dataset().model_copy(update={'generated_at':generated}))

    def test_same_original_proof_cannot_change_across_decision_snapshots(self):
        earlier=row('a',20);later=row('a',5)
        changed=replace(earlier.outcome,xp=50)
        later=later.model_copy(update={'context':replace(later.context,studies=(*later.context.studies,changed)),
            'history_available_at':later.history_available_at|{changed.reference:earlier.outcome_available_at}})
        with self.assertRaisesRegex(OfflineError,'offline_conflicting_proof'):run(dataset(earlier,later))

    def test_unknown_proof_availability_does_not_erase_or_invent_known_evidence(self):
        earlier=row('a',20);proof=earlier.context.studies[0]
        unknown=row('a',5)
        unknown=unknown.model_copy(update={'context':replace(unknown.context,studies=(*unknown.context.studies,proof)),
            'history_available_at':unknown.history_available_at|{proof.reference:None}})
        self.assertEqual(run(dataset(unknown,earlier))['excluded'],{'history_not_available_at_decision':1})
        conflicting=row('a',4)
        conflicting=conflicting.model_copy(update={'context':replace(conflicting.context,studies=(*conflicting.context.studies,proof)),
            'history_available_at':conflicting.history_available_at|{proof.reference:proof.accepted_at+timedelta(seconds=3)}})
        with self.assertRaisesRegex(OfflineError,'offline_conflicting_proof'):run(dataset(earlier,unknown,conflicting))

    def test_json_contract_is_strict_and_rejects_extra_identity_fields_and_naive_proof_times(self):
        raw=json.loads(comparison().model_dump_json())
        self.assertEqual(len(Dataset.model_validate_json(json.dumps(raw)).snapshots),4)
        for path,value in ((('user_id',),123),(('context','master_enabled'),'true'),
                           (('context','telegram_id'),123),(('outcome','xp'),'1')):
            altered=json.loads(json.dumps(raw));target=altered['snapshots'][0]
            for name in path[:-1]:target=target[name]
            target[path[-1]]=value
            with self.assertRaises(ValidationError):Dataset.model_validate_json(json.dumps(altered))
        raw['snapshots'][0]['history_available_at'][next(iter(raw['snapshots'][0]['history_available_at']))]='2026-10-01T10:00:00'
        with self.assertRaises(ValidationError):Dataset.model_validate_json(json.dumps(raw))

    def test_reproducible_aggregate_has_no_private_keys_or_training_records(self):
        data=comparison();first=run(data);second=run(data)
        self.assertEqual(first,second)
        report=json.dumps(first)
        for row_value in data.snapshots:
            self.assertNotIn(row_value.learner_key,report)
            self.assertNotIn(row_value.outcome.reference,report)
        self.assertNotIn('features',first)
        shuffled=run(data.model_copy(update={'snapshots':tuple(reversed(data.snapshots))}))
        self.assertEqual(first['overall'],shuffled['overall'])


class OfflineCliTests(unittest.TestCase):
    def test_real_command_works_without_application_config_or_database_and_leaves_input_unchanged(self):
        now=datetime.now(timezone.utc)
        with TemporaryDirectory() as directory:
            source=Path(directory)/'private-snapshot.json';source.write_text(comparison(now).model_dump_json())
            original=source.read_bytes()
            result=subprocess.run([sys.executable,str(ROOT/'scripts/smart_reminder_offline_eval.py'),
                '--input',str(source),'--cutoff',(now-timedelta(days=10)).isoformat(),'--min-group-accounts','2'],
                cwd=directory,env={'PATH':os.environ.get('PATH','')},capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads(result.stdout)
            self.assertEqual(report['data_kind'],'synthetic')
            self.assertEqual(report['overall']['model_mae_minutes'],0)
            self.assertFalse(report['ml_ready'])
            self.assertEqual(source.read_bytes(),original)
            self.assertEqual(list(Path(directory).iterdir()),[source])

    def test_missing_invalid_oversized_and_private_argument_errors_are_scrubbed(self):
        with TemporaryDirectory() as directory:
            source=Path(directory)/'PRIVATE-ID-secret.json'
            args=['--input',str(source),'--cutoff',NOW.isoformat(),'--min-group-accounts','2']
            for content in (None,'PRIVATE',comparison().model_dump_json()):
                if content is not None:source.write_text(content)
                out,err=StringIO(),StringIO()
                with redirect_stdout(out),redirect_stderr(err),patch.object(cli,'MAX_BYTES',16):
                    self.assertEqual(cli.main(args),2)
                self.assertEqual(out.getvalue(),'')
                self.assertNotIn('PRIVATE',err.getvalue())
            err=StringIO()
            with redirect_stderr(err),self.assertRaises(SystemExit):cli.main(['--PRIVATE-secret'])
            self.assertEqual(err.getvalue(),'offline_arguments_invalid\n')

    def test_no_application_config_or_model_store_is_imported(self):
        result=subprocess.run([sys.executable,'-c',
            'import scripts.smart_reminder_offline_eval; import sys; assert "app.config" not in sys.modules; assert "app.db.session" not in sys.modules'],
            cwd=ROOT,env={'PATH':os.environ.get('PATH','')},capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
