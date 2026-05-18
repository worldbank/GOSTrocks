import os
import rasterio

import pandas as pd
import geopandas as gpd
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

from shapely.geometry import Point
from .dataMisc import aws_search_ntl
from .misc import tPrint
from . import rasterMisc as rMisc


def extract_monthly_ntl(aoi, out_folder, sel_files=[]):
    """Extract monthly nighttime lights imagery from AWS S3 bucket for the given area of
            interest (AOI) and save to the specified output folder.

    Parameters
    ----------
    aoi : geopandas.GeoDataFrame
        Area of interest to extract imagery for, should be a polygonal dataframe
    out_folder : str
        path to the folder to save the extracted imagery to
    sel_files : list, optional
        list of files to extract, if nothing is provided, it will default to all files returned from
            gostrocks.dataMisc.aws_search_ntl(), by default []
    """
    if len(sel_files) == 0:
        sel_files = aws_search_ntl()

    # Create the output folder if it does not exist
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)

    all_res = []
    for cur_file in sel_files:
        out_file = os.path.join(out_folder, os.path.basename(cur_file))
        if not os.path.exists(out_file):
            tPrint(f"Extracting {os.path.basename(cur_file)} to {out_folder}")
            with rasterio.Env(GDAL_HTTP_UNSAFESSL="YES"):
                curRaster = rasterio.open(cur_file)
                if curRaster.crs != aoi.crs:
                    aoi = aoi.to_crs(curRaster.crs)
                data, out_meta = rMisc.clipRaster(curRaster, aoi, out_file, crop=False)
                all_res.append([data, out_meta, out_file])
    return all_res


def read_raster_box(curRaster, geometry, bandNum=1):
    """read section of a rasterio object with a specified geometry

    Parameters
    ----------
    curRaster : rasterio object
        raster file to read from
    geometry : shapely.geometry
        Geometery to read from raster
    bandNum : int, optional
        band in curRaster to read, by default 1

    Returns
    -------
    numpy array
        array of raster values from curRaster within geometry
    """
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
    with rasterio.Env(GDAL_HTTP_UNSAFESSL="YES"):
        all_layers = df["PATH"].apply(
            lambda x: read_raster_box(rasterio.open(x), extent)
        )
    all_vals = np.dstack(all_layers)
    if agg_method == "MEAN":
        final_vals = np.nanmean(all_vals, axis=2)

    return final_vals


