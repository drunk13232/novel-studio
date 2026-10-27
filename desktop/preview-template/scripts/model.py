"""V0.1 schemas and empty authoring templates; no invented story content."""
import copy
import json
from pathlib import Path
from yaml_io import write

VERSION = '0.1'
CURRENT = {'schema_version': VERSION, 'revision': 0,
           'project': dict.fromkeys(['title', 'genre', 'current_volume', 'current_scene', 'story_date']),
           'pov': dict.fromkeys(['current_character', 'tense', 'person']),
           'location': {'current': None}, 'active_characters': [], 'active_threads': [],
           'recent_events': [], 'open_foreshadowing': [], 'hard_constraints': [], 'warnings': []}
CURRENT['project']['current_chapter'] = 0
CHARACTER = {'id': None, 'name': None, 'aliases': [],
             'status': {'alive': True, 'location': None, 'physical_condition': None,
                        'mental_condition': None, 'age': None, 'limitations': []},
             'relationships': {}, 'knowledge': {'knows': [], 'suspects': [], 'does_not_know': []},
             'goals': {'short_term': [], 'long_term': []}, 'secrets': {'personal': []},
             'inventory': [], 'abilities': [], 'recent_changes': [], 'last_updated_chapter': None,
             'writer_view': [], 'characterization': {'values': [], 'voice': [], 'established_goals': []}}
VIEW = {'text': None, 'visibility': 'CHARACTER', 'known_by': [], 'since_chapter': None, 'story_time': None}
RECEIPT = {'character_id': None, 'acquired_chapter': None, 'story_time': None, 'source_event': None}
FACT = {'canonical_truth': None, 'introduced_chapter': None, 'known_by': [], 'suspected_by': [],
        'false_beliefs': {}, 'restricted_until': None, 'public': False, 'public_since_chapter': None,
        'public_story_time': None}
FORESHADOW = {'title': None, 'introduced_chapter': None, 'status': 'OPEN', 'importance': None,
              'visible_to_reader': False, 'known_by': [],
              'planned_window': dict.fromkeys(['earliest', 'preferred', 'latest']),
              'setup': None, 'developments': [], 'intended_payoff': None, 'restrictions': [],
              'resolved_chapter': None, 'writer_view': []}
THREAD = {'title': None, 'type': 'main', 'status': 'OPEN', 'introduced_chapter': None,
          'last_advanced_chapter': None, 'characters': [], 'developments': [], 'writer_view': []}
EVENT = {'id': None, 'chapter': None, 'story_time': None, 'location': None, 'characters': [],
         'summary': None, 'writer_view': [], 'evidence': None}
RELATIONSHIP = {'characters': [], 'kind': None, 'strength': None, 'last_updated_chapter': None, 'writer_view': []}
LOCATION = {'name': None, 'writer_view': [], 'daylight_hours': [], 'travel_minutes': {}}
ITEM = {'name': None, 'holder': None, 'location': None, 'status': None, 'writer_view': []}
FACTION = {'name': None, 'members': [], 'writer_view': []}
CONTRACT = {'schema_version': VERSION, 'hard': [], 'strong': [], 'soft': [], 'preferences': []}
RULE = {'id': None, 'statement': None, 'check': None, 'writer_view': []}
STYLE = {'schema_version': VERSION, 'language_density': None, 'dialogue_ratio': None,
         'description_preferences': [], 'interiority': None, 'pacing': None,
         'pov': {'person': None, 'tense': None, 'distance': None}, 'allow_internet_slang': None,
         'allow_author_summary': None, 'metaphor_density': None,
         'banned_expressions': [], 'ai_high_risk_expressions': [], 'hemingway_opt_in': False}
SCENE = {'id': None, 'purpose': None, 'location': None, 'characters': [], 'conflict': None,
         'turn': None, 'outcome': None, 'emotional_change': None, 'writer_view': []}
PLAN = {'chapter': {'number': None, 'title': None, 'volume': None}, 'pov': {'character': None},
        'setting': {'location': None, 'story_time': None}, 'chapter_goal': None,
        'character_goals': {}, 'scenes': [], 'must_include': [], 'must_not_include': [],
        'foreshadowing': {'advance': [], 'introduce': [], 'resolve': []},
        'knowledge_changes': [], 'state_changes_expected': [], 'ending_hook': None,
        'writer_view': [], 'approved_disclosures': []}
MEMORY_KEYS = ['events', 'character_changes', 'relationship_changes', 'knowledge_changes',
               'location_changes', 'item_changes', 'faction_changes', 'new_foreshadowing',
               'advanced_foreshadowing', 'resolved_foreshadowing', 'plot_threads_opened',
               'plot_threads_advanced', 'plot_threads_closed']
