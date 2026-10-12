"""Тесты boardgen: конфиг, parse_vin, граф, валидатор, рендерер, мини-интеграция.

Запуск:  python3 -m unittest discover tests -v   (из корня репо)
"""

import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from boardgen import budget as budget_mod  # noqa: E402
from boardgen import cards as cards_mod  # noqa: E402
from boardgen import config as config_mod  # noqa: E402
from boardgen import graph as graph_mod  # noqa: E402
from boardgen import markdown as md_mod  # noqa: E402
from boardgen import render as render_mod  # noqa: E402
from boardgen import validate as validate_mod  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINI = os.path.join(ROOT, 'examples', 'mini')

CODES = {
    'B0.1',
    'B0.2',
    'B1',
    'B3',
    'B4',
    'B8',
    'B9.4',
    'D2',
    'D6b',
    'E2',
    'E6',
    'M1.5',
    'P2',
    'P3',
    'P5',
    'S7',
    'S9',
    'S13',
}


def make_config(**kw):
    data = {
        'total_weeks': 26,
        'quarters_weeks': 13,
        'streams': {'A': {'label': 'Ядро'}, 'B': {'label': 'Мат'}, 'C': {'label': 'Практ'}},
        'code_to_stream': {'exact': {}, 'prefix': {'A': 'A', 'B': 'B', 'C': 'C'}},
    }
    data.update(kw)
    return config_mod.RoadmapConfig.from_dict(data)


def blk(weeks, hours=None, vin='', name=''):
    return {'weeks': list(weeks), 'hours': hours, 'vin': vin, 'name': name}


# ===== config =====
class TestConfig(unittest.TestCase):
    def test_buffer_weeks_derived(self):
        cfg = make_config(buffer_weeks=None)
        self.assertEqual(cfg.buffer_weeks, [13, 26])

    def test_stream_of_longest_prefix(self):
        cfg = make_config(code_to_stream={'exact': {'AX': 'B'}, 'prefix': {'A': 'A', 'AB': 'C'}})
        self.assertEqual(cfg.stream_of('AX'), 'B')
        self.assertEqual(cfg.stream_of('AB1'), 'C')
        self.assertEqual(cfg.stream_of('A1'), 'A')
        self.assertIsNone(cfg.stream_of('Z9'))

    def test_ls_key_default_and_custom(self):
        self.assertEqual(make_config().ls_key, 'boardgen')
        cfg = make_config(ls_key='my-roadmap')
        self.assertEqual(cfg.meta()['ls_key'], 'my-roadmap')

    def test_meta_shape(self):
        meta = make_config(start_date='2026-11-01').meta()
        self.assertEqual(meta['total_weeks'], 26)
        self.assertEqual(meta['buffer_weeks'], [13, 26])
        self.assertIn('stream_labels', meta)


# ===== parse_vin =====
class TestParseVin(unittest.TestCase):
    CASES = [
        ('', [], {}, []),
        ('B0.1.', ['B0.1'], {}, []),
        ('D2, B1 (EKF)', ['D2', 'B1'], {}, []),
        ('D2, B1; (фон: B3)', ['D2', 'B1'], {}, []),
        ('— (корень; P2 идёт параллельно)', [], {}, []),
        ('B4 (част. с W39+)', [], {'B4': 'W39+'}, []),
        ('B0.2 (мн). Выход: база для E2 и E6', ['B0.2'], {}, []),
        ('B99 (опечатка)', [], {}, ['B99']),
        ('W27 Сб-1, RPi5', [], {}, []),
        ('P3–P5 и S13', ['P3', 'P5', 'S13'], {}, []),
    ]

    def test_cases(self):
        for vin, hard, partial, unknown in self.CASES:
            with self.subTest(vin=vin):
                h, p, u = graph_mod.parse_vin('X1', vin, CODES)
                self.assertEqual(sorted(h), sorted(hard))
                self.assertEqual(p, partial)
                self.assertEqual(u, unknown)

    def test_self_reference(self):
        h, p, u = graph_mod.parse_vin('B1', 'B1 (сам)', CODES)
        self.assertEqual((h, p, u), ([], {}, []))


