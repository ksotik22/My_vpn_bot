# V2RayTun Telegram VPN Bot — MVP

Первая рабочая версия Telegram-бота, который:

- регистрирует пользователей;
- показывает список стран;
- автоматически выбирает VPS с наименьшей загрузкой;
- создаёт UUID для пользователя;
- по SSH вызывает скрипт на VPS;
- добавляет пользователя в Xray;
- получает VLESS Reality-ссылку;
- отправляет её пользователю для импорта в V2RayTun;
- хранит пользователей и VPS в SQLite.

## Архитектура

Telegram → aiogram → SQLite → SSH → VPS/Xray → VLESS Reality → V2RayTun

## Требования

- Python 3.11+
- Linux VPS для бота (или локальный компьютер для теста)
- один или несколько Linux VPS с установленным Xray
- SSH-доступ к VPN VPS
- Telegram bot token от @BotFather

## 1. Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Заполни `.env`:

```env
BOT_TOKEN=123456:ABC...
ADMIN_IDS=123456789
DATABASE_PATH=./data/bot.db
```

`ADMIN_IDS` — Telegram ID администратора через запятую.

## 2. Подготовка VPN VPS

На каждом VPS:

```bash
sudo mkdir -p /opt/vpn-bot
sudo cp server/add_vless_user.sh /opt/vpn-bot/
sudo chmod +x /opt/vpn-bot/add_vless_user.sh
```

Перед этим Xray должен быть уже настроен на VPS с VLESS Reality inbound.

Скрипт ожидает, что конфигурация Xray находится здесь:

```text
/etc/xray/config.json
```

И inbound имеет:

```json
{
  "tag": "vless-reality",
  "protocol": "vless"
}
```

Скрипт добавляет клиента в `settings.clients`.

В `server/add_vless_user.sh` нужно указать параметры Reality:
- DOMAIN
- PORT
- SNI
- PUBLIC_KEY
- SHORT_ID

## 3. Запуск

```bash
python bot.py
```

В Telegram:

```text
/start
```

Администратор:

```text
/addvps nl NL1 1.2.3.4 root /root/.ssh/id_ed25519
```

После этого пользователи увидят Нидерланды.

Формат:

```text
/addvps <country_code> <name> <host> <ssh_user> <ssh_key_path>
```

Пример:

```text
/addvps nl Amsterdam-1 203.0.113.10 root /root/.ssh/id_ed25519
```

## 4. Команды

Пользователь:

- `/start`
- `/vpn`
- `/myvpn`

Администратор:

- `/addvps`
- `/vps`
- `/users`

## Важное

Это MVP. Перед публичным запуском стоит добавить:
- срок действия конфигураций;
- лимиты устройств;
- подписки;
- оплату;
- health-check VPS;
- автоматическое удаление просроченных пользователей;
- Redis/PostgreSQL вместо SQLite;
- отдельного VPN-agent вместо SSH;
- rate limit;
- webhook вместо polling;
- резервное копирование БД.

Не храни Telegram bot token или SSH private key в репозитории.
