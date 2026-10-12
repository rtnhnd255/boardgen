"""Конфигурация роадмапа: загрузка roadmap.json + нейтральные дефолты (SPEC §6).

Вся специфика конкретного роадмапа живёт здесь, ядро принимает только
RoadmapConfig и не знает ни про какие конкретные коды/потоки.
"""

import json
import os

DEFAULT_COLORS = {'A': '#1a365d', 'B': '#00838f', 'C': '#e65100', 'D': '#6a1b9a', 'E': '#c62828'}
DEFAULT_STREAMS = ['A', 'B', 'C', 'D', 'E']


class RoadmapConfig:
    def __init__(self, base_dir='.', **kw):
        self.base_dir = base_dir
        self.start_date = kw.get('start_date')
        self.total_weeks = int(kw.get('total_weeks') or 78)
        self.quarters_weeks = int(kw.get('quarters_weeks') or 13)
        self._buffer_weeks = kw.get('buffer_weeks')
        self.total_hours = kw.get('total_hours')
        self.max_hours_per_week = float(kw.get('max_hours_per_week') or 32)
        self.completed_codes = set(kw.get('completed_codes') or [])
        self.chapters = [(c['file'], c['title']) for c in (kw.get('chapters') or [])]
        self.page_title = kw.get('page_title') or 'Роадмап'
        self.ls_key = kw.get('ls_key') or 'boardgen'
        self.subtitle = kw.get('subtitle') or ''
        # потоки: id → {label, color}
        streams = kw.get('streams') or {}
        self.streams = {
            sid: {
                'label': v.get('label', sid) if isinstance(v, dict) else str(v),
                'color': (v.get('color') if isinstance(v, dict) else None)
                or DEFAULT_COLORS.get(sid, '#5a6a7a'),
            }
            for sid, v in streams.items()
        } or {
            sid: {'label': 'Поток ' + sid, 'color': DEFAULT_COLORS.get(sid, '#5a6a7a')}
            for sid in DEFAULT_STREAMS
        }
        # код → поток: точные коды + префиксы (длиннейший побеждает)
        c2s = kw.get('code_to_stream') or {}
        self._exact = dict(c2s.get('exact') or {})
        self._prefix = dict(c2s.get('prefix') or {})
        self.alias = dict(kw.get('alias') or {})
        self.name_overrides = dict(kw.get('name_overrides') or {})
        self.expected = set(kw['expected']) if kw.get('expected') else None
        self.rates = dict(kw.get('rates') or {})

    # ---- фабрики ----
    @classmethod
    def from_dict(cls, data, base_dir='.'):
        return cls(base_dir=base_dir, **(data or {}))

    @classmethod
    def from_json(cls, path):
        base = os.path.dirname(os.path.abspath(path))
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        # base_dir в конфиге — относительно самого конфига (главы могут жить выше)
        rel = data.pop('base_dir', None)
        if rel:
            base = os.path.normpath(os.path.join(base, rel))
        return cls.from_dict(data, base_dir=base)

    @classmethod
    def for_files(cls, paths, base_dir='.'):
        """Конфиг на лету: главы из --input (title = имя файла без расширения)."""
        cfg = cls(base_dir=base_dir)
        cfg.chapters = [(p, os.path.splitext(os.path.basename(p))[0]) for p in paths]
        return cfg

    # ---- производные ----
    @property
    def stream_ids(self):
        return list(self.streams.keys())

    @property
    def buffer_weeks(self):
        if self._buffer_weeks:
            return sorted(self._buffer_weeks)
        nq = self.quarter_count
        return [q * self.quarters_weeks for q in range(1, nq + 1)]

    @property
    def quarter_count(self):
        return (self.total_weeks + self.quarters_weeks - 1) // self.quarters_weeks

    def stream_of(self, code):
        if code in self._exact:
            return self._exact[code]
        best, best_len = None, -1
        for pref, stream in self._prefix.items():
            if code.startswith(pref) and len(pref) > best_len:
                best, best_len = stream, len(pref)
        return best

    def chapter_paths(self):
        """Абсолютные пути глав (относительно base_dir)."""
        return [(os.path.join(self.base_dir, f), t) for f, t in self.chapters]

    # ---- канва-мета ----
    def meta(self):
        return {
            'ls_key': self.ls_key,
            'start_date': self.start_date,
            'total_weeks': self.total_weeks,
            'quarters_weeks': self.quarters_weeks,
            'buffer_weeks': self.buffer_weeks,
            'stream_ids': self.stream_ids,
            'stream_labels': {k: v['label'] for k, v in self.streams.items()},
            'stream_colors': {k: v['color'] for k, v in self.streams.items()},
        }
