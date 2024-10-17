import json
import aiosqlite
import asyncio
from aiohttp import ClientSession, web
from aiologger.loggers.json import JsonLogger
from datetime import datetime


logger = JsonLogger.with_default_handlers(
    level='DEBUG',
    serializer_kwargs={'ensure_ascii': False},
)

# здесь будут храниться объекты, общие для всего приложения
app_storage: dict = {}


async def create_table():
    async with aiosqlite.connect('weather.db') as db:
        await db.execute('CREATE TABLE IF NOT EXISTS requests '
                         '(date text, city text, weather text)')
        await db.commit()


async def save_to_db(city, weather):
    async with aiosqlite.connect('weather.db') as db:
        await db.execute('INSERT INTO requests VALUES (?, ?, ?)',
                         (datetime.now(), city, weather))
        await db.commit()


async def get_weather(city):
    url = f'http://api.openweathermap.org/data/2.5/weather'
    params = {'q': city, 'APPID': '2a4ff86f9aaa70041ec8e82db64abf56'}

    # используем единую сессию
    async with app_storage['session'].get(url=url, params=params) as response:
        weather_json = await response.json()
        try:
            return weather_json["weather"][0]["main"]
        except KeyError:
            return 'Нет данных'


async def handle(request):
    city_en = request.rel_url.query['city']

    await logger.info(f'Поступил запрос на город: {city_en}')

    weather_en = await get_weather(city_en)

    result = {'city': city_en, 'weather': weather_en}

    await save_to_db(city_en, weather_en)

    return web.Response(text=json.dumps(result, ensure_ascii=False))


async def main():
    # создаем единую сессию для всего приложения
    app_storage['session'] = ClientSession()

    # контекстный менеджер чтобы сессия корректно закрылась после завершения приложения
    async with app_storage['session']:
        await create_table()
        app = web.Application()

        app.add_routes([web.get('/weather', handle)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8080)
        await site.start()

        while True:
            await asyncio.sleep(3600)


if __name__ == '__main__':
    asyncio.run(main())
