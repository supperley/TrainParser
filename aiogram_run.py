import asyncio
from create_bot import bot, dp, scheduler, admins
from handlers.error import error_router
from handlers.list import list_router
from handlers.start import start_router
from handlers.search import search_router
# from work_time.time_func import send_time_msg
from aiogram.types import BotCommand, BotCommandScopeDefault, ErrorEvent


# Функция, которая настроит командное меню (дефолтное для всех пользователей)
async def set_commands():
    commands = [BotCommand(command='start', description='Старт')]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


# Функция, которая выполнится когда бот запустится
async def start_bot():
    await set_commands()
    try:
        for admin_id in admins:
            await bot.send_message(admin_id, f'Я запущен 🥳')
    except:
        pass


# Функция, которая выполнится когда бот завершит свою работу
async def stop_bot():
    try:
        for admin_id in admins:
            await bot.send_message(admin_id, 'Бот остановлен')
    except:
        pass


@dp.errors()
async def errors_handler(event: ErrorEvent):
    print(f"Error caught: {event.exception} while processing {event.update}")
    print(event.exception)
    # logger.error("Error caught: %r while processing %r", event.exception, event.update)


async def main():
    # scheduler.add_job(send_time_msg, 'interval', seconds=10)
    # scheduler.start()
    # регистрация роутеров
    dp.include_router(start_router)
    dp.include_router(search_router)
    dp.include_router(list_router)
    # dp.include_router(admin_router)
    dp.include_router(error_router)

    # регистрация функций
    dp.startup.register(start_bot)
    dp.shutdown.register(stop_bot)

    # запуск бота в режиме long polling при запуске бот очищает все обновления, которые были за его моменты бездействия
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())