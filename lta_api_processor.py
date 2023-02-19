from setup_constants import storage_path, sg_timezone, headers, bus_types, bus_load
import requests
import datetime
import telebot
import json
from haversine import haversine, Unit

def bus_est_arrival_min(time1: datetime.datetime) -> int:
    return round((time1 - datetime.datetime.now(tz = sg_timezone)).seconds / 60)

def get_bus_arrival_status(time1: datetime.datetime) -> str:
    if time1 < datetime.datetime.now(tz = sg_timezone):
        return "Gone"
    
    est = bus_est_arrival_min(time1)

    if not(est): return "Arriving Soon"
    
    return f"in {str(est)} min"

def bus_ordering(element):
    return int("".join([i for i in element['ServiceNo'] if i.isdigit()]))

def parse_arrival_data(bus_arrival_data: dict):
    result = ""
    if not('Services' in bus_arrival_data or len(bus_arrival_data['Services'])):
        return "I can't find this bus service. It is either that you entered the wrong bus station code, or the service might not be operating at this time."

    # Sort the bus services as per normal, but those with letterings go right after their counterparts without letters.
    for service in sorted(bus_arrival_data['Services'], key = bus_ordering):
        result += f"<b>Bus No. {service['ServiceNo']}</b>\n"
        for bus in [service['NextBus'], service['NextBus2'], service['NextBus3']]:
            if not bus['OriginCode']: continue 
            arrival_status = get_bus_arrival_status(datetime.datetime.fromisoformat(bus['EstimatedArrival']))
            result += f"{bus_types[bus['Type']]} {arrival_status} ({bus_load[bus['Load']]})\n"
        result += "\n"

    return result

def get_arrivals(station: str, bus: str) -> str:
    try:
        url = f"http://datamall2.mytransport.sg/ltaodataservice/BusArrivalv2?BusStopCode={station}" + \
            ("" if bus == "-1" else f"&ServiceNo={bus}")
        r = requests.get(url, headers = headers)
        bus_arrival_data = r.json()
        bus_arrival_data["last_updated"] = datetime.datetime.isoformat(datetime.datetime.now(tz = sg_timezone))
        
        with open(f"{storage_path}arrival_info/{station}.json", "w+") as f: 
            f.write(json.dumps(bus_arrival_data))
    except Exception as e:
        print(str(e))

def query_arrivals(station: str, bus: str) -> dict:
    # Lazily retrieve the arrival information for each service.
    bus_arrival_data = {}
    try:
        with open(f"{storage_path}arrival_info/{station}.json", "r") as f: 
            bus_arrival_data = json.loads(f.read()) 
        
        # If it's been about 15 seconds since we last updated this list, then retrieve the new list.
        # TODO: Figure out when LTA refreshes their data to be even lazier.
        if (datetime.datetime.now(tz = sg_timezone) - datetime.datetime.fromisoformat(bus_arrival_data["last_updated"])).seconds >= 15: 
            get_arrivals(station, bus)
            with open(f"{storage_path}arrival_info/{station}.json", "r") as f: 
                bus_arrival_data = json.loads(f.read())
    except FileNotFoundError:
        get_arrivals(station, bus)
        with open(f"{storage_path}arrival_info/{station}.json", "r") as f: 
            bus_arrival_data = json.loads(f.read())
    finally:
        if bus == "-1": return bus_arrival_data

        # Prune the unnecessary entries.
        for i in range(len(bus_arrival_data['Services']) - 1, -1, -1):
            if bus_arrival_data['Services'][i]['ServiceNo'] != bus: bus_arrival_data['Services'].pop(i)

        return bus_arrival_data

def display_arrivals(station: str, bus: str) -> str:
    bus_arrival_data = query_arrivals(station, bus)
    return parse_arrival_data(bus_arrival_data)
        

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
        url = f"http://datamall2.mytransport.sg/ltaodataservice/BusStops?$skip={query_count*500}"
        r = requests.get(url, headers = headers)
        resp = r.json()
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

def query_nearest_bus_stations(location: telebot.types.Location) -> dict:
    bus_station_dict = {}
    try:
        # TODO: Lazily update the list of bus stations daily.
        with open(f"{storage_path}bus_station_info.json", "r") as f:
            bus_station_dict = json.loads(f.read())

        # If it's been a day since we last updated this list, then retrieve the new list.
        if (datetime.datetime.now(tz = sg_timezone) - datetime.datetime.fromisoformat(bus_station_dict["last_updated"])).days >= 1: 
            get_all_bus_stations()
            with open(f"{storage_path}bus_station_info.json", "r") as f:
                bus_station_dict = json.loads(f.read())
    except FileNotFoundError as e:
        get_all_bus_stations()
        with open(f"{storage_path}bus_station_info.json", "r") as f:
            bus_station_dict = json.loads(f.read())
    finally:
        closest_neighbors = get_closest_bus_stations(location, bus_station_dict["bus_stops"])
        return closest_neighbors

def display_nearest_bus_stations(location: telebot.types.Location):
    closest_neighbors = query_nearest_bus_stations(location)
    result = f"Here is the arrival info of the nearest bus stations to you: \n\n{'=' * 20}\n\n"
    for neighbor_code, neighbor_name, dist in closest_neighbors:
        result = result + f"{neighbor_name} Station ({round(dist)}m away):\n{display_arrivals(neighbor_code, '-1')}{'=' * 20}\n\n"
    
    return result
