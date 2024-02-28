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


def tabulateUnq(unqResults, verbose=False, columnPrefix="c"):
    allVals = []
    for r in unqResults:
        allVals.append(r[0].tolist())
    flattened = [val for sublist in allVals for val in sublist]
    unq = np.unique(np.array(flattened)).tolist()
    # unqCols = ["c_%s" % xxx for xxx in unq]
    allRes = []
    for r in unqResults:
        try:
            curRes = [0] * len(unq)
            for idx in range(0, len(r[0].tolist())):
                curRes[unq.index(r[0].tolist()[idx])] = r[1].tolist()[idx]
        except:
            print(r)
        allRes.append(curRes)
    return pd.DataFrame(allRes, columns=["%s_%s" % (columnPrefix, xxx) for xxx in unq])


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
    """Create a fishnet shapefile inside the defined coordinates

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

    def get_box(row, col, l, r, b, t, gridWidth, gridHeight):
        ll = Point(l + (row * gridWidth), b + (col + gridHeight))
        ul = Point(l + (row * gridWidth), t + (col + gridHeight))
        ur = Point(r + (row * gridWidth), t + (col + gridHeight))
        lr = Point(r + (row * gridWidth), b + (col + gridHeight))
        box = Polygon([ll, ul, ur, lr, ll])
        return box

    def get_point(row, col, l, r, b, t, gridWidth, gridHeight):
        pt = Point((l + r) / 2 + (col * gridWidth), (t + b) / 2 - (row * gridHeight))
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
    outdf = gpd.GeoDataFrame(columns=indf.columns)
    outdf.crs = indf.crs
    for idx, row in indf.iterrows():
        row.geometry.type
        if row.geometry.type in ["Polygon", "Point"]:
            outdf = outdf.append(row, ignore_index=True)
        if row.geometry.type in ["MultiPoint", "MultiPolygon"]:
            multdf = gpd.GeoDataFrame(columns=indf.columns)
            recs = len(row.geometry)
            multdf = multdf.append([row] * recs, ignore_index=True)
            for geom in range(recs):
                multdf.loc[geom, "geometry"] = row.geometry[geom]
            outdf = outdf.append(multdf, ignore_index=True)
    return outdf


def project_UTM(inD):
    """Project an input data frame to UTM coordinates.

    :param inD: input geodataframe to explode
    :type inD: gpd.GeoDataFrame
    :return: exploded geodaatframe
    :rtype: gpd.GeoDataFrame
    """
    import utm

    # get UTM zones for upper right and lower left of input dataframe

    if inD.crs != {"init": "epsg:4326"}:
        raise (ValueError("Cannot process input dataframe that is not WGS84"))

    inBounds = inD.total_bounds
    ll_utm = utm.from_latlon(inBounds[1], inBounds[0])
    ur_utm = utm.from_latlon(inBounds[3], inBounds[2])

    if (ll_utm[2] != ur_utm[2]) or (ll_utm[3] != ur_utm[3]):
        raise (
            ValueError(
                "The input shape spans multiple UTM zones: %s_%s to %s_%s"
                % (ll_utm[2], ll_utm[3], ur_utm[2], ur_utm[3])
            )
        )

    letter = "6"
    if ll_utm[3] == "U":
        letter = "7"
    outUTM = "32%s%s" % (letter, ll_utm[2])
    return inD.to_crs({"init": "epsg:%s" % outUTM})


def get_utm(gdf, bbox=True):
    if bbox:
        center = box(*gdf.total_bounds).centroid
    else:
        center = gdf.unary_union.centroid
    utm_crs_list = query_utm_crs_info(
        datum_name="WGS 84",
        area_of_interest=AreaOfInterest(
            west_lon_degree=center.x,
            south_lat_degree=center.y,
            east_lon_degree=center.x,
            north_lat_degree=center.y,
        ),
    )
    utm_crs = CRS.from_epsg(utm_crs_list[0].code)
    return utm_crs
