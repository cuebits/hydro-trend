from sqlite3.dbapi2 import DateFromTicks
from flask import Flask, render_template, request, redirect

import sqlite3
import folium
import os
import io
import pandas
import reverse_geocoder

app = Flask(__name__)
cwd = os.getcwd()

placeholder = "Usage, tab separated columns:\n\n'Dates'\tStation\n'Latitude'\tLatitude\tLatitude\n'Longitude'\tLongitude\tLongitude\nDate\tRainfall\nDate\tRainfall\nDate\tRainfall"

# Home page
@app.route("/")
def index():

    # Establish hydro database connection
    db = db_connect()

    # Create folium map
    folium_map = folium.Map(location=(0, 0), zoom_start=3, width="90%", height="80%", left="5%", top="5%")
    folium_map.save("templates/map.html")

    # Return index page
    return render_template("index.html")

# Upload page
@app.route("/upload")
def upload():

    return render_template("upload.html", placeholder=placeholder)

# Uploaded data function
@app.route("/add-data", methods=["GET","POST"])
def data_upload():

    if request.method == "POST":

        # Establish hydro database connection
        db = db_connect()

        data_raw = request.form.get("data")
        df_process(data_raw, db)

    return redirect("/")


# Connect to a SQLite database
def create_connection(path):
    connection = None
    try:
        connection = sqlite3.connect(path)
        print("Connection to SQLite DB successfull.")
    except sqlite3.Error as e:
        print(f"The error '{e}' occured.")

    return connection

# Function for establishing connection to database and initialising tables if they don't exist. Called on index page.
def db_connect():
    db = create_connection(cwd + "\\hyrdo-db.sqlite")
    return db

# Function for processing raw text input into workable data frames
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
            print(country)

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
            db.execute(f"ALTER TABLE {country} ADD {heading}")

            for date, rain in zip(date_range, column[2:]):
                db.execute(f"INSERT INTO {country} (dates, {heading}) VALUES (?, ?) ON CONFLICT (dates) DO UPDATE SET {heading} = ?", (date, rain, rain))
            db.commit()
            





if __name__ == '__main__':
    app.run(debug=True)


