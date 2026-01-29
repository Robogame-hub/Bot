import os
import random
import time
import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from config import *

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения или используем значение по умолчанию
TOKEN = os.getenv("BOT_TOKEN", "8540229374:AAH-V-8TGx7obKTd9FoRc30pSj1I-6rpk88")

bot = Bot(TOKEN)
dp = Dispatcher()

# Используем постоянное хранилище для базы данных
# На Railway: /data для Volume, локально: текущая директория
DB_PATH = os.getenv("DB_PATH", ".")
# Проверяем, существует ли /data (Railway Volume)
if os.path.exists("/data"):
    DB_PATH = "/data"
elif not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH, exist_ok=True)
DB = os.path.join(DB_PATH, "lohotron.db")

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
            if ENABLE_STAR_SPIN and current_time - last_star_spin >= STAR_SPIN_COOLDOWN:
                star_buttons.append(
                    InlineKeyboardButton(text="⭐ Крутить вне очереди (1⭐ ТЕСТ)", callback_data="test_star_spin_1")
                )
            
            # Кнопка буста за 3 звезды (если прошло 1 час) - ТЕСТОВЫЙ РЕЖИМ
            if ENABLE_STAR_BOOST and current_time - last_star_boost >= STAR_BOOST_COOLDOWN:
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
            tokens INTEGER DEFAULT 100,
            last_spin INTEGER DEFAULT 0,
            last_daily INTEGER DEFAULT 0,
            last_star_spin INTEGER DEFAULT 0,
            last_star_boost INTEGER DEFAULT 0,
            boost_until INTEGER DEFAULT 0,
            last_activity INTEGER DEFAULT 0,
            warning_sent INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, chat_id)
        )
        """)
        await db.commit()
        
        # Миграция: добавляем новые поля если их нет
        try:
            await db.execute("ALTER TABLE users ADD COLUMN last_activity INTEGER DEFAULT 0")
            await db.commit()
            logger.info("Добавлена колонка last_activity")
        except Exception as e:
            if "duplicate column name" not in str(e).lower() and "already exists" not in str(e).lower():
                logger.warning(f"Ошибка при добавлении last_activity: {e}")
        
        try:
            await db.execute("ALTER TABLE users ADD COLUMN warning_sent INTEGER DEFAULT 0")
            await db.commit()
            logger.info("Добавлена колонка warning_sent")
        except Exception as e:
            if "duplicate column name" not in str(e).lower() and "already exists" not in str(e).lower():
                logger.warning(f"Ошибка при добавлении warning_sent: {e}")

# ---------------- HELPERS ----------------

def now():
    return int(time.time())

def spin_result():
    return [random.choice(EMOJIS) for _ in range(5)]

def format_slots_display(slots):
    """Форматирует слоты для красивого отображения с разделением ячеек"""
    # Создаем визуальное разделение ячеек
    slots_str = "  |  ".join(slots)
    return f"🎰\n━━━━━━━━━━━━━━━━━━\n  {slots_str}\n━━━━━━━━━━━━━━━━━━\n🎰"

def format_slots_animated(slots, current_slot=0, spin_step=0):
    """Создает анимированное отображение слотов (для эффекта кручения)
    
    Args:
        slots: финальные слоты
        current_slot: текущий слот, который крутится (0-4)
        spin_step: шаг кручения текущего слота (0-2, на 3-м фиксируется)
    """
    animated = []
    for i in range(5):
        if i < current_slot:
            # Слот уже зафиксирован - показываем финальное значение
            animated.append(slots[i])
        elif i == current_slot:
            # Текущий слот крутится
            if spin_step < 3:
                # Показываем случайный эмодзи
                animated.append(random.choice(EMOJIS))
            else:
                # Фиксируем финальное значение
                animated.append(slots[i])
        else:
            # Слот еще не инициализирован - показываем крестик
            animated.append("❌")
    return format_slots_display(animated)

def format_slots_display(slots):
    """Форматирует слоты для красивого отображения с разделением ячеек"""
    # Создаем визуальное разделение ячеек
    slots_str = " | ".join(slots)
    return f"🎰 [{slots_str}] 🎰"

def format_slots_animated(slots, current_slot=0, spin_step=0):
    """Создает анимированное отображение слотов (для эффекта кручения)
    
    Args:
        slots: финальные слоты
        current_slot: текущий слот, который крутится (0-4)
        spin_step: шаг кручения текущего слота (0-2, на 3-м фиксируется)
    """
    animated = []
    for i in range(5):
        if i < current_slot:
            # Слот уже зафиксирован - показываем финальное значение
            animated.append(slots[i])
        elif i == current_slot:
            # Текущий слот крутится
            if spin_step < 3:
                # Показываем случайный эмодзи
                animated.append(random.choice(EMOJIS))
            else:
                # Фиксируем финальное значение
                animated.append(slots[i])
        else:
            # Слот еще не инициализирован - показываем крестик
            animated.append("❌")
    return format_slots_display(animated)

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

async def update_user_activity(user_id, chat_id):
    """Обновляет время последней активности пользователя"""
    try:
        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "UPDATE users SET last_activity=? WHERE user_id=? AND chat_id=?",
                (now(), user_id, chat_id)
            )
            await db.commit()
    except:
        pass

@dp.message(Command("startLohotron", "startlohotron", "help"))
async def start(msg: Message):
    # Обновляем активность
    await update_user_activity(msg.from_user.id, msg.chat.id)
    
    help_text = """
