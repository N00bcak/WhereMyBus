from telebot.asyncio_handler_backends import State, StatesGroup
import asyncio
import re
import lta_api_processor
from setup_constants import bot

class BusCommandStates(StatesGroup):
    station = State()
    bus = State()

@bot.message_handler(commands=['start'])
async def say_hi(message):
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.reply_to(message, "Hello!")


@bot.message_handler(state = "*", commands='bus')
async def get_bus_station(message):
    await bot.set_state(message.from_user.id, BusCommandStates.station, message.chat.id)
    await bot.send_message(message.chat.id, "What is your bus stop code?")
    a = await bot.get_state(message.from_user.id)
    print(a)

@bot.message_handler(state = BusCommandStates.station)
async def get_bus(message):
    msg_txt = message.text
    # A bus stop code is definitely 5 digits. Unless the user is trying to mess with me.
    try:
        result = re.search(r"\d{5}", msg_txt)
        station = int(msg_txt[result.start():result.end()])
    except Exception as e:
        print(str(e))
        await bot.reply_to(message, "I couldn't find a valid bus station :<")
        await bot.delete_state(message.from_user.id, message.chat.id)
        return

    await bot.set_state(message.from_user.id, BusCommandStates.bus, message.chat.id)
    # Now we ask them for the bus number, which should be some sequence of digits. Unless the user is trying to mess with me.
    await bot.send_message(message.chat.id, "Which bus number? ('A' for all)")
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['station'] = message.text

@bot.message_handler(state = BusCommandStates.bus)
async def retrieve_info(message):
    msg_txt = message.text
    try:
        if msg_txt == "A":
            bus = -1
        else:
            result = re.search(r"\d+", message.text)
            bus = int(msg_txt[result.start():result.end()])
    except Exception as e:
        print(str(e))
        await bot.reply_to(message, "I couldn't find a valid bus number :<")
        return
    
    # Now we can trigger the process to get arrival timings.
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        await bot.send_message(message.chat.id, lta_api_processor.query_arrival(data['station'], bus), parse_mode = "HTML")
        await bot.delete_state(message.from_user.id, message.chat.id)

asyncio.run(bot.infinity_polling())