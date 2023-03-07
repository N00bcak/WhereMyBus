from src.setup_constants import headers, storage_path, sg_timezone
import src.lta_api_utils as utils
import requests
import datetime
import asyncio
import json

# These functions directly interact or control scheduled interactions with the LTA API.
def request_bus_routes(skip: int) -> dict:
    url = f"http://datamall2.mytransport.sg/ltaodataservice/BusRoutes?$skip={skip}"
    r = requests.get(url, headers = headers)
    return r.json()

def request_arrival_data(station: str, bus: str) -> dict:
    url = f"http://datamall2.mytransport.sg/ltaodataservice/BusArrivalv2?BusStopCode={station}" + \
            ("" if bus == "-1" else f"&ServiceNo={bus}")
    r = requests.get(url, headers = headers)
    return r.json()

def request_bus_station_data(skip: int = 0) -> dict:
    url = f"http://datamall2.mytransport.sg/ltaodataservice/BusStops?$skip={skip}"
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

def get_all_bus_operation_times():
    # Retrieves all the bus operation times by station from LTA.
    
    # We only ever run this function after get_all_bus_stations, therefore we can skip the try except clause.
    bus_station_codes = [station["BusStopCode"] for station in utils.load_from_storage_bus_stations()["bus_stops"]]
    
    bus_operation_dict = {
        "operation_times" : {}
    }
    for station_code in bus_station_codes: bus_operation_dict["operation_times"][station_code] = {}

    resp = {}
    query_count = 0
    while("value" not in resp.keys() or len(resp["value"])):
        resp = request_bus_routes(query_count * 500)
        for svc in resp["value"]: 
            bus_operation_dict["operation_times"][svc["BusStopCode"]][svc["ServiceNo"]] = svc
        query_count += 1

    with open(f"{storage_path}bus_operation_info.json", "w+") as f:
        bus_operation_dict["last_updated"] = datetime.datetime.isoformat(datetime.datetime.now(tz = sg_timezone))
        f.write(json.dumps(bus_operation_dict))

def refresh_static_data():
    return
    get_all_bus_stations()
    get_all_bus_operation_times()


async def query_static_data():
    # In this function, we lazily query the "static" data inherent to the public bus system in SG.
    # As one can expect, this includes information like bus stops and bus operation timings.
    while True:
        # TODO: Devise a way to integrate both get_all_bus_stations and get_all_bus_operation_times without too much clutter.
        print("Refreshing bus network information...")
        refresh_static_data()
        print("Done!")
        
        tmwdatetime = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days = 1), datetime.time())
        wait_sec = datetime.timedelta(seconds = (tmwdatetime - datetime.datetime.now()).seconds, microseconds = (tmwdatetime - datetime.datetime.now()).microseconds)
        await asyncio.sleep(wait_sec.seconds + wait_sec.microseconds / 1000000)