MEMORY = {'chapter': None, 'body_sha256': None, **{k: [] for k in MEMORY_KEYS}, 'operations': []}
STATES = {'current-story-state.yaml': CURRENT,
          **{f'{k}.yaml': {field: [] if field == 'events' else {}}
             for k, field in [('relationships', 'relationships'), ('timeline', 'events'),
                               ('knowledge-state', 'facts'), ('foreshadowing', 'foreshadowing'),
                               ('plot-threads', 'threads'), ('locations', 'locations'),
                               ('items', 'items'), ('factions', 'factions')]},
          'chapter-ledger.yaml': {'last_commit': None, 'entries': []}}


def nullable(type_name):
    return {'type': [type_name, 'null']}


def obj(props, required=None, extra=False):
    return {'type': 'object', 'properties': props, 'required': list(props) if required is None else required,
            'additionalProperties': extra}


def array(item=None):
    return {'type': 'array', 'items': item or nullable('string')}


def infer(template):
    if isinstance(template, dict):
        return obj({k: infer(v) for k, v in template.items()})
    if isinstance(template, list):
        return array()
    if isinstance(template, bool):
        return {'type': 'boolean'}
    if isinstance(template, int):
        return {'type': 'integer', 'minimum': 0}
    if template is None:
        return nullable('string')
    return {'type': 'string'}


def schemas():
    definitions = {name: infer(value) for name, value in
                   [('current', CURRENT), ('character', CHARACTER), ('view', VIEW), ('receipt', RECEIPT),
                    ('fact', FACT), ('foreshadow', FORESHADOW), ('thread', THREAD), ('event', EVENT),
                    ('relationship', RELATIONSHIP), ('location', LOCATION), ('item', ITEM),
                    ('faction', FACTION), ('contract', CONTRACT), ('rule', RULE), ('style', STYLE),
                    ('scene', SCENE), ('plan', PLAN)]}
    ref = lambda name: {'$ref': '#/$defs/' + name}
    mapof = lambda name: {'type': 'object', 'additionalProperties': ref(name)}
    for name, keys in {'current': [], 'character': ['last_updated_chapter'], 'view': ['since_chapter'],
                       'receipt': ['acquired_chapter'], 'fact': ['introduced_chapter', 'restricted_until', 'public_since_chapter'],
                       'foreshadow': ['introduced_chapter', 'resolved_chapter'],
                       'thread': ['introduced_chapter', 'last_advanced_chapter'], 'event': ['chapter'],
                       'relationship': ['last_updated_chapter']}.items():
        for key in keys:
            definitions[name]['properties'][key] = {'type': ['integer', 'null'], 'minimum': 0}
    for key in ['current_chapter', 'current_volume']:
        definitions['current']['properties']['project']['properties'][key] = {'type': ['integer', 'null'], 'minimum': 0}
    definitions['current']['properties']['recent_events'] = array()
    definitions['view']['properties']['visibility'] = {'enum': ['PUBLIC', 'CHARACTER', 'AUTHOR']}
    definitions['character']['properties']['status']['properties']['age'] = {'type': ['number', 'null'], 'minimum': 0}
    definitions['character']['properties']['relationships'] = {'type': 'object', 'additionalProperties': nullable('string')}
    for name in ['character', 'foreshadow', 'thread', 'event', 'relationship', 'location', 'item', 'faction', 'rule', 'scene', 'plan']:
        definitions[name]['properties']['writer_view'] = array(ref('view'))
    for name in ['known_by', 'suspected_by']:
        definitions['fact']['properties'][name] = array(ref('receipt'))
    definitions['fact']['properties']['false_beliefs'] = {'type': 'object', 'additionalProperties': obj({
        'belief': nullable('string'), 'acquired_chapter': {'type': 'integer', 'minimum': 0},
        'story_time': nullable('string'), 'source_event': nullable('string')})}
    definitions['foreshadow']['properties']['status'] = {'enum': ['OPEN', 'DEVELOPING', 'READY', 'RESOLVED', 'ABANDONED']}
    definitions['thread']['properties']['status'] = {'enum': ['OPEN', 'ACTIVE', 'DORMANT', 'RESOLVED', 'DROPPED']}
    definitions['thread']['properties']['type'] = {'enum': ['main', 'sub', 'character', 'romance', 'mystery']}
    for key in ['earliest', 'preferred', 'latest']:
        definitions['foreshadow']['properties']['planned_window']['properties'][key] = {'type': ['integer', 'null'], 'minimum': 0}
    for key in ['number', 'volume']:
        definitions['plan']['properties']['chapter']['properties'][key] = {'type': ['integer', 'null'], 'minimum': 0}
    definitions['plan']['properties']['character_goals'] = {'type': 'object', 'additionalProperties': array()}
    definitions['plan']['properties']['scenes'] = array(ref('scene'))
    definitions['plan']['properties']['knowledge_changes'] = array({'type': 'object', 'additionalProperties': True})
    definitions['plan']['properties']['state_changes_expected'] = array({'type': 'object', 'additionalProperties': True})
    definitions['plan']['properties']['approved_disclosures'] = array(obj({
        'fact_id': {'type': 'string'}, 'character_id': {'type': 'string'}, 'scene_id': {'type': 'string'},
        'source_event': {'type': 'string'}, 'author_approved': {'type': 'boolean'}}))
    # Optional, backward compatible metadata. Reader awareness never grants POV knowledge.
    definitions['fact']['properties']['reader_known_since_chapter'] = {'type':['integer','null'],'minimum':0}
    disclosure = definitions['plan']['properties']['approved_disclosures']['items']
    disclosure['properties']['audience'] = {'enum':['CHARACTER','READER','BOTH']}
    for key in ['hard', 'strong', 'soft', 'preferences']:
        definitions['contract']['properties'][key] = array(ref('rule'))
    definitions['location']['properties']['daylight_hours'] = array({'type': 'integer', 'minimum': 0, 'maximum': 23})
    definitions['location']['properties']['travel_minutes'] = {'type': 'object', 'additionalProperties': {'type': 'number', 'minimum': 0}}
    for key in ['check']:
        definitions['rule']['properties'][key] = {'enum': [None, 'injury', 'knowledge', 'alive', 'time', 'location', 'age', 'item', 'ability', 'sequence', 'manual']}
    definitions['ledger'] = obj({'last_commit': {'type': ['string', 'null']}, 'entries': array(obj({
        'chapter': {'type': 'integer', 'minimum': 1}, 'body_sha256': {'type': 'string'},
        'proposal_id': {'type': 'string'}, 'proposal_sha256': {'type': 'string'}, 'committed_at': {'type': 'string'}, 'revision': {'type': 'integer'}}))})
    definitions['timeline'] = obj({'events': array(ref('event'))})
    for filename, field, row in [('relationships', 'relationships', 'relationship'), ('knowledge-state', 'facts', 'fact'),
                                  ('foreshadowing', 'foreshadowing', 'foreshadow'), ('plot-threads', 'threads', 'thread'),
                                  ('locations', 'locations', 'location'), ('items', 'items', 'item'), ('factions', 'factions', 'faction')]:
        definitions[filename] = obj({field: mapof(row)})
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$defs': definitions}


