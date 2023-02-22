from src.setup_constants import storage_path, sg_timezone, headers, bus_types, bus_load
import requests
import datetime
import telebot
import json
from haversine import haversine, Unit

# Dictionaries
bus_route_dict = {
    "bus_routes": {}
}
# The below functions process bus arrival timings and display them in a readable format.

# TODO: Figure out a smarter way to determine is a bus is in operation or not.
# def request_bus_routes(skip: int) -> dict:
#     url = f"http://datamall2.mytransport.sg/ltaodataservice/BusRoutes?$skip={skip}"
#     r = requests.get(url, headers = headers)
#     return r.json()

# def get_all_bus_routes():
#     # Retrieves all the bus services from LTA.
#     bus_route_dict = {
#         "bus_routes": {}
#     }
#     resp = {}
#     query_count = 0
#     while("value" not in resp.keys() or len(resp["value"])):
#         resp = request_bus_routes(query_count * 500)
#         for svc in resp["value"]: bus_route_dict["bus_routes"][svc["ServiceNo"]] = []
#         for svc in resp["value"]: bus_route_dict["bus_routes"][svc["ServiceNo"]][svc["BusStopCode"]].append(svc)
#         query_count += 1

#     with open(f"{storage_path}bus_route_info.json", "w+") as f:
#         bus_route_dict["last_updated"] = datetime.datetime.isoformat(datetime.datetime.now(tz = sg_timezone))
#         f.write(json.dumps(bus_route_dict))
#         print("Great Success!")

# def load_from_storage_bus_routes():
#     with open(f"{storage_path}bus_route_info.json", "r") as f:
#         return json.loads(f.read())

# # We split the week into weekdays, saturdays, and sundays. Because LTA does as well.
# def is_weekday(weekday: int):
#     # According to ISO 8601, 1 is a Monday, 2 is a Tuesday, and so on until 7, which is a Sunday.
#     if weekday == 6: return 'SAT'
#     if weekday == 7: return 'SUN'
#     return 'WD'

# def bus_in_operation(station: str, bus: str):
#     global bus_route_dict

#     # Checks if a bus is in operation.
#     datetime_now = datetime.datetime.now(tz = sg_timezone)
#     weekday = datetime_now.isoweekday()
#     hhmm = datetime_now.strftime("%H%M")
#     try:
#         if not len(bus_route_dict["bus_routes"]): bus_route_dict = load_from_storage_bus_routes()
#         # If it's been a day since we last updated this list, then retrieve the new list.
#         if (datetime_now - datetime.datetime.fromisoformat(bus_route_dict["last_updated"])).days >= 1: 
#             get_all_bus_routes()
#             bus_route_dict = load_from_storage_bus_routes()
#     except FileNotFoundError:
#         get_all_bus_routes()
#         if not len(bus_route_dict["bus_routes"]): bus_route_dict = load_from_storage_bus_routes()
#     except Exception as e:
#         print(str(e))
#     finally:
#         first_bus = bus_route_dict["bus_routes"][bus][station][f"{is_weekday(weekday)}_FirstBus"]
#         last_bus = bus_route_dict["bus_routes"][bus][station][f"{is_weekday(weekday)}_LastBus"]

#         return not(int(last_bus) < int(hhmm) < int(first_bus))

def bus_est_arrival_min(time1: datetime.datetime) -> int:
    return round((time1 - datetime.datetime.now(tz = sg_timezone)).seconds / 60)

def get_bus_arrival_status(time1: datetime.datetime) -> str:
    # Strangely enough, the bus can be estimated to be gone when you query the API.
    # This is probably because:
    # - The bus actually left
    # - L + ratio + infrequent updates + bad bus timing
    # In order to preserve my social credits, I'm assuming the former.
    if time1 < datetime.datetime.now(tz = sg_timezone):
        return "Gone"
    
    est = bus_est_arrival_min(time1)

    if not(est): return "Arriving Soon"
    
    return f"{str(est)} min"

def bus_ordering(element):
    # This ordering ensures that services and their letter variants (e.g. 89 and 89e) will be displayed next to each other.
    return int("".join([i for i in element['ServiceNo'] if i.isdigit()]))

def parse_arrival_data(bus_arrival_data: dict):
    result = ""
    if not('Services' in bus_arrival_data or len(bus_arrival_data['Services'])):
        return "I can't find this bus service. Please check that you have not entered the wrong bus station code."

    for service in sorted(bus_arrival_data['Services'], key = bus_ordering):
        result += f"<b>Bus No. {service['ServiceNo']}</b>\n"
        # if 'NotOperational' in service:
        #     result += "Not Operating"
        #     continue
        
        for bus in [service['NextBus'], service['NextBus2'], service['NextBus3']]:
            if not bus['EstimatedArrival']: continue 
            arrival_status = get_bus_arrival_status(datetime.datetime.fromisoformat(bus['EstimatedArrival']))
            result += f"{bus_types[bus['Type']]} -- {arrival_status} {bus_load[bus['Load']]}"
            if bus['Feature'] == 'WAB': result += '\u267f'
            result += "\n"
        result += "\n"
    return result

