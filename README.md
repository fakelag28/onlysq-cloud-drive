# OnlySQ Cloud Drive

[![PyPI version](https://img.shields.io/pypi/v/onlysq-drive.svg)](https://pypi.org/project/onlysq-drive/)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-green)
![Windows](https://img.shields.io/badge/platform-Windows-0078D6)
![WinFsp](https://img.shields.io/badge/WinFsp-required-orange)

**OnlySQ Drive** - это неофициальное Windows-приложение и CLI-инструмент, который монтирует **OnlySQ Cloud** как отдельный диск в Проводнике Windows.

![screen_1](https://i.yapx.ru/daQBw.png)

После настройки у пользователя появляется полноценный диск вроде `O:`, с которым можно работать почти как с обычным:

* загружать файлы в облако через Проводник,
* скачивать и открывать файлы,
* удалять их,
* копировать публичную ссылку через контекстное меню,
* автоматически поднимать диск после входа в Windows без ручного запуска терминала.

---

## Особенности

* **Отдельный диск в Проводнике Windows**
  OnlySQ Cloud отображается как обычный диск с собственной буквой, например `O:`.

* **Простая установка через Python / pip**
  Проект ставится как обычный Python-пакет и управляется CLI-командой `onlysq-drive`.

* **Автозапуск при входе в Windows**
  После настройки диск может подниматься автоматически без дополнительных окон и ручных команд.

* **Контекстное меню “Copy public link”**
  Можно быстро копировать публичную ссылку на файл прямо из Проводника.

* **Локальный индекс и кэш**
  Приложение хранит индекс файлов и кэш на ПК, чтобы быстрее показывать содержимое и восстанавливать его после перезапуска системы.

* **SQLite внутри**
  Для метаданных используется локальная база, без необходимости поднимать отдельный сервер или БД.

* **CLI-управление**
  Всё настраивается и обслуживается понятными командами: `setup`, `doctor`, `stats`, `mount`, `config` и т.д.

![screen_2](https://i.yapx.ru/daQCS.png)

---

## Как это работает

`OnlySQ Drive` создаёт пользовательскую файловую систему для Windows и монтирует её как обычный диск.
Когда ты создаёшь или копируешь файл на этот диск, приложение:

1. сохраняет файл во временный локальный кэш,
2. загружает его в OnlySQ Cloud,
3. сохраняет метаданные в локальный индекс,
4. делает файл доступным для дальнейшего открытия, скачивания и удаления.

![screen_3](https://i.yapx.ru/daQDI.png)

### Важно

Сейчас API OnlySQ Cloud предоставляет базовые операции загрузки, скачивания и удаления файла. Из-за этого клиент хранит **локальный индекс** файлов у пользователя. Это значит:

* на **этом же ПК** после перезагрузки всё сохраняется,
* но на **другом ПК** дерево файлов автоматически не восстановится без переноса локального индекса.

---

## Стек

* **Python 3.10+**
* **WinFsp**
* **winfspy**
* **SQLite**
* **requests**
* **Windows Task Scheduler**
* **Windows Explorer shell integration**

---

## Установка

### Требования

* Windows 10 / 11
* Python **3.10+**
* установленный **WinFsp**

### 1. Установить WinFsp

Через `winget`:

```powershell
winget install -e --id WinFsp.WinFsp
```

### 2. Установить пакет

Из PyPI:

```powershell
pip install onlysq-drive
```

Из wheel-файла:

```powershell
pip install onlysq_drive-1.0.0-py3-none-any.whl
```

Из исходников:

```powershell
pip install -e .
```

---

## Быстрый старт

### Пример полного сценария установки (Powershell)

```powershell
winget install -e --id WinFsp.WinFsp
pip install onlysq-drive
onlysq-drive setup --mount O: --label "OnlySQ Cloud"
onlysq-drive doctor
Start-ScheduledTask -TaskName "OnlySQ Drive"
```

После этого:

* появляется диск `O:`,
* ставится автозапуск,
* добавляется контекстное меню,
* после следующего входа в Windows диск продолжает работать автоматически.

### Проверка

```powershell
onlysq-drive doctor
onlysq-drive stats
```

---

## Использование

### Смонтировать диск вручную

```powershell
onlysq-drive mount
```

> Эта команда полезна для ручного теста.
> Для постоянной работы лучше использовать `setup` или `install-autostart`.

### Проверить состояние

```powershell
onlysq-drive doctor
```

### Посмотреть статистику

```powershell
onlysq-drive stats
```

### Посмотреть содержимое виртуальной папки

```powershell
onlysq-drive ls
onlysq-drive ls /folder
```

### Информация о файле

```powershell
onlysq-drive info /example.txt
```

### Скопировать публичную ссылку

```powershell
onlysq-drive copy-link /example.txt
```

### Скачать файл в обычную папку Windows

```powershell
onlysq-drive pull /example.txt "C:\Users\User\Downloads\example.txt"
```

### Удалить файл

```powershell
onlysq-drive rm /example.txt
```

---

## Все команды CLI

### Инициализация и настройка

#### `onlysq-drive init`

Создаёт:

* конфиг,
* SQLite-индекс,
* директорию кэша.

Пример:

```powershell
onlysq-drive init --mount O: --label "OnlySQ Cloud"
```

#### `onlysq-drive setup`

Полная первичная настройка:

* `init`
* установка контекстного меню
* установка автозапуска
* опционально установка иконки диска

Пример:

```powershell
onlysq-drive setup --mount O: --label "OnlySQ Cloud"
```

---

### Диагностика и обслуживание

#### `onlysq-drive doctor`

Показывает:

* версию Python,
* платформу,
* путь к конфигу,
* букву диска,
* доступность `winfspy`,
* базовую диагностику окружения.

#### `onlysq-drive stats`

Показывает:

* количество файлов,
* количество папок,
* общий размер,
* состояние индекса.

---

### Работа с виртуальным диском

#### `onlysq-drive mount`

Монтирует диск вручную.

#### `onlysq-drive ls [path]`

Показывает содержимое папки.

#### `onlysq-drive info <path>`

Показывает информацию по файлу или папке.

#### `onlysq-drive pull <virtual_path> <local_path>`

Скачивает файл из облака/кэша в обычную папку Windows.

#### `onlysq-drive rm <path>`

Удаляет файл или пустую папку.

#### `onlysq-drive copy-link <path>`

Копирует публичную ссылку файла в буфер обмена.

---

### Конфиг

#### `onlysq-drive config show`

Показывает текущий конфиг.

#### `onlysq-drive config set <key> <value>`

Меняет поле в конфиге.

Примеры:

```powershell
onlysq-drive config show
onlysq-drive config set mount_drive O:
onlysq-drive config set volume_label "OnlySQ Cloud"
```

---

### Интеграция с Windows

#### `onlysq-drive install-context-menu`

Добавляет пункт в контекстное меню Проводника:

* **OnlySQ: Copy public link**

#### `onlysq-drive uninstall-context-menu`

Удаляет этот пункт.

#### `onlysq-drive install-autostart`

Создаёт задачу автозапуска при входе пользователя в Windows.

#### `onlysq-drive uninstall-autostart`

Удаляет задачу автозапуска.

#### `onlysq-drive install-drive-icon <icon.ico>`

Устанавливает кастомную иконку для буквы диска.

#### `onlysq-drive uninstall-drive-icon`

Удаляет кастомную иконку.

---

### Полное удаление локальных данных

#### `onlysq-drive purge --yes`

Удаляет:

* конфиг,
* SQLite-индекс,
* кэш,
* локальные служебные файлы.

Пример:

```powershell
onlysq-drive purge --yes
```

---

## Автозапуск после перезагрузки

Если выполнен:

```powershell
onlysq-drive install-autostart
```

или

```powershell
onlysq-drive setup ...
```

то после входа пользователя в Windows диск будет запускаться автоматически.

Это значит, что в обычном режиме **не нужно держать терминал открытым постоянно**.
Пользователь один раз настраивает систему, а дальше диск поднимается сам.

---

## Кастомная иконка диска

Можно назначить собственную иконку:

```powershell
onlysq-drive install-drive-icon "C:\Icons\onlysq.ico"
```

Удалить иконку:

```powershell
onlysq-drive uninstall-drive-icon
```

> Лучше использовать `.ico` файл с несколькими размерами внутри.

---

## Где хранятся данные

### Конфиг

```text
%APPDATA%\OnlySQDrive\config.json
```

### Индекс

```text
%APPDATA%\OnlySQDrive\index.sqlite3
```

### Кэш

```text
%LOCALAPPDATA%\OnlySQDrive\cache
```

### Логи автозапуска

```text
%LOCALAPPDATA%\OnlySQDrive\logs\autostart.log
```

---

## Структура проекта

```text
onlysq-drive/
├─ pyproject.toml
├─ README.md
├─ onlysq_drive/
│   ├─ __init__.py
│   ├─ cli.py
│   ├─ launcher.py
│   ├─ mount.py
│   ├─ fs_ops.py
│   ├─ cloud_client.py
│   ├─ index_db.py
│   ├─ config.py
│   ├─ autostart.py
│   ├─ context_menu.py
│   ├─ drive_icon.py
└─  └─ utils.py
```

---

## Ограничения

* Это **неофициальный** клиент OnlySQ Cloud.
* Проект зависит от установленного **WinFsp**.
* Сейчас восстановление дерева файлов основано на **локальном индексе**.
* Если удалить локальный индекс, на другом ПК структура облачного диска автоматически не восстановится.
* Проект ориентирован исключительно на Windows.

---

## Удаление

### Удалить автозапуск и интеграции

```powershell
onlysq-drive uninstall-autostart
onlysq-drive uninstall-context-menu
onlysq-drive uninstall-drive-icon
```

### Удалить локальные данные

```powershell
onlysq-drive purge --yes
```

### Удалить пакет

```powershell
pip uninstall onlysq-drive
```

---

## Лицензия

Проект распространяется под лицензией **MIT**.

---

## Disclaimer

Это **неофициальное** приложение.
Все права на бренд, API и платформу принадлежат **OnlySQ**.