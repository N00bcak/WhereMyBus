from telebot.asyncio_handler_backends import State, StatesGroup
import asyncio
import re
from src import lta_api_processor, lta_api_interface, favorites_db, lta_api_utils
from src.favorites_db import NoFavoriteStationsException, BusStationNotExistsException
from src.setup_constants import bot
from telebot.util import quick_markup
import datetime

async def parse_bus_station_code(message):
    # A bus stop code is definitely 5 digits. 
    # Unless the user is trying to mess with me.
    msg_txt = message.text
    try:
        result = re.search(r"\d{5}", msg_txt)
        station = msg_txt[result.start():result.end()]
        return station
    except Exception as e:
        print(str(e))
        await bot.reply_to(message, "I couldn't find a valid bus station :<")
        await bot.delete_state(message.from_user.id, message.chat.id)
        return None


# Handles command states for the /bus command, which allows me to get input from the user via a dialogue.
class ArrivalCommandStates(StatesGroup):
    station = State()
    bus = State()

class FavoriteCommandStates(StatesGroup):
    add = State()
    delete = State()

# start command

@bot.message_handler(commands = ['start'])
async def say_hi(message):
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_chat_action(message.chat.id, 'typing')
    await bot.reply_to(message, f"Hello! I'm a bot that can help you get the latest bus timings!\nType /help for more information!")

@bot.message_handler(commands = ['help'])
async def give_help(message):

    help_message = """<b>What are my commands?</b>
                    /start - Pokes me >:(
                    /help - See this help message! :D

                    (The below commands may require a 5-digit bus station code you can find at the bus stops themselves or on Google.)
                    /bus - Get the latest bus arrival information from me!
                    /fav_bus - Get the latest bus arrivals on your FAVORITE bus stops! :D
                    /see_fav - See all your favorite bus stops and their codes!
                    /add_fav - Add a bus station to your favorites!
                    /del_fav - Remove a bus station from your favorites!

                    <b>What else can I do?</b>
                    If you send me your location, I will find the three (3) closest bus stations to you, and tell you their arrival information!
                    """.replace("    ","")

    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_chat_action(message.chat.id, 'typing')
    await bot.reply_to(message, help_message, 
                    parse_mode = "HTML")

# Location was sent.

@bot.message_handler(content_types = ['location'])
async def arrival_get_nearest_bus_station_info(message):
    await bot.send_chat_action(message.chat.id, 'typing')
    refresh_markup = quick_markup({
        "Refresh": {"callback_data": f"refresh_nearest_arrivals,{message.location}"}
    })
    await bot.send_message(message.chat.id, 
                    lta_api_processor.display_nearest_bus_stations(message.location), 
                    parse_mode = "HTML", 
                    reply_markup = refresh_markup 
                    )

# bus command

@bot.message_handler(commands='bus')
async def arrival_get_bus_station(message):
    await bot.set_state(message.from_user.id, ArrivalCommandStates.station, message.chat.id)
    await bot.send_message(message.chat.id, "What is your bus stop code?")

@bot.message_handler(state = ArrivalCommandStates.station)
async def arrival_get_bus(message):
    station = await parse_bus_station_code(message)

    if not lta_api_utils.get_station_name(station):
        await bot.send_message(message.chat.id, "I couldn't find a valid bus station :<")
        await bot.delete_state(message.from_user.id, message.chat.id)
        return

    await bot.set_state(message.from_user.id, ArrivalCommandStates.bus, message.chat.id)
    # Now we ask them for the bus number, which should be some sequence of digits and maybe a letter at the back. 
    # Unless the user is trying to mess with me.
    await bot.send_message(message.chat.id, "Which bus number? ('A' for all)")
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['arrival_station'] = station

@bot.message_handler(state = ArrivalCommandStates.bus)
async def arrival_retrieve_info(message):
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

        refresh_markup = quick_markup({
            "Refresh": {"callback_data": f"refresh_display_arrivals,{data['arrival_station']},{bus}"}
        })
        text = lta_api_processor.display_arrivals(data['arrival_station'], bus)
        if not text:
            text = "I can't find this bus service. Please check that you have not entered the wrong bus station code."
            refresh_markup = {}
        await bot.send_message(message.chat.id, text,
                            parse_mode = "HTML",
                            reply_markup = refresh_markup
                            )
        await bot.delete_state(message.from_user.id, message.chat.id)

# add_favorite command
@bot.message_handler(commands = ['add_fav','add_favorite'])
async def add_favorite_get_bus_station(message):
    await bot.set_state(message.from_user.id, FavoriteCommandStates.add, message.chat.id)
    await bot.send_message(message.chat.id, "Which bus stop code would you like to favorite?")

