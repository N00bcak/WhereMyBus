from telebot import asyncio_filters
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
import dotenv
import os
import datetime

# This file is responsible for setting up project-wide objects, constants, and reference dictionaries.

dotenv.load_dotenv()
BOT_TOKEN = os.getenv("BOT_API_TOKEN")
LTA_TOKEN = os.getenv("LTA_API_TOKEN")
storage_path = f"{os.path.dirname(__file__)}/../storage/"
bot = AsyncTeleBot(BOT_TOKEN, state_storage = StateMemoryStorage())
bot.add_custom_filter(asyncio_filters.StateFilter(bot))

sg_timezone = datetime.timezone(datetime.timedelta(hours = 8.0))

headers = {
    'AccountKey': LTA_TOKEN,
    'accept': 'application/json'
}

bus_types = {
    'SD': "Single",
    'DD': "Double",
    'BD': "Bendy"
}

# Given that I am using colored emojis, 
# TODO: Create an alternative for people with color deficiencies.
bus_load = {
    'SEA': "\U0001f7e9",
    'SDA': "\U0001f7e8",
    'LSD': 	"\U0001f7e5"
}
