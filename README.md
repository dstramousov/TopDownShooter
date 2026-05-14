# Top Down Shooter — (Pyray)

- Python 3.12+
- Pyray только как слой окна / рендера / ввода
- NumPy для хранения tilemap
- один `config.toml`
- logging с проектной обёрткой и цветным выводом
- простая i18n-подготовка (`lang/en`, `lang/ua`)

## Что уже есть

<img width="1273" height="935" alt="Screenshot from 2026-05-14 13-30-44" src="https://github.com/user-attachments/assets/a107ee09-5487-4469-8109-b3ef452e362c" />


- статическая debug-карта с домом и двором;
- procedural generator `small / medium / large`;
- чистая модель карты, не зависящая от Pyray;
- рендер Kenney tiles через `TextureAtlas` и `TileRenderer`;
- игрок с движением, коллизиями, прицеливанием и hitscan-стрельбой;
- конфигурируемые оружия с разной скорострельностью и уроном;
- tracer, impact marks, debris, muzzle flash;
- враги с FOV + LOS обнаружением игрока;
- debug cone зрения врагов по `F5`;
- урон игроку, HP, game over и быстрый restart.

## Что изменилось на этом шаге

- у игрока появилось здоровье и flash-реакция на урон;
- у врагов появилась ближняя атака с cooldown;
- HUD показывает:
  - полоску HP игрока;
  - активное оружие;
  - количество живых врагов;
- при смерти игрока показывается `GAME OVER`;
- `Enter` или `Space` перезапускают текущую карту без смены режима;
- overlay теперь показывает текущее здоровье игрока.

## Управление

- `WASD` / стрелки — движение
- `Мышь` — направление взгляда
- `ЛКМ` — стрельба
- `Q` — переключение оружия (`default` / `pistol` / `smg`)
- `F1` — overlay
- `F2` — hitboxes
- `F3` — debug beam / laser sight
- `F4` — blocker overlay
- `F5` — vision cone debug
- `1..4` — режим карты
- `R` — reroll / reload
- `Enter` / `Space` — restart after death

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m topdown.main --mode debug_static
```

Примеры:

```bash
PYTHONPATH=src python -m topdown.main --mode generated_small --seed 7
PYTHONPATH=src python -m topdown.main --mode generated_medium --seed 42
PYTHONPATH=src python -m topdown.main --mode generated_large --seed 99
```

## Тесты

```bash
PYTHONPATH=src pytest
```
