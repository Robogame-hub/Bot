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
    """Создает базовую клавиатуру с кнопками команд"""
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

async def get_keyboard_with_stars(user_id, chat_id):
    """Создает клавиатуру с кнопками команд и звездами"""
    buttons = [
        [
            InlineKeyboardButton(text="🎰 Крутить слот-машину", callback_data="cmd_spinlohotron"),
            InlineKeyboardButton(text="📦 Показать жетоны и очки", callback_data="cmd_myinventory")
        ],
        [
            InlineKeyboardButton(text="🔄 Обменять очки на жетоны", callback_data="cmd_exchangelohotron"),
            InlineKeyboardButton(text="🏆 ТОП-10 игроков чата", callback_data="cmd_ratinglohotron")
        ]
    ]
    
    # Проверяем доступность кнопок со звездами
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT last_star_spin, last_star_boost, boost_until FROM users WHERE user_id=? AND chat_id=?",
            (user_id, chat_id)
        )
        row = await cur.fetchone()
        
        star_buttons = []
        if row:
            last_star_spin, last_star_boost, boost_until = row
            current_time = now()
            
            # Кнопка крутки за 1 звезду (если прошло 10 минут) - ТЕСТОВЫЙ РЕЖИМ
            if current_time - last_star_spin >= STAR_SPIN_COOLDOWN:
                star_buttons.append(
                    InlineKeyboardButton(text="⭐ Крутить вне очереди (1⭐ ТЕСТ)", callback_data="test_star_spin_1")
                )
            
            # Кнопка буста за 3 звезды (если прошло 1 час) - ТЕСТОВЫЙ РЕЖИМ
            if current_time - last_star_boost >= STAR_BOOST_COOLDOWN:
                star_buttons.append(
                    InlineKeyboardButton(text="⚡ Уменьшить интервал на 1ч (3⭐ ТЕСТ)", callback_data="test_star_boost_3")
                )
        
        if star_buttons:
            buttons.append(star_buttons)
    
    buttons.append([
        InlineKeyboardButton(text="ℹ️ Справка и правила игры", callback_data="cmd_startlohotron")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

SPIN_COST = 15
COOLDOWN = 600  # 10 минут
COOLDOWN_BOOSTED = 300  # 5 минут (при бусте)
DAILY_TOKENS = 50
STAR_SPIN_COOLDOWN = 600  # 10 минут кулдаун для кнопки звездной крутки
STAR_BOOST_DURATION = 3600  # 1 час длительность буста
STAR_BOOST_COOLDOWN = 3600  # 1 час кулдаун для кнопки буста

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
            last_star_spin INTEGER DEFAULT 0,
            last_star_boost INTEGER DEFAULT 0,
            boost_until INTEGER DEFAULT 0,
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
    await msg.reply(help_text, parse_mode=ParseMode.HTML, reply_markup=await get_keyboard_with_stars(msg.from_user.id, msg.chat.id))

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
                "SELECT points, tokens, last_spin, last_daily, boost_until FROM users WHERE user_id=? AND chat_id=?",
                (user.id, chat_id)
            )
            row = await cur.fetchone()
            if not row:
                return await msg.reply("❌ Ошибка при получении данных пользователя", reply_markup=await get_keyboard_with_stars(user.id, chat_id))
            
            points, tokens, last_spin, last_daily, boost_until = row
            
            # Определяем текущий кулдаун (с учетом буста)
            current_cooldown = COOLDOWN_BOOSTED if (boost_until and now() < boost_until) else COOLDOWN

            # DAILY TOKENS
            if now() - last_daily > 86400:
                tokens += DAILY_TOKENS
                await db.execute(
                    "UPDATE users SET tokens=?, last_daily=? WHERE user_id=? AND chat_id=?",
                    (tokens, now(), user.id, chat_id)
                )
                await db.commit()
                await msg.reply(f"🎁 Получено {DAILY_TOKENS} ежедневных жетонов!", reply_markup=await get_keyboard_with_stars(user.id, chat_id))

            if tokens < SPIN_COST:
                return await msg.reply("❌ Недостаточно жетонов!", reply_markup=await get_keyboard_with_stars(user.id, chat_id))

            if now() - last_spin < current_cooldown:
                wait = current_cooldown - (now() - last_spin)
                boost_text = " (буст активен!)" if (boost_until and now() < boost_until) else ""
                return await msg.reply(f"⏳ Крутить можно через {wait//60} мин {wait%60} сек{boost_text}", reply_markup=await get_keyboard_with_stars(user.id, chat_id))

            line = spin_result()
            win, text = calc_win(line)

            tokens -= SPIN_COST
            points += win

            await db.execute("""
            UPDATE users SET points=?, tokens=?, last_spin=? 
            WHERE user_id=? AND chat_id=?
            """, (points, tokens, now(), user.id, chat_id))
            await db.commit()

            boost_text = " ⚡ (Буст активен!)" if (boost_until and now() < boost_until) else ""
            await msg.reply(
                f"🎰 {' | '.join(line)}\n"
                f"👉 {text}\n"
                f"🏆 +{win} очков\n"
                f"💰 Очки: {points}\n"
                f"🎟 Жетоны: {tokens}{boost_text}",
                reply_markup=await get_keyboard_with_stars(user.id, chat_id)
            )
    except Exception as e:
        await msg.reply(f"❌ Произошла ошибка: {str(e)}", reply_markup=await get_keyboard_with_stars(msg.from_user.id, msg.chat.id))

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
                return await msg.reply("❌ Вы еще не играли. Используйте /spin для начала игры.", reply_markup=await get_keyboard_with_stars(user.id, chat_id))

            points, tokens = row
            if points < 50:
                return await msg.reply("❌ Нужно минимум 50 очков", reply_markup=await get_keyboard_with_stars(user.id, chat_id))

            points -= 50
            tokens += 5

            await db.execute(
                "UPDATE users SET points=?, tokens=? WHERE user_id=? AND chat_id=?",
                (points, tokens, user.id, chat_id)
            )
            await db.commit()

        await msg.reply("🔄 Обмен выполнен: -50 очков → +5 жетонов", reply_markup=await get_keyboard_with_stars(user.id, chat_id))
    except Exception as e:
        await msg.reply(f"❌ Произошла ошибка: {str(e)}", reply_markup=await get_keyboard_with_stars(msg.from_user.id, msg.chat.id))

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
            return await msg.reply("📊 Пока нет игроков в этом чате", reply_markup=await get_keyboard_with_stars(msg.from_user.id, chat_id))

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

        await msg.reply(text, parse_mode=ParseMode.HTML, reply_markup=await get_keyboard_with_stars(msg.from_user.id, chat_id))
    except Exception as e:
        await msg.reply(f"❌ Произошла ошибка: {str(e)}", reply_markup=await get_keyboard_with_stars(msg.from_user.id, msg.chat.id))

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
        
        await msg.reply(text, reply_markup=await get_keyboard_with_stars(user.id, chat_id))
    except Exception as e:
        await msg.reply(f"❌ Произошла ошибка: {str(e)}", reply_markup=await get_keyboard_with_stars(msg.from_user.id, msg.chat.id))

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

# ---------------- STAR PAYMENTS (ТЕСТОВЫЙ РЕЖИМ) ----------------

@dp.callback_query(lambda c: c.data.startswith("test_star_"))
async def handle_test_star_button(callback: CallbackQuery):
    """Обработчик нажатий на тестовые кнопки со звездами (без реальных платежей)"""
    try:
        user = callback.from_user
        chat_id = callback.message.chat.id
        data = callback.data
        
        async with aiosqlite.connect(DB) as db:
            # Проверяем доступность
            cur = await db.execute(
                "SELECT last_star_spin, last_star_boost FROM users WHERE user_id=? AND chat_id=?",
                (user.id, chat_id)
            )
            row = await cur.fetchone()
            if not row:
                await callback.answer("❌ Ошибка получения данных", show_alert=True)
                return
            
            last_star_spin, last_star_boost = row
            current_time = now()
            
            if data == "test_star_spin_1":
                # Проверяем кулдаун
                if current_time - last_star_spin < STAR_SPIN_COOLDOWN:
                    wait = STAR_SPIN_COOLDOWN - (current_time - last_star_spin)
                    await callback.answer(f"⏳ Кнопка будет доступна через {wait//60} мин", show_alert=True)
                    return
                
                # ТЕСТОВЫЙ РЕЖИМ: сразу выполняем действие без платежа
                # Обновляем время последней звездной крутки
                await db.execute(
                    "UPDATE users SET last_star_spin=? WHERE user_id=? AND chat_id=?",
                    (now(), user.id, chat_id)
                )
                # Сбрасываем таймер обычной крутки
                await db.execute(
                    "UPDATE users SET last_spin=0 WHERE user_id=? AND chat_id=?",
                    (user.id, chat_id)
                )
                await db.commit()
                
                # Выполняем крутку
                await perform_spin(user.id, chat_id, star_spin=True)
                await callback.answer("✅ Крутка вне очереди выполнена! (ТЕСТ)", show_alert=False)
                
            elif data == "test_star_boost_3":
                # Проверяем кулдаун
                if current_time - last_star_boost < STAR_BOOST_COOLDOWN:
                    wait = STAR_BOOST_COOLDOWN - (current_time - last_star_boost)
                    await callback.answer(f"⏳ Кнопка будет доступна через {wait//60} мин", show_alert=True)
                    return
                
                # ТЕСТОВЫЙ РЕЖИМ: сразу выполняем действие без платежа
                # Обновляем время последнего буста и устанавливаем время окончания буста
                boost_until = now() + STAR_BOOST_DURATION
                await db.execute(
                    "UPDATE users SET last_star_boost=?, boost_until=? WHERE user_id=? AND chat_id=?",
                    (now(), boost_until, user.id, chat_id)
                )
                await db.commit()
                
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚡ Буст активирован! Интервал круток уменьшен до 5 минут на 1 час! (ТЕСТ)",
                    reply_markup=await get_keyboard_with_stars(user.id, chat_id)
                )
                await callback.answer("✅ Буст активирован! (ТЕСТ)", show_alert=False)
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике тестовых звездных кнопок: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)

