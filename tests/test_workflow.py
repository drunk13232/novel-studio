"""Hand-authored micro-fixtures and failure tests. No model calls or real prose."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import model as m
import novel_workflow as w
import yaml_io as y

FIXTURE = y.read(ROOT / 'tests/fixtures/scenario.yaml')


def view(text, visibility='CHARACTER', actors=None, chapter=0, time=None):
    return {'text': text, 'visibility': visibility, 'known_by': actors or ['A'],
            'since_chapter': chapter, 'story_time': time or FIXTURE['story_time']}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        m.initialize(self.root)
        self.addCleanup(self.temp.cleanup)
        state = copy.deepcopy(m.STATES)
        current = state['current-story-state.yaml']
        current['project'].update(story_date=FIXTURE['story_time'])
        current['pov']['current_character'] = 'A'
        current['location']['current'] = 'L1'
        current['active_characters'] = ['A', 'B']
        for cid in ['A', 'B']:
            char = copy.deepcopy(m.CHARACTER)
            char.update(id=cid, name=cid, last_updated_chapter=0)
            char['status']['location'] = 'L1'
            state[f'characters/{cid}.yaml'] = char
        a = state['characters/A.yaml']
        a['status'].update(physical_condition=FIXTURE['injury'], limitations=['left_arm_load'])
        a['knowledge']['does_not_know'] = ['K1']
        b = state['characters/B.yaml']
        b['secrets']['personal'] = [FIXTURE['secret']]
        b['knowledge']['knows'] = ['K1']
        b['writer_view'] = [view('B 在房间里。', 'PUBLIC'), view(FIXTURE['secret'], 'AUTHOR')]
        place = copy.deepcopy(m.LOCATION)
        place.update(name='fixture room', daylight_hours=list(range(6, 19)), writer_view=[view('房间里有一扇窗。', 'PUBLIC')])
        state['locations.yaml']['locations']['L1'] = place
        event = copy.deepcopy(m.EVENT)
        event.update(id='E0', chapter=0, story_time=FIXTURE['story_time'], location='L1', characters=['B'], summary=FIXTURE['secret'])
        state['timeline.yaml']['events'] = [event]
        fact = copy.deepcopy(m.FACT)
        fact.update(canonical_truth=FIXTURE['secret'], introduced_chapter=0, known_by=[{
            'character_id': 'B', 'acquired_chapter': 0, 'story_time': FIXTURE['story_time'], 'source_event': 'E0'}])
        state['knowledge-state.yaml']['facts']['K1'] = fact
        f = copy.deepcopy(m.FORESHADOW)
        f.update(title=FIXTURE['secret'], introduced_chapter=0, intended_payoff=FIXTURE['secret'],
                 writer_view=[view('B 避开目光。')])
        state['foreshadowing.yaml']['foreshadowing']['F1'] = f
        current['open_foreshadowing'] = ['F1']
        for relative, value in state.items():
            y.write(self.root / 'state' / relative, value)
        self.plan = copy.deepcopy(m.PLAN)
        self.plan['chapter'].update(number=1, volume=1, title=FIXTURE['secret'])
        self.plan['pov']['character'] = 'A'
        self.plan['setting'].update(location='L1', story_time='2030-01-02T01:00:00+08:00')
        self.plan.update(chapter_goal=FIXTURE['secret'], ending_hook=FIXTURE['secret'], must_not_include=[FIXTURE['secret']],
                         writer_view=[view('保护左臂，留意眼前人的反应。')])
        scene = copy.deepcopy(m.SCENE)
        scene.update(id='S1', location='L1', characters=['A', 'B'], purpose=FIXTURE['secret'],
                     writer_view=[view('A 暂时无法确定凶手身份。')])
        self.plan['scenes'] = [scene]
        rule = copy.deepcopy(m.RULE)
        rule.update(id='NO_LEAK', statement=FIXTURE['secret'], check='knowledge',
                    writer_view=[view('不得使用 POV 尚未获得的信息。', 'PUBLIC')])
        contract = copy.deepcopy(m.CONTRACT)
        contract['hard'] = [rule]
        y.write(self.root / 'settings/canon-contract.yaml', contract)
        self.body_relative = 'chapters/fixture.txt'
        self.body = self.root / self.body_relative
        self.body.parent.mkdir(exist_ok=True)
        self.body.write_text(FIXTURE['good_body'], encoding='utf-8')

    def checks(self, body_key, claims_key):
        self.body.write_text(FIXTURE[body_key], encoding='utf-8')
        claims = {'body_sha256': w.digest(self.body.read_bytes()), 'claims': FIXTURE[claims_key]}
        return {kind: w.check(self.root, self.body, claims, kind) for kind in ['contract', 'continuity', 'character']}

    def witness(self):
        # These are simulated review records for transaction tests only; no literary acceptance claimed.
        paths = {}
        for kind in w.REVIEW_KINDS:
            relative = f'reviews/fixture/{kind}.yaml'
            y.write(self.root / relative, {'result': 'PASS', 'body_sha256': w.digest(self.body.read_bytes()),
                                         'coverage': 'SEMANTIC_REVIEW', 'reviewer': 'SIMULATED_FIXTURE_ONLY',
                                         'reviewed_rules': ['fixture assertion'], 'findings_resolved': True})
            paths[kind] = relative
        return w.final_witness(self.root, self.body_relative, 1, paths)

    def proposal(self):
        witness = self.witness()
        observations = {key: [] for key in m.MEMORY_KEYS + ['operations']}
        observations['operations'] = [{'file': 'current-story-state.yaml', 'pointer': '/project/story_date',
                                       'before': FIXTURE['story_time'], 'after': self.plan['setting']['story_time'],
                                       'evidence': 'A 尚不知道凶手是谁。'}]
        extraction = w.extract(self.root, witness, observations)
        proposal = w.propose(self.root, witness, extraction, 'fixture-1')
        y.write(self.root / 'state/proposed/fixture-1.review.yaml', {
            'result': 'PASS', 'coverage': 'SEMANTIC_DIFF_REVIEW', 'reviewer': 'SIMULATED_FIXTURE_ONLY',
            'proposal_sha256': w.digest(proposal), 'extraction_complete': True,
            'verified_operations': [o['file'] + o['pointer'] for o in extraction['operations']]})
        return proposal

    def test_bad_injury_knowledge_hard_fail(self):
        reports = self.checks('bad_body', 'bad_claims')
        self.assertTrue(all(report['result'] == 'FAIL' for report in reports.values()))
        self.assertIn('injury', {i['category'] for i in reports['continuity']['issues']})
        self.assertIn('knowledge', {i['category'] for i in reports['character']['issues']})
        self.assertTrue(any(i['severity'] == 'HARD' for i in reports['contract']['violations']))
        y.write(ROOT / 'docs/validation-v0.1/fixture-bad-reports.yaml', reports)

    def test_good_no_false_positive(self):
        reports = self.checks('good_body', 'good_claims')
        self.assertEqual(['PASS'] * 3, [r['result'] for r in reports.values()])
        y.write(ROOT / 'docs/validation-v0.1/fixture-good-reports.yaml', reports)

    def test_contract_levels_and_explained_strong(self):
        claims = {'body_sha256': w.digest(self.body.read_bytes()), 'claims': [{
            'type': 'ability', 'character': 'A', 'ability_id': 'NEW', 'location': 'p1',
            'evidence': 'A 用右手拿起轻物'}]}
        outcomes = {}
        for level in ['hard', 'strong', 'soft', 'preferences']:
            contract = copy.deepcopy(m.CONTRACT)
            rule = copy.deepcopy(m.RULE); rule.update(id='ABILITY_SOURCE', statement='能力需来源', check='ability')
            contract[level] = [rule]; y.write(self.root / 'settings/canon-contract.yaml', contract)
            outcomes[level] = w.check(self.root, self.body, claims, 'contract')['result']
        self.assertEqual({'hard': 'FAIL', 'strong': 'FAIL', 'soft': 'WARN', 'preferences': 'WARN'}, outcomes)
        claims['claims'][0]['acquisition_evidence'] = 'A 用右手拿起轻物'
        contract = copy.deepcopy(m.CONTRACT); contract['strong'] = [rule]
        y.write(self.root / 'settings/canon-contract.yaml', contract)
        # Machine verifies that the cited explanation exists; semantic sufficiency still requires Skill.
        self.assertEqual('PASS', w.check(self.root, self.body, claims, 'contract')['result'])

    def test_context_excludes_every_secret_surface(self):
        packet = w.context(self.root, self.plan)
        rendered = json.dumps(packet, ensure_ascii=False)
        self.assertNotIn(FIXTURE['secret'], rendered)
        self.assertNotIn('canonical_truth', rendered)
        self.assertNotIn('intended_payoff', rendered)
        self.assertNotIn('AUTHOR-ONLY', rendered)
        self.assertIn(FIXTURE['injury'], rendered)
        self.assertEqual([], packet['pov_knowledge']['known'])
        y.write(ROOT / 'docs/validation-v0.1/fixture-writer-context.yaml', packet)

    def test_b_pov_gets_known_truth(self):
        self.plan['pov']['character'] = 'B'
        self.assertEqual('B 是凶手。', w.context(self.root, self.plan)['pov_knowledge']['known'][0]['text'])

    def test_future_material_and_reader_visibility_excluded(self):
        material = {'recent_summaries': [view('FUTURE_SECRET', chapter=2), view('OTHER_ACTOR_SECRET', actors=['B']),
                                       view('AUTHOR_SECRET', 'AUTHOR')], 'previous_scene': [view('已知的上一场。')], 'global_rules': []}
        packet = w.context(self.root, self.plan, materials=material)
        self.assertEqual([], packet['recent_summaries'])
        self.assertEqual(['已知的上一场。'], packet['previous_scene'])

    def test_next_chapter_time_does_not_grant_future_knowledge(self):
        material = {'global_rules': [], 'previous_scene': [], 'recent_summaries': [
            view('FUTURE_WITH_OLD_CHAPTER_LABEL', chapter=0, time='2030-01-02T00:30:00+08:00')]}
        self.assertEqual([], w.context(self.root, self.plan, materials=material)['recent_summaries'])
        path = self.root / 'state/knowledge-state.yaml'; data = y.read(path)
        data['facts']['K1'].update(public=True, public_since_chapter=0, public_story_time='2030-01-02T00:30:00+08:00')
        y.write(path, data)
        with self.assertRaises(ValueError): w.load_state(self.root)

    def test_false_belief_does_not_expose_answer(self):
        path = self.root / 'state/knowledge-state.yaml'
        data = y.read(path)
        data['facts']['K1']['false_beliefs']['A'] = {'belief': 'A 以为另有其人。', 'acquired_chapter': 0,
                                                 'story_time': FIXTURE['story_time'], 'source_event': 'E0'}
        y.write(path, data)
        packet = w.context(self.root, self.plan)
        self.assertEqual([{'text': 'A 以为另有其人。'}], packet['pov_knowledge']['beliefs'])
        self.assertNotIn(FIXTURE['secret'], json.dumps(packet, ensure_ascii=False))

    def test_disclosure_requires_exact_scene_and_approval(self):
        self.plan['approved_disclosures'] = [{'fact_id': 'K1', 'character_id': 'A', 'scene_id': 'S1',
                                            'source_event': 'E1', 'author_approved': True}]
        self.assertEqual([], w.context(self.root, self.plan)['pov_knowledge']['scene_disclosures'])
        self.assertEqual('B 是凶手。', w.context(self.root, self.plan, 'S1')['pov_knowledge']['scene_disclosures'][0]['text'])

    def test_temporal_two_hours_not_daylight(self):
        self.body.write_text('两个小时后，清晨阳光已经照进窗户。', encoding='utf-8')
        claims = {'body_sha256': w.digest(self.body.read_bytes()), 'claims': [{'type': 'time', 'location': 'p1',
            'evidence': '两个小时后，清晨阳光已经照进窗户。', 'elapsed_minutes': 120,
            'story_time': '2030-01-02T01:00:00+08:00', 'daylight': True, 'location_id': 'L1'}]}
        self.assertEqual('FAIL', w.check(self.root, self.body, claims, 'continuity')['result'])

    def test_growth_with_story_support_not_ooc(self):
        claims = {'body_sha256': w.digest(self.body.read_bytes()), 'claims': [{'type': 'emotion', 'character': 'A',
            'location': 'p1', 'evidence': '左臂仍固定着', 'deviation': True, 'supporting_evidence': '左臂仍固定着'}]}
        self.assertEqual('PASS', w.check(self.root, self.body, claims, 'character')['result'])

    def test_reports_never_edit_body_or_state(self):
        before = w.digest(w.load_state(self.root))
        self.checks('bad_body', 'bad_claims')
        body = self.body.read_bytes()
        self.assertEqual(before, w.digest(w.load_state(self.root)))
        w.context(self.root, self.plan)
        self.assertEqual(body, self.body.read_bytes())

    def test_claim_hash_and_paragraph_binding(self):
        with self.assertRaises(ValueError):
            w.check(self.root, self.body, {'body_sha256': 'stale', 'claims': []}, 'contract')
        with self.assertRaises(ValueError):
            w.check(self.root, self.body, {'body_sha256': w.digest(self.body.read_bytes()), 'claims': [
                {'type': 'action', 'character': 'A', 'location': 'p2', 'evidence': '左臂仍固定着'}]}, 'continuity')

    def test_final_requires_all_semantic_reviews(self):
        with self.assertRaises(ValueError):
            w.final_witness(self.root, self.body_relative, 1, {})
        witness = self.witness()
        path = self.root / witness['reviews']['style']['path']
        report = y.read(path); report['coverage'] = 'STRUCTURED_CLAIMS_ONLY'; y.write(path, report)
        with self.assertRaises(ValueError): w.verify_final(self.root, witness)

    def test_extraction_before_final_or_without_evidence_rejected(self):
        with self.assertRaises((ValueError, KeyError)):
            w.extract(self.root, {}, {})
        observations = {key: [] for key in m.MEMORY_KEYS + ['operations']}
        observations['events'] = [{'evidence': '不存在的内容'}]
        with self.assertRaises(ValueError): w.extract(self.root, self.witness(), observations)

    def test_proposal_does_not_change_state(self):
        before = w.digest(w.load_state(self.root))
        self.proposal()
        self.assertEqual(before, w.digest(w.load_state(self.root)))
        self.assertEqual(['fixture-1.yaml'], w.status(self.root)['Pending State Diff'])

    def test_valid_commit_and_idempotency(self):
        proposal = self.proposal(); receipt = w.validate_proposal(self.root, proposal)
        self.assertEqual('COMMITTED', w.commit(self.root, proposal, receipt)['action'])
        state = w.load_state(self.root)
        self.assertEqual(1, state['current-story-state.yaml']['project']['current_chapter'])
        self.assertEqual(1, len(state['chapter-ledger.yaml']['entries']))
        self.assertEqual('ALREADY_COMMITTED', w.commit(self.root, proposal, receipt)['action'])
        self.assertEqual([], w.status(self.root)['Pending State Diff'])

    def test_tampered_proposal_or_receipt_rejected(self):
        proposal = self.proposal(); receipt = w.validate_proposal(self.root, proposal)
        before = w.digest(w.load_state(self.root))
        receipt['candidate_sha256'] = 'tampered'
        with self.assertRaises(ValueError): w.commit(self.root, proposal, receipt)
        self.assertEqual(before, w.digest(w.load_state(self.root)))
        receipt = w.validate_proposal(self.root, proposal)
        proposal['extraction']['operations'][0]['after'] = '2030-01-02T02:00:00+08:00'
        with self.assertRaises(ValueError): w.commit(self.root, proposal, receipt)

    def test_stale_state_or_final_rejected(self):
        proposal = self.proposal(); receipt = w.validate_proposal(self.root, proposal)
        self.body.write_text('修改过的终稿', encoding='utf-8')
        with self.assertRaises(ValueError): w.commit(self.root, proposal, receipt)

    def test_authority_changes_invalidate_final(self):
        witness = self.witness()
        path = self.root / 'settings/style-profile.yaml'
        profile = y.read(path); profile['language_density'] = 'changed'; y.write(path, profile)
        with self.assertRaises(ValueError): w.verify_final(self.root, witness)

    def test_parent_pointer_cannot_replace_canon(self):
        proposal = self.proposal()
        project = w.load_state(self.root)['current-story-state.yaml']['project']
        after = copy.deepcopy(project); after['genre'] = 'unauthorized'
        proposal['extraction']['operations'][0].update(pointer='/project', before=project, after=after)
        with self.assertRaises(ValueError): w.candidate(self.root, proposal)

    def test_missing_or_tampered_diff_review_rejected(self):
        proposal = self.proposal()
        path = self.root / 'state/proposed/fixture-1.review.yaml'
        data = y.read(path); data['proposal_sha256'] = 'stale'; y.write(path, data)
        with self.assertRaises(ValueError): w.validate_proposal(self.root, proposal)

    def test_failure_rolls_back_all_files(self):
        proposal = self.proposal(); receipt = w.validate_proposal(self.root, proposal)
        before = w.digest(w.load_state(self.root))
        with self.assertRaises(OSError): w.commit(self.root, proposal, receipt, fail_after=4)
        self.assertEqual(before, w.digest(w.load_state(self.root)))
        self.assertFalse((self.root / 'state/.commit.lock').exists())
        self.assertFalse((self.root / 'state/proposed/transaction.json').exists())

    def test_canon_and_path_targets_rejected(self):
        state = w.load_state(self.root)
        for target in ['../settings/canon-contract.yaml', 'chapter-ledger.yaml', 'settings/style-profile.yaml']:
            with self.assertRaises(ValueError):
                w.apply_operations(state, [{'file': target, 'pointer': '/x', 'before': None, 'after': 'bad'}])
        with self.assertRaises(ValueError):
            w.apply_operations(state, [{'file': 'knowledge-state.yaml', 'pointer': '/facts/K1/canonical_truth',
                                        'before': FIXTURE['secret'], 'after': '改写真相'}])
        with self.assertRaises(ValueError): w.safe_path(self.root, '../outside.yaml')

    def test_invalid_schema_and_cross_reference_rejected(self):
        proposal = self.proposal()
        proposal['extraction']['operations'][0].update(pointer='/active_characters', before=['A', 'B'], after=['missing'])
        with self.assertRaises(ValueError): w.validate_proposal(self.root, proposal)
        path = self.root / 'state/characters/A.yaml'; char = y.read(path)
        char['knowledge']['knows'] = ['K1']; y.write(path, char)
        with self.assertRaises(ValueError): w.load_state(self.root)

    def test_yaml_roundtrip_and_unsafe_features(self):
        self.assertEqual(self.plan, y.loads(y.dumps(self.plan)))
        self.assertEqual({'x': [{'a': 1, 'b': [2]}]}, y.loads('x:\n  - a: 1\n    b: [2]\n'))
        for source in ['a: 1\na: 2', 'a: &x secret', 'a:\n\tb: 1', '---\na: 1', '{"a":1,"a":2}']:
            with self.assertRaises(ValueError): y.loads(source)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WorkflowTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'result': 'PASS' if result.wasSuccessful() else 'FAIL', 'tests_run': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors),
              'scope': 'Manual micro-fixture + mechanical guards; simulated Final records only; no model prose execution.'}
    out = ROOT / 'docs/validation-v0.1/tests.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
