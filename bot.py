import asyncio
import logging
import os
import uuid
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from dotenv import load_dotenv

from db import Database
from ssh_provisioner import provision_user

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}
DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/bot.db")
SSH_TIMEOUT = int(os.getenv("SSH_TIMEOUT", "20"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing in .env")

logging.basicConfig(level=logging.INFO)

db = Database(DATABASE_PATH)
dp = Dispatcher()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "👋 <b>VPN Bot</b>\n\n"
        "Получить VPN-конфигурацию для V2RayTun:\n"
        "/vpn\n\n"
        "Текущая конфигурация:\n"
        "/myvpn"
    )


@dp.message(Command("vpn"))
async def vpn(message: Message):
    servers = db.get_active_servers()
    if not servers:
        await message.answer("❌ Сейчас нет доступных VPN-серверов.")
        return

    buttons = [
        [InlineKeyboardButton(
            text=f"🇺🇳 {s['name']} ({s['country'].upper()})",
            callback_data=f"getvpn:{s['id']}"
        )]
        for s in servers
    ]

    await message.answer(
        "🌍 <b>Выберите страну:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@dp.callback_query(F.data.startswith("getvpn:"))
async def get_vpn(callback: CallbackQuery):
    await callback.answer("Создаю конфигурацию…")
    user_id = callback.from_user.id
    server_id = int(callback.data.split(":")[1])

    server = db.get_server(server_id)
    if not server or not server["active"]:
        await callback.message.answer("❌ Сервер больше недоступен.")
        return

    existing = db.get_user_config(user_id)
    if existing and existing["active"]:
        await callback.message.answer(
            "У вас уже есть активная конфигурация.\n"
            "Используйте /myvpn"
        )
        return

    client_uuid = str(uuid.uuid4())

    try:
        result = await asyncio.to_thread(
            provision_user,
            server,
            client_uuid,
            f"tg-{user_id}",
            SSH_TIMEOUT
        )
    except Exception as e:
        logging.exception("Provisioning failed")
        await callback.message.answer(
            "❌ Не удалось создать конфигурацию. "
            "Администратор получил ошибку."
        )
        return

    db.create_user_config(
        telegram_id=user_id,
        server_id=server_id,
        client_uuid=client_uuid,
        email=f"tg-{user_id}",
        vless_url=result["vless_url"]
    )

    await callback.message.answer(
        "✅ <b>VPN готов</b>\n\n"
        "Импортируйте эту ссылку в V2RayTun:\n\n"
        f"<code>{result['vless_url']}</code>\n\n"
        "⚠️ Не передавайте ссылку другим людям."
    )


@dp.message(Command("myvpn"))
async def myvpn(message: Message):
    config = db.get_user_config(message.from_user.id)
    if not config or not config["active"]:
        await message.answer("У вас пока нет активной VPN-конфигурации. /vpn")
        return

    await message.answer(
        "🔐 <b>Ваша конфигурация</b>\n\n"
        f"Сервер: {config['server_name']}\n\n"
        f"<code>{config['vless_url']}</code>"
    )


@dp.message(Command("addvps"))
async def addvps(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) != 6:
        await message.answer(
            "Формат:\n"
            "/addvps <country> <name> <host> <ssh_user> <ssh_key_path>\n\n"
            "Пример:\n"
            "/addvps nl Amsterdam-1 203.0.113.10 root /root/.ssh/id_ed25519"
        )
        return

    _, country, name, host, ssh_user, ssh_key = parts
    server_id = db.add_server(
        country=country,
        name=name,
        host=host,
        ssh_user=ssh_user,
        ssh_key=ssh_key
    )

    await message.answer(f"✅ VPS добавлен. ID: {server_id}")


@dp.message(Command("vps"))
async def vps(message: Message):
    if not is_admin(message.from_user.id):
        return

    servers = db.get_all_servers()
    if not servers:
        await message.answer("VPS пока нет.")
        return

    lines = ["<b>VPS:</b>"]
    for s in servers:
        lines.append(
            f"#{s['id']} {s['name']} | {s['country'].upper()} | "
            f"{s['host']} | active={bool(s['active'])}"
        )
    await message.answer("\n".join(lines))


@dp.message(Command("users"))
async def users(message: Message):
    if not is_admin(message.from_user.id):
        return

    rows = db.get_user_configs()
    if not rows:
        await message.answer("Пользователей пока нет.")
        return

    lines = ["<b>VPN users:</b>"]
    for r in rows:
        lines.append(
            f"{r['telegram_id']} → {r['server_name']} → "
            f"{'active' if r['active'] else 'disabled'}"
        )
    await message.answer("\n".join(lines))


async def main():
    db.init()
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
