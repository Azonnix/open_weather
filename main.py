import asyncio
import aiosqlite
import json
from aiohttp import ClientSession, web
from aiologger.loggers.json import JsonLogger
from datetime import datetime


logger = JsonLogger.with_default_handlers(
    level='DEBUG',
    serializer_kwargs={'ensure_ascii': False},
)


app_storage = {}


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

    async with app_storage['session'].get(url=url, params=params) as response:
        weather_json = await response.json()
        try:
            return weather_json["weather"][0]["main"]
        except KeyError:
            return 'Нет данных'


async def get_translation(text, source, target):
    # await logger.info(f'Поступил запрос на перевод слова: {text}')

    url = 'https://libretranslate.de/translate'
    data = {'q': text, 'source': source, 'target': target, 'format': 'text'}

    async with app_storage['session'].post(url, json=data) as response:
        translate_json = await response.json()

        try:
            return translate_json['translatedText']
        except KeyError:
            return text


async def handle(request):
    city_ru = request.rel_url.query['city']

    # await logger.info(f'Поступил запрос на город: {city_ru}')

    city_en = await get_translation(city_ru, 'ru', 'en')
    weather_en = await get_weather(city_en)
    weather_ru = await get_translation(weather_en, 'en', 'ru')

    result = {'city': city_ru, 'weather': weather_ru}

    await save_to_db(city_ru, weather_ru)

    return web.Response(text=json.dumps(result, ensure_ascii=False))


async def main():
    app_storage['session'] = ClientSession()

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


if __name__ == "__main__":
    asyncio.run(main())

# import time
# import requests
#
#
# def get_weather(city):
#     url = f'http://api.openweathermap.org/data/2.5/weather'
#     params = {'q': city, 'APPID': '2a4ff86f9aaa70041ec8e82db64abf56'}
#
#     weather_json = requests.get(url=url, params=params).json()
#     print(f'{city}: {weather_json["weather"][0]["main"]}')
#
#
# def main(cities_):
#     for city in cities_:
#         get_weather(city)
#
#
# cities = ['Moscow', 'St. Petersburg', 'Rostov-on-Don', 'Kaliningrad', 'Vladivostok',
#           'Minsk', 'Beijing', 'Delhi', 'Istanbul', 'Tokyo', 'London', 'New York']
#
# print(time.strftime('%X'))
#
# main(cities)
#
# print(time.strftime('%X'))
