"""Restricted legacy YAML codec with a safe optional PyYAML format bridge.

Supported: indented maps/sequences, quoted/plain scalars, JSON flow values.
Unsupported YAML syntax fails closed; this is not a full YAML implementation.
"""
import json
import re
from pathlib import Path


def scalar(text):
    text = text.strip()
    if not text:
        return None
    if text.startswith(('&', '*', '!', '|', '>')):
        raise ValueError('YAML anchors, tags and block scalars are unsupported')
    if text.startswith(('"', '[', '{')):
        return json.loads(text)
    if text.startswith("'"):
        if not text.endswith("'"):
            raise ValueError('Unclosed scalar')
        return text[1:-1].replace("''", "'")
    if text in ('null', '~'):
        return None
    if text in ('true', 'false'):
        return text == 'true'
    if re.fullmatch(r'-?(0|[1-9][0-9]*)(\.[0-9]+)?', text):
        return float(text) if '.' in text else int(text)
    return text


def _legacy_loads(source):
    source = source.lstrip('\ufeff')
    if source.lstrip().startswith(('{', '[')):
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate key: ' + key)
                result[key] = value
            return result
        return json.loads(source, object_pairs_hook=unique)
    lines = []
    for number, raw in enumerate(source.splitlines(), 1):
        if '\t' in raw:
            raise ValueError(f'Line {number}: tabs unsupported')
        # Strip comments only outside quotes/JSON flow collections.
        quote, depth, escaped, end = None, 0, False, len(raw)
        for index, char in enumerate(raw):
            if escaped:
                escaped = False
                continue
            if char == '\\' and quote == '"':
                escaped = True
            elif quote:
                if char == quote:
                    quote = None
            elif char in "\"'":
                quote = char
            elif char in '[{':
                depth += 1
            elif char in ']}':
                depth -= 1
            elif char == '#' and depth == 0 and (index == 0 or raw[index-1].isspace()):
                end = index
                break
        raw = raw[:end].rstrip()
        if not raw.strip():
            continue
        if raw.strip() in ('---', '...'):
            raise ValueError('Document markers unsupported; one document per file')
        indent = len(raw) - len(raw.lstrip(' '))
        if indent % 2:
            raise ValueError(f'Line {number}: indentation must be a multiple of two')
        lines.append((indent, raw.strip()))
    if not lines:
        return None

    def split_pair(text):
        match = re.match(r'^([A-Za-z0-9_.-]+):(?:\s+(.*)|$)', text)
        if not match or match[1] == '<<':
            raise ValueError('Unsupported mapping: ' + text)
        return match[1], match[2] or ''

    def block(index, indent):
        is_list = lines[index][1] == '-' or lines[index][1].startswith('- ')
        result = [] if is_list else {}
        while index < len(lines) and lines[index][0] == indent:
            text = lines[index][1]
            if is_list:
                if not (text == '-' or text.startswith('- ')):
                    raise ValueError('Mixed sequence/mapping')
                item = text[1:].strip()
                index += 1
                if re.match(r'^[A-Za-z0-9_.-]+:(?:\s|$)', item):
                    key, value = split_pair(item)
                    obj = {}
                    if value:
                        obj[key] = scalar(value)
                    elif index < len(lines) and lines[index][0] == indent + 4:
                        obj[key], index = block(index, indent + 4)
                    else:
                        obj[key] = None
                    if index < len(lines) and lines[index][0] == indent + 2:
                        rest, index = block(index, indent + 2)
                        if not isinstance(rest, dict) or key in rest:
                            raise ValueError('Invalid sequence mapping')
                        obj.update(rest)
                    result.append(obj)
                elif item:
                    result.append(scalar(item))
                elif index < len(lines) and lines[index][0] == indent + 2:
                    value, index = block(index, indent + 2)
                    result.append(value)
                else:
                    result.append(None)
            else:
                key, value = split_pair(text)
                if key in result:
                    raise ValueError('Duplicate key: ' + key)
                index += 1
                if value:
                    result[key] = scalar(value)
                elif index < len(lines) and lines[index][0] == indent + 2:
                    result[key], index = block(index, indent + 2)
                else:
                    result[key] = None
        return result, index
    result, index = block(0, 0)
    if index != len(lines):
        raise ValueError('Unexpected indentation')
    return result



def loads(text):
    """Keep the legacy value rules, accepting safe PyYAML sequence formatting.

    Existing domain services already use PyYAML. The fallback is parsing only:
    aliases/anchors/tags, non-string keys and duplicate mappings fail closed.
    Dates and YAML 1.1 ON/OFF words remain strings as in the original codec.
    """
    try:return _legacy_loads(text)
    except ValueError as original:
        if str(original).startswith('Duplicate key:'):raise
        try:import yaml
        except ImportError:raise original
        if len(text.encode('utf8'))>2*1024*1024:raise ValueError('YAML too large')
        if any(isinstance(t,(yaml.tokens.AliasToken,yaml.tokens.AnchorToken,yaml.tokens.TagToken)) for t in yaml.scan(text)):
            raise ValueError('YAML aliases, anchors and tags are not supported')
        class Loader(yaml.SafeLoader):pass
        Loader.yaml_implicit_resolvers={k:[x for x in v if x[0] not in ['tag:yaml.org,2002:timestamp','tag:yaml.org,2002:bool']] for k,v in yaml.SafeLoader.yaml_implicit_resolvers.items()}
        Loader.add_implicit_resolver('tag:yaml.org,2002:bool',re.compile(r'^(?:true|false|True|False|TRUE|FALSE)$'),list('tTfF'))
        def mapping(loader,node,deep=False):
            result={}
            for key_node,value_node in node.value:
                key=loader.construct_object(key_node,deep=deep)
                if not isinstance(key,str):raise ValueError('YAML mapping keys must be strings')
                if key in result:raise ValueError('Duplicate key: '+key)
                result[key]=loader.construct_object(value_node,deep=deep)
            return result
        Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,mapping)
        value=yaml.load(text,Loader=Loader)
        def depth(v,n=0):
            if n>32:raise ValueError('YAML too deep')
            if isinstance(v,dict):
                for x in v.values():depth(x,n+1)
            if isinstance(v,list):
                for x in v:depth(x,n+1)
        depth(value);return value

def dumps(value, indent=0):
    prefix = ' ' * indent
    if isinstance(value, dict) and value:
        parts = []
        for key, item in value.items():
            if not re.fullmatch(r'[A-Za-z0-9_.-]+', str(key)):
                raise ValueError('Keys must be portable IDs: ' + str(key))
            if isinstance(item, (dict, list)) and item:
                parts.append(prefix + key + ':\n' + dumps(item, indent + 2))
            else:
                parts.append(prefix + key + ': ' + json.dumps(item, ensure_ascii=False))
        return '\n'.join(parts)
    if isinstance(value, list) and value:
        return '\n'.join(prefix + '-\n' + dumps(item, indent + 2)
                         if isinstance(item, (dict, list)) and item
                         else prefix + '- ' + json.dumps(item, ensure_ascii=False) for item in value)
    return prefix + json.dumps(value, ensure_ascii=False)


def read(path):
    return loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(value) + '\n', encoding='utf-8')
