"""Валидатор (SPEC §7): чистая функция, параметризуется конфигом."""

import re


def run(graph, blocks, order, cfg):
    errs, warns = [], []
    ws = {c: (blocks[c]['weeks'] or (1, 1)) for c in order}
    graph_map, partial = graph['graph'], graph['partial']

    # V1
    for c in order:
        for pr in graph_map.get(c, []) + list(partial.get(c, {})):
            if pr not in graph['codes']:
                errs.append(f'V1 {c}: вход {pr} не существует')
        for tok in graph.get('unknown', {}).get(c, []):
            errs.append(f'V1 {c}: «Вход:» упоминает {tok} — не код реестра (опечатка?)')

    # V2
    color = {}

    def dfs(u, path):
        color[u] = 1
        for v in graph_map.get(u, []):
            if color.get(v) == 1:
                errs.append('V2 цикл: ' + ' -> '.join(path + [v]))
            elif color.get(v, 0) == 0:
                dfs(v, path + [v])
        color[u] = 2

    for c in order:
        if color.get(c, 0) == 0:
            dfs(c, [c])

    # V3: непрерывность каждого потока W1..total_weeks
    cov = {}
    for c in order:
        stream = cfg.stream_of(c)
        for w in range(ws[c][0], ws[c][1] + 1):
            cov.setdefault(stream, set()).add(w)
    for sid in cfg.stream_ids:
        missing = [w for w in range(1, cfg.total_weeks + 1) if w not in cov.get(sid, ())]
        if missing:
            errs.append(f'V3 поток {sid}: дырки {missing}')

    # V4
    for c in order:
        for pr in graph_map.get(c, []):
            if pr in cfg.completed_codes or pr not in ws:
                continue
            if ws[pr][1] >= ws[c][0]:
                errs.append(
                    f'V4 {c} старт W{ws[c][0]}: вход {pr} идёт до W{ws[pr][1]} (нет пометки част/параллельн)'
                )

    # V5
    for c in order:
        b = blocks[c]
        if b['hours'] is None:
            warns.append(f'V5 {c}: часы не указаны')
        elif b['hours'] / (ws[c][1] - ws[c][0] + 1) > cfg.max_hours_per_week:
            errs.append(f'V5 {c}: >{cfg.max_hours_per_week:g} ч/нед')

    # V6 (только если задан канон expected)
    if cfg.expected is not None:
        extra, gone = graph['codes'] - cfg.expected, cfg.expected - graph['codes']
        if extra:
            errs.append(f'V6 лишние коды: {sorted(extra)}')
        if gone:
            errs.append(f'V6 нет карточек: {sorted(gone)}')

    # V7
    for c in order:
        if re.search(r'[✅☑✗⬜]', blocks[c]['vin']):
            errs.append(f'V7 {c}: статические метки во Вход')

    return errs, warns
