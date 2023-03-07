from src.setup_constants import sg_timezone, bus_types, bus_load
import src.lta_api_utils as utils 
import src.lta_api_interface as interface
import datetime
import telebot
import json
from haversine import haversine, Unit

# Most of the computational heavy-lifting and dictionary processing is done here.

def bus_in_operation(station: str, bus: str):
    # Checks if a bus is in operation.
    datetime_now = datetime.datetime.now(tz = sg_timezone)
    weekday = datetime_now.isoweekday()
    hhmm = int(datetime_now.strftime("%H%M"))
    try:
        bus_operation_dict = utils.load_from_storage_bus_operation_times()
    except FileNotFoundError:
        interface.refresh_static_data()
        bus_operation_dict = utils.load_from_storage_bus_operation_times()
    except Exception as e:
        print(str(e))
    finally:
        arrival_data = bus_operation_dict["operation_times"][station][bus]
        first_bus = int(arrival_data[f"{utils.is_weekday(weekday)}_FirstBus"])
        last_bus = int(arrival_data[f"{utils.is_weekday(weekday)}_LastBus"])
        if last_bus < first_bus: last_bus += 2400
        return first_bus < hhmm and hhmm < last_bus

def get_bus_arrival_status(time1: datetime.datetime) -> str:
    # Strangely enough, the bus can be estimated to be gone when you query the API.
    # This is probably because:
    # - The bus actually left
    # - L + ratio + infrequent updates + bad bus timing
    # Due to negative experiences with bus timings I am now assuming the latter.  
    datetime_now = datetime.datetime.now(tz = sg_timezone)  
    est = utils.bus_est_arrival_min(time1)

    if est <= 0 or time1 < datetime_now: return "Arriving Soon"
    
    return f"{str(est)} min"

def parse_arrival_data(bus_arrival_data: dict, bus_operation_data: dict, bus: str):
    result = ""
    if bus != "-1" and not(bus in bus_operation_data):
        return "I can't find this bus service. Please check that you have not entered the wrong bus station code."
    services = bus_arrival_data['Services']
    for service_no in sorted(bus_operation_data.keys(), key = utils.bus_ordering):
        service = {}
        for i in services:
            if i['ServiceNo'] == service_no: 
                service = i
                break
        
        result += f"<b>Bus No. {service_no}</b>\n"
        
        if not bus_in_operation(bus_arrival_data['BusStopCode'], service_no) or service == {}:
            result += "This bus is not operational at this moment.\n\n"
            continue

        for bus in [service['NextBus'], service['NextBus2'], service['NextBus3']]:
            if not bus['EstimatedArrival']: continue 
            arrival_status = get_bus_arrival_status(datetime.datetime.fromisoformat(bus['EstimatedArrival']))
            result += f"{bus_types[bus['Type']]} -- {arrival_status} {bus_load[bus['Load']]}"
            if bus['Feature'] == 'WAB': result += '\u267f'
            result += "\n"
        result += "\n"
    return result

def query_arrivals(station: str, bus: str) -> dict:
    # Lazily retrieve the arrival information for each service.
    bus_arrival_data = {}
    bus_operation_data = {}
    try:
        bus_arrival_data = utils.load_from_storage_arrival_info(station)
        # If it's been about 10 seconds since we last updated this list, then retrieve the new list.
        if (datetime.datetime.now(tz = sg_timezone) - datetime.datetime.fromisoformat(bus_arrival_data["last_updated"])).seconds >= 10: 
            interface.get_arrivals(station, bus)
            bus_arrival_data = utils.load_from_storage_arrival_info(station)
    except FileNotFoundError:
        interface.get_arrivals(station, bus)
        bus_arrival_data = utils.load_from_storage_arrival_info(station)
    finally:
        if bus == "-1": return bus_arrival_data
        for i in range(len(bus_arrival_data['Services']) - 1, -1, -1):
            # Prune all unnecessary entries.
            if bus_arrival_data['Services'][i]['ServiceNo'] != bus:
                bus_arrival_data['Services'].pop(i)

        return bus_arrival_data

def display_arrivals(station: str, bus: str) -> str:
    bus_arrival_data = query_arrivals(station, bus)
    bus_operation_data = utils.load_from_storage_bus_operation_times()["operation_times"][station]
    return parse_arrival_data(bus_arrival_data, bus_operation_data, bus)

def display_arrivals_multiple_stations(station_list) -> str:
    
    result = f"Here is the arrival info of your favorite stations: \n\n{'=' * 20}\n\n"
    for station in station_list:
        result = result + f"{utils.get_station_name(station)} Station:\n{display_arrivals(station, '-1')}{'=' * 20}\n\n"
    return result
    
def display_multiple_station_names(station_list):
    result = f"Here are your favorite stations: \n\n{'=' * 20}\n\n"
    for station in station_list:
        result = result + f"- {utils.get_station_name(station)} Station (Code: {station})\n"
    return result

def get_closest_bus_stations(location: telebot.types.Location, bus_station_list: dict, k: int = 3):
    tups = []
    caller_location = (location.latitude, location.longitude) # (lat, long)
    for bus_station in bus_station_list:
        bus_station_coords = (bus_station["Latitude"], bus_station["Longitude"])
        # Calculate the geographical distance with an ellipsoidal model of the earth yadi yada
        gps_distance = haversine(caller_location, bus_station_coords, unit = Unit.METERS)
        tups.append((bus_station["BusStopCode"], bus_station["Description"], gps_distance))

    # Sorts the tuples by the distance and returns the k nearest neighbors.
    return sorted(tups, key = lambda x: x[2])[0:k]

def query_nearest_bus_stations(location: telebot.types.Location) -> dict:
    bus_station_dict = {}
    try:
        bus_station_dict = utils.load_from_storage_bus_stations()
    except FileNotFoundError as e:
        interface.refresh_static_data()
        bus_station_dict = utils.load_from_storage_bus_stations()
    finally:
        closest_neighbors = get_closest_bus_stations(location, bus_station_dict["bus_stops"])
        return closest_neighbors

def display_nearest_bus_stations(location: telebot.types.Location):
    closest_neighbors = query_nearest_bus_stations(location)
    result = f"Here is the arrival info of the nearest bus stations to you: \n\n{'=' * 20}\n\n"
    for neighbor_code, neighbor_name, dist in closest_neighbors:
        result = result + f"{neighbor_name} Station ({round(dist)}m away):\n{display_arrivals(neighbor_code, '-1')}{'=' * 20}\n\n"
    
    return result
