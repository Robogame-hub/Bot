import os
import random
import time
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode

# Получаем токен из переменных окружения или используем значение по умолчанию
TOKEN = os.getenv("BOT_TOKEN", "8540229374:AAH-V-8TGx7obKTd9FoRc30pSj1I-6rpk88")

bot = Bot(TOKEN)
dp = Dispatcher()

DB = "lohotron.db"

EMOJIS = ["🍎", "🍌", "🍺", "💩", "🤡", "🐸", "🍩", "⭐"]

# Клавиатура с кнопками команд (используем описания из setup_commands.py)
def get_command_keyboard():
    """Создает клавиатуру с кнопками команд"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎰 Крутить слот-машину", callback_data="cmd_spinlohotron"),
            InlineKeyboardButton(text="📦 Показать жетоны и очки", callback_data="cmd_myinventory")
        ],
        [
            InlineKeyboardButton(text="🔄 Обменять очки на жетоны", callback_data="cmd_exchangelohotron"),
            InlineKeyboardButton(text="🏆 ТОП-10 игроков чата", callback_data="cmd_ratinglohotron")
        ],
        [
            InlineKeyboardButton(text="ℹ️ Справка и правила игры", callback_data="cmd_startlohotron")
        ]
    ])
    return keyboard

SPIN_COST = 15
COOLDOWN = 600  # 10 минут
DAILY_TOKENS = 50

# ---------------- DATABASE ----------------

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER,
            chat_id INTEGER,
            points INTEGER DEFAULT 0,
            tokens INTEGER DEFAULT 50,
            last_spin INTEGER DEFAULT 0,
            last_daily INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, chat_id)
        )
        """)
        await db.commit()

# ---------------- HELPERS ----------------

def now():
    return int(time.time())

def spin_result():
    return [random.choice(EMOJIS) for _ in range(5)]

def calc_win(line):
    counts = {e: line.count(e) for e in set(line)}
    
    # Проверяем джекпот (5 звезд)
    if "⭐" in counts and counts["⭐"] == 5:
        return 30, "ДЖЕКПОТ ⭐⭐⭐⭐⭐"
    
    # Проверяем любые совпадения эмодзи (кроме звезд)
    max_count = 0
    max_emoji = None
    for emoji, count in counts.items():
        if emoji != "⭐" and count > max_count:
            max_count = count
            max_emoji = emoji
    
    # Начисляем очки за совпадения
    if max_count == 5:
        return 15, f"5 {max_emoji}"
    elif max_count == 4:
        return 10, f"4 {max_emoji}"
    elif max_count == 3:
        return 7, f"3 {max_emoji}"
    elif max_count == 2:
        return 5, f"2 {max_emoji}"
    
    return 0, "Ничего 😈"

# ---------------- COMMANDS ----------------

@dp.message(Command("startLohotron", "startlohotron", "help"))
async def start(msg: Message):
    help_text = """
🎰 <b>ЛОХОТРОН БОТ</b> 🎰

<b>Команды:</b>
/spinLohotron@LohotronRuletBot - Крутить слот-машину (15 жетонов)
/exchangeLohotron@LohotronRuletBot - Обменять 50 очков на 5 жетонов
/ratingLohotron@LohotronRuletBot - ТОП-10 игроков чата
/myInventory@LohotronRuletBot - Показать ваши жетоны и очки

<b>Правила:</b>
• Каждый день получаешь 50 жетонов
• Кулдаун между крутками: 10 минут
• Выигрыши: 2 одинаковых = 5 очков, 3 = 7 очков, 4 = 10 очков, 5 = 15 очков
• 5 звезд ⭐ = 30 очков (ДЖЕКПОТ!)

Удачи! 🍀
"""
    await msg.reply(help_text, parse_mode=ParseMode.HTML, reply_markup=get_command_keyboard())

@dp.message(Command("spinLohotron", "spinlohotron"))
async def spin(msg: Message):
    try:
        user = msg.from_user
        chat_id = msg.chat.id

        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, chat_id) VALUES (?,?)",
                (user.id, chat_id)
            )
            await db.commit()

            cur = await db.execute(
                "SELECT points, tokens, last_spin, last_daily FROM users WHERE user_id=? AND chat_id=?",
                (user.id, chat_id)
            )
            row = await cur.fetchone()
            if not row:
                return await msg.reply("❌ Ошибка при получении данных пользователя")
            
            points, tokens, last_spin, last_daily = row

            # DAILY TOKENS
            if now() - last_daily > 86400:
                tokens += DAILY_TOKENS
                await db.execute(
                    "UPDATE users SET tokens=?, last_daily=? WHERE user_id=? AND chat_id=?",
                    (tokens, now(), user.id, chat_id)
                )
                await db.commit()
                await msg.reply(f"🎁 Получено {DAILY_TOKENS} ежедневных жетонов!", reply_markup=get_command_keyboard())

            if tokens < SPIN_COST:
                return await msg.reply("❌ Недостаточно жетонов!", reply_markup=get_command_keyboard())

            if now() - last_spin < COOLDOWN:
                wait = COOLDOWN - (now() - last_spin)
                return await msg.reply(f"⏳ Крутить можно через {wait//60} мин {wait%60} сек", reply_markup=get_command_keyboard())

            line = spin_result()
            win, text = calc_win(line)

            tokens -= SPIN_COST
            points += win

            await db.execute("""
            UPDATE users SET points=?, tokens=?, last_spin=? 
            WHERE user_id=? AND chat_id=?
            """, (points, tokens, now(), user.id, chat_id))
            await db.commit()

        await msg.reply(
            f"🎰 {' | '.join(line)}\n"
            f"👉 {text}\n"
            f"🏆 +{win} очков\n"
            f"💰 Очки: {points}\n"
            f"🎟 Жетоны: {tokens}",
            reply_markup=get_command_keyboard()
        )
    except Exception as e:
        await msg.reply(f"❌ Произошла ошибка: {str(e)}", reply_markup=get_command_keyboard())

