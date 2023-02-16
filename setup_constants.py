from telebot import asyncio_filters
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
import dotenv
import os

dotenv.load_dotenv()
BOT_TOKEN = os.getenv("BOT_API_TOKEN")
LTA_TOKEN = os.getenv("LTA_API_TOKEN")

bot = AsyncTeleBot(BOT_TOKEN, state_storage = StateMemoryStorage())
bot.add_custom_filter(asyncio_filters.StateFilter(bot))

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
