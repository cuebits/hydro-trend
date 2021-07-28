import zipfile
import numpy
import os

from datetime import datetime
from flask import Flask, render_template, request, redirect, send_from_directory, send_file
from io import BytesIO

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

    # Clear old files
    delete_old_files(cwd + "\\temp\\")
    
    # Get list of countries for form
    nations_list, nationcoderef = get_nations_list()

    # If user has selected a country
    if request.method == "POST":
        
        db = db_connect()

        # Get user form data
        nation2code = request.form.get("nation")
        nation = nationcoderef.at[nation2code, "Country"]
        start_year = int(request.form.get("start_year"))
        end_year = int(request.form.get("end_year"))
        
        # Get dataframe of nation then convert to list for easy slicing
        df = nation2df(nation2code, db, indexed=False, start_year=start_year, end_year=end_year)
        stations = df.columns.tolist()
        data = df.values.tolist()

        # Set download directory and output dataframe to CSV file for user download
        download_dir = "\\temp\\" + datetime.now().strftime("%Y%m%d%H%M%S") + "\\"
        os.makedirs(cwd + download_dir)
        df = df.set_index("dates")
        df.to_csv(cwd + download_dir + nation2code + "_data.csv")
        download_dir = download_dir + nation2code + "_data.csv"

        return render_template("browse.html", hide="", nations_list=nations_list, current_year=datetime.now().year, nation2code=nation2code, nation=nation, header_row=stations, table=data, download_link=download_dir)

    else: 

        return render_template("browse.html", hide="hidden", nations_list=nations_list, current_year=datetime.now().year)


@app.route('/temp/<path:filename>', methods=['GET','POST'])
def download(filename):

    # If sent a zip, the file name is actually the directory of the folder to zip
    # Check if last 4 characters of address is "/zip"
    if filename[-4:] == "/zip":

        # Set directory to current working directory/temp/folder name (remove "/zip")
        dir = cwd + "\\temp\\" + filename[:-4]

        # Create a zip file in memory
        zipinmemory = BytesIO()
        with zipfile.ZipFile(zipinmemory, 'w') as zf:
            for file in os.listdir(dir):
                zf.write(dir + file, os.path.basename(dir + file))
        
        # Rewind the buffer cursor to start of file
        zipinmemory.seek(0)
        
        return send_file(zipinmemory, attachment_filename=filename[:-5]+".zip", as_attachment=True)

    # Else if not a zip file, just send the file directly
    return send_from_directory(directory=cwd+'/temp', path=filename, filename=filename)


@app.route('/stats', methods=['GET','POST'])
def stats():

    # Clear old files
    delete_old_files(cwd + "\\temp\\")
    
    # Get list of countries for form
    nations_list, nationcoderef = get_nations_list()
    
    #  If user has selected a nation
    if request.method == "POST":
        
        db = db_connect()

        # Get nation code from user input, and then get nation data from database
        nation2code = request.form.get("nation")
        nation = nationcoderef.at[nation2code, "Country"]
        start_year = int(request.form.get("start_year"))
        end_year = int(request.form.get("end_year"))


        df = nation2df(nation2code, db, indexed=False, start_year=start_year, end_year=end_year)

        # Run MK analysis on data
        alpha = float(request.form.get("alpha"))
        sens_df, mk_df = mkanalysis(df, alpha=alpha)

        # Set download directory and output dataframe to CSV file for user download
        download_dir = "/temp/" + datetime.now().strftime("%Y%m%d%H%M%S") + "/"
        os.makedirs(cwd + download_dir)
        sens_df.to_csv(cwd + download_dir + nation2code + "_sens.csv")
        mk_df.to_csv(cwd + download_dir + nation2code + "_mk.csv")
        sens_dl = download_dir + nation2code + "_sens.csv"
        mk_dl = download_dir + nation2code + "_mk.csv"

        # Truncate Sen's Slopes to 3 decimal places
        sens_df = numpy.trunc(10000 * sens_df) / 10000

        # Format dataframes for display
        sens_df = sens_df.reset_index()
        mk_df = mk_df.reset_index()

        sens_df = sens_df.rename(columns={'index':'Stations'})
        mk_df = mk_df.rename(columns={'index':'Stations'})

        return render_template("stats.html", hide="", alpha=alpha, current_year=datetime.now().year, nations_list=nations_list, nation=nation, header_row=sens_df.columns.tolist(), sens_table=sens_df.values.tolist(), mk_table=mk_df.values.tolist(), sens_dl=sens_dl, mk_dl=mk_dl)

    else: 

        return render_template("stats.html", hide="hidden", nations_list=nations_list, current_year=datetime.now().year)


@app.route("/maps", methods=["GET", "POST"])
def map_gen():

    # Clear old files
    delete_old_files(cwd + "\\temp\\")

    # Get list of countries for form
    nations_list, nationcoderef = get_nations_list()
    
    #  If user has selected a nation
    if request.method == "POST":

        db = db_connect()

        # Get user inputs, and then get nation data from database
        nation2code = request.form.get("nation")
        start_year = int(request.form.get("start_year"))
        end_year = int(request.form.get("end_year"))
        map_type = request.form.get("map_type")
        crs = int(request.form.get("crs"))

        nation3code = nationcoderef.at[nation2code, "Alpha-3 code"]
        nation = nationcoderef.at[nation2code, "Country"]

        df = nation2df(nation2code, db, indexed=False, start_year=start_year, end_year=end_year)

        # Run MK analysis on data
        sens_df, mk_df = mkanalysis(df)

        # Make temporary directory
        imagedir = "\\temp\\" + datetime.now().strftime("%Y%m%d%H%M%S") + "\\"
        os.makedirs(cwd + imagedir)

        # Generate images and then write to directory
        trendmapgen(sens_df, nation3code, map_type, cwd + imagedir, crs, axis_buffer=5)

        # Send back list of images and download link for zip file
        filelist= [file for file in os.listdir(cwd + imagedir) if file.endswith('.png')]

        return render_template("maps.html", hide="", current_year=datetime.now().year, nations_list=nations_list, nation=nation, analysis_type=map_type, imagedir=imagedir, image_list=filelist)

    else: 

        return render_template("maps.html", hide="hidden", current_year=datetime.now().year, nations_list=nations_list, imagedir="")

if __name__ == '__main__':
    app.run(debug=True)