🎰 <b>ЛОХОТРОН БОТ</b> 🎰

<b>Команды:</b>
/spinLohotron@LohotronRuletBot - Крутить слот-машину (15 жетонов)
/exchangeLohotron@LohotronRuletBot - Обменять 50 очков на 5 жетонов
/ratingLohotron@LohotronRuletBot - ТОП-10 игроков чата
/myInventory@LohotronRuletBot - Показать ваши жетоны и очки

<b>Правила:</b>
• Начальное количество: 100 жетонов
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
        await update_user_activity(user.id, chat_id)

        async with aiosqlite.connect(DB) as db:
            # Создаем пользователя с начальными значениями
            current_time = now()
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, chat_id, tokens, last_daily, last_activity) VALUES (?,?,100,0,?)",
                (user.id, chat_id, current_time)
            )
            # Обновляем активность для существующих пользователей
            await db.execute(
                "UPDATE users SET last_activity=? WHERE user_id=? AND chat_id=?",
                (current_time, user.id, chat_id)
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

            # DAILY TOKENS (только если прошло больше 24 часов и last_daily не равен 0)
            if last_daily > 0 and now() - last_daily > 86400:
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

            # Генерируем результат
            line = spin_result()
            win, text = calc_win(line)

            # Списываем жетоны
            tokens -= SPIN_COST

            # Отправляем сообщение со слотами (анимация кручения) - новым сообщением
            spin_msg = await bot.send_message(chat_id=chat_id, text="🎰 Крутим слоты...")
            
            # Анимация кручения: каждый слот обновляется 3 раза, затем фиксируется
            for slot_index in range(5):  # 5 слотов
                for spin_step in range(3):  # 3 обновления для каждого слота
                    await asyncio.sleep(0.3)
                    animated_display = format_slots_animated(line, slot_index, spin_step)
                    try:
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=spin_msg.message_id,
                            text=animated_display
                        )
                    except:
                        pass
                # Фиксируем слот (4-й шаг - показываем финальное значение)
                await asyncio.sleep(0.2)
                animated_display = format_slots_animated(line, slot_index, 3)
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=spin_msg.message_id,
                        text=animated_display
                    )
                except:
                    pass
            
            # Финальный результат (все слоты зафиксированы)
            await asyncio.sleep(0.3)
            final_display = format_slots_display(line)
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=spin_msg.message_id,
                    text=final_display
                )
            except:
                pass

            # Обновляем данные в БД
            points += win
            current_time = now()
            await db.execute("""
            UPDATE users SET points=?, tokens=?, last_spin=?, last_activity=? 
            WHERE user_id=? AND chat_id=?
            """, (points, tokens, current_time, current_time, user.id, chat_id))
            await db.commit()

            # Отправляем результаты с кнопками - ответом на сообщение со слотами
            await asyncio.sleep(0.5)
            boost_text = " ⚡ (Буст активен!)" if (boost_until and now() < boost_until) else ""
            await bot.send_message(
                chat_id=chat_id,
                text=f"👉 {text}\n"
                     f"🏆 +{win} очков\n"
                     f"💰 Очки: {points}\n"
                     f"🎟 Жетоны: {tokens}{boost_text}",
                reply_to_message_id=spin_msg.message_id,
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
        await update_user_activity(user.id, chat_id)

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
        await update_user_activity(msg.from_user.id, chat_id)

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
        await update_user_activity(user.id, chat_id)

        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT tokens, points FROM users WHERE user_id=? AND chat_id=?",
                (user.id, chat_id)
            )
            row = await cur.fetchone()
            
            if not row:
                # Если пользователь еще не играл, создаем запись
                current_time = now()
                await db.execute(
                    "INSERT OR IGNORE INTO users (user_id, chat_id, tokens, last_daily, last_activity) VALUES (?,?,100,0,?)",
                    (user.id, chat_id, current_time)
                )
                await db.execute(
                    "UPDATE users SET last_activity=? WHERE user_id=? AND chat_id=?",
                    (current_time, user.id, chat_id)
                )
                await db.commit()
                tokens, points = 100, 0  # Начальные значения
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
        await update_user_activity(callback.from_user.id, callback.message.chat.id)
        
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
        await update_user_activity(user.id, chat_id)
        
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
                current_time = now()
                await db.execute(
                    "UPDATE users SET last_star_spin=?, last_activity=? WHERE user_id=? AND chat_id=?",
                    (current_time, current_time, user.id, chat_id)
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
                    current_time = now()
                    boost_until = current_time + STAR_BOOST_DURATION
                    await db.execute(
                        "UPDATE users SET last_star_boost=?, boost_until=?, last_activity=? WHERE user_id=? AND chat_id=?",
                        (current_time, boost_until, current_time, user.id, chat_id)
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
            
            # Отправляем сообщение со слотами (анимация кручения)
            spin_msg = await bot.send_message(chat_id=chat_id, text="🎰 Крутим слоты...")
            
            # Анимация кручения: каждый слот обновляется 3 раза, затем фиксируется
            for slot_index in range(5):  # 5 слотов
                for spin_step in range(3):  # 3 обновления для каждого слота
                    await asyncio.sleep(0.3)
                    animated_display = format_slots_animated(line, slot_index, spin_step)
                    try:
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=spin_msg.message_id,
                            text=animated_display
                        )
                    except:
                        pass
                # Фиксируем слот (4-й шаг - показываем финальное значение)
                await asyncio.sleep(0.2)
                animated_display = format_slots_animated(line, slot_index, 3)
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=spin_msg.message_id,
                        text=animated_display
                    )
                except:
                    pass
            
            # Финальный результат (все слоты зафиксированы)
            await asyncio.sleep(0.3)
            final_display = format_slots_display(line)
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=spin_msg.message_id,
                    text=final_display
                )
            except:
                pass
            
            points += win
            current_time = now()
            await db.execute("""
            UPDATE users SET points=?, tokens=?, last_spin=?, last_activity=? 
            WHERE user_id=? AND chat_id=?
            """, (points, tokens, current_time, current_time, user_id, chat_id))
            await db.commit()
            
            # Отправляем результаты с кнопками
            await asyncio.sleep(0.5)
            boost_text = " ⚡ (Буст активен!)" if (boost_until and now() < boost_until) else ""
            star_text = " ⭐ (Вне очереди!)" if star_spin else ""
            
            await bot.send_message(
                chat_id=chat_id,
                text=f"👉 {text}\n"
                     f"🏆 +{win} очков\n"
                     f"💰 Очки: {points}\n"
                     f"🎟 Жетоны: {tokens}{boost_text}{star_text}",
                reply_to_message_id=spin_msg.message_id,
                reply_markup=await get_keyboard_with_stars(user_id, chat_id)
            )
    except Exception as e:
        logger.error(f"Ошибка выполнения крутки: {e}")

