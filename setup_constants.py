from telebot import asyncio_filters
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
import dotenv
import os
import datetime

dotenv.load_dotenv()
BOT_TOKEN = os.getenv("BOT_API_TOKEN")
LTA_TOKEN = os.getenv("LTA_API_TOKEN")
storage_path = f"{os.path.dirname(__file__)}/storage/"
bot = AsyncTeleBot(BOT_TOKEN, state_storage = StateMemoryStorage())
bot.add_custom_filter(asyncio_filters.StateFilter(bot))

sg_timezone = datetime.timezone(datetime.timedelta(hours = 8.0))

headers = {
    'AccountKey': LTA_TOKEN,
    'accept': 'application/json'
}

bus_types = {
    'SD': "Single Decker",
    'DD': "Double Decker",
    'BD': "Bendy"
}

bus_load = {
    'SEA': "Seats Available",
    'SDA': "Limited Seats",
    'LSD': "Almost Full, wait for the next bus!"
}