# ===== graph =====
class TestBuildGraph(unittest.TestCase):
    def blocks(self):
        return {
            'A1': blk((9, 13), 30.0, 'A2', 'Модель'),
            'A2': blk((1, 8), 26.0, '', 'База'),
            'B1': blk((1, 6), 12.0, '', 'Курс'),
            'C1': blk((7, 13), 14.0, 'B1 (част. с W9+)', 'Пет'),
        }

    def test_buffer_suffix_first_stream_only(self):
        cfg = make_config()
        g = graph_mod.build_graph(self.blocks(), list(self.blocks()), cfg)
        by = {n[0]: n for n in g['board']}
        self.assertTrue(by['A1'][1].endswith('+буфер'))  # A, W13 = буфер
        self.assertFalse(by['B1'][1].endswith('+буфер'))  # B, W6 — не буфер

    def test_partial_in_pr_and_dict(self):
        cfg = make_config()
        g = graph_mod.build_graph(self.blocks(), list(self.blocks()), cfg)
        by = {n[0]: n for n in g['board']}
        self.assertEqual(by['C1'][5], 'B1')
        self.assertEqual(by['C1'][6], {'B1': 'W9+'})

    def test_weeks_format(self):
        cfg = make_config()
        g = graph_mod.build_graph(self.blocks(), list(self.blocks()), cfg)
        by = {n[0]: n for n in g['board']}
        self.assertEqual(by['A2'][2], 'W1-8')
        self.assertEqual(by['B1'][2], 'W1-6')

    def test_name_overrides(self):
        cfg = make_config(name_overrides={'A2': 'Базовый курс'})
        g = graph_mod.build_graph(self.blocks(), list(self.blocks()), cfg)
        by = {n[0]: n for n in g['board']}
        self.assertEqual(by['A2'][1], 'Базовый курс')


# ===== validate =====
class TestValidate(unittest.TestCase):
    def world(self):
        blocks, order = {}, []
        plan = {'A': ['A1', 'A2'], 'B': ['B1', 'B2'], 'C': ['C1', 'C2']}
        for codes in plan.values():
            for i, code in enumerate(codes):
                a, b = 1 + i * 13, 13 + i * 13
                blocks[code] = blk((a, b), float(b - a + 1))
                order.append(code)
        g = {'board': [], 'graph': {c: [] for c in order}, 'partial': {}, 'unknown': {}, 'codes': set(order)}
        return g, blocks, order

    def only(self, errs, v):
        return [e for e in errs if e.startswith(v)]

    def test_clean(self):
        g, b, o = self.world()
        errs, warns = validate_mod.run(g, b, o, make_config())
        self.assertEqual(errs, [])
        self.assertEqual(warns, [])

    def test_v1_typo_and_dangling(self):
        g, b, o = self.world()
        g['graph']['A1'] = ['B1', 'NOPE']
        errs, _ = validate_mod.run(g, b, o, make_config())
        self.assertTrue(any('NOPE' in e for e in self.only(errs, 'V1')))
        g['unknown'] = {'A1': ['A99']}
        errs, _ = validate_mod.run(g, b, o, make_config())
        self.assertTrue(any('A99' in e for e in self.only(errs, 'V1')))

    def test_v2_cycle(self):
        g, b, o = self.world()
        g['graph']['A1'] = ['C1']
        g['graph']['C1'] = ['A1']
        errs, _ = validate_mod.run(g, b, o, make_config())
        self.assertTrue(self.only(errs, 'V2'))

    def test_v3_gap(self):
        g, b, o = self.world()
        b['A1']['weeks'] = [2, 13]
        errs, _ = validate_mod.run(g, b, o, make_config())
        v3 = self.only(errs, 'V3')
        self.assertEqual(len(v3), 1)
        self.assertIn('A', v3[0])

    def test_v4_overlap_and_exemptions(self):
        g, b, o = self.world()
        b['A1']['weeks'] = [1, 13]
        g['graph']['B1'] = ['A1']  # A до W13, B с W1?? нет: B1 W14-26
        g['graph']['C1'] = []
        # соберём настоящий заезд: A2 W14-26 → C1 W20-26?
        g, b, o = self.world()
        b['C1']['weeks'] = [14, 26]
        g['graph']['C1'] = ['A2']  # A2 идёт до W26 ≥ старта W14
        errs, _ = validate_mod.run(g, b, o, make_config())
        self.assertTrue(self.only(errs, 'V4'))
        g['partial']['C1'] = {'A2': 'W20+'}
        g['graph']['C1'] = []
        errs, _ = validate_mod.run(g, b, o, make_config())
        self.assertEqual(self.only(errs, 'V4'), [])
        cfg = make_config(completed_codes=['A2'])
        g, b, o = self.world()
        b['C1']['weeks'] = [14, 26]
        g['graph']['C1'] = ['A2']
        errs, _ = validate_mod.run(g, b, o, cfg)
        self.assertEqual(self.only(errs, 'V4'), [])

    def test_v5_hours(self):
        g, b, o = self.world()
        b['B1']['hours'] = 500.0  # 500/13 > 32
        errs, _ = validate_mod.run(g, b, o, make_config())
        self.assertTrue(any('B1' in e for e in self.only(errs, 'V5')))
        g, b, o = self.world()
        b['B1']['hours'] = None
        errs, warns = validate_mod.run(g, b, o, make_config())
        self.assertEqual(errs, [])
        self.assertTrue(any('B1' in w for w in warns))

    def test_v6_optional_canon(self):
        g, b, o = self.world()
        cfg = make_config(expected=['A1', 'A2', 'B1', 'C1', 'X9'])
        errs, _ = validate_mod.run(g, b, o, cfg)
        self.assertTrue(self.only(errs, 'V6'))
        errs, _ = validate_mod.run(g, b, o, make_config())
        self.assertEqual(self.only(errs, 'V6'), [])  # без канона — выключен

    def test_v7_static_marks(self):
        g, b, o = self.world()
        b['B1']['vin'] = 'A1 ✅'
        errs, _ = validate_mod.run(g, b, o, make_config())
        self.assertTrue(any('B1' in e for e in self.only(errs, 'V7')))