# ---------------- INACTIVE USERS CLEANUP ----------------

async def check_inactive_users():
    """Проверяет неактивных пользователей и отправляет предупреждения/удаляет данные"""
    try:
        current_time = now()
        three_days = 3 * 86400  # 3 дня в секундах
        five_days = 5 * 86400   # 5 дней в секундах
        
        async with aiosqlite.connect(DB) as db:
            # Получаем всех пользователей с их активностью
            cur = await db.execute(
                "SELECT user_id, chat_id, last_activity, warning_sent FROM users WHERE last_activity > 0"
            )
            users = await cur.fetchall()
            
            for user_id, chat_id, last_activity, warning_sent in users:
                inactive_time = current_time - last_activity
                
                # Предупреждение на 3-й день (если еще не отправляли)
                if inactive_time >= three_days and inactive_time < five_days and warning_sent == 0:
                    try:
                        await bot.send_message(
                            chat_id=chat_id,
                            text="⚠️ <b>Предупреждение!</b>\n\n"
                                 "Вы не заходили в бота уже 3 дня.\n"
                                 "Если не зайдете в течение 2 дней, ваши данные будут удалены.\n\n"
                                 "Используйте любую команду бота, чтобы сохранить прогресс!",
                            parse_mode=ParseMode.HTML
                        )
                        await db.execute(
                            "UPDATE users SET warning_sent=1 WHERE user_id=? AND chat_id=?",
                            (user_id, chat_id)
                        )
                        await db.commit()
                    except Exception as e:
                        logger.error(f"Ошибка отправки предупреждения пользователю {user_id}: {e}")
                
                # Финальное предупреждение и удаление на 5-й день
                elif inactive_time >= five_days:
                    try:
                        # Отправляем финальное предупреждение
                        if warning_sent == 1:  # Если уже отправляли первое предупреждение
                            await bot.send_message(
                                chat_id=chat_id,
                                text="❌ <b>Ваши данные удалены</b>\n\n"
                                     "Вы не заходили в бота 5 дней.\n"
                                     "Все ваши данные (очки, жетоны, прогресс) были удалены.\n\n"
                                     "Используйте /startLohotron для начала заново.",
                                parse_mode=ParseMode.HTML
                            )
                        # Удаляем данные пользователя
                        await db.execute(
                            "DELETE FROM users WHERE user_id=? AND chat_id=?",
                            (user_id, chat_id)
                        )
                        await db.commit()
                        logger.info(f"Удалены данные неактивного пользователя {user_id} из чата {chat_id}")
                    except Exception as e:
                        logger.error(f"Ошибка удаления данных пользователя {user_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка проверки неактивных пользователей: {e}")

async def cleanup_task():
    """Периодическая задача для проверки неактивных пользователей"""
    while True:
        try:
            await check_inactive_users()
        except Exception as e:
            logger.error(f"Ошибка в задаче очистки: {e}")
        # Проверяем раз в день (86400 секунд)
        await asyncio.sleep(86400)

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
