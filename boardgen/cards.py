"""Парсер карточек (SPEC §2): ### CODE · Название — Wa–b (N ч) + **Вход:**.

Спилл-оверы объединяются union'ом недель; часы и «Вход:» — из первого вхождения
в порядке глав (детерминизм).
"""

import re


def _code_of(title, aliases):
    for pref, code in aliases.items():
        if title.startswith(pref):
            return code
    m = re.match(r'^([A-Za-zФ][A-Za-z0-9.]*)\s*·', title)
    return m.group(1) if m else None


def parse_cards(chapters, aliases):
    """chapters: [(абс.путь, title)] → (blocks, order)."""
    blocks, order = {}, []
    for path, _title in chapters:
        with open(path, encoding='utf-8') as f:
            md = f.read()
        for chunk in re.split(r'^### ', md, flags=re.M)[1:]:
            title = chunk.split('\n', 1)[0].strip()
            code = _code_of(title, aliases)
            if not code:
                continue
            wm = re.search(r'W(\d+)(?:[–-]W?(\d+))?', title)
            hm = re.search(r'\((\d+(?:[.,]\d+)?)\s*ч', title)
            if code not in blocks:
                nm = re.search(r'·\s*(.+?)\s*—', title)
                blocks[code] = {
                    'weeks': None,
                    'hours': None,
                    'vin': '',
                    'name': nm.group(1).strip() if nm else '',
                }
                order.append(code)
            b = blocks[code]
            if wm:
                a_, z_ = int(wm.group(1)), int(wm.group(2) or wm.group(1))
                b['weeks'] = (
                    [a_, z_] if b['weeks'] is None else [min(b['weeks'][0], a_), max(b['weeks'][1], z_)]
                )
            if hm and b['hours'] is None:
                b['hours'] = float(hm.group(1).replace(',', '.'))
            if not b['vin']:
                vm = re.search(r'\*\*Вход[^*]*:\*\*\s*(.*)', chunk)
                if vm:
                    b['vin'] = vm.group(1).strip()
    return blocks, order
