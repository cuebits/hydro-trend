# HydroTrend
#### Video Demo:  <URL HERE>
#### Summary: 
Interactive web application for viewing, adding, and analysing rainfall data. Includes an interactive map for veiwing the available data in the database, functions to download data as a CSV, statistical analysis (Mann-Kendall test for non-parametric trends) and a static map image generator that allows you to visualise how rainfall has changed over a given period for a country. 

## Introduction
This app was built to assist follow-up research of the research paper ["Evidence of climate change in south east Australian water data"](https://drive.google.com/file/d/1egNLWQuNnzxzXjiOheR68cT9zheViHn4/view). It allows users to submit their own rainfall data to a shared database, and for others to download the raw data, analysed data, and static maps visualising the spatial trends over a selected analysis period. It is intended for the UNSW Water Research Centre and as a final project for the Harvard University online computer science course CS50X. 

## Dependencies
This web app makes use of a number of external libraries, common for data analysis, but a few other more obscure libraries found on GitHub. 
### Python Native Libraries
- sqlite3: for the storing of rainfall data in a SQLite database
- os and shutil: for file and directory management
- io: for generating CSV and ZIP files in memory
- datetime
- zipfile: for batch donwloading image files for static map generation
### Common External Libraries
- flask: used for building the web application
- numpy and pandas: for data array mainpulation
- geopandas and shapely: for interpreting GIS data
- matplotlib: for creating maps
- folium: for generating the home page interactive map
- beautiful soup 4: minor HTML management
### Other Libraries
- pymannkendall: for statistical analysis, [big thank you to Md. Manjurul Hussain Shourov](https://pypi.org/project/pymannkendall/)
- reverse_geocoder: for easily extracting countries from coordinates [big thank you to Ajay Thampi](https://github.com/thampiman/reverse-geocoder)
- smoomapy: for generating IDW smoothed maps [big thank you to user mthh](https://github.com/mthh/smoomapy)

All three can be found on PyPi. I've added smoomampy into the python-modules folder as it was slightly modified for the purposes of this app. 

## Web Pages
### Home
Has the folium interactive map with the rainfall stations in the database on the map with blue markers. The callouts list the station name, coordinates, and the start and end date of the data range. 

### Upload Data 
Here you can download the CSV template for adding your data. Copy and paste the data from Excel, and paste in the data into the text area. Make sure the data is tab separated. Then click "Submit to Database". 
For future development: 
- [ ] CSV file upload. 

### Browse Data
Browse the available rainfall station database for a particular country and date range. The data will be made available for CSV download.
For future development: 
- [ ] Sub-country level data breakdown (states, provinces etc)

### Analyse Data
The page analyses selected data by outputting a table of Thiel-Sen slope estimators (mm/year) and a table of trend results i.e. whether or not the slopes are statistically significant for the given alpha level. 
#### Long-term (annual or continuous)
The data is analysed continuously, so no reshaping for months. Useful in seeing whether rain has increased or decreased overall for a particular region. 

#### Monthly (month to month trends)
This is a way of seeing how seasonality has changed over the long-term and is of interest to climate change research. The slopes show how particular months have changed over the given period.

### Generate Maps
This generates static PNG images of maps with rainfall trend mapped with the inverse distance weighted method. In addition, you may select a coordinate reference system to project the data, depending on the user region of interest. It also generates a link to create a ZIP download of all the images. 
For future development: 
- [ ] Correct CRS projection for smoomapy
- [ ] Add additional CRS systems and integrate correctly into system

## Breakdown of Files and Functions
The below is a quick guide for how each function operates. 
### app.py
Most of the functions are straightforward Flask redirects that get user input and call other functions. The browse, stats, and maps templates pass the "hidden" attribute to a div in the HMTL templates to hide the sections of the page that display data before a form is submitted. 
#### File Downloads
When a route is passed through to the /temp/ directory, the filename passed is sent as a download. If the link instead is a folder with "/zip" at the end, a ZIP IO stream is generated in memory that writes the contents of the directory in the archive, then the file in memory is sent to the user as a download. 

### webappfunctions.py
#### db_connect
Establishes a connection to a SQLite database known as "hydro-db". 
#### df_process
Takes raw, tab separated text input and converts it into a dataframe. It creates the necessary tables in the database if they don't exist, one for the stations and one for the country. The database lists all stations available in the database in the "stations" table, and stores the actual rainfall values in a table for each country, with the stations as columns and the dates as unique rows.

Note that the queries use the "ON CONFLICT" keywords to preserve the order of and prevent duplicating of the dates rows (which are declared unique). Note however, that in the unlikley situation that there are stations in the same country with the same name, the new data will overwrite the previous records. 
For future development: 
- [ ] Sanitise SQL inputs, as SQLite cannot create tables or columns with variable names in a secure way

#### render_home_map
Generate a folium map. Then queries the stations table in the database and creates a marker for the map for each entry. Beatiful Soup removes some CSS. 
For future development: 
- [ ] Generate a better HTML template from Folium

#### nation2df
Gathers the data from a particular nation and returns all the available data in a pandas dataframe. 

#### delete_old_files
Deletes directories older than 1 day in the temp directory. 

#### get_nations_list
Gets list of nations from the database, i.e. the list of tables that aren't called "stations". This list is used populate the dropdowns for the forms and identify the nations spatially on the shape file. 

### statsanalysis.py
#### mkanalysis
Takes a dataframe, significance level (alpha), and an analysis type ("Monthly" or "Annual") and returns dataframes of the Thiel-Sen slope estimates and Mann-Kendall results, respectively. 

#### trendmapgen
Generates the trend maps of the selected country and date range. Takes a geodataframe (or dataframe), ISO 3166-1 Alpha 3 nation code, temporary directory, CRS, and an axis buffer (hardcoded to 5 degrees).
1. Sets extents of maps that are the buffer of latitude and longitude wider than the extremes of the stations in the dataframe. 
2. Converts the dataframe to a geodataframe if it already isn't one. 
3. Extracts the minimum and maximum slopes for the data to determine the colour scales and breaks for the IDW mapping. 
4. Loads the shapefiles and masks the IDW for the selected country. 
5. Plots the results on a map with the MATLAB plotting library module.
6. Saves the output images in the temp directory 

For future development:
- [ ] Dynamically set the axis buffer, or the map extents
- [ ] Select different colour gradient maps for the trend axes
- [ ] Make the outputs prettier, with:
     - North points
     - Gridlines
     - Different font
     - Title padding
     - Axis labels

#### df_gdf
Converts dataframes to geopandas geodataframes. 
