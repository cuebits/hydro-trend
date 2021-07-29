from sqlite3.dbapi2 import Connection
from datetime import datetime

import sqlite3
import folium
import os
import io
import numpy
import pandas
import reverse_geocoder
import bs4 
import shutil

cwd = os.getcwd()
placeholder = "Usage tab separated columns:\n\n'Station'\tStation\n'Latitude'\tLatitude\tLatitude\n'Longitude'\tLongitude\tLongitude\nDate\tRainfall\nDate\tRainfall\nDate\tRainfall"

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
        for station, column in df.iteritems():

            # Extract date range of data
            if station == "Station":
                date_range = column.iloc[2:].to_list()
                continue
            
            # Find country of station, get two letter country code from reverse geocoder
            lat = column.iloc[0]
            lon = column.iloc[1]
            country = reverse_geocoder.search((lat, lon))[0]['cc']

            # Rename station name with country code at start, allows for stations with same names from different countries, and then replace spaces with underscores
            station = (country + "_" + station).replace(" ", "_")

            # Create tables for stations, and for countries
            db.execute("CREATE TABLE IF NOT EXISTS stations (station_id TEXT NOT NULL, latitude REAL NOT NULL, longitude REAL NOT NULL, start_year INTEGER, end_year INTEGER, country TEXT NOT NULL)")
            db.execute(f"CREATE TABLE IF NOT EXISTS {country} (dates REAL PRIMARY KEY UNIQUE NOT NULL)")

            # Check if stations are existing, if so, update existing rows and continue loop
            stations_table = pandas.read_sql_query("SELECT * FROM stations", db)
            if station in stations_table["station_id"].to_list():
                for date, rain in zip(date_range, column[2:]):
                    db.execute(f"INSERT INTO {country} (dates, {station}) VALUES (?, ?) ON CONFLICT (dates) DO UPDATE SET {station} = ?", (date, rain, rain))
                db.commit()
                continue
            
            # Remove latitude and longitude data from column
            rain_data = column[2:].to_list()

            # Extract start and end year for this column
            index = 0
            start_year: int = 3000
            for entry in rain_data:

                # Skip first null entries
                if pandas.isnull(entry):
                    index += 1
                    continue
                
                entry_year = int(date_range[index][:4])
                # Until first year data is encountered
                if entry_year < start_year:
                    start_year = entry_year

                # Keep storing years if not null entry, final non-null entry is end year
                if pandas.isnull(entry) is False:
                    end_year = entry_year

                index += 1

            # Insert data into tables
            db.execute("INSERT INTO stations (station_id, latitude, longitude, start_year, end_year, country) VALUES (?, ?, ?, ?, ?, ?)", (station, lat, lon, start_year, end_year, country))

            db.execute(f"ALTER TABLE {country} ADD {station}")

            for date, rain in zip(date_range, rain_data):
                db.execute(f"INSERT INTO {country} (dates, {station}) VALUES (?, ?) ON CONFLICT (dates) DO UPDATE SET {station} = ?", (date, rain, rain))
            db.commit()
            

def render_home_map():
    
    # Initialise and save map HTML
    folium_map = folium.Map(location=(0, 0), zoom_start=3, width="90%", height="80%", left="5%", top="5%")

    # Query database for all stations
    db = db_connect()
    stations_table = pandas.read_sql_query("SELECT * FROM stations", db)

    # Add markers to map
    for i in range(0,len(stations_table)):
        html=f"""
            <head><link href="/static/styles.css" rel="stylesheet"></head>
            <link href="/static/styles.css" rel="stylesheet">
            <h1 style="font-size:20px;font-family:Arial"> {stations_table.iloc[i]['station_id']}</h1>
            <p style="font-size:12px;font-family:Arial">
                Country: {stations_table.iloc[i]['country']}
                <br>
                Date range: {stations_table.iloc[i]['start_year']} - {stations_table.iloc[i]['end_year']}
                <br>
                Coordinates: {stations_table.iloc[i]['latitude']}, {stations_table.iloc[i]['longitude']}
            </p>
            """
        iframe = folium.IFrame(html=html, width=300, height=100)
        popup = folium.Popup(iframe, max_width=2650)
        folium.Marker(
            location=[stations_table.iloc[i]['latitude'], stations_table.iloc[i]['longitude']],
            popup=popup,
            icon=folium.DivIcon(html=f"""
                <div><svg>
                    <circle cx="10" cy="10" r="6" fill="cornflowerblue" opacity=".8"/>
                </svg></div>""")
        ).add_to(folium_map)

    # Save map as HTML
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