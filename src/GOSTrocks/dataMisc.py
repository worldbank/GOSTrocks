import os
import json
import urllib
import boto3
import boto3.session
import rasterio

import pandas as pd
import geopandas as gpd

from botocore.config import Config
from botocore import UNSIGNED
from osgeo import gdal

import rasterMisc as rMisc


def download_WSF(
    extent,
    wsf_url="https://download.geoservice.dlr.de/WSF2019/files/WSF2019_cog.tif",
    out_file="",
):
    """_summary_

    Parameters
    ----------
    extent : _type_
        _description_
    wsf_url : str, optional
        _description_, by default "https://download.geoservice.dlr.de/WSF2019/files/WSF2019_cog.tif"
    """

    # Open the WSF COG
    wsf_raster = rasterio.open(wsf_url)
    data, profile = rMisc.clipRaster(raster=wsf_raster, bounds=extent)
    if out_file != "":
        with rasterio.open(out_file, "w", **profile) as dst:
            dst.write(data)
    return (data, profile)


def aws_search_ntl(
    bucket="globalnightlight",
    prefix="composites",
    region="us-east-1",
    unsigned=True,
    verbose=False,
):
    """get list of nighttime lights files from open AWS bucket - https://registry.opendata.aws/wb-light-every-night/

    :param bucket: bucket to search for imagery, defaults to 'globalnightlight'
    :type bucket: str, optional
    :param prefix: prefix storing images. Not required for LEN, defaults to 'composites'
    :type prefix: str, optional
    :param region: AWS region for bucket, defaults to 'us-east-1'
    :type region: str, optional
    :param unsigned: if True, search buckets without stored boto credentials, defaults to True
    :type unsigned: bool, optional
    :param verbose: print additional support messages, defaults to False
    :type verbose: bool, optional
    """
    if unsigned:
        s3client = boto3.client("s3", verify=False, config=Config(signature_version=UNSIGNED))
    else:
        s3client = boto3.client("s3", verify=False)

    # Loop through the S3 bucket and get all the keys for files that are .tif
    more_results = True
    loops = 0
    good_res = []
    while more_results:
        if verbose:
            print(f"Completed loop: {loops}")
        if loops > 0:
            objects = s3client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                ContinuationToken=token,  # noqa
            )
        else:
            objects = s3client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        more_results = objects["IsTruncated"]
        if more_results:
            token = objects["NextContinuationToken"]  # noqa
        loops += 1
        for res in objects["Contents"]:
            if res["Key"].endswith("avg_rade9.tif") and ("slcorr" in res["Key"]):
                good_res.append(
                    f"https://globalnightlight.s3.amazonaws.com/{res['Key']}"
                )

    return good_res


def get_geoboundaries(
    iso3,
    level,
    geo_api="https://www.geoboundaries.org/api/current/gbOpen/{iso3}/{adm}/",
):
    """Download boundaries dataset from geobounadries

    :param iso3: ISO3 code of country to download
    :type iso3: str
    :param level: Admin code to download in format of "ADM1" or "ADM2"
    :type level: str
    :return: spatial data representing the administrative boundaries
    :rtype: gpd.GeoDataFrame
    """
    cur_url = geo_api.format(iso3=iso3, adm=level)
    try:
        with urllib.request.urlopen(cur_url) as url:
            data = json.load(url)
            geo_data = gpd.read_file(data["gjDownloadURL"])
            return geo_data
    except Exception:
        all_url = geo_api.format(iso3=iso3, adm="ALL")
        raise (
            ValueError(
                f"Cannot find admin dataset {cur_url}. Check out {all_url} for details on what is available"
            )
        )


def get_fathom_vrts(return_df=False):
    """Get a list of VRT files of Fathom data from the GOST S3 bucket. Note that the
    VRT files are not searched dynamically but are stored in a text file in the same
    folder as the function.

    return_df: if True, return a pandas dataframe with the VRT files and their components, defaults to False which returns just the list of VRT files
    """
    vrt_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "fathom_vrts.txt"
    )
    all_vrts = []
    with open(vrt_file, "r") as f:
        for line in f:
            all_vrts.append(line.strip())
    if return_df:
        vrt_pd = pd.DataFrame(
            [x.split("-")[4:10] for x in all_vrts],
            columns=[
                "RETURN",
                "FLOOD_TYPE",
                "DEFENCE",
                "DEPTH",
                "YEAR",
                "CLIMATE_MODEL",
            ],
        )
        vrt_pd["PATH"] = all_vrts
        return vrt_pd
    return all_vrts

def get_worldcover(df, download_folder, worldcover_vrt='WorldCover.vrt',
                   version='v200',
                   print_command=False, verbose=False):
    """ Download ESA globcover from AWS (https://aws.amazon.com/marketplace/pp/prodview-7oorylcamixxc)

    Parameters
    ----------
    df : geopandas.GeoDataFrame
        Data frame used to select tiles to download; selects tiles based on the data frame unary_union
    download_folder : string 
        path to folder to download tiles
    worldcover_vrt : str, optional
        name of the VRT file to create, by default 'WorldCover.vrt'
    version : str, optional
        version of Worldcover to download, by default 'v200', other option is 'v100
    print_command : bool, optional
        if true, print the awscli commands to download the tiles. If false, uses boto3
        to download the tiles, by default False
    verbose : bool, optional
        Print more updates during processing, by default False
    """
    
    bucket='esa-worldcover'
    esa_file_geojson = 'esa_worldcover_grid.geojson'
    s3 = boto3.client('s3', verify=False, config=Config(signature_version=UNSIGNED))
    tiles_geojson = os.path.join(download_folder, esa_file_geojson)

    if not os.path.exists(tiles_geojson):
        s3.download_file(bucket, esa_file_geojson, tiles_geojson)

    tile_path = "{version}/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
    
    in_tiles = gpd.read_file(tiles_geojson)
    sel_tiles = in_tiles.loc[in_tiles.intersects(df.unary_union)]

    all_tiles = []
    for idx, row in sel_tiles.iterrows():
        cur_tile_path = tile_path.format(tile=row['ll_tile'], version=version)
        cur_out = os.path.join(download_folder, f"WorldCover_{row['ll_tile']}.tif")
        all_tiles.append(cur_out)
        if not os.path.exists(cur_out):
            if print_command:
                command = f"aws s3 --no-sign-request --no-verify-ssl cp s3://{bucket}/{cur_tile_path} {cur_out}"
                print(command)
            else:
                if not os.path.exists(cur_out):
                    if verbose:
                        print(f"Downloading {cur_tile_path} to {cur_out}")
                    s3.download_file(bucket,cur_tile_path, cur_out)
                else:
                    if verbose:
                        print(f"File {cur_out} already exists")
    out_vrt = os.path.join(download_folder, worldcover_vrt)
    gdal.BuildVRT(out_vrt, all_tiles, options=gdal.BuildVRTOptions())
    
    return(all_tiles)