async def perform_spin(user_id, chat_id, star_spin=False):
    """Выполняет крутку (используется для обычной и звездной крутки)"""
    try:
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT points, tokens, last_spin, boost_until FROM users WHERE user_id=? AND chat_id=?",
                (user_id, chat_id)
            )
            row = await cur.fetchone()
            if not row:
                return
            
            points, tokens, last_spin, boost_until = row
            
            # Проверяем кулдаун (если не звездная крутка)
            if not star_spin:
                current_cooldown = COOLDOWN_BOOSTED if (boost_until and now() < boost_until) else COOLDOWN
                if now() - last_spin < current_cooldown:
                    return
            
            if tokens < SPIN_COST:
                return
            
            line = spin_result()
            win, text = calc_win(line)
            
            tokens -= SPIN_COST
            points += win
            
            await db.execute("""
            UPDATE users SET points=?, tokens=?, last_spin=? 
            WHERE user_id=? AND chat_id=?
            """, (points, tokens, now(), user_id, chat_id))
            await db.commit()
            
            boost_text = " ⚡ (Буст активен!)" if (boost_until and now() < boost_until) else ""
            star_text = " ⭐ (Вне очереди!)" if star_spin else ""
            
            await bot.send_message(
                chat_id=chat_id,
                text=f"🎰 {' | '.join(line)}\n"
                     f"👉 {text}\n"
                     f"🏆 +{win} очков\n"
                     f"💰 Очки: {points}\n"
                     f"🎟 Жетоны: {tokens}{boost_text}{star_text}",
                reply_markup=await get_keyboard_with_stars(user_id, chat_id)
            )
    except Exception as e:
        logger.error(f"Ошибка выполнения крутки: {e}")

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
