<a id="top"></a>

# OnlySQ Cloud Drive

[![PyPI version](https://img.shields.io/pypi/v/onlysq-drive.svg)](https://pypi.org/project/onlysq-drive/)
![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-green)
![Windows](https://img.shields.io/badge/platform-Windows-0078D6)
![Linux](https://img.shields.io/badge/platform-Linux-FCC624)
![WinFsp](https://img.shields.io/badge/WinFsp-required-orange)
![FUSE3](https://img.shields.io/badge/FUSE3-required-orange)

**OnlySQ Drive** — это неофициальное **кроссплатформенное** приложение и CLI-инструмент, который монтирует **OnlySQ Cloud**:

- на **Windows** — как отдельный диск в Проводнике через **WinFsp + winfspy**;
- на **Linux** — как обычный каталог в файловой системе через **FUSE3 + pyfuse3**.

После настройки можно работать с облаком почти как с локальным хранилищем:

- загружать файлы через файловый менеджер,
- скачивать и открывать файлы,
- удалять их,
- копировать публичную ссылку,
- поднимать монтирование автоматически после входа в систему.

![screen_windows](https://i.yapx.ru/daQBw.png)
![screen_linux](https://i.yapx.ru/da2BT.png)

---

## ⚡ Быстрые переходы

- [Что это такое](#overview)
- [Поддерживаемые платформы](#platforms)
- [Основные возможности](#features)
- [Как это работает](#how-it-works)
- [Установка](#installation)
- [Быстрый старт](#quick-start)
- [Повседневное использование](#usage)
- [Все команды CLI](#cli)
- [Автозапуск](#autostart)
- [Интеграция с файловым менеджером](#integration)
- [Где хранятся данные](#paths)
- [Структура проекта](#structure)
- [Ограничения](#limitations)
- [Удаление](#removal)
- [Credits](#credits)
- [Лицензия и disclaimer](#license)

---

<a id="overview"></a>
## Что это такое

`OnlySQ Drive` даёт одну кодовую базу для **Windows** и **Linux**. То есть теперь это уже не отдельные проекты с разной логикой и разной документацией, а один пакет с общей CLI-командой `onlysq-drive`, где платформенно-зависимые части выбираются автоматически.

Это удобно по трём причинам:

1. **одна команда и один README** для обеих ОС;
2. **общая логика индекса, кэша и работы с API**;
3. **разные системные интеграции** подключаются только там, где они реально поддерживаются.

<p align="right"><a href="#top">↑ Наверх</a></p>

---

<a id="platforms"></a>
## Поддерживаемые платформы

| Платформа | Как монтируется | Бэкенд | Автозапуск | Контекстное меню | Дополнительно |
|---|---|---|---|---|---|
| **Windows 10 / 11** | отдельный диск, например `O:` | `WinFsp` + `winfspy` | **Task Scheduler** | **Explorer** | кастомная иконка диска |
| **Linux** | каталог, например `~/OnlySQCloud` или `/run/media/$USER/OnlySQCloud` | `FUSE3` + `pyfuse3` + `trio` | **systemd --user** | **Dolphin / Nautilus / Nemo / Caja** | боковая панель файлового менеджера |

### Поведение по умолчанию

- **Windows:** точка монтирования по умолчанию — `O:`
- **Linux:** точка монтирования по умолчанию — `/run/media/$USER/OnlySQCloud`, а если такой путь не подходит — `~/OnlySQCloud`

<p align="right"><a href="#top">↑ Наверх</a></p>

---

<a id="features"></a>
## Основные возможности

- **Кроссплатформенный CLI** — одна команда `onlysq-drive` для Windows и Linux.
- **Локальный индекс и кэш** — быстрый доступ к структуре файлов и повторным операциям.
- **SQLite внутри** — без отдельной БД и без дополнительного сервера.
- **Автозапуск после входа в систему**:
  - Windows — через Планировщик заданий,
  - Linux — через `systemd --user`.
- **Копирование публичной ссылки** из контекстного меню.
- **Интеграция с файловыми менеджерами**:
  - Windows — Проводник,
  - Linux — Dolphin, Nautilus, Nemo, Caja.
- **Поддержка боковой панели на Linux**:
  - Dolphin через FUSE mount options,
  - GTK-менеджеры через `x-gvfs-show` и GTK bookmarks.
- **Кастомная иконка диска на Windows**.
  На Linux команда `install-drive-icon` сохранена для совместимости CLI, но является **no-op**.

![screen_features](https://i.yapx.ru/daQCS.png)

<p align="right"><a href="#top">↑ Наверх</a></p>

---

<a id="how-it-works"></a>
## Как это работает

Когда ты копируешь файл в смонтированный диск/каталог, приложение:

1. сохраняет файл во временный локальный кэш,
2. загружает его в **OnlySQ Cloud**,
3. записывает метаданные в локальный индекс,
4. делает файл доступным для последующего чтения, скачивания, удаления и копирования публичной ссылки.

![screen_flow](https://i.yapx.ru/daQDI.png)

### Важно

Сейчас API OnlySQ Cloud даёт базовые операции загрузки, скачивания и удаления. Из-за этого клиент хранит **локальный индекс** файлов у пользователя.

Это означает:

- на **этом же ПК** после перезапуска структура сохраняется;
- на **другом ПК** дерево файлов автоматически не восстановится без переноса локального индекса.

<p align="right"><a href="#top">↑ Наверх</a></p>

---

<a id="installation"></a>
## Установка

### Требования

#### Windows

- Windows 10 / 11
- Python **3.10+**
- установленный **WinFsp**

#### Linux

- Linux с поддержкой **FUSE3**
- Python **3.10+**
- системные пакеты для FUSE3
- Python-пакеты `pyfuse3` и `trio`
- для `copy-link` на Linux нужен один из буферных инструментов:
  - `wl-copy` (Wayland)
  - `xclip`
  - `xsel`

### Варианты установки пакета

#### Из исходников репозитория

```bash
pip install .
```

#### Из wheel-файла

```bash
pip install onlysq_drive-1.1.1-py3-none-any.whl
```

#### Из PyPI

```bash
pip install onlysq-drive
```

> Если ты тестируешь именно локальную объединённую версию, лучше ставить **из исходников** или из своего wheel-файла, а не полагаться на уже опубликованный пакет.

### Установка системных зависимостей

#### Windows: WinFsp

Через `winget`:

```powershell
winget install -e --id WinFsp.WinFsp
```

или через встроенный помощник:

```powershell
onlysq-drive bootstrap
```

#### Linux: FUSE3

Можно поставить вручную или через встроенный помощник:

```bash
onlysq-drive bootstrap
```

Поддерживаются распространённые менеджеры пакетов:

- `apt-get`
- `dnf`
- `pacman`

<p align="right"><a href="#top">↑ Наверх</a></p>

---

<a id="quick-start"></a>
## Быстрый старт

### Windows

```powershell
winget install -e --id WinFsp.WinFsp
pip install .
onlysq-drive setup --mount O: --label "OnlySQ Cloud"
onlysq-drive doctor
```

Если хочешь сразу запустить автозадачу после настройки:

```powershell
Start-ScheduledTask -TaskName "OnlySQ Drive"
```

После этого:

- появляется диск `O:`,
- добавляется пункт контекстного меню,
- настраивается автозапуск,
- диск может подниматься автоматически после входа в систему.

### Linux (универсальный вариант)

```bash
onlysq-drive bootstrap
pip install .
onlysq-drive setup --mount ~/OnlySQCloud --label "OnlySQ Cloud"
onlysq-drive doctor
```

После этого:

- появляется точка монтирования,
- добавляется пункт контекстного меню файлового менеджера,
- добавляется запись в боковую панель,
- настраивается `systemd --user` автозапуск.

### Linux: ручная установка зависимостей

#### Ubuntu / Debian

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip libfuse3-dev fuse3 pkg-config
pip install .
onlysq-drive setup --mount ~/OnlySQCloud --label "OnlySQ Cloud"
```

#### Fedora

```bash
sudo dnf install -y python3 python3-pip fuse3-devel fuse3 pkgconf-pkg-config
pip install .
onlysq-drive setup --mount ~/OnlySQCloud --label "OnlySQ Cloud"
```

#### Arch Linux / Manjaro / CachyOS

```bash
sudo pacman -S --noconfirm python python-pip fuse3 pkgconf
pip install .
onlysq-drive setup --mount ~/OnlySQCloud --label "OnlySQ Cloud"
```

### Проверка

```bash
onlysq-drive doctor
onlysq-drive stats
```

<p align="right"><a href="#top">↑ Наверх</a></p>

---

<a id="usage"></a>
## Повседневное использование

### Смонтировать вручную

```bash
onlysq-drive mount
```

> Команда полезна для ручного теста. Для постоянной работы лучше использовать `setup` или `install-autostart`.

### Проверить состояние

```bash
onlysq-drive doctor
```

### Посмотреть статистику

```bash
onlysq-drive stats
```

### Посмотреть содержимое виртуальной папки

```bash
onlysq-drive ls
onlysq-drive ls /folder
```

### Информация о файле

```bash
onlysq-drive info /example.txt
```

### Скопировать публичную ссылку

```bash
onlysq-drive copy-link /example.txt
```

### Скачать файл в локальную папку

#### Windows

```powershell
onlysq-drive pull /example.txt "C:\Users\User\Downloads\example.txt"
```

#### Linux

```bash
onlysq-drive pull /example.txt ~/Downloads/example.txt
```

### Удалить файл

```bash
onlysq-drive rm /example.txt
```

<p align="right"><a href="#top">↑ Наверх</a></p>

---

<a id="cli"></a>
## Все команды CLI

### Инициализация и настройка

#### `onlysq-drive init`

Создаёт базовую локальную структуру:

- конфиг,
- каталоги данных,
- каталоги кэша,
- при последующей работе — локальную SQLite-базу.

Примеры:

```powershell
onlysq-drive init --mount O: --label "OnlySQ Cloud"
```

```bash
onlysq-drive init --mount ~/OnlySQCloud --label "OnlySQ Cloud"
```

#### `onlysq-drive setup`

Платформенная первичная настройка.

Что делает:

- сохраняет `mountpoint` и `volume_label`, если они переданы,
- ставит контекстное меню,
- на Linux добавляет запись в боковую панель,
- ставит автозапуск,
- на Windows может установить иконку диска через `--icon`.

Примеры:

```powershell
onlysq-drive setup --mount O: --label "OnlySQ Cloud" --icon "C:\Icons\onlysq.ico"
```

```bash
onlysq-drive setup --mount ~/OnlySQCloud --label "OnlySQ Cloud"
```

#### `onlysq-drive bootstrap`

Помогает поставить системные зависимости:

- **Windows:** пытается установить `WinFsp` через `winget` или `choco`
- **Linux:** ставит пакеты FUSE3 через системный пакетный менеджер и затем устанавливает `pyfuse3` и `trio`

---

### Диагностика и обслуживание

#### `onlysq-drive doctor`

Показывает:

- версию Python,
- платформу,
- путь к конфигу,
- букву диска или mountpoint,
- доступность системных зависимостей.

На Windows дополнительно проверяются:

- импорт `winfspy`,
- наличие каталога WinFsp.

На Linux дополнительно проверяются:

- импорт `pyfuse3`,
- наличие `fusermount3`.

#### `onlysq-drive stats`

Показывает:

- количество файлов,
- количество папок,
- общий размер,
- количество `dirty` файлов.

---

### Работа с виртуальной файловой системой

#### `onlysq-drive mount`

Монтирует диск/каталог вручную.

#### `onlysq-drive ls [path]`

Показывает содержимое папки.

#### `onlysq-drive info <path>`

Показывает JSON-информацию по файлу или папке.

#### `onlysq-drive pull <virtual_path> <local_path>`

Скачивает файл из облака или кэша в локальный путь.

#### `onlysq-drive rm <path>`

Удаляет файл или пустую папку.

#### `onlysq-drive copy-link <path>`

Копирует публичную ссылку файла в буфер обмена.

---

### Конфиг

#### `onlysq-drive config show`

Показывает текущий конфиг в JSON.

#### `onlysq-drive config set <key> <value>`

Меняет поле в конфиге.

Примеры:

```bash
onlysq-drive config show
onlysq-drive config set mountpoint O:
onlysq-drive config set volume_label "OnlySQ Cloud"
```

```bash
onlysq-drive config set mountpoint ~/OnlySQCloud
onlysq-drive config set request_timeout 180
```

---

### Интеграция с системой

#### `onlysq-drive install-context-menu`

Добавляет пункт контекстного меню:

- **Windows:** Проводник Windows
- **Linux:** Dolphin / Nautilus / Nemo / Caja

```bash
onlysq-drive install-context-menu
```

#### `onlysq-drive uninstall-context-menu`

Удаляет этот пункт.

#### `onlysq-drive install-autostart`

Ставит автозапуск:

- **Windows:** Scheduled Task
- **Linux:** `systemd --user` service

#### `onlysq-drive uninstall-autostart`

Удаляет автозапуск.

#### `onlysq-drive install-drive-icon <icon_path>`

- **Windows:** назначает кастомную иконку диска
- **Linux:** команда доступна, но ничего не меняет

#### `onlysq-drive uninstall-drive-icon`

Удаляет кастомную иконку диска на Windows.
На Linux — no-op.

---

### Полное удаление локальных данных

#### `onlysq-drive purge --yes`

Удаляет:

- конфиг,
- SQLite-индекс,
- кэш,
- автозапуск,
- контекстное меню,
- на Linux также записи боковой панели.

```bash
onlysq-drive purge --yes
```

<p align="right"><a href="#top">↑ Наверх</a></p>

---

<a id="autostart"></a>
## Автозапуск

### Windows

После `setup` или `install-autostart` создаётся задача **OnlySQ Drive** в Планировщике заданий.

Запустить вручную:

```powershell
Start-ScheduledTask -TaskName "OnlySQ Drive"
```

### Linux

После `setup` или `install-autostart` создаётся `systemd --user` сервис `onlysq-drive`.

Полезные команды:

```bash
# статус
systemctl --user status onlysq-drive

# запустить
systemctl --user start onlysq-drive

# остановить
systemctl --user stop onlysq-drive

# смотреть логи
journalctl --user -u onlysq-drive -f
```

<p align="right"><a href="#top">↑ Наверх</a></p>

---

<a id="integration"></a>
## Интеграция с файловым менеджером

### Windows

Поддерживается:

- отдельный диск в Проводнике,
- контекстное меню **OnlySQ: Copy public link**,
- кастомная иконка диска.

### Linux

Поддерживается:

- FUSE mountpoint как обычный каталог,
- контекстное меню **OnlySQ: Copy public link**,
- боковая панель файлового менеджера,
- работа с GTK/KDE окружениями.

Поддержка по Linux-файловым менеджерам:

- **Dolphin**
- **Nautilus**
- **Nemo**
- **Caja**
- для боковой панели также подходят GTK-менеджеры вроде **Thunar** и **PCManFM**

<p align="right"><a href="#top">↑ Наверх</a></p>

---

<a id="paths"></a>
## Где хранятся данные

### Windows

#### Конфиг

```text
%APPDATA%\OnlySQDrive\config.json
```

#### Индекс

```text
%APPDATA%\OnlySQDrive\index.sqlite3
```

#### Кэш

```text
%LOCALAPPDATA%\OnlySQDrive\cache
```

#### Логи автозапуска

```text
%LOCALAPPDATA%\OnlySQDrive\logs\autostart.log
```

### Linux

#### Конфиг

```text
~/.config/onlysq-drive/config.json
```

#### Индекс

```text
~/.local/share/onlysq-drive/index.sqlite3
```

#### Кэш

```text
~/.cache/onlysq-drive/files
```

#### Логи автозапуска

```text
~/.local/share/onlysq-drive/logs/autostart.log
```

<p align="right"><a href="#top">↑ Наверх</a></p>

---

<a id="structure"></a>
## Структура проекта

```text
onlysq-drive/
├─ pyproject.toml
├─ README.md
└─ src/
   └─ onlysq_drive/
      ├─ __init__.py
      ├─ cli.py               # общий CLI entry point
      ├─ launcher.py          # фоновый запуск / autostart launcher
      ├─ mount.py             # выбор WinFsp или FUSE-монтирования
      ├─ fs_ops.py            # файловые операции для Windows
      ├─ fs_ops_linux.py      # файловые операции для Linux (pyfuse3)
      ├─ cloud_client.py      # HTTP-клиент для OnlySQ Cloud API
      ├─ index_db.py          # SQLite-индекс
      ├─ config.py            # JSON-конфиг
      ├─ autostart.py         # Task Scheduler / systemd user service
      ├─ shell_integration.py # Explorer / file-manager context menu
      ├─ sidebar.py           # боковая панель Linux-файловых менеджеров
      ├─ drive_icon.py        # иконка диска Windows, no-op на Linux
      ├─ clipboard.py         # Windows clipboard / wl-copy / xclip / xsel
      ├─ paths.py             # platform-specific paths
      └─ vpaths.py            # нормализация виртуальных путей
```

<p align="right"><a href="#top">↑ Наверх</a></p>

---

<a id="limitations"></a>
## Ограничения

- Это **неофициальный** клиент OnlySQ Cloud.
- Восстановление дерева файлов основано на **локальном индексе**.
- Если удалить локальный индекс, на другом ПК структура автоматически не восстановится.
- **Windows** требует установленный **WinFsp**.
- **Linux** требует **FUSE3** и Python-зависимости `pyfuse3` + `trio`.
- На Linux для `copy-link` нужен доступный инструмент буфера обмена: `wl-copy`, `xclip` или `xsel`.
- Кастомная иконка диска работает только на Windows.

<p align="right"><a href="#top">↑ Наверх</a></p>

---

<a id="removal"></a>
## Удаление

### Удалить автозапуск и интеграции

```bash
onlysq-drive uninstall-autostart
onlysq-drive uninstall-context-menu
onlysq-drive uninstall-drive-icon
```

### Удалить локальные данные

```bash
onlysq-drive purge --yes
```

### Удалить пакет

```bash
pip uninstall onlysq-drive
```

<p align="right"><a href="#top">↑ Наверх</a></p>

---

<a id="credits"></a>
## Credits

- оригинальная Windows-версия: **[fakelag28 / onlysq-cloud-drive](https://github.com/fakelag28/onlysq-cloud-drive)**
- Linux-адаптация, из которой была взята логика Linux-поддержки: **[AndrewImm-OP / onlysq-cloud-drive-linux](https://github.com/AndrewImm-OP/onlysq-cloud-drive-linux)**

<p align="right"><a href="#top">↑ Наверх</a></p>

---

<a id="license"></a>
## Лицензия и disclaimer

### Лицензия

Проект распространяется под лицензией **MIT**.

### Disclaimer

Это **неофициальное** приложение.
Все права на бренд, API и платформу принадлежат **OnlySQ**.

<p align="right"><a href="#top">↑ Наверх</a></p>
