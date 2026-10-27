"""Conservative Chinese dialogue metadata. Never writes authoritative data."""
import re


def dialogue_rows(body, cards):
    aliases = {}
    for row in cards:
        card = row['canonical']
        for name in [card.get('name'), *card.get('aliases', [])]:
            if name:
                aliases.setdefault(name, set()).add(card['id'])
    rows = []
    # No alternating-speaker, nearest-name, pronoun, or dead-person inference.
    names = '|'.join(re.escape(n) for n in sorted(aliases, key=len, reverse=True))
    tag = re.compile(r'(?:^|[。！？；，：、\s])(?P<name>' + (names or r'(?!)') + r')(?P<channel>在电话(?:那头|中|里)|在听筒(?:里|中)|隔着电话)?(?:说|问|答|回答|说道|问道|回答道)[：:，,]?\s*$')
    after_tag = re.compile(r'^\s*[，,]?\s*(?P<name>' + (names or r'(?!)') + r')(?P<channel>在电话(?:那头|中|里)|在听筒(?:里|中)|隔着电话)?(?:说|问|答|回答|说道|问道|回答道)[。！？，,.!?]?\s*$')
    for paragraph, text in enumerate(body.splitlines(), 1):
        quotes = list(re.finditer(r'“([^“”]*)”|「([^「」]*)」', text))
        for index, quote in enumerate(quotes):
            before = text[quotes[index-1].end() if index else 0:quote.start()]
            after = text[quote.end():quotes[index+1].start() if index+1 < len(quotes) else len(text)]
            candidates = [m for m in [tag.search(before), after_tag.match(after)] if m]
            identities = set().union(*(aliases[m['name']] for m in candidates)) if candidates else set()
            # A quoted/remembered utterance is not evidence of live participation.
            recalled = bool(re.search(r'回忆|想起|转述|记录|曾经|当时|以前|记得', before))
            speaker = next(iter(identities)) if len(identities) == 1 and not recalled else 'UNKNOWN'
            remote = any(m['channel'] for m in candidates)
            rows.append({'paragraph': paragraph, 'text': quote.group(1) or quote.group(2) or '',
                         'speaker': speaker, 'channel': 'PHONE' if remote and speaker != 'UNKNOWN' else 'UNKNOWN',
                         'evidence': 'EXPLICIT_SPEECH_TAG' if speaker != 'UNKNOWN' else 'UNKNOWN',
                         'physical_presence': 'UNKNOWN'})
    return rows


def cast_projection(card, body, cards):
    dialogue = dialogue_rows(body, cards)
    pov=card.get('pov') or {}
    pov=pov.get('character') if isinstance(pov,dict) else pov
    remote = {r['speaker'] for r in dialogue if r['channel'] == 'PHONE' and r['speaker']!=pov}
    explicit = {r['speaker'] for r in dialogue if r['speaker'] != 'UNKNOWN'}
    # Scene/card casts remain assertions from the plan, not observations from prose.
    physical = set(card.get('characters', [])) | {c for s in card.get('scenes', []) for c in s.get('characters', [])}
    physical -= remote
    mentioned = {r['canonical']['id'] for r in cards
                 if any(n and n in body for n in [r['canonical'].get('name'), *r['canonical'].get('aliases', [])])}
    return {'physical_planned': sorted(physical), 'remote_explicit': sorted(remote),
            'on_page': sorted(physical | explicit), 'mentions': sorted(mentioned - physical - explicit),
            'dialogue': dialogue}
