from sqlite3.dbapi2 import Connection
from datetime import datetime

import sqlite3
import folium
import os
import io
import pandas
import reverse_geocoder
import bs4 
import shutil

cwd = os.getcwd()
placeholder = "Usage tab separated columns:\n\n'Dates'\tStation\n'Latitude'\tLatitude\tLatitude\n'Longitude'\tLongitude\tLongitude\nDate\tRainfall\nDate\tRainfall\nDate\tRainfall"

# Function for establishing connection to database
def db_connect():
    
    db = None
    try:
        db = sqlite3.connect(cwd + "\\hyrdo-db.sqlite")
        print("Connection to SQLite DB successfull.")
    except sqlite3.Error as e:
        print(f"The error '{e}' occured.")

    return db


# Function for processing raw text input into workable data frames and inputting into database
def df_process(data, db):
        
        # Read into data frame
        df = pandas.read_csv(io.StringIO(data), sep="\t")

        # Write to SQL Table of Stations
        date_range = []
        # Iterate over each station in the dataframe
        for heading, column in df.iteritems():

            # Extract date range of data
            if heading == "Date":
                date_range = column.iloc[2:]
                continue
            
            # Find country of station
            lat = column.iloc[0]
            lon = column.iloc[1]
            country = reverse_geocoder.search((lat, lon))[0]['cc']

            # Create tables for stations, and for countries
            db.execute("CREATE TABLE IF NOT EXISTS stations (station_id TEXT NOT NULL, latitude REAL NOT NULL, longitude REAL NOT NULL, start_year INTEGER, end_year INTEGER, country TEXT NOT NULL)")
            db.execute(f"CREATE TABLE IF NOT EXISTS {country} (dates REAL PRIMARY KEY UNIQUE NOT NULL)")

            # Check if stations are existing, if so, update existing rows and continue loop
            table = pandas.read_sql_query("SELECT * FROM stations", db)
            if heading in table["station_id"].to_list():
                for date, rain in zip(date_range, column[2:]):
                    db.execute(f"INSERT INTO {country} (dates, {heading}) VALUES (?, ?) ON CONFLICT (dates) DO UPDATE SET {heading} = ?", (date, rain, rain))
                db.commit()
                continue

            # Insert data into tables
            db.execute("INSERT INTO stations (station_id, latitude, longitude, country) VALUES (?, ?, ?, ?)", (heading, lat, lon, country))

            # Check if numeric headings, then add underscore to start
            if heading[0].isdigit():
                heading = "_" + heading

            db.execute(f"ALTER TABLE {country} ADD {heading}")

            for date, rain in zip(date_range, column[2:]):
                db.execute(f"INSERT INTO {country} (dates, {heading}) VALUES (?, ?) ON CONFLICT (dates) DO UPDATE SET {heading} = ?", (date, rain, rain))
            db.commit()
            

def render_home_map():
    
    # Initialise and save map HTML
    folium_map = folium.Map(location=(0, 0), zoom_start=3, width="90%", height="80%", left="5%", top="5%")
    folium_map.save("templates/map.html")

    # Remove Folium CSS
    html = open(cwd + "/templates/map.html")
    soup = bs4.BeautifulSoup(html, 'html.parser')
    txt = soup.find("link", {"href": "https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css"})
    txt.replace_with("")
    txt = soup.find("link", {"href": "https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap-theme.min.css"})
    txt.replace_with("") 
    with open(cwd + "\\templates\map.html","wb") as output:
        output.write(soup.prettify("utf-8"))
    

# Function to query station data from database for a nation
def nation2df(nation: str, db: Connection, indexed: bool, start_year = 0, end_year = 3000):

    # Geat all data from nation
    rawdata = db.execute(f"SELECT * FROM {nation}").fetchall()
    
    # Loop through list, remove items from list where the year is lower than the start year or higher than end year
    data = []
    for row in rawdata:
        if int(row[0][:4]) >= start_year and int(row[0][:4]) <= end_year: 
            data.append(row)
    
        
    # Get station names from column names in nations table, then get coordinates from stations table
    headers = db.execute(f"PRAGMA table_info({nation})").fetchall()
    stations = []
    latlon = [["Latitude"],["Longitude"]]
    for heading in headers:

        # Get station name
        stations.append(heading[1])
        
        if heading[1] == "dates":
            continue

        coordinates = db.execute("SELECT latitude, longitude FROM stations WHERE station_id LIKE ?", (heading[1],)).fetchall()
        latlon[0].append(coordinates[0][0])
        latlon[1].append(coordinates[0][1])

    # Create new data frame, append lat and lon rows
    df = pandas.DataFrame(data, columns=stations)
    df.loc[-2] = latlon[0]
    df.loc[-1] = latlon[1]
    df.index = df.index + 2
    df = df.sort_index()

    # If an indexed dataframe was requested, set the index
    if indexed:
        df = df.set_index(df.columns[0])

    return df


# Function that deletes all directories older than one day
def delete_old_files(dir):

    directories = os.listdir(dir)

    for folder in directories:
        try: 
            if (datetime.now() - datetime.strptime(folder, "%Y%m%d%H%M%S")).days > 0:
                shutil.rmtree(dir + folder)
        except:
            continue

    return


# Funtion to get list of nation names for forms
def get_nations_list():

    db = db_connect()
    nations = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND NAME NOT LIKE 'sqlite_%' AND NAME NOT LIKE 'stations'").fetchall()
    nationcoderef = pandas.read_csv("data\\nations.csv")
    nationcoderef = nationcoderef.set_index("Alpha-2 code")
    nations_list = []
    for nation in nations:
        # Clean nations list from SQL input
        nations_list.append([nation[0], nationcoderef.at[nation[0],"Country"]])

    return nations_list, nationcoderef