"""Markdown → HTML для карточек (S6). Порт parse_md дословно; отличие —
счётчик чекбоксов и список кодов — поля экземпляра (детерминизм id:
один CardRenderer на сборку, файлы в порядке config.MD_FILES).
"""

import html
import re


def esc(text):
    return html.escape(text, quote=False)


def inline(s):
    s = esc(s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    return re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)


class CardRenderer:
    def __init__(self, codes):
        self.codes = list(codes)  # порядок = от граф-сборки (len desc)
        self.ck_no = 0

    def _cid(self, cur_code):
        self.ck_no += 1
        return f'ck-{cur_code}-{self.ck_no}' if cur_code else f'ck-x-{self.ck_no}'

    def render(self, md):
        lines = md.split('\n')
        out = []
        cur_code = ''
        pending_ck = False
        ol_ck = False
        ol_open = False
        in_gate = False

        def close_ol():
            nonlocal ol_open
            if ol_open:
                out.append('</ol>')
                ol_open = False

        def close_gate():
            nonlocal in_gate
            if in_gate:
                out.append('</ul>')
                in_gate = False

        skip_past = -1
        for i, t in enumerate(lines):  # noqa: PLW2901 — t.rstrip() нормализует строку
            if i <= skip_past:
                continue
            t = t.rstrip()  # noqa: PLW2901 — нормализация строки цикла
            if i == 0 and t.startswith('# '):
                continue
            if t.startswith('```'):
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('```'):
                    j += 1
                skip_past = j
                continue
            if not t.strip() or re.fullmatch(r'-{3,}', t.strip()):
                close_ol()
                close_gate()
                continue

            if not re.match(r'^\d+\.\s+', t):
                pending_ck = False

            # Headers
            m = re.match(r'^(#{1,3})\s+(.*)$', t)
            if m:
                close_ol()
                close_gate()
                lvl = len(m.group(1))
                raw = m.group(2)
                txt = inline(raw)
                mc = re.match(
                    r'^(P\d+|S\d+|B[\w.]+|C\d+|CPP\d+|M\d+(?:\.\d+)?|D\d+[ab]?|E\d+(?:\.\d+)?|VIO|Ф1|OpenCV|C\+\+)',
                    raw,
                )
                hid = ''
                blk_btn = ''
                if lvl == 3 and mc:
                    code = mc.group(1).replace('C++', 'CPP')
                    cur_code = code
                    hid = f' id="blk-{code}"'
                    blk_btn = f'<span class="blk-btn" data-blk="{code}">⬜</span><span class="cvf" data-blk="{code}" title="показать на канвасе">◎</span> '
                mg = re.match(r'^(G[1-6])\b', raw)
                if lvl == 2 and mg:
                    hid = f' id="gte-{mg.group(1)}"'
                tag = f'h{lvl}'
                out.append(f'<{tag}{hid}>{blk_btn}{txt}</{tag}>')
                continue

            # Tables
            if t.strip().startswith('|'):
                close_ol()
                close_gate()
                rows = []
                j = i
                while j < len(lines) and lines[j].strip().startswith('|'):
                    cells = [c.strip() for c in lines[j].strip().strip('|').split('|')]
                    if not all(re.fullmatch(r':?-{2,}:?', c) for c in cells):
                        rows.append(cells)
                    j += 1
                if rows:
                    tbl = '<table><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in rows[0]) + '</tr>'
                    for r in rows[1:]:
                        tbl += '<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>'
                    tbl += '</table>'
                    out.append(tbl)
                skip_past = j - 1
                continue

            # Label lines (**Вход:**, **Гейт:**, ...)
            m2 = re.match(r'^\*\*([^:*]+):\*\*\s*(.*)$', t)
            if m2:
                close_ol()
                close_gate()
                label, rest = m2.group(1), m2.group(2).strip()
                label_lower = label.lower()

                if '☐' in rest:
                    out.append(f'<div class="kv"><b>{inline(label)}:</b></div>')
                    out.append('<ul class="gate">')
                    for item in rest.split('☐')[1:]:  # noqa: PLW2901 — нормализация пункта
                        item = item.strip()  # noqa: PLW2901 — нормализация пункта  # noqa: PLW2901 — нормализация пункта
                        if item:
                            out.append(
                                f'<li><input type="checkbox" class="ck" data-ck="{self._cid(cur_code)}">{inline(item)}</li>'
                            )
                    out.append('</ul>')
                elif 'вход' in label_lower:
                    # статические ✅/✗ срезаны — статус ставится динамически в JS
                    rest = re.sub(r'\s*[\u2705\u2713\u2717\u274c\u2b1c]', '', rest)
                    txt = inline(rest)
                    for kc in self.codes:
                        kc_esc = re.escape(kc)
                        xref_code = kc.replace('C++', 'CPP')
                        txt = re.sub(
                            r'(?<![\w-])' + kc_esc + r'(?![\w-])',
                            f'<a href="#blk-{xref_code}" class="xref" data-blk="{xref_code}">{kc}</a>',
                            txt,
                        )
                    out.append(f'<div class="kv"><b>{inline(label)}:</b> {txt}</div>')
                elif label_lower.startswith('теория') or label_lower.startswith('практика'):
                    rest_s = rest.strip()
                    items = []
                    if rest_s:
                        if re.match(r'^1\)\s+', rest_s):
                            parts = re.split(r'\s+\d+\)\s+', rest_s)
                            items = [p.strip(' ·;') for p in parts if p.strip(' ·;')]
                        elif '·' in rest_s and label_lower.startswith('практика'):
                            items = [p.strip(' ·') for p in rest_s.split('·') if p.strip(' ·')]
                        elif ';' in rest_s and label_lower.startswith('теория'):
                            items = [p.strip(' ;') for p in rest_s.split(';') if p.strip(' ;')]
                        else:
                            items = [rest_s]
                    if items:
                        out.append(f'<div class="kv"><b>{inline(label)}:</b></div>')
                        out.append('<ul class="pr-list">')
                        for item in items:
                            out.append(
                                f'<li><input type="checkbox" class="ck" data-ck="{self._cid(cur_code)}">{inline(item)}</li>'
                            )
                        out.append('</ul>')
                    else:
                        pending_ck = True
                else:
                    txt = inline(rest)
                    out.append(f'<div class="kv"><b>{inline(label)}:</b> {txt}</div>')
                continue

            # Standalone ☐ lines
            stripped = t.strip()
            if stripped.startswith('☐'):
                close_ol()
                close_gate()
                out.append('<ul class="gate">')
                for item in stripped.split('☐')[1:]:  # noqa: PLW2901 — нормализация пункта
                    item = item.strip()  # noqa: PLW2901 — нормализация пункта
                    if item:
                        out.append(
                            f'<li><input type="checkbox" class="ck" data-ck="{self._cid(cur_code)}">{inline(item)}</li>'
                        )
                out.append('</ul>')
                continue

            # Lists with ☐
            m3 = re.match(r'^[-*]\s+(.*)$', t)
            if m3 and '☐' in m3.group(1):
                close_ol()
                close_gate()
                if not out or not out[-1].startswith('<ul class="gate'):
                    out.append('<ul class="gate">')
                for item in m3.group(1).split('☐')[1:]:  # noqa: PLW2901 — нормализация пункта
                    item = item.strip()  # noqa: PLW2901 — нормализация пункта
                    if item:
                        out.append(
                            f'<li><input type="checkbox" class="ck" data-ck="{self._cid(cur_code)}">{inline(item)}</li>'
                        )
                continue

            # Regular lists
            if m3:  # noqa: PLW2901 — последовательные матчеры, портировано дословно
                close_ol()
                close_gate()
                out.append(f'<ul><li>{inline(m3.group(1))}</li></ul>')
                continue

            # Ordered lists
            m4 = re.match(r'^\d+\.\s+(.*)$', t)
            if m4:
                if not ol_open:
                    close_ol()
                    close_gate()
                    out.append('<ol>')
                    ol_open = True
                    ol_ck = pending_ck
                if ol_ck:
                    out.append(
                        f'<li><input type="checkbox" class="ck" data-ck="{self._cid(cur_code)}">{inline(m4.group(1))}</li>'
                    )
                else:
                    out.append(f'<li>{inline(m4.group(1))}</li>')
                continue

            close_ol()
            close_gate()
            out.append(f'<p>{inline(t.strip())}</p>')

        close_ol()
        close_gate()
        return '\n'.join(out)
