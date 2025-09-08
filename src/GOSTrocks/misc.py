import os
import time
import math
import logging

import geopandas as gpd
import pandas as pd
import numpy as np

from math import ceil
from shapely.geometry import Point, Polygon, box

from pyproj import CRS
from pyproj.aoi import AreaOfInterest
from pyproj.database import query_utm_crs_info

def get_folder_size(folder_path):
    """
    Calculates the total size of a folder in bytes, including all subdirectories and files.

    Args:
        folder_path (str): The path to the folder.

    Returns:
        int: The total size of the folder in bytes.
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # Use os.path.getsize() to get the size of each file
            # Handle potential errors like broken symbolic links or permission issues
            try:
                total_size += os.path.getsize(fp)
            except (FileNotFoundError, PermissionError):
                # Skip files that cannot be accessed
                continue
    return total_size

def loggingInfo(lvl=logging.INFO):
    """Set logging settings to info (default) and print useful information

    :param lvl: logging level for setting, defaults to logging.INFO
    :type lvl: logging.INFO
    """
    logging.basicConfig(format="%(asctime)s:%(levelname)s: %(message)s", level=lvl)


def tPrint(s):
    """prints the time along with the message"""
    print("%s\t%s" % (time.strftime("%H:%M:%S"), s))


def round_to_1(x):
    return round(x, -int(math.floor(math.log10(x))))


def drange(start, stop, step):
    """Create an interable range made with decimal point steps"""
    r = start
    while r < stop:
        yield r
        r += step


def getHistIndex(hIdx, val):
    """Get the index of a specific [val] within a list of histogram values

    :param hIdx: list of values (from histogram calculation)
    :type hIdx: list of numbers
    :param val: value to search for
    :type val: number
    :return: index in hIdx where val falls
    :rtype: int
    """
    lastH = 0
    for h in range(0, len(hIdx)):
        curH = hIdx[h]
        if curH > val:
            return lastH
        lastH = h
    return len(hIdx) - 1


def listSum(inD):
    """get sum of values in list

    :param inD: list of numbers
    :type inD: list
    """
    total = 0
    for x in inD:
        total += x
    return total


def getHistPer(inD):
    """Convert a list of values into a percent of total

    :param inD: list of values
    :type inD: list of numbers
    :return: list of values of same length of inD.
    :rtype: list of float
    """
    tSum = listSum(inD)
    for hIdx in range(0, len(inD)):
        inD[hIdx] = inD[hIdx] / tSum
    return inD

def createFishnet(
    xmin,
    xmax,
    ymin,
    ymax,
    gridHeight,
    gridWidth,
    type="POLY",
    crsNum=4326,
    outputGridfn="",
):
    """Create a vector fishnet shapefile inside the defined coordinates

    :param xmin: minimum longitude
    :type xmin: float
    :param xmax: maximum longitude
    :type xmax: float
    :param ymin: minimum latitude
    :type ymin: float
    :param ymax: maximum latitude
    :type ymax: float
    :param gridHeight: resolution of the grid cells in crsNum units
    :type gridHeight: float
    :param gridWidth: resolution of the grid cells in crsNum units
    :type gridWidth: float
    :param type: geometry type of output fishnet, defaults to 'POLY'
    :type type: str, optional
    :param crsNum: units of output crs, defaults to 4326
    :type crsNum: int, optional
    :param outputGridfn: path for output shapefile, defaults to '', which creates no shapefile
    :type outputGridfn: str, optional
    :return: geodataframe of fishnet
    :rtype: gpd.GeoDataFrame
    """

    def get_box(row, col, left, r, b, t, gridWidth, gridHeight):
        ll = Point(left + (row * gridWidth), b + (col + gridHeight))
        ul = Point(left + (row * gridWidth), t + (col + gridHeight))
        ur = Point(r + (row * gridWidth), t + (col + gridHeight))
        lr = Point(r + (row * gridWidth), b + (col + gridHeight))
        box = Polygon([ll, ul, ur, lr, ll])
        return box

    def get_point(row, col, left, r, b, t, gridWidth, gridHeight):
        pt = Point((left + r) / 2 + (col * gridWidth), (t + b) / 2 - (row * gridHeight))
        return pt

    # convert sys.argv to float
    xmin = float(xmin)
    xmax = float(xmax)

    ymin = float(ymin)
    ymax = float(ymax)
    gridWidth = float(gridWidth)
    gridHeight = float(gridHeight)

    # get rows
    rows = ceil((ymax - ymin) / gridHeight)
    # get columns
    cols = ceil((xmax - xmin) / gridWidth)

    # start grid cell envelope
    ringXleftOrigin = xmin
    ringXrightOrigin = xmin + gridWidth
    ringYtopOrigin = ymax
    ringYbottomOrigin = ymax - gridHeight

    all_res = []
    for rowIdx in range(0, rows):
        for colIdx in range(0, cols):
            if type == "POLY":
                box = get_box(
                    rowIdx,
                    colIdx,
                    ringXleftOrigin,
                    ringXrightOrigin,
                    ringYbottomOrigin,
                    ringYtopOrigin,
                    gridWidth,
                    gridHeight,
                )
            elif type == "POINT":
                box = get_point(
                    rowIdx,
                    colIdx,
                    ringXleftOrigin,
                    ringXrightOrigin,
                    ringYbottomOrigin,
                    ringYtopOrigin,
                    gridWidth,
                    gridHeight,
                )
            all_res.append([rowIdx, colIdx, box])
    res = gpd.GeoDataFrame(
        pd.DataFrame(all_res, columns=["rowIdx", "colIdx", "geometry"]),
        geometry="geometry",
        crs=f"epsg:{crsNum}",
    )
    if outputGridfn != "":
        res.to_file(outputGridfn)
    return res


def explodeGDF(indf):
    """Convert geodataframe with multi-part polygons to one with single part polygons

    :param indf: input geodataframe to explode
    :type indf: gpd.GeoDataFrame
    :return: exploded geodaatframe
    :rtype: gpd.GeoDataFrame
    """
    all_dfs = []
    for idx, row in indf.iterrows():        
        if row.geometry.geom_type in ["Polygon", "Point", "LineString"]:
            all_dfs.append(pd.DataFrame([row]))
        if row.geometry.geom_type in ["MultiPoint", "MultiPolygon", "MultiLineString"]:
            recs = len(row.geometry.geoms)
            multdf = gpd.GeoDataFrame([row] * recs).reset_index()
            for idx in range(recs):
                geom = row.geometry.geoms[idx]
                multdf.loc[idx, "geometry"] = geom
            all_dfs.append(multdf)
    return(gpd.GeoDataFrame(pd.concat(all_dfs), geometry='geometry', crs=indf.crs).reset_index())