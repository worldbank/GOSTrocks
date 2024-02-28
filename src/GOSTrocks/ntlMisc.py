import sys
import os
import inspect
import rasterio

import pandas as pd
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

curPath = os.path.realpath(
    os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])
)
if curPath not in sys.path:
    sys.path.append(curPath)

from dataMisc import aws_search_ntl
from misc import tPrint
import rasterMisc as rMisc


def read_raster_box(curRaster, geometry, bandNum=1):
    # get pixel coordinates of the geometry's bounding box
    ul = curRaster.index(*geometry.bounds[0:2])
    lr = curRaster.index(*geometry.bounds[2:4])
    # read the subset of the data into a numpy array
    window = ((float(lr[0]), float(ul[0] + 1)), (float(ul[1]), float(lr[1] + 1)))
    data = curRaster.read(bandNum, window=window)
    return data


def calc_annual(df, extent, agg_method="MEAN"):
    """Combine monthly nighttime lights images into an annual composite

    :param df: data frame of images with three columns: YEAR, MONTH, PATH
    :type df: pandas.DataFrame
    :param extent: area to extract imagery from
    :type extent: shapely.Polygon
    """
    all_layers = df["PATH"].apply(lambda x: read_raster_box(rasterio.open(x), extent))
    all_vals = np.dstack(all_layers)
    if agg_method == "MEAN":
        final_vals = np.nanmean(all_vals, axis=2)

    return final_vals


def generate_annual_composites(aoi, agg_method="MEAN", sel_files=[], out_folder=""):
    """_summary_

    :param aoi: geopandas polygonal dataframe to use for clip clip extent based on crop param
    :type aoi: geopandas.GeoDataFrame
    :param method: How to aggregate monthly nighttime lights layers into annual layers, defaults to MEAN
    :type method: str, optional
    :param sel_files: list of ntl files to process, defaults to [], which will use gostrocks.dataMisc.aws_search_ntl to find all variables
    :type sel_files: list, optional
    """
    if len(sel_files) == 0:
        sel_files = aws_search_ntl()
    yr_month = [x.split("_")[1] for x in sel_files]
    yr = [x[:4] for x in yr_month]
    information = pd.DataFrame(
        [yr, yr_month, sel_files], index=["YEAR", "MONTH", "PATH"]
    ).transpose()
    annual_vals = information.groupby("YEAR").apply(lambda x: calc_annual(x, aoi))

    # Write the files to output
    if out_folder != "":
        if not os.path.exists(out_folder):
            os.makedirs(out_folder)
        out_meta = rasterio.open(information["PATH"].iloc[0]).profile.copy()
        for label, res in annual_vals.items():
            out_meta.update(
                width=res.shape[0],
                height=res.shape[1],
                transform=rasterio.transform.from_bounds(
                    *aoi.bounds, res.shape[0], res.shape[1]
                ),
            )
            out_file = os.path.join(out_folder, f"VIIRS_{label}_annual.tif")
            with rasterio.open(out_file, "w", **out_meta) as out_r:
                out_r.write_band(1, res)
    return annual_vals


def map_viirs(
    cur_file,
    out_file="",
    class_bins=[-10, 0.5, 1, 2, 3, 5, 10, 15, 20, 30, 40, 50],
    text_x=0,
    text_y=5,
    dpi=100,
):
    """Map VIIRS nighttime lights imagery, optionally create output image

    :param cur_file: path to input geotiff
    :type cur_file: string
    :param out_file: path to create output image, defaults to '' which does not create a file
    :type out_file: str, optional
    :param class_bins: breaks for applying colour ramp, defaults to [-10,0.5,1,2,3,5,10,15,20,30,40,50]
    :type class_bins: list, optional
    :param text_x: position on map to position year text (left to right), defaults to 0
    :type text_x: int, optional
    :param text_y: position on map to position year text (top to bottom), defaults to 5
    :type text_y: int, optional
    :param dpi: dotes per inch for output image, defaults to 100
    :type dpi: int, optional
    """
    # extract the year from the file name
    year = cur_file.split("_")[-1][:4]

    # Open the VIIRS data and reclassify
    inR = rasterio.open(cur_file)
    inD = inR.read()
    inC = xr.apply_ufunc(np.digitize, inD, class_bins)

    # Plot the figure, remove grid and ticks
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])

    ### TODO: add the year to the map, may need to experiment with the location depend on geography
    ax.text(text_x, text_y, year, fontsize=40, color="white")

    # plt.margins(0,0)
    if out_file != "":
        # plt.imsave(out_file, inC[0,:,:], cmap=plt.get_cmap('magma'))
        plt.imshow(inC[0, :, :], cmap=plt.get_cmap("magma"))
        fig.savefig(out_file, dpi=dpi, bbox_inches="tight", pad_inches=0)
    else:
        # https://matplotlib.org/stable/tutorials/colors/colormaps.html
        plt.imshow(inC[0, :, :], cmap=plt.get_cmap("magma"))


def run_zonal(inD, ntl_files=[], minval=0.1, verbose=False, calc_sd=True):
    """Run zonal statistics against a series of nighttime lights files

    :param inD: input geopandas dataframe in which to summarize results
    :type inD: gpd.GeoDataFrames
    :param ntl_files: list of ntl files to summarize, defaults to [] which will search for all files in the s3 bucket using datMisc.aws_search_ntl()
    :type ntl_files: list, optional
    :param minval: Minimum value to summarize in nighttime lights, defaults to 0.1 which means all values below this become 0
    :type minval: float, optional
    :param verbose: print additional information, defaults to False
    :type verbose: bool, optional
    :param calc_sd: _description_, defaults to True
    :type calc_sd: bool, optional
    """

    """ run zonal stats on all ntl files
    INPUT
        inD [geopandas dataframe]

    RETURNS
        pandas dataframe
    """
    if len(ntl_files) == 0:
        ntl_files = aws_search_ntl()

    for ntl_file in ntl_files:
        name = ntl_file.split("/")[-1].split("_")[2][:8]
        if verbose:
            tPrint(name)
        inR = rasterio.open(ntl_file)
        ntl_res = rMisc.zonalStats(inD, inR, minVal=minval, calc_sd=calc_sd)
        out_cols = ["SUM", "MIN", "MAX", "MEAN"]
        if calc_sd:
            out_cols.append("SD")
        ntl_df = pd.DataFrame(ntl_res, columns=out_cols)
        inD[f"ntl_{name}_SUM"] = ntl_df["SUM"]
    return inD