SCHEMAS = schemas()
FILE_SCHEMAS = {'current-story-state.yaml': 'current', 'chapter-ledger.yaml': 'ledger',
                **{k: k[:-5] for k in STATES if k not in ['current-story-state.yaml', 'chapter-ledger.yaml']}}


def validate(value, schema, path='$'):
    """Validator for the exact keywords emitted above, not arbitrary JSON Schema."""
    if '$ref' in schema:
        schema = SCHEMAS['$defs'][schema['$ref'].split('/')[-1]]
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(path + ': invalid enum')
    types = schema.get('type', [])
    types = [types] if isinstance(types, str) else types
    predicates = {'null': lambda x: x is None, 'object': lambda x: isinstance(x, dict),
                  'array': lambda x: isinstance(x, list), 'string': lambda x: isinstance(x, str),
                  'integer': lambda x: type(x) is int, 'number': lambda x: type(x) in (float, int),
                  'boolean': lambda x: type(x) is bool}
    if types and not any(predicates[t](value) for t in types):
        raise ValueError(path + ': wrong type')
    if type(value) in (int, float):
        if value < schema.get('minimum', float('-inf')) or value > schema.get('maximum', float('inf')):
            raise ValueError(path + ': out of range')
    if isinstance(value, dict):
        for key in schema.get('required', []):
            if key not in value:
                raise ValueError(path + ': missing ' + key)
        for key, item in value.items():
            subschema = schema.get('properties', {}).get(key, schema.get('additionalProperties', True))
            if subschema is False:
                raise ValueError(path + ': unexpected ' + key)
            if isinstance(subschema, dict):
                validate(item, subschema, path + '/' + key)
    if isinstance(value, list):
        for index, item in enumerate(value):
            validate(item, schema.get('items', {}), path + '/' + str(index))


def initialize(root):
    """Create missing templates only. Existing author files are never overwritten."""
    root = Path(root)
    files = {**{'state/' + k: v for k, v in STATES.items()},
             'settings/canon-contract.yaml': CONTRACT, 'settings/style-profile.yaml': STYLE,
             'outlines/chapter-template.yaml': PLAN,
             **{'templates/state/' + name + '.yaml': value for name, value in [
                 ('character', CHARACTER), ('knowledge-fact', FACT), ('receipt', RECEIPT), ('writer-view', VIEW),
                 ('foreshadow', FORESHADOW), ('plot-thread', THREAD), ('event', EVENT),
                 ('relationship', RELATIONSHIP), ('location', LOCATION), ('item', ITEM), ('faction', FACTION), ('canon-rule', RULE)]},
             'templates/memory-extraction.yaml': MEMORY}
    for relative, value in files.items():
        if not (root / relative).exists():
            write(root / relative, copy.deepcopy(value))
    for relative in ['state/characters', 'state/proposed']:
        (root / relative).mkdir(parents=True, exist_ok=True)
        (root / relative / '.gitkeep').touch(exist_ok=True)
    schema_path = root / 'schemas/novel-v0.1.schema.json'
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(json.dumps(SCHEMAS, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    initialize(Path(__file__).resolve().parents[1])
