from flask import Flask, render_template, request, redirect, send_from_directory
from webappfunctions import *
from statsanalysis import *


app = Flask(__name__)


# Home page
@app.route("/")
def index():

    # Establish hydro database connection
    db = db_connect()

    # Create folium map
    render_home_map()

    # Return index page
    return render_template("index.html")


# Upload page
@app.route("/upload", methods=["GET","POST"])
def upload():

    if request.method == "POST":

        # Establish hydro database connection, get form data, then execute dataframe processing function
        db = db_connect()
        data_raw = request.form.get("data")
        df_process(data_raw, db)

        return redirect("/")
    
    else: 
        return render_template("upload.html", placeholder=placeholder)


# Data browsing page
@app.route("/browse", methods=["GET","POST"])
def browse():

    # Get list of countries for form
    db = db_connect()
    nations = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND NAME NOT LIKE 'sqlite_%' AND NAME NOT LIKE 'stations'").fetchall()
    nations_list = []
    for nation in nations:
        # Clean nations list from SQL input
        nations_list.append(nation[0])

    # If user has selected a country
    if request.method == "POST":
        
        # Get nation code from user input
        nation = request.form.get("nation")
        
        # Get dataframe of nation then convert to list for easy slicing
        df = nation2df(nation, db, indexed=False)
        stations = df.columns.tolist()
        data = df.values.tolist()

        # Set download directory and output dataframe to CSV file for user download
        download_dir = "/temp/" + nation + "_data.csv"
        df.to_csv(cwd + download_dir)

        return render_template("browse.html", hide="", nations_list=nations_list, nation=nation, header_row=stations, table=data, download_link=download_dir)

    else: 

        return render_template("browse.html", hide="hidden", nations_list=nations_list)


@app.route('/temp/<path:filename>', methods=['GET','POST'])
def download(filename):

    return send_from_directory(directory=cwd+'/temp', path=filename, filename=filename)


@app.route('/stats', methods=['GET','POST'])
def stats():
    db = db_connect()
    df = nation2df('US', db, indexed=False)
    sens_df, mk_df = mkanalysis(df)
    return redirect("/")


if __name__ == '__main__':
    app.run(debug=True)