# ---------------- EXCHANGE ----------------

@dp.message(Command("exchangeLohotron", "exchangelohotron"))
async def exchange(msg: Message):
    try:
        user = msg.from_user
        chat_id = msg.chat.id

        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT points, tokens FROM users WHERE user_id=? AND chat_id=?",
                (user.id, chat_id)
            )
            row = await cur.fetchone()
            if not row:
                return await msg.reply("❌ Вы еще не играли. Используйте /spin для начала игры.", reply_markup=get_command_keyboard())

            points, tokens = row
            if points < 50:
                return await msg.reply("❌ Нужно минимум 50 очков", reply_markup=get_command_keyboard())

            points -= 50
            tokens += 5

            await db.execute(
                "UPDATE users SET points=?, tokens=? WHERE user_id=? AND chat_id=?",
                (points, tokens, user.id, chat_id)
            )
            await db.commit()

        await msg.reply("🔄 Обмен выполнен: -50 очков → +5 жетонов", reply_markup=get_command_keyboard())
    except Exception as e:
        await msg.reply(f"❌ Произошла ошибка: {str(e)}", reply_markup=get_command_keyboard())

# ---------------- RATING ----------------

@dp.message(Command("ratingLohotron", "ratinglohotron"))
async def rating(msg: Message):
    try:
        chat_id = msg.chat.id

        async with aiosqlite.connect(DB) as db:
            cur = await db.execute("""
            SELECT user_id, points FROM users 
            WHERE chat_id=? ORDER BY points DESC LIMIT 10
            """, (chat_id,))
            rows = await cur.fetchall()

        if not rows:
            return await msg.reply("📊 Пока нет игроков в этом чате", reply_markup=get_command_keyboard())

        text = "🏆 <b>ТОП-10 ЛОХОВ ЧАТА</b>\n\n"
        for i, (uid, pts) in enumerate(rows, 1):
            # Пытаемся получить имя пользователя из чата
            try:
                member = await bot.get_chat_member(chat_id, uid)
                name = member.user.full_name or f"User {uid}"
            except:
                name = f"User {uid}"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {pts} очков\n"

        await msg.reply(text, parse_mode=ParseMode.HTML, reply_markup=get_command_keyboard())
    except Exception as e:
        await msg.reply(f"❌ Произошла ошибка: {str(e)}", reply_markup=get_command_keyboard())

# ---------------- INVENTORY ----------------

@dp.message(Command("myInventory", "myinventory"))
async def inventory(msg: Message):
    try:
        user = msg.from_user
        chat_id = msg.chat.id

        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT tokens, points FROM users WHERE user_id=? AND chat_id=?",
                (user.id, chat_id)
            )
            row = await cur.fetchone()
            
            if not row:
                # Если пользователь еще не играл, создаем запись
                await db.execute(
                    "INSERT OR IGNORE INTO users (user_id, chat_id) VALUES (?,?)",
                    (user.id, chat_id)
                )
                await db.commit()
                tokens, points = 50, 0  # Начальные значения
            else:
                tokens, points = row

        text = f"""У вас
Жетонов: {tokens}
Очков: {points}"""
        
        await msg.reply(text, reply_markup=get_command_keyboard())
    except Exception as e:
        await msg.reply(f"❌ Произошла ошибка: {str(e)}", reply_markup=get_command_keyboard())

# ---------------- CALLBACK HANDLERS ----------------

@dp.callback_query(lambda c: c.data.startswith("cmd_"))
async def handle_callback(callback: CallbackQuery):
    """Обработчик нажатий на кнопки"""
    try:
        command = callback.data.replace("cmd_", "")
        msg = callback.message
        
        # Вызываем соответствующую команду, используя сообщение из callback
        if command == "spinlohotron":
            await spin(msg)
        elif command == "exchangelohotron":
            await exchange(msg)
        elif command == "ratinglohotron":
            await rating(msg)
        elif command == "myinventory":
            await inventory(msg)
        elif command == "startlohotron":
            await start(msg)
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в обработчике кнопок: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)

# ---------------- START ----------------

async def main():
    try:
        print("=" * 50)
        print("Инициализация базы данных...")
        await init_db()
        print("✓ База данных инициализирована!")
        
        # Проверка подключения
        me = await bot.get_me()
        print(f"✓ Бот подключен: @{me.username} ({me.first_name})")
        print(f"✓ ID бота: {me.id}")
        
        print("=" * 50)
        print("🚀 Запуск polling...")
        print("Бот готов к работе! Отправьте /start в Telegram")
        print("=" * 50)
        
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        print(f"ОШИБКА при запуске бота: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
