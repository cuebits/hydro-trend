import pymannkendall
import pandas
import geopandas
import smoomapy
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg') # Avoids runtime errors

from shapely.geometry import Point
from numpy import reshape, linspace

# Function to generate monthly sens slope and mk trend test dataframes
def mkanalysis(df: pandas.DataFrame, alpha=0.05):

    # Extract coordinates and remove from dataframe to be analysed
    coordinates = df.iloc[0:2].values.tolist()
    coordinates[0].pop(0)
    coordinates[1].pop(0)
    df = df.drop([0,1])

    # Extract dates column and transform it into a time series
    dates = pandas.Series(df["dates"])
    dates = pandas.to_datetime(dates)
     
    # Create new data frames for Sen's Slopes and m-k tests
    sens_df = pandas.DataFrame()
    mk_df = pandas.DataFrame()

    # Iterate for each station in the data frame
    for label, content in df.iteritems():
        
        # Skip the dates column
        if label == "dates":
            continue

        # Convert the column to a time series
        content = pandas.Series(content.values, index = dates)

        # Reshape the time series into a matrix with months as columns
        monthly_array = content.values                              # Create an array with the values from the current data frame column
        monthly_array = reshape(monthly_array, (-1, 12)).T    # Reshape to 12 x N, then transpose so each array index corresponds with a month

        # Create temporary columns for storing into the new data frame
        sens_temp = []
        mk_temp = []

        # For each column in the array, run the tests
        for month in monthly_array:
            
            # Append the desired test results to the sens_temporary column
            mk_result = pymannkendall.original_test(month, alpha=alpha)
            sens_temp.append(mk_result.slope)
            mk_temp.append(mk_result.trend)

        # Add each station to the data frames
        sens_df[label] = sens_temp
        mk_df[label] = mk_temp

    # Add months columns
    sens_df["Month"] = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    mk_df["Month"] = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    sens_df = sens_df.set_index("Month")
    mk_df = mk_df.set_index("Month")

    # Transpose data frames
    sens_df = sens_df.T
    mk_df = mk_df.T

    # Reinsert lat/lon rows
    sens_df["Latitude"] = coordinates[0]
    sens_df["Longitude"] = coordinates[1]
    mk_df["Latitude"] = coordinates[0]
    mk_df["Longitude"] = coordinates[1]    

    return sens_df, mk_df


def trendmapgen(gdf, nation3code, analysis_type, dir, crs=4326, axis_buffer=5):
    
    # Temp set extents of map
    minx, miny, maxx, maxy = min(gdf["Longitude"]) - axis_buffer, min(gdf["Latitude"]) - axis_buffer, max(gdf["Longitude"]) + axis_buffer, max(gdf["Latitude"]) + axis_buffer

    # If input dataframe is not a geodataframe, convert it to one
    if isinstance(gdf, pandas.DataFrame):
        gdf = df_to_gdf(gdf, crs)

    minslope = gdf.drop(["Latitude", "Longitude", "geometry"], axis=1).min().min()
    maxslope = gdf.drop(["Latitude", "Longitude", "geometry"], axis=1).max().max()

    # Read world and lakes shape file, then extract mask from nation name
    world = geopandas.read_file("data\\GIS Data\\ne_10m_admin_0_countries.shp")
    water = geopandas.read_file("data\\GIS Data\\World_Lakes.shp")
    
    mask = world[(world.ADM0_A3==nation3code)]

    # Run plots and subplots
    ax = plt.subplot()                      
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_facecolor("#d1e0e6")
    gdf.plot(ax=ax, color="k", markersize=3, zorder=100)
    water.plot(ax=ax, color="#d1e0e6", zorder=3)
    world.plot(ax=ax, color="#c6cccf", zorder=1)

    # Generate stations locations map
    plt.title(label="Rainfall Station Locations")
    plt.savefig(dir + "stat_loc_" + nation3code + ".png", dpi=450)

    # Define precision of IDW contours
    num_breaks = 100
    breaks_min = round(minslope, ndigits=3)
    breaks_max = round(maxslope, ndigits=3)
    plot_breaks = linspace(breaks_min, breaks_max, num_breaks)  
    
    if analysis_type == "annual":
        # TODO

        return 

    # Iterate through months and save each image
    i = 1 # For file naming, keeps months in chronological order, not alphabetical 
    for month, slopes in gdf.iteritems():
        
        # Skip non-month columns
        if month == "Latitude" or month == "Longitude" or month == "geometry":
            continue
        
        # Create new geodataframe for each month
        month_gdf = geopandas.GeoDataFrame(slopes, geometry=geopandas.points_from_xy(gdf.Longitude, gdf.Latitude))
        
        # Perform IDW functions
        idw = smoomapy.SmoothIdw(month_gdf, month, 1, nb_pts=20000, mask=mask)
        res = idw.render(nb_class=num_breaks, user_defined_breaks=plot_breaks, disc_func="equal_interval", output="GeoDataFrame")

        # Reset figure
        plt.figure()
        fig, ax = plt.subplots()
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        ax.set_facecolor("#d1e0e6")

        # Plot next month
        gdf.plot(ax=ax, color="k", markersize=3, zorder=100, alpha=0.2)
        water.plot(ax=ax, color="#d1e0e6", zorder=3)
        world.plot(ax=ax, color="#c6cccf", zorder=1)
        res.plot(ax=ax, cmap="RdBu", column="center", linewidth=0.1, zorder=99, legend=False)

        # Create normalised colour bar
        norm = matplotlib.colors.TwoSlopeNorm(vmin=breaks_min, vcenter=0, vmax=breaks_max)
        cbar = plt.cm.ScalarMappable(norm=norm, cmap="RdBu")
        fig.colorbar(cbar, ax=ax)

        # Save output image in directory
        plt.title(label=month + " Sens's Slopes")
        plt.savefig(dir + "{:0>2d}".format(i) + "_" + month + "_sens_" + nation3code + ".png", dpi=450)
        plt.close()

        i += 1  

    return


def df_to_gdf(inputdf, crs=4326):
    geometry = [Point(xy) for xy in zip(inputdf["Longitude"], inputdf["Latitude"])]
    return geopandas.GeoDataFrame(inputdf, geometry=geometry, crs=crs)