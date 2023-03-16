import sqlite3
from src.setup_constants import storage_path
from src import lta_api_processor, lta_api_utils

class NoFavoriteStationsException(Exception):
    "You don't seem to have any favorites!"
    pass

class BusStationNotExistsException(Exception):
    "The requested bus station does not exist!"
    pass

# This file handles the database work behind the favorites command.

def start_db():
    db = sqlite3.connect(f"{storage_path}favorites.db")
    cur = db.cursor()
    db_list = [i[0] for i in cur.execute('''SELECT name FROM sqlite_master''').fetchall()]

    if "favorite" not in db_list:
        cur.execute("CREATE TABLE favorite (id, station_list)")
    
    db.commit()

    return db, cur

def add_favorite(user_id: str, station: str):

    db, cur = start_db()

    user = cur.execute("SELECT * FROM favorite WHERE id = ?", (user_id,)).fetchone()

    if not lta_api_utils.get_station_name(station):
        raise BusStationNotExistsException

    if not user:
        cur.execute("INSERT INTO favorite (id, station_list) VALUES (?,?)", (user_id, station))
    elif station in user[1]:
        pass
    else:
        station_csv = f"{user[1]}{',' if len(user[1]) else ''}{station}"
        cur.execute("UPDATE favorite SET station_list = ? WHERE id = ?", (station_csv, user_id))
    
    db.commit()
    db.close()

    return lta_api_utils.get_station_name(station)

def delete_favorite(user_id: str, station: str):
    db, cur = start_db()
    user = cur.execute("SELECT * FROM favorite WHERE id = ?", (user_id,)).fetchone()
    if not(user and len(user[1])):
        raise NoFavoriteStationsException
    else:
        station_csv = user[1]
        station_csv = station_csv.replace(station, "").replace(",,", ",")
        if len(station_csv) and station_csv[-1] == ",": station_csv = station_csv[:-1]
        cur.execute("UPDATE favorite SET station_list = ? WHERE id = ?", (station_csv, user_id))
    db.commit()
    db.close()

    return lta_api_utils.get_station_name(station)

def check_favorites(user_id: str):
    db, cur = start_db()
    user = cur.execute("SELECT * FROM favorite WHERE id = ?", (user_id,)).fetchone()
    if not(user and len(user[1])):
        raise NoFavoriteStationsException

def get_favorite_arrivals(user_id: str):
    db, cur = start_db()
    user = cur.execute("SELECT * FROM favorite WHERE id = ?", (user_id,)).fetchone()
    if not(user and len(user[1])):
        raise NoFavoriteStationsException
    else:
        station_csv = user[1]
        return lta_api_processor.display_arrivals_multiple_stations(station_csv.split(","))
    
def get_favorites(user_id: str):
    db, cur = start_db()
    user = cur.execute("SELECT * FROM favorite WHERE id = ?", (user_id,)).fetchone()
    if not(user and len(user[1])):
        raise NoFavoriteStationsException
    else:
        station_csv = user[1]
        return station_csv.split(',')

        