def request_arrival_data(station: str, bus: str) -> dict:
    url = f"http://datamall2.mytransport.sg/ltaodataservice/BusArrivalv2?BusStopCode={station}" + \
            ("" if bus == "-1" else f"&ServiceNo={bus}")
    r = requests.get(url, headers = headers)
    return r.json()

def get_arrivals(station: str, bus: str) -> str:
    try:
        bus_arrival_data = request_arrival_data(station, bus)
        bus_arrival_data["last_updated"] = datetime.datetime.isoformat(datetime.datetime.now(tz = sg_timezone))
        
        # If many queries to the same bus station occur at the same time, (realistically, I'm going to be the only user, but let me dream, ok?)
        # We can answer all of them with a single API call.
        # This should hopefully keep us out of trouble.
        with open(f"{storage_path}arrival_info/{station}.json", "w+") as f: 
            f.write(json.dumps(bus_arrival_data))
    except Exception as e:
        print(str(e))

def load_from_storage_arrival_info(station: str) -> dict:
    with open(f"{storage_path}arrival_info/{station}.json", "r") as f: 
        return json.loads(f.read()) 

def query_arrivals(station: str, bus: str) -> dict:
    # Lazily retrieve the arrival information for each service.
    bus_arrival_data = {}
    try:
        bus_arrival_data = load_from_storage_arrival_info(station)
        
        # If it's been about 15 seconds since we last updated this list, then retrieve the new list.
        if (datetime.datetime.now(tz = sg_timezone) - datetime.datetime.fromisoformat(bus_arrival_data["last_updated"])).seconds >= 15: 
            get_arrivals(station, bus)
            bus_arrival_data = load_from_storage_arrival_info(station)
    except FileNotFoundError:
        get_arrivals(station, bus)
        bus_arrival_data = load_from_storage_arrival_info(station)
    finally:
        if bus == "-1": return bus_arrival_data
        for i in range(len(bus_arrival_data['Services']) - 1, -1, -1):
            # Prune all unnecessary entries.
            if bus_arrival_data['Services'][i]['ServiceNo'] != bus:
                bus_arrival_data['Services'].pop(i)


        return bus_arrival_data

def display_arrivals(station: str, bus: str) -> str:
    bus_arrival_data = query_arrivals(station, bus)
    return parse_arrival_data(bus_arrival_data)

def request_bus_station_data(skip: int = 0) -> dict:
    url = f"http://datamall2.mytransport.sg/ltaodataservice/BusStops?$skip={skip}"
    r = requests.get(url, headers = headers)
    return r.json()

def get_all_bus_stations():
    # Retrieves all the bus stations from LTA.
    bus_station_dict = {
        "bus_stops": []
    }
    # Because each query only returns 500 stations when there are CLEARLY WAY MORE than 500 stations...
    # We will have to uh. Spam the endpoint. (sorry not sorry)
    resp = {}
    query_count = 0
    while("value" not in resp.keys() or len(resp["value"])):
        resp = request_bus_station_data(query_count * 500)
        for stop in resp["value"]: bus_station_dict["bus_stops"].append(stop)
        query_count += 1
    with open(f"{storage_path}bus_station_info.json", "w+") as f:
        bus_station_dict["last_updated"] = datetime.datetime.isoformat(datetime.datetime.now(tz = sg_timezone))
        f.write(json.dumps(bus_station_dict))

def get_closest_bus_stations(location, bus_station_list, k = 3):
    tups = []
    caller_location = (location.latitude, location.longitude) # (lat, long)
    for bus_station in bus_station_list:
        bus_station_coords = (bus_station["Latitude"], bus_station["Longitude"])
        # Calculate the geographical distance with an ellipsoidal model of the earth yadi yada
        gps_distance = haversine(caller_location, bus_station_coords, unit = Unit.METERS)
        tups.append((bus_station["BusStopCode"], bus_station["Description"], gps_distance))

    # Sorts the tuples by the distance and returns the k nearest neighbors.
    return sorted(tups, key = lambda x: x[2])[0:k]

def load_from_storage_bus_stations() -> dict:
    with open(f"{storage_path}bus_station_info.json", "r") as f:
        return json.loads(f.read())

def query_nearest_bus_stations(location: telebot.types.Location) -> dict:
    bus_station_dict = {}
    try:
        bus_station_dict = load_from_storage_bus_stations()
        # If it's been a day since we last updated this list, then retrieve the new list.
        if (datetime.datetime.now(tz = sg_timezone) - datetime.datetime.fromisoformat(bus_station_dict["last_updated"])).days >= 1: 
            get_all_bus_stations()
        bus_station_dict = load_from_storage_bus_stations()
    except FileNotFoundError as e:
        get_all_bus_stations()
        bus_station_dict = load_from_storage_bus_stations()
    finally:
        closest_neighbors = get_closest_bus_stations(location, bus_station_dict["bus_stops"])
        return closest_neighbors

def display_nearest_bus_stations(location: telebot.types.Location):
    closest_neighbors = query_nearest_bus_stations(location)
    result = f"Here is the arrival info of the nearest bus stations to you: \n\n{'=' * 20}\n\n"
    for neighbor_code, neighbor_name, dist in closest_neighbors:
        result = result + f"{neighbor_name} Station ({round(dist)}m away):\n{display_arrivals(neighbor_code, '-1')}{'=' * 20}\n\n"
    
    return result
