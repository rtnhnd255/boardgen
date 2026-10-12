"""Сборка графа зависимостей из «Вход:» (SPEC §2.1). Потоки и суффиксы — из конфига."""

import re

_SHAPE = re.compile(r'^[A-ZФ]{1,2}\d+(?:\.\d+)?$')
_STOP = {'RK4'}


def short_name(name, limit=18):
    sn = ' '.join(name.split()[:3])
    return (sn[:limit] + '…') if len(sn) > limit else sn


def parse_vin(code, vin, codes):
    """→ (hard, partial, unknown): жёсткие, частичные {код: метка}, опечатки-токены."""
    hard, partial, unknown = [], {}, []
    if not vin:
        return hard, partial, unknown
    head = re.split(r'[Вв]ыход', vin)[0]
    for seg in head.split(';'):
        toks = [
            t
            for t in (
                x.rstrip('.')
                for x in re.findall(r'(?<![\w-])([A-Za-zФ][A-Za-z0-9.]*(?:\.\d)?)(?![\w-])', seg)
            )
        ]
        codes_in = [t for t in toks if t in codes and t != code]
        soft = re.search(r'фон|параллельн', seg)
        if not soft:
            for t in toks:
                if (
                    t != code
                    and t not in codes
                    and t not in unknown
                    and _SHAPE.match(t)
                    and not re.match(r'^[WQG]\d', t)
                    and t not in _STOP
                ):
                    unknown.append(t)
        if not codes_in:
            continue
        if soft:
            continue
        if re.search(r'част', seg):
            wm = re.search(r'W(\d+)', seg)
            for t in codes_in:
                partial[t] = ('W' + wm.group(1) + '+') if wm else 'част.'
        else:
            hard.extend(t for t in codes_in if t not in hard)
    return hard, partial, unknown


def build_graph(blocks, order, cfg):
    """→ dict(board, graph, partial, unknown, codes). Форма board — SPEC §8/JS."""
    codes = set(blocks)
    graph, partial, unknown = {}, {}, {}
    for c in order:
        hard, pt, unk = parse_vin(c, blocks[c]['vin'], codes)
        graph[c] = hard
        if pt:
            partial[c] = pt
        if unk:
            unknown[c] = unk

    board = []
    for c in order:
        b = blocks[c]
        st, en = b['weeks'] or (1, 1)
        stream = cfg.stream_of(c)
        name = cfg.name_overrides.get(c) or short_name(b['name']) or c
        if stream == cfg.stream_ids[0] and en in cfg.buffer_weeks:
            name += '+буфер'
        q = 'Q' + str((st - 1) // cfg.quarters_weeks + 1)
        pr = graph[c] + list(partial.get(c, {}).keys())
        weeks = f'W{st}' + (f'-{en}' if en != st else '')
        board.append((c, name, weeks, q, stream, ','.join(pr), partial.get(c) or ''))
    return {'board': board, 'graph': graph, 'partial': partial, 'unknown': unknown, 'codes': codes}
