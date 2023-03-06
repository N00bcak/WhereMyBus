from telebot.asyncio_handler_backends import State, StatesGroup
import asyncio
import re
from src import lta_api_processor
from src.setup_constants import bot
import datetime

# Handles command states for the /bus command, which allows me to get input from the user via a dialogue.
class ArrivalCommandStates(StatesGroup):
    station = State()
    bus = State()

@bot.message_handler(commands = ['start'])
async def say_hi(message):
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_chat_action(message.chat.id, 'typing')
    await bot.reply_to(message, f"Hello! I'm a bot that can help you get the latest bus timings!\nType /bus to get the bus timings for a certain stop!\nSend me your location to get info on all the bus stations closest to you! (We don't track your data!)")

# The user sent us their location.
@bot.message_handler(content_types = ['location'])
async def get_nearest_bus_station_info(message):
    await bot.send_chat_action(message.chat.id, 'typing')
    await bot.reply_to(message, lta_api_processor.display_nearest_bus_stations(message.location), parse_mode = "HTML")

# The user is asking about a certain bus
@bot.message_handler(state = "*", commands='bus')
async def get_bus_station(message):
    await bot.set_state(message.from_user.id, ArrivalCommandStates.station, message.chat.id)
    await bot.send_message(message.chat.id, "What is your bus stop code?")

@bot.message_handler(state = ArrivalCommandStates.station)
async def get_bus(message):
    msg_txt = message.text
    # A bus stop code is definitely 5 digits. 
    # Unless the user is trying to mess with me.
    try:
        result = re.search(r"\d{5}", msg_txt)
        station = msg_txt[result.start():result.end()]
    except Exception as e:
        print(str(e))
        await bot.reply_to(message, "I couldn't find a valid bus station :<")
        await bot.delete_state(message.from_user.id, message.chat.id)
        return

    await bot.set_state(message.from_user.id, ArrivalCommandStates.bus, message.chat.id)
    # Now we ask them for the bus number, which should be some sequence of digits and maybe a letter at the back. 
    # Unless the user is trying to mess with me.
    await bot.send_message(message.chat.id, "Which bus number? ('A' for all)")
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['arrival_station'] = station

@bot.message_handler(state = ArrivalCommandStates.bus)
async def retrieve_info(message):
    msg_txt = message.text
    try:
        if msg_txt == "A":
            bus = "-1"
        else:
            result = re.search(r"\d+[a-zA-Z]?", message.text)
            bus = msg_txt[result.start():result.end()]
    except Exception as e:
        print(str(e))
        await bot.reply_to(message, "I couldn't find a valid bus number :<")
        return
    
    # Now we can trigger the process to get arrival timings.
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        await bot.send_chat_action(message.chat.id, 'typing')
        await bot.send_message(message.chat.id, lta_api_processor.display_arrivals(data['arrival_station'], bus), parse_mode = "HTML")
        await bot.delete_state(message.from_user.id, message.chat.id)

async def bot_setup():
    await asyncio.gather(lta_api_processor.query_static_data(),
                            bot.infinity_polling())

asyncio.run(bot_setup())