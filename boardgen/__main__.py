#!/usr/bin/env python3
"""CLI boardgen.

python3 -m boardgen build --config roadmap.json [--output board.html]
python3 -m boardgen build --input a.md --input b.md [--output out.html]
python3 -m boardgen check --config roadmap.json
"""

import argparse
import json
import os
import sys

from . import budget as budget_mod
from . import cards as cards_mod
from . import config as config_mod
from . import graph as graph_mod
from . import markdown as md_mod
from . import render as render_mod
from . import validate as validate_mod


def _load(cfg):
    blocks, order = cards_mod.parse_cards(cfg.chapter_paths(), cfg.alias)
    graph = graph_mod.build_graph(blocks, order, cfg)
    return cfg, blocks, order, graph


def _report(errs, warns):
    for w in warns:
        print('ПРЕДУПРЕЖДЕНИЕ:', w)
    if errs:
        print(f'ОШИБКИ ВАЛИДАТОРА ({len(errs)}):')
        for e in errs:
            print('  ', e)


def _assemble(cfg, blocks, order, graph):
    codes = sorted({n[0] for n in graph['board']}, key=len, reverse=True)
    renderer = md_mod.CardRenderer(codes)
    chapters, toc = [], []
    for path, title in cfg.chapter_paths():
        with open(path, encoding='utf-8') as f:
            md = f.read()
        anchor = path.rsplit('/', 1)[-1].split('.')[0].replace('_', '-')
        chapters.append((anchor, title, renderer.render(md)))
        toc.append((anchor, title))
    chapters.append(('budget', 'Бюджет часов', budget_mod.budget_html(blocks, order, cfg)))

    toc_html = ''.join(f'<a href="#{a}" class="toc-link">{t}</a><br>' for a, t in toc)
    ch_html = ''
    for anchor, title, body in chapters:
        ch_html += f'<section class="chapter" id="{anchor}">\n<h2>{title}</h2>\n{body}\n</section>\n'
    return render_mod.build_page(
        {
            'board_json': json.dumps([list(n) for n in graph['board']]),
            'chapters_html': ch_html,
            'toc_html': toc_html,
            'block_count': len(graph['board']),
            'meta_json': json.dumps(cfg.meta(), ensure_ascii=False),
            'title': cfg.page_title,
            'subtitle': cfg.subtitle,
        }
    )


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog='boardgen', description='генератор интерактивных досок из markdown-роадмапов'
    )
    ap.add_argument(
        'mode',
        nargs='?',
        default='build',
        choices=['build', 'check'],
        help='build — сборка (по умолчанию); check — только валидация',
    )
    ap.add_argument('--config', help='roadmap.json (см. docs/SPEC.md §6)')
    ap.add_argument(
        '--input', action='append', default=[], help='md-файл главы (повторяемый; порядок = порядок глав)'
    )
    ap.add_argument('--output', default='board.html', help='выходной HTML (по умолчанию board.html)')
    args = ap.parse_args(argv)

    if not args.config and not args.input:
        ap.error('нужен --config или хотя бы один --input')

    if args.config:
        cfg = config_mod.RoadmapConfig.from_json(args.config)
        if args.input:  # явные --input переопределяют главы конфига
            cfg.chapters = [(p, p.rsplit('/', 1)[-1].split('.')[0]) for p in args.input]
    else:
        cfg = config_mod.RoadmapConfig.for_files(args.input)

    cfg, blocks, order, graph = _load(cfg)
    errs, warns = validate_mod.run(graph, blocks, order, cfg)
    _report(errs, warns)
    if errs:
        return 1
    if args.mode == 'check':
        print('валидация: ошибок нет' + (f', предупреждений {len(warns)}' if warns else ''))
        return 0

    page = _assemble(cfg, blocks, order, graph)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'{args.output}: {os.path.getsize(args.output)} bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
