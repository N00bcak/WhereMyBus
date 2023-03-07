from src.setup_constants import sg_timezone, storage_path
import datetime
import json


# Functions auxiliary to those in lta_api_processor.py.

def load_from_storage_bus_operation_times():
    with open(f"{storage_path}bus_operation_info.json", "r") as f:
        return json.loads(f.read())

def load_from_storage_bus_stations() -> dict:
    with open(f"{storage_path}bus_station_info.json", "r") as f:
        return json.loads(f.read())

def load_from_storage_arrival_info(station: str) -> dict:
    with open(f"{storage_path}arrival_info/{station}.json", "r") as f: 
        return json.loads(f.read())

# We split the week into weekdays, saturdays, and sundays. Because LTA does as well.
def is_weekday(weekday: int):
    # According to ISO 8601, 1 is a Monday, 2 is a Tuesday, and so on until 7, which is a Sunday.
    if weekday == 6: return 'SAT'
    if weekday == 7: return 'SUN'
    return 'WD'

def bus_est_arrival_min(time1: datetime.datetime) -> int:
    return round((time1 - datetime.datetime.now(tz = sg_timezone)).seconds / 60)

def bus_ordering(element):
    # This ordering ensures that services and their letter variants (e.g. 89 and 89e) will be displayed next to each other.
    return int("".join([i for i in element if i.isdigit()]))

def get_station_name(station_code: str):
    bus_station_dict = {}
    try:
        bus_station_dict = load_from_storage_bus_stations()
    except FileNotFoundError as e:
        interface.refresh_static_data()
        bus_station_dict = load_from_storage_bus_stations()
    finally:
        for station_info in bus_station_dict["bus_stops"]:
            if station_info["BusStopCode"] == station_code: return station_info["Description"]