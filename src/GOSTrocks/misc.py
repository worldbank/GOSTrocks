import os
import time
import logging

import geopandas as gpd
import pandas as pd

from math import ceil
from shapely.geometry import Point, Polygon


def get_folder_size(folder_path):
    """Get the total size of a folder in bytes.

    Parameters
    ----------
    folder_path : str
        The path to the folder.

    Returns
    -------
    int
        The total size of the folder in bytes.
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
    """Set the logging level

    Parameters
    ----------
    lvl : int, optional
        Logging level to set, by default logging.INFO
    """
    logging.basicConfig(format="%(asctime)s:%(levelname)s: %(message)s", level=lvl)


def tPrint(s):
    """Prints the time along with the message

    Parameters
    ----------
    s : str
        The message to print
    """
    print("%s\t%s" % (time.strftime("%H:%M:%S"), s))


def drange(start, stop, step):
    """Generate a range object with decimal points

    Parameters
    ----------
    start : float
        The starting value of the range.
    stop : float
        The end value of the range.
    step : float
        The step size for the range.

    Yields
    ------
    float
        The next value in the range.
    """
    r = start
    while r < stop:
        yield r
        r += step


def getHistIndex(hIdx, val):
    """Get the index of a specific [val] within a list of histogram values

    Parameters
    ----------
    hIdx : list
        List of histogram values.
    val : float
        Value to search for.

    Returns
    -------
    int
        Index in hIdx where val falls.
    """

    lastH = 0
    for h in range(0, len(hIdx)):
        curH = hIdx[h]
        if curH > val:
            return lastH
        lastH = h
    return len(hIdx) - 1


def listSum(inD):
    """get the total value of a list

    Parameters
    ----------
    inD : list
        List of numbers.

    Returns
    -------
    float
        Total value of the list.
    """
    total = 0
    for x in inD:
        total += x
    return total


def getHistPer(inD):
    """Convert list of values into percentage of a total

    Parameters
    ----------
    inD : list
        List of numbers.

    Returns
    -------
    list
        List of percentages corresponding to the input values.
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
    """Create a vector fishnet inside the defined range

    Parameters
    ----------
    xmin : float
        Minimum x-coordinate of the fishnet.
    xmax : float
        Maximum x-coordinate of the fishnet.
    ymin : float
        Minimum y-coordinate of the fishnet.
    ymax : float
        Maximum y-coordinate of the fishnet.
    gridHeight : float
        Height of each grid cell.
    gridWidth : float
        Width of each grid cell.
    type : str, optional
        Geometry type of the fishnet, by default "POLY"
    crsNum : int, optional
        Coordinate reference system number, by default 4326
    outputGridfn : str, optional
        Path to the output grid file, by default ""

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame containing the fishnet grid
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
    """Convert multi-part geometries into separate rows in a GeoDataFrame

    Parameters
    ----------
    indf : _type_
        _description_
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
    return gpd.GeoDataFrame(
        pd.concat(all_dfs), geometry="geometry", crs=indf.crs
    ).reset_index()
