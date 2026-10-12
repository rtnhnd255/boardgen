"""boardgen — генератор интерактивных досок из markdown-роадмапов.

Поток: cards → graph → validate → markdown ×N + budget → render → один HTML.
Формат роадмапа: docs/SPEC.md. CLI: python3 -m boardgen --help.
"""

__version__ = '3.0.0'
