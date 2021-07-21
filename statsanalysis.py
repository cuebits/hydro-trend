import pymannkendall
import pandas
import geopandas
import smoomapy
import os
import matplotlib.pyplot as plt
import matplotlib

from shapely.geometry import Point
from numpy import reshape, linspace
from datetime import datetime


# Function to generate monthly sens slope and mk trend test dataframes
def mkanalysis(df: pandas.DataFrame, alpha=0.05):

    # Extract coordinates and remove from dataframe to be analysed
    coordinates = df.iloc[0:2].values.tolist()
    coordinates[0].pop(0)
    coordinates[1].pop(0)
    df = df.drop([0,1])
    print(coordinates)
    print(df)

    # Extract dates column and transform it into a time series
    dates = pandas.Series(df["dates"])
    print(dates)
    dates = pandas.to_datetime(dates)
    print(dates)
     
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
