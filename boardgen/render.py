"""Финальная сборка страницы из ассетов и данных.

Маркеры %%X%% заменяются .replace-ами: никакой f-string-магии в ассетах.
Инвариант: в собранной странице не остаётся ни одного маркера.
"""

import os

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def _read_asset(name):
    with open(os.path.join(ASSETS, name), encoding='utf-8') as f:
        return f.read()


def build_page(payload):
    """payload: dict с ключами board_json, chapters_html, toc_html,
    block_count, meta_json, title, subtitle."""
    board_json = payload['board_json']
    chapters_html = payload['chapters_html']
    toc_html = payload['toc_html']
    block_count = payload['block_count']
    meta_json = payload['meta_json']
    title = payload.get('title') or 'Роадмап'
    subtitle = payload.get('subtitle') or ''
    page = _read_asset('page.html')
    for marker, value in (
        ('%%STYLES%%', _read_asset('styles.css').rstrip('\n')),
        ('%%SCRIPTS%%', _read_asset('board.js').rstrip('\n')),
        ('%%META%%', meta_json),
        ('%%BOARD_JSON%%', board_json),
        ('%%CHAPTERS%%', chapters_html),
        ('%%TOC%%', toc_html),
        ('%%BLOCK_COUNT%%', str(block_count)),
        ('%%TITLE%%', title),
        ('%%SUBTITLE%%', subtitle),
    ):
        assert marker in page, 'маркер отсутствует в page.html: ' + marker
        page = page.replace(marker, value)
    assert '%%' not in page, 'в собранной странице остался несубституированный маркер'
    return page
