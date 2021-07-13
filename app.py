from sqlite3.dbapi2 import DateFromTicks
from flask import Flask, render_template, request, redirect

import sqlite3
import folium
import os
import io
import pandas

app = Flask(__name__)
cwd = os.getcwd()

placeholder = "Usage, tab separated columns:\n'Station'\tStation\n'Latitude'\tLatitude\n'Longitude'\tLongitude\nDate\tRainfall"

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
    db.execute("CREATE TABLE IF NOT EXISTS stations (station_id TEXT PRIMARY KEY NOT NULL, latitude REAL NOT NULL, longitude REAL NOT NULL)")    # Expand to include date range and country
    db.execute("CREATE TABLE IF NOT EXISTS rainfall (station_id TEXT PRIMARY KEY NOT NULL, record_date REAL NOT NULL, precipitation REAL, FOREIGN KEY (station_id) REFERENCES stations (station_id))")
    return db

# Function for processing raw text input into workable data frames
def df_process(data, db):
        
        # Read into data frame
        df = pandas.read_csv(io.StringIO(data), sep="\t", index_col=0)

        # Write to SQL Table of Stations
        # Iterate over each station in the dataframe
        for label, content in df.iteritems():

            if label == "Date":
                continue
            
            lat = content.iloc[0]
            lon = content.iloc[1]

            db.execute("INSERT INTO stations (station_id, latitude, longitude) VALUES (?, ?, ?)", (label, lat, lon))
            db.commit()


if __name__ == '__main__':
    app.run(debug=True)


