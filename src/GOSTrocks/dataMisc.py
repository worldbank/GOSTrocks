import os
import json
import urllib
import boto3
import rasterio
import requests
import warnings
import urllib.request
import urllib.parse

import pandas as pd
import geopandas as gpd

from botocore.config import Config
from botocore import UNSIGNED

from . import rasterMisc as rMisc


def download_WSF(
    extent,
    wsf_url="https://download.geoservice.dlr.de/WSF2019/files/WSF2019_cog.tif",
    out_file="",
):
    """Download the World Settlement Footprint (WSF) dataset from DLR.
        The WSF dataset is a global raster dataset that provides information on the spatial distribution of built area

    Parameters
    ----------
    extent : shapely.geometry.Polygon
        Polygon to clip the WSF dataset to
    wsf_url : str, optional
        WSF download link, by default "https://download.geoservice.dlr.de/WSF2019/files/WSF2019_cog.tif"
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
    unsigned=True,
    verbose=False,
):
    """get list of nighttime lights files from open AWS bucket - https://registry.opendata.aws/wb-light-every-night/

    Parameters
    ----------
    bucket : str, optional
        bucket to search for imagery, defaults to 'globalnightlight', by default "globalnightlight"
    prefix : str, optional
        prefix storing images. Not required for LEN, defaults to 'composites', by default "composites"
    unsigned : bool, optional
        prefix storing images. Not required for LEN, defaults to 'composites', by default True
    verbose : bool, optional
        print additional support messages, defaults to False, by default False

    Returns
    -------
    _type_
        _description_
    """
    if unsigned:
        s3client = boto3.client(
            "s3", verify=False, config=Config(signature_version=UNSIGNED)
        )
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

    Parameters
    ----------
    iso3 : bool
        ISO3 code of country to download
    level : str
        Admin code to download in format of "ADM1" or "ADM2"
    geo_api : str, optional
        by default "https://www.geoboundaries.org/api/current/gbOpen/{iso3}/{adm}/"

    Returns
    -------
    gpd.GeoDataFrame
        spatial data representing the administrative boundaries
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

    return_df: if True, return a pandas dataframe with the VRT files and their components,
            defaults to False which returns just the list of VRT files
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


def get_worldcover(
    df,
    download_folder,
    worldcover_vrt="WorldCover.vrt",
    version="v200",
    print_command=False,
    verbose=False,
):
    """Download ESA globcover from AWS (https://aws.amazon.com/marketplace/pp/prodview-7oorylcamixxc)

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

    bucket = "esa-worldcover"
    esa_file_geojson = "esa_worldcover_grid.geojson"
    s3 = boto3.client("s3", verify=False, config=Config(signature_version=UNSIGNED))
    tiles_geojson = os.path.join(download_folder, esa_file_geojson)

    if not os.path.exists(tiles_geojson):
        s3.download_file(bucket, esa_file_geojson, tiles_geojson)

    tile_path = "{version}/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"

    in_tiles = gpd.read_file(tiles_geojson)
    sel_tiles = in_tiles.loc[in_tiles.intersects(df.unary_union)]

    all_tiles = []
    for idx, row in sel_tiles.iterrows():
        cur_tile_path = tile_path.format(tile=row["ll_tile"], version=version)
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
                    s3.download_file(bucket, cur_tile_path, cur_out)
                else:
                    if verbose:
                        print(f"File {cur_out} already exists")
    try:
        from osgeo import gdal  # noqa

        out_vrt = os.path.join(download_folder, worldcover_vrt)
        gdal.BuildVRT(out_vrt, all_tiles, options=gdal.BuildVRTOptions())
    except Exception:
        print("GDAL not installed, cannot create VRT")

    return all_tiles


def gdf_esri_service(url, layer=0, verify_ssl=True):
    """Download a GeoPandas dataframe from an ESRI service

    Parameters
    ----------
    url : str
        URL to the ESRI service without the layer number
    layer : int, optional
        Layer number to download, by default 0

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame of the data

    https://medium.com/@jesse.b.nestler/how-to-extract-every-feature-from-an-esri-map-service-using-python-b6e34743574a
    """
    # Look at metadata of url
    with urllib.request.urlopen(f"{url}/?f=pjson") as service_url:
        service_data = json.loads(service_url.read().decode())

    queryable = ["Query" in service_data["capabilities"]]

    if queryable:
        query_url = f"{url}/{layer}/query"
        # get total number of records in complete service
        n_queries = service_data["maxRecordCount"]
        count_query = {
            "outFields": "*",
            "where": "1=1",
            "returnCountOnly": True,
            "f": "json",
        }
        count_str = urllib.parse.urlencode(count_query)
        with urllib.request.urlopen(f"{query_url}?{count_str}") as count_url:
            count_json = json.loads(count_url.read().decode())
            n_records = count_json["count"]
        if n_records < n_queries:  # We can download all the data in a single query
            all_records_query = {
                "outFields": "*",
                "where": "1=1",
                "returnGeometry": True,
                "f": "geojson",
            }
            query_str = urllib.parse.urlencode(all_records_query)
            all_query_url = f"{query_url}?{query_str}"
            with requests.get(
                all_query_url, verify=verify_ssl, stream=False
            ) as geojson_result:
                return gpd.read_file(geojson_result.text)
        else:
            step_query = {
                "outFields": "*",
                "where": "1=1",
                "returnGeometry": True,
                "f": "geojson",
                "resultRecordCount": n_queries,
                "resultOffset": 0,
            }
            for offset in range(0, n_records, n_queries):
                step_query["resultOffset"] = offset
                query_str = urllib.parse.urlencode(step_query)
                step_query_url = f"{query_url}?{query_str}"
                with requests.get(
                    step_query_url, verify=verify_ssl, stream=False
                ) as step_query_result:
                    cur_res = gpd.read_file(step_query_result.text)
                if offset == 0:
                    gdf = cur_res
                else:
                    gdf = pd.concat([gdf, cur_res])
            return gdf
    else:
        raise ValueError("Service is not queryable :(")


def get_acled_creds():
    """Get the ACLED credentials from a .acled file in the user's home directory

    Returns
    -------
    Dictionary
        email and API key for ACLED
    """
    acled_file = os.path.join(os.path.expanduser("~"), ".acled")
    with open(acled_file, "r") as f:
        email = f.readline().strip().split("=")[1]
        api_key = f.readline().strip().split("=")[1]
    return {"email": email, "api_key": api_key}


def acled_search(
    api_key, email, bounding_box=None, iso3=None, start_date=None, fields=[]
):
    """Search the ACLED API for data based on either a bounding box, ISO3 code, or start date
        https://apidocs.acleddata.com/acled_endpoint.html

    Parameters
    ----------
    api_key : string
        ACLED api key foud on your ACLED dashboard
    email : string
        ACLED email found on your ACLED dashboard
    bounding_box : array of float, optional
        bounding box to search for, defined as minx, miny, maxx, maxy (shpely.geometry.bounds)
    iso3 : string, optional
        numeric iso code for the country. Can be found using pycountry.countries.get(alpha_3=iso3).numeric
    start_date : string, optional
        starting date to search for events, in the format of "YYYY-MM-DD"

    Returns
    -------
    pd.DataFrame
        results of the search converted into DataFrame

    Raises
    ------
    ValueError
        If API call fails for whatever reason
    """

    acled_url = "https://api.acleddata.com/acled/read"
    acled_params = {
        "email": email,
        "key": api_key,
    }

    # Add optional parameters
    if bounding_box is not None:
        acled_params["longitude"] = "|".join(
            [str(bounding_box[0]), str(bounding_box[2])]
        )
        acled_params["longitude_where"] = "BETWEEN"
        acled_params["latitude"] = "|".join(
            [str(bounding_box[1]), str(bounding_box[3])]
        )
        acled_params["latitude_where"] = "BETWEEN"
    if iso3 is not None:
        acled_params["iso"] = iso3
    if start_date is not None:
        acled_params["event_date"] = start_date
        acled_params["event_date_where"] = ">"
    if len(fields) > 0:
        acled_params["fields"] = "|".join(fields)

    page = 1
    default_page_size = 5000
    continue_pagination = True

    all_results = []
    while continue_pagination:
        acled_params["page"] = page
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=Warning)
            res = requests.get(acled_url, params=acled_params, verify=False)
        # print(res.url)
        if res.json()["status"] == 200:
            cur_res = pd.DataFrame(res.json()["data"])
            all_results.append(cur_res)
            if res.json()["count"] < default_page_size:
                continue_pagination = False
            page += 1
        else:
            raise ValueError(f"ACLED API call failed on page {res.url}")

    return pd.concat(all_results)
