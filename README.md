# boardgen

Генератор интерактивных досок из markdown-роадмапов. Один входной конфиг +
карточки → один самодостаточный HTML (работает с `file://`): канва-граф
зависимостей, чекбоксы с автосохранением прогресса, буферные гейт-зоны,
критический путь, поиск, миникарта, таблица бюджета часов, print-CSS.

## Быстрый старт

```bash
python3 -m boardgen check --config examples/mini/roadmap.json
python3 -m boardgen build --config examples/mini/roadmap.json --output mini.html
# или без конфига:
python3 -m boardgen build --input plan.md --output board.html
python3 -m unittest discover tests        # 31 тест
```

## Формат

Карточка = `### CODE · Название — W4–12 (45 ч)` + label-поля (`Вход/Слоты/
Теория/Практика/Гейт/Число/Файлы/Источники`). DAG строится из «Вход:»
(жёсткие / `(фон:)` мягкие / `(част. с WN+)` частичные рёбра). Полная
спецификация: **docs/SPEC.md**. Пример: `examples/mini/`.

## Структура

```
boardgen/          пакет: config (roadmap.json→RoadmapConfig) · cards · graph ·
                   validate (V1–V7) · markdown · budget · render · assets/
  assets/          page.html (%%маркеры%%) · styles.css · board.js (META-управляем)
tests/             31 тест: юниты + мини-интеграция + токсики
examples/mini/     26-недельный пример (2 главы, 3 потока, 12 блоков)
docs/              ANALYSIS · PLAN (включая бэклог фич) · SPEC
skills/            скиллы для opencode/claude/codex (генерация роадмапов)
```

## Инварианты

- id чекбоксов `ck-{CODE}-{n}` детерминированы порядком глав (localStorage
  пользователей привязан к нему — порядок файлов не менять).
- Сборка падает громко: валидатор V1–V7 → nonzero exit + отчёт.
- Выход — один HTML без внешних зависимостей (кроме Google Fonts с офлайн-деградацией).
- Никакой специфики конкретного роадмапа в ядре: всё — в `roadmap.json`.

## Линт

```bash
ruff check . && ruff format --check .
```
