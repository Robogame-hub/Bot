"""
Скрипт для автоматической установки команд бота через Bot API
"""
import os
import asyncio
from aiogram import Bot
from aiogram.types import BotCommand

TOKEN = os.getenv("BOT_TOKEN", "8540229374:AAH-V-8TGx7obKTd9FoRc30pSj1I-6rpk88")

# Команды бота (Telegram требует команды в нижнем регистре)
# В боте команды обрабатываются case-insensitive
commands = [
    BotCommand(command="startlohotron", description="Справка и правила игры"),
    BotCommand(command="spinlohotron", description="Крутить слот-машину"),
    BotCommand(command="exchangelohotron", description="Обменять очки на жетоны"),
    BotCommand(command="ratinglohotron", description="ТОП-10 игроков чата"),
    BotCommand(command="myinventory", description="Показать жетоны и очки"),
]

async def set_commands():
    """Устанавливает команды бота через Bot API"""
    bot = Bot(TOKEN)
    
    try:
        await bot.set_my_commands(commands)
        print("OK: Команды успешно установлены!")
        print("\nУстановленные команды:")
        for cmd in commands:
            print(f"  /{cmd.command} - {cmd.description}")
    except Exception as e:
        print(f"ERROR: Ошибка при установке команд: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    print("=" * 50)
    print("Установка команд бота через Bot API")
    print("=" * 50)
    print()
    asyncio.run(set_commands())

