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

# Handles command states for the /alertnextbus command.
class AlertCommandStates(StatesGroup):
    station = State()
    bus = State()

@bot.message_handler(commands = ['start'])
async def say_hi(message):
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.reply_to(message, f"Hello! I'm a bot that can help you get the latest bus timings!\nType /bus to get the bus timings for a certain stop!\nSend me your location to get info on all the bus stations closest to you! (We don't track your data!)")

# The user sent us their location.
@bot.message_handler(content_types = ['location'])
async def get_nearest_bus_station_info(message):
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
        await bot.send_message(message.chat.id, lta_api_processor.display_arrivals(data['arrival_station'], bus), parse_mode = "HTML")
        await bot.delete_state(message.from_user.id, message.chat.id)

@bot.message_handler(commands = ['nextbusalert'])
async def remind_me_bus(message):
    # Retrieves the arrival time of a bus, and sets a timer for a message to be sent to the user.
    await bot.set_state(message.from_user.id, AlertCommandStates.station, message.chat.id)
    await bot.send_message(message.chat.id, "Which bus stop do you want me to look out for?")

# TODO: Think of how to merge the duplicate functions below with the previous ones. For future, refactoring me. >:)
@bot.message_handler(state = AlertCommandStates.station)
async def alert_get_bus(message):
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

    await bot.set_state(message.from_user.id, AlertCommandStates.bus, message.chat.id)
    # Now we ask them for the bus number, which should be some sequence of digits and maybe a letter at the back. 
    # Unless the user is trying to mess with me.
    await bot.send_message(message.chat.id, "Which bus service should I look out for?")
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['alert_station'] = station

@bot.message_handler(state = AlertCommandStates.bus)
async def set_alert(message):
    msg_txt = message.text
    try:
        result = re.search(r"\d+[a-zA-Z]?", message.text)
        bus = msg_txt[result.start():result.end()]
    except Exception as e:
        print(str(e))
        await bot.reply_to(message, "I couldn't find a valid bus number :<")
        return
    
    # Now we set an alarm for the next bus.
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        station = data['alert_station']
        bus_arrival_data = lta_api_processor.query_arrivals(station, bus)
        bus_service = bus_arrival_data['Services'][0]
        for arrival in [bus_service['NextBus'], bus_service['NextBus2'], bus_service['NextBus3']]:
            if not arrival['OriginCode']: continue 
            bus_est = lta_api_processor.bus_est_arrival_min(datetime.datetime.fromisoformat(arrival['EstimatedArrival']))
            if bus_est > 2:
                break

    await bot.send_message(message.chat.id, f"I set an alarm for the next arrival of bus {bus} at station {station} :D\nYou will be notified 2 minutes before the bus is slated to arrive.")

    await asyncio.sleep((bus_est - 2) * 60)
    await bot.send_message(message.chat.id, f"Your bus {bus} is arriving at station {station} soon!")
    await bot.delete_state(message.from_user.id, message.chat.id)

asyncio.run(bot.infinity_polling())