def generate_annual_composites(aoi, agg_method="MEAN", sel_files=[], out_folder=""):
    """Collapse several monthly nighttime lights images into an annual composite

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
    yr = [int(x[:4]) for x in yr_month]
    information = pd.DataFrame(
        [yr, yr_month, sel_files], index=["YEAR", "MONTH", "PATH"]
    ).transpose()
    with rasterio.Env(GDAL_HTTP_UNSAFESSL="YES"):
        annual_vals = information.groupby("YEAR").apply(
            lambda x: calc_annual(x, aoi.union_all(), agg_method)
        )

    # Write the files to output
    if out_folder != "":
        if not os.path.exists(out_folder):
            os.makedirs(out_folder)
        with rasterio.Env(GDAL_HTTP_UNSAFESSL="YES"):
            out_meta = rasterio.open(information["PATH"].iloc[0]).profile.copy()
        for label, res in annual_vals.items():
            # print([*aoi.bounds, res.shape[0], res.shape[1]])
            out_meta.update(
                width=res.shape[0],
                height=res.shape[1],
                transform=rasterio.transform.from_bounds(
                    *aoi.union_all().bounds, res.shape[0], res.shape[1]
                ),
            )
            out_file = os.path.join(out_folder, f"VIIRS_{label}_annual.tif")
            with rasterio.Env(GDAL_HTTP_UNSAFESSL="YES"):
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

def run_zonal_flares(inD, flares_file, ntl_images=[], buffer_dist=5000, minval=0.1, verbose=False, calc_sd=True):
    """Run zonal statistics against a series of nighttime lights files, masking values to 0 around flares

    :param inD: input geopandas dataframe in which to summarize results
    :type inD: gpd.GeoDataFrames
    :param ntl_images: list of ntl images to summarize, defaults to [] which will search for all files in the s3 bucket using datMisc.aws_search_ntl()
    :type ntl_images: list, optional
    :param flares_file: path to flares file
    :type flares_file: str
    :param minval: Minimum value to summarize in nighttime lights, defaults to 0.1 which means all values below this become 0
    :type minval: float, optional
    :param verbose: print additional information, defaults to False
    :type verbose: bool, optional
    :param calc_sd: calculate standard deviation, defaults to True
    :type calc_sd: bool, optional
    """
    if len(ntl_images) == 0:
        ntl_images = aws_search_ntl()

    if verbose:
        tPrint(f"Creating flare mask with buffer distance of {buffer_dist} meters")
    # read in the flares file and create a mask
    flaring_d = pd.read_excel(flares_file)
    flaring_d["ID"] = flaring_d.index
    flaring_geoms = [Point(x) for x in zip(flaring_d["Longitude"], flaring_d["Latitude"])]
    flaring_d = gpd.GeoDataFrame(flaring_d, geometry=flaring_geoms, crs=4326)
    buffered_flare = flaring_d.copy().to_crs("ESRI:54009")

    buffered_flare["geometry"] = buffered_flare["geometry"].apply(
        lambda x: x.buffer(buffer_dist)
    )
    buffered_flare = buffered_flare.to_crs(4326)

    with rasterio.Env(GDAL_HTTP_UNSAFESSL='YES'):
        ntl_r = rasterio.open(ntl_images[0])
        ntl_window = rasterio.windows.from_bounds(*inD.total_bounds, transform=ntl_r.transform)
        ntl_data = ntl_r.read(1, window=ntl_window)
        masked_ntl_data = ntl_data.copy()

        temp_meta = ntl_r.meta.copy()
        temp_meta.update({
            "height": ntl_window.height,
            "width": ntl_window.width,
            "transform": rasterio.windows.transform(ntl_window, ntl_r.transform)
        })
    # Loop through the NTL images and calculate zonal stats for each, saving results to a CSV file
    final_ntl_res = inD.copy()
    for idx, ntl_image in enumerate(ntl_images):
        ntl_name = ntl_image.split("/")[-1].split("_")[2][:6]
        if verbose:
            tPrint(f"Processing {ntl_name} ({idx+1}/{len(ntl_images)})")
        # Set rasterio environment to ignore SSL certificate issues with AWS
        with rasterio.Env(GDAL_HTTP_UNSAFESSL='YES'):
            with rasterio.open(ntl_image) as ntl_r:                
                if inD.crs != ntl_r.crs:
                    inD = inD.to_crs(ntl_r.crs)
                # Calculate zonal stats on the raw NTL data
                raw_ntl = rMisc.zonalStats(inD, ntl_image, minVal=minval, reProj=True)
                raw_ntl = pd.DataFrame(raw_ntl, columns=["SUM", "MIN", "MAX", "MEAN"])
                final_ntl_res[f"{ntl_name}_RAW"] = raw_ntl["SUM"]
                
                ntl_data = ntl_r.read(1, window=ntl_window)
                masked_ntl_data = ntl_data.copy()

                with rMisc.create_rasterio_inmemory(temp_meta, ntl_data) as ntl_raster:
                    flare_mask = rMisc.rasterizeDataFrame(buffered_flare, None, templateRaster=ntl_raster, nodata=0)
                    flare_mask = (~flare_mask["vals"].astype(bool)).astype(int)
                    bool_flare_mask = flare_mask.astype(bool)
                    if bool_flare_mask.shape != masked_ntl_data.shape:
                        new_mask = np.zeros(masked_ntl_data.shape, dtype=bool)
                        new_mask[:bool_flare_mask.shape[0], :bool_flare_mask.shape[1]] = bool_flare_mask
                        bool_flare_mask = new_mask
                    masked_ntl_data[~bool_flare_mask] = 0
                
                with rMisc.create_rasterio_inmemory(ntl_r.profile, masked_ntl_data) as masked_ntl_raster:
                    masked_ntl = rMisc.zonalStats(inD, masked_ntl_raster, minVal=minval, return_df=True)
                    final_ntl_res[f"{ntl_name}_MASKED"] = masked_ntl["SUM"]        