# ===== markdown =====
class TestCardRenderer(unittest.TestCase):
    def test_id_sequence_across_renders(self):
        r = md_mod.CardRenderer(['P1', 'P2'])
        h1 = r.render('### P2 · T — W1 (1 ч)\n**Гейт:** \u2610 one \u2610 two')
        h2 = r.render('### C10 · T2 — W2 (1 ч)\n**Гейт:** \u2610 three')
        self.assertIn('data-ck="ck-P2-1"', h1)
        self.assertIn('data-ck="ck-P2-2"', h1)
        self.assertIn('data-ck="ck-C10-3"', h2)

    def test_table_no_cascade(self):
        md = '| H1 | H2 |\n| --- | --- |\n| a | b |\n| c | d |\n'
        html = md_mod.CardRenderer([]).render(md)
        self.assertEqual(html.count('<table>'), 1)
        self.assertEqual(html.count('<tr>'), 3)

    def test_fence_skipped(self):
        html = md_mod.CardRenderer([]).render('a\n```\ncode | x\n```\nb')
        self.assertNotIn('code | x', html)
        self.assertIn('a', html)

    def test_theory_checkboxes(self):
        html = md_mod.CardRenderer([]).render('### P2 · T — W1 (1 ч)\n**Теория:** 1) x. 2) y.')
        self.assertEqual(html.count('type="checkbox"'), 2)

    def test_input_xref(self):
        html = md_mod.CardRenderer(['P1']).render('### P2 · T — W1 (1 ч)\n**Вход:** P1.')
        self.assertIn('href="#blk-P1"', html)


# ===== budget + render =====
class TestCoverStats(unittest.TestCase):
    def test_stats_parameterized_no_hardcode(self):
        """Обложка не содержит прибитых 78/5 — только id-заполнители."""
        with open(os.path.join(render_mod.ASSETS, 'page.html'), encoding='utf-8') as f:
            page = f.read()
        self.assertIn('id="stat-weeks"', page)
        self.assertIn('id="stat-streams"', page)
        self.assertNotIn('>78<', page)
        self.assertNotIn('<div class="v">5</div>', page)
        with open(os.path.join(render_mod.ASSETS, 'board.js'), encoding='utf-8') as f:
            js = f.read()
        self.assertIn("getElementById('stat-weeks')", js)