@bot.message_handler(state = FavoriteCommandStates.add)
async def add_favorite_bus_station(message):
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_chat_action(message.chat.id, 'typing')
    station = await parse_bus_station_code(message)
    try:
        station_name = favorites_db.add_favorite(message.from_user.id, station)
        await bot.send_message(message.chat.id, f"I've added {station_name} to your list of favorites!")
    except BusStationNotExistsException:
        await bot.send_message(message.chat.id, f"I couldn't find that bus station :<.\nPlease check that you haven't entered the wrong code.")
    
    
# del_favorite command
@bot.message_handler(commands = ['del_fav','del_favorite', 'delete_fav', 'delete_favorite'])
async def delete_favorite_get_bus_station(message):
    await bot.set_state(message.from_user.id, FavoriteCommandStates.delete, message.chat.id)
    try:
        favorites_db.check_favorites(message.from_user.id)
    except NoFavoriteStationsException:
        await bot.send_message(message.chat.id, "Hmm, you don't seem to have any favorite bus stations. Use /add_fav to add some!")
    else:
        await bot.send_message(message.chat.id, f"Which bus stop code would you like to remove from your favorites?")

@bot.message_handler(state = FavoriteCommandStates.delete)
async def delete_favorite_bus_station(message):
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_chat_action(message.chat.id, 'typing')
    station = await parse_bus_station_code(message)
    try:
        station_name = favorites_db.delete_favorite(message.from_user.id, station)
        await bot.send_message(message.chat.id, f"I've removed {station_name} from your list of favorites!")
    except NoFavoriteStationsException:
        await bot.send_message(message.chat.id, "Hmm, you don't seem to have any favorite bus stations. Use /add_fav to add some!")

# see_favorites command
@bot.message_handler(commands = ['favorites', 'see_fav', 'see_faves', 'show_favorites'])
async def show_favorite_bus_stations(message):
    await bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        station_list = favorites_db.get_favorites(message.from_user.id)
        await bot.send_message(message.chat.id, lta_api_processor.display_multiple_station_names(station_list), 
                            parse_mode = "HTML"
                            )
    except NoFavoriteStationsException:
        await bot.send_message(message.chat.id, "Hmm, you don't seem to have any favorite bus stations. Use /add_fav to add some!")

# show_favorites command
@bot.message_handler(commands = ['favorite_arrivals', 'fav_arrivals', 'fav_bus'])
async def show_favorite_bus_station_arrivals(message):
    await bot.send_chat_action(message.chat.id, 'typing')
    try:
        station_list = favorites_db.get_favorites(message.from_user.id)
        button_dict = {}
        for station_code in station_list:
            button_dict[f"{lta_api_utils.get_station_name(station_code)}({station_code})"] = {'callback_data': f"station,{station_code}"}
        station_markup = quick_markup(button_dict)
        await bot.send_message(message.chat.id, "Tap on the buttons to get the arrival times for each station!", 
                            parse_mode = "HTML",
                            reply_markup = station_markup)
    except NoFavoriteStationsException:
        await bot.send_message(message.chat.id, "Hmm, you don't seem to have any favorite bus stations. Use /add_fav to add some!")

@bot.callback_query_handler(lambda query: "station" in query.data)
async def print_station(query):
    message = query.message
    data = query.data.split(',')
    station_code = data[1]
    markup = quick_markup({
            'Refresh': {'callback_data': f"refresh_display_arrivals,{data[1]},-1"}
    })
    await bot.send_message(message.chat.id, lta_api_processor.display_arrivals(data[1], "-1"),
                        parse_mode = 'HTML',
                        reply_markup = markup)


@bot.callback_query_handler(lambda query: "refresh" in query.data)
async def refresh_message(query):

    # Unfortunately we have to work around the limitations of Telegram's InlineKeyboardButtons to provide the same querying ability.
    message = query.message
    data = query.data.split(',')
    if data[0] == 'refresh_display_arrivals':
        text = lta_api_processor.display_arrivals(data[1], data[2])
        markup = quick_markup({
            'Refresh': {'callback_data': f"refresh_display_arrivals,{data[1]},{data[2]}"}
        })
    elif data[0] == 'refresh_nearest_arrivals':
        text = lta_api_processor.display_nearest_bus_stations(data[1]),
        markup = quick_markup({
            "Refresh": {"callback_data": f"refresh_nearest_arrivals,{data[1]}"}
        })
    
    chat_id = message.chat.id
    await bot.delete_message(message.chat.id, message.id)
    await bot.send_message(chat_id, text,
                            parse_mode = "HTML", 
                            reply_markup = markup)

async def bot_setup():
    await asyncio.gather(lta_api_interface.query_static_data(),
                            bot.infinity_polling())

asyncio.run(bot_setup())