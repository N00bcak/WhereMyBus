from setup_constants import headers, bus_types, bus_load
import requests
import datetime


def get_bus_arrival_status(time1: datetime.datetime, fmt: str) -> str:
    sg_timezone = datetime.timezone(datetime.timedelta(hours = 8.0))
    if time1 < datetime.datetime.now(tz = sg_timezone):
        return "Gone"
    est = (time1 - datetime.datetime.now(tz = sg_timezone)).seconds // 60
    
    if not(est): return "Arriving Soon"
    
    return f"in {str(est)} min"

def parse_arrival_data(bus_arrival_data: dict):
    result = ""
    if not(len(bus_arrival_data['Services'])):
        return "Did you key in the wrong bus station code or bus service? I can't find anything."

    for service in bus_arrival_data['Services']:
        result += f"<b>Bus No. {service['ServiceNo']}</b>\n"
        for bus in [service['NextBus'], service['NextBus2'], service['NextBus3']]:
            if not bus['OriginCode']: continue 
            arrival_status = get_bus_arrival_status(datetime.datetime.fromisoformat(bus['EstimatedArrival']), "%M")
            result += f"{bus_types[bus['Type']]} {arrival_status} ({bus_load[bus['Load']]})\n"
        result += "\n"

    return result

def query_arrival(station: int, bus: int) -> str:
    url = f"http://datamall2.mytransport.sg/ltaodataservice/BusArrivalv2?BusStopCode={station}" + \
        ("" if bus == -1 else f"&ServiceNo={bus}")
    try:
        r = requests.get(url, headers=headers)
        bus_arrival_data = r.json()
        return parse_arrival_data(bus_arrival_data)
    except Exception as e:
        return f"Oops! Something went wrong... I guess.\n Debug: {str(e)}"