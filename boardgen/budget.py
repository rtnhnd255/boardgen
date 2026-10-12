"""Таблица бюджета часов поток × квартал (ставки и итог — из конфига)."""


def budget_html(blocks, order, cfg):
    nq = cfg.quarter_count
    filled = {(sid, q): 0.0 for sid in cfg.stream_ids for q in range(1, nq + 1)}
    for c in order:
        b = blocks[c]
        if not b['hours']:
            continue
        sid = cfg.stream_of(c)
        q = (b['weeks'][0] - 1) // cfg.quarters_weeks + 1
        filled[(sid, q)] += b['hours']

    head = ''.join(f'<th>Q{q}</th>' for q in range(1, nq + 1))
    rows = ''
    tot = 0.0
    for sid in cfg.stream_ids:
        cells = ''
        srow = 0.0
        for q in range(1, nq + 1):
            v = filled[(sid, q)]
            srow += v
            rate = cfg.rates.get(sid)
            bud = rate * cfg.quarters_weeks if rate else None
            col = '#2e7d32' if bud and v >= bud * 0.8 else ('#b45309' if bud and v >= bud * 0.5 else '#999')
            target = f'<br><span style="font-size:9px;color:#aaa">/{bud}</span>' if bud else ''
            cells += f'<td style="color:{col}">{v:.0f}{target}</td>'
        tot += srow
        row_total = f'{srow:.0f}'
        if cfg.rates.get(sid) is not None:
            row_total += f' / {cfg.rates[sid] * cfg.total_weeks}'
        rows += f'<tr><td><b>{sid}</b></td>{cells}<td><b>{row_total}</b></td></tr>'

    grand = f'<b>{tot:.0f}</b>'
    if cfg.total_hours:
        pct = tot / cfg.total_hours * 100
        grand = f'<b>{tot:.0f}</b> / {cfg.total_hours} ({pct:.0f}%)'
    rates_note = ', '.join(f'{k}={v}' for k, v in cfg.rates.items()) or 'не заданы'
    return (
        '<section class="chapter" id="budget">'
        '<h2>Бюджет часов — поток × квартал (заполнено / доступно по слотам)</h2>'
        f'<table><tr><th>Поток</th>{head}<th>Σ {cfg.total_weeks} нед</th></tr>'
        + rows
        + f'<tr><td><b>Σ</b></td><td colspan="{nq}"></td><td>{grand}</td></tr></table>'
        f'<p style="font-size:11px;color:#5a6a7a">Ставки слотов/нед: {rates_note}. '
        'Заполнено = сумма часов из заголовков карточек. Ячейка зелёная ≥80% ставки, '
        'коричневая ≥50%.</p>'
        '</section>'
    )