class TestBudget(unittest.TestCase):
    def test_rates_and_total(self):
        blocks = {'A1': blk((1, 13), 78.0), 'B1': blk((1, 13), None)}
        html = budget_mod.budget_html(blocks, list(blocks), make_config(rates={'A': 6}))
        self.assertIn('id="budget"', html)
        self.assertNotIn('None', html)

    def test_no_rates_no_targets(self):
        blocks = {'A1': blk((1, 13), 78.0)}
        html = budget_mod.budget_html(blocks, list(blocks), make_config())
        self.assertNotIn('/78', html)


class TestRender(unittest.TestCase):
    def test_markers_and_invariant(self):
        page = render_mod.build_page(
            {
                'board_json': '[1]',
                'chapters_html': '<section>x</section>',
                'toc_html': '<a>y</a>',
                'block_count': 1,
                'meta_json': '{"total_weeks": 26}',
                'title': 'T',
                'subtitle': 'S',
            }
        )
        self.assertNotIn('%%', page)
        self.assertIn('window.ROADMAP_META = {"total_weeks": 26};', page)
        self.assertEqual(page.count('<title>T</title>'), 1)
        self.assertIn('<h1>T</h1>', page)
        self.assertIn('S', page)
        self.assertIn('function draw()', page)


# ===== интеграция: мини-пример =====
class TestMiniIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg = config_mod.RoadmapConfig.from_json(os.path.join(MINI, 'roadmap.json'))
        cls.cfg = cfg
        cls.blocks, cls.order = cards_mod.parse_cards(cfg.chapter_paths(), cfg.alias)
        cls.graph = graph_mod.build_graph(cls.blocks, cls.order, cfg)
        codes = sorted({n[0] for n in cls.graph['board']}, key=len, reverse=True)
        r = md_mod.CardRenderer(codes)
        cls.chapters = []
        for path, _title in cfg.chapter_paths():
            with open(path, encoding='utf-8') as f:
                cls.chapters.append(r.render(f.read()))

    def test_validator_green(self):
        errs, warns = validate_mod.run(self.graph, self.blocks, self.order, self.cfg)
        self.assertEqual(errs, [])
        self.assertEqual(warns, [])

    def test_12_blocks_streams(self):
        self.assertEqual(len(self.graph['board']), 12)
        self.assertEqual({n[4] for n in self.graph['board']}, {'A', 'B', 'C'})

    def test_tracks_continuous(self):
        cov = {}
        for n in self.graph['board']:
            p = n[2].split('-')
            a = int(p[0][1:])
            b = int(p[1].replace('W', '')) if len(p) > 1 else a
            for w in range(a, b + 1):
                cov.setdefault(n[4], set()).add(w)
        for sid in 'ABC':
            self.assertEqual([w for w in range(1, 27) if w not in cov[sid]], [])

    def test_partial_edge(self):
        by = {n[0]: n for n in self.graph['board']}
        self.assertEqual(by['C3'][6], {'A4': 'W18+'})

    def test_checkbox_ids_unique(self):
        ids = [i for ch in self.chapters for i in re.findall(r'data-ck="([^"]+)"', ch)]
        self.assertEqual(len(ids), len(set(ids)))


class TestToxic(unittest.TestCase):
    """Токсик-сценарии на временных карточках (реальные файлы не трогаем)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='bg_toxic_')
        for fname in ('01.md',):
            with open(os.path.join(self.tmp, fname), 'w', encoding='utf-8') as f:
                f.write(
                    '### A1 · X — W1–2 (2 ч)\n**Вход:** — (корень).\n'
                    '### B1 · Y — W3–13 (10 ч)\n**Вход:** A1, B99 (опечатка)\n'
                )
        self.cfg = make_config()
        self.cfg.base_dir = self.tmp
        self.cfg.chapters = [('01.md', 'T')]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_typo_fails_check(self):
        blocks, order = cards_mod.parse_cards(self.cfg.chapter_paths(), self.cfg.alias)
        graph = graph_mod.build_graph(blocks, order, self.cfg)
        errs, _ = validate_mod.run(graph, blocks, order, self.cfg)
        self.assertTrue(any(e.startswith('V1') and 'B99' in e for e in errs))


if __name__ == '__main__':
    unittest.main()
