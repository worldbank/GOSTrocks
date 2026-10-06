import functools
import glob
import gzip
import json
import multiprocessing
import os
import shutil
import ssl
import tempfile
import urllib.parse
import urllib.request
import warnings
from io import BytesIO
from multiprocessing.pool import ThreadPool
from typing import Any, Callable, Iterable, List, Optional, Tuple

import boto3
import geopandas as gpd
import pandas as pd
import pyproj
import rasterio
import requests
import s2sphere
import shapely
import tqdm.notebook
from botocore import UNSIGNED
from botocore.config import Config
from google.auth import credentials
from google.cloud import storage
from IPython import display
from rasterio.transform import Affine
from shapely.geometry import Polygon, box
from shapely.ops import transform

from . import rasterMisc as rMisc


def download_google_2_5d(extent, year, out_folder="google_2_5d", crs="EPSG:4326", overwrite=False,
                         create_vrt=False):
    """Download Open Buildings 2.5D Temporal v1 tiles intersecting an area.

    Parameters
    ----------
    extent : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Area of interest, in the coordinate reference system specified by crs.
    year : int
        Dataset year, from 2016 through 2023 inclusive.
    out_folder : str or os.PathLike, optional
        Download directory. Cloud object subdirectories are preserved to avoid
        filename collisions. Existing files are reused unless overwrite is True.
    crs : str or pyproj.CRS, optional
        Coordinate reference system of extent; defaults to WGS84 longitude/latitude.
    overwrite : bool, optional
        Replace existing downloaded tiles.
    create_vrt : bool, optional
        Write google_2_5d.vrt in out_folder without osgeo bindings. Tiles must
        share a CRS, north-up pixel grid, band types, and no-data values.
        No VRT is written when no tiles are found. Defaults to False.

    Returns
    -------
    list of str
        Local paths of the intersecting GeoTIFFs, sorted by cloud object name.
        An empty list indicates no coverage for this area and year.

    Notes
    -----
    Uses anonymous access to the public open-buildings-temporal-data bucket.
    Downloads complete tiles, including all available dataset channels; it does
    not clip or mosaic them. Tiles can be large. Raster values and native CRSs
    are preserved. See https://sites.research.google/gr/open-buildings/temporal/.
    Antimeridian-spanning geometries must be split before calling this function.
    """
    if not isinstance(extent, (shapely.geometry.Polygon, shapely.geometry.MultiPolygon)):
        raise TypeError("extent must be a Shapely Polygon or MultiPolygon")
    if extent.is_empty or not extent.is_valid:
        raise ValueError("extent must be nonempty and valid")
    if isinstance(year, bool) or not isinstance(year, int) or not 2016 <= year <= 2023:
        raise ValueError("year must be an integer from 2016 through 2023")

    to_wgs84 = pyproj.Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    region = transform(to_wgs84.transform, extent)
    west, south, east, north = region.bounds
    if not region.is_valid or not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
        raise ValueError("extent must transform to valid WGS84 coordinates")
    if east - west > 180:
        raise ValueError("Split antimeridian-spanning extents before downloading")

    covering = s2sphere.RegionCoverer()
    covering.min_level = 2
    covering.max_level = 2
    rectangle = s2sphere.LatLngRect.from_point_pair(
        s2sphere.LatLng.from_degrees(south, west),
        s2sphere.LatLng.from_degrees(north, east),
    )
    client = storage.Client.create_anonymous_client()
    bucket_name = "open-buildings-temporal-data"
    bucket = client.bucket(bucket_name)
    objects = set()
    for cell in covering.get_covering(rectangle):
        prefix = f"v1/manifests/{cell.to_token()}_"
        for blob in client.list_blobs(bucket_name, prefix=prefix):
            if f"_{year}_" not in blob.name:
                continue
            manifest = json.loads(blob.download_as_bytes())
            for tileset in manifest["tilesets"]:
                to_tile_crs = pyproj.Transformer.from_crs(
                    "EPSG:4326", tileset["crs"], always_xy=True
                )
                tile_region = transform(to_tile_crs.transform, region)
                for source in tileset["sources"]:
                    affine = source["affineTransform"]
                    tile_transform = Affine(
                        affine["scaleX"], affine.get("shearX", 0), affine["translateX"],
                        affine.get("shearY", 0), affine["scaleY"], affine["translateY"],
                    )
                    width = source["dimensions"]["width"]
                    height = source["dimensions"]["height"]
                    footprint = Polygon([
                        tile_transform * corner
                        for corner in [(0, 0), (width, 0), (width, height), (0, height)]
                    ])
                    if not footprint.intersects(tile_region):
                        continue
                    for uri in source["uris"]:
                        full_uri = manifest["uriPrefix"] + uri
                        parsed = urllib.parse.urlparse(full_uri)
                        if parsed.scheme != "gs" or parsed.netloc != bucket_name:
                            raise ValueError(f"Unexpected tile URI: {full_uri}")
                        object_name = parsed.path.lstrip("/")
                        parts = object_name.split("/")
                        if any(part in ("", ".", "..") or "\\" in part or ":" in part for part in parts):
                            raise ValueError(f"Unsafe tile path: {object_name}")
                        objects.add(object_name)

    paths = []
    for object_name in sorted(objects):
        destination = os.path.join(os.fspath(out_folder), *object_name.split("/"))
        if overwrite or not os.path.isfile(destination):
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            descriptor, temporary_path = tempfile.mkstemp(
                suffix=".part", dir=os.path.dirname(destination)
            )
            os.close(descriptor)
            try:
                bucket.blob(object_name).download_to_filename(temporary_path)
                os.replace(temporary_path, destination)
            finally:
                if os.path.exists(temporary_path):
                    os.remove(temporary_path)
        paths.append(destination)

    if create_vrt and paths:
        from rasterio.shutil import copy as copy_raster
        from rio_vrt import build_vrt

        with rasterio.open(paths[0]) as first_tile:
            tile_crs = first_tile.crs
            tile_transform = first_tile.transform
            tile_types = first_tile.dtypes
            tile_nodata = first_tile.nodatavals
            resolution = first_tile.res
        for path in paths:
            with rasterio.open(path) as tile:
                if tile.crs != tile_crs or tile_crs is None:
                    raise ValueError("VRT tiles must share a CRS; reproject mixed-CRS tiles first")
                if (tile.transform.b != 0 or tile.transform.d != 0
                        or tile.transform.a <= 0 or tile.transform.e >= 0
                        or tile.res != resolution):
                    raise ValueError("VRT tiles must share a north-up pixel resolution")
                offsets = (
                    (tile.transform.c - tile_transform.c) / resolution[0],
                    (tile.transform.f - tile_transform.f) / resolution[1],
                )
                if any(abs(offset - round(offset)) > 1e-6 for offset in offsets):
                    raise ValueError("VRT tiles must align on the same pixel grid")
                if tile.dtypes != tile_types or any(
                    str(actual) != str(expected)
                    for actual, expected in zip(tile.nodatavals, tile_nodata)
                ):
                    raise ValueError("VRT tiles must share band types and no-data values")
        vrt_path = os.path.join(out_folder, "google_2_5d.vrt")
        if len(paths) == 1:
            copy_raster(paths[0], vrt_path, driver="VRT")
        else:
            build_vrt(vrt_path, paths, relative=True, mosaic=True, res=resolution)
    return paths


def get_all_wb_iso3():
    """Get a list of all ISO3 codes for countries in the World Bank dataset

    Returns
    -------
    list
        List of ISO3 codes for countries in the World Bank dataset
    """
    url = 'https://services.arcgis.com/iQ1dY19aHwbSDYIF/ArcGIS/rest/services/World_Bank_Global_Administrative_Divisions/FeatureServer/1/query?where=%22FID%22%3E0&objectIds=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&resultType=none&distance=0.0&units=esriSRUnit_Meter&outDistance=&relationParam=&returnGeodetic=false&outFields=ISO_A3&returnGeometry=false&returnCentroid=false&returnEnvelope=false&featureEncoding=esriDefault&multipatchOption=xyFootprint&maxAllowableOffset=&geometryPrecision=&outSR=&defaultSR=&datumTransformation=&applyVCSProjection=false&returnIdsOnly=false&returnUniqueIdsOnly=false&returnCountOnly=false&returnExtentOnly=false&returnQueryGeometry=false&returnDistinctValues=false&cacheHint=false&collation=&orderByFields=&groupByFieldsForStatistics=&returnAggIds=false&outStatistics=&having=&resultOffset=&resultRecordCount=&returnZ=false&returnM=false&returnTrueCurves=false&returnExceededLimitFeatures=true&quantizationParameters=&sqlFormat=none&f=pjson&token='
    response = requests.get(url, verify=False)
    data = json.loads(response.content.decode())
    iso3_list = [feature['attributes']['ISO_A3'] for feature in data['features']]
    return iso3_list

def download_wb_boundaries(level: str,
                            iso3: str=None,                                                       
                            url: str='https://services.arcgis.com/iQ1dY19aHwbSDYIF/arcgis/rest/services/World_Bank_Global_Administrative_Divisions/FeatureServer/{level}/query?',
                            verify_ssl: bool=False                            
                           ):
    """ Download WB_GAD boundaries from ArcGIS REST API
    Parameters
    ----------
    level : str
        Administrative level to download, must be one of "ADM0_Lines", "ADM0_All", "ADM0_Countries", "ADM1", "ADM2", "NDLSA"
    iso3 : str, optional
        ISO3 code of country to download, by default None which downloads all countries
    url : str, optional 
        URL to the ArcGIS REST API, by default 'https://services.arcgis.com/iQ1dY19aHwbSDYIF/arcgis/rest/services/World_Bank_Global_Administrative_Divisions/FeatureServer/{level}/query?'
    verify_ssl : bool, optional
        Whether to verify SSL certificates when making the request, by default False
    """
    if level not in ["ADM0_Lines", "ADM0_All", "ADM0", "ADM1", "ADM2", "NDLSA"]:
        raise ValueError("Level must be one of 'ADM0_Lines', 'ADM0_All', 'ADM0', 'ADM1', 'ADM2', 'NDLSA'")
    level_dictionary = {
        "ADM0_Lines": "0",
        "ADM0_All": "4",
        "ADM0": "1",
        "ADM1": "2",
        "ADM2": "3",
        "NDLSA": "4"
    }
    query_params = {
        "outfields": "*",
        "f": "pgeojson"
    }
    if iso3 is not None:
        query_params["where"] = f"\"ISO_A3\"='{iso3}'"
    query_str = urllib.parse.urlencode(query_params)
    query_url = url.format(level=level_dictionary[level]) + query_str
    response = requests.get(query_url, verify=verify_ssl) # <--- Ignore SSL if verify_ssl is False
    adm_gdf = gpd.read_file(BytesIO(response.content))
    return(adm_gdf)
    


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
    # mute InsecureRequestWarning
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    # search through the S3 bucket s3://wbg-geography01/FATHOM/ for all vrt files
    s3 = boto3.client("s3", verify=False)
    bucket = "wbg-geography01"
    prefix = "FATHOM/"
    all_vrts = []
    token = None
    more_results = True
    while more_results:
        if token:
            objects = s3.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                ContinuationToken=token,  # noqa
                Delimiter="/",  # noqa
            )
        else:
            objects = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        more_results = objects["IsTruncated"]
        if more_results:
            token = objects["NextContinuationToken"]  # noqa
        for res in objects.get("Contents", []):
            if res["Key"].endswith(".vrt"):
                all_vrts.append(f"s3://{bucket}/{res['Key']}")    
    
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
    with urllib.request.urlopen(f"{url}/?f=pjson", context=ssl._create_unverified_context()) as service_url:
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
        with urllib.request.urlopen(f"{query_url}?{count_str}", context=ssl._create_unverified_context()) as count_url:
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
            print(all_query_url)
            with requests.get(all_query_url, verify=verify_ssl, stream=False) as geojson_result:
                try:
                    return gpd.read_file(geojson_result.text)
                except Exception as e:                    
                    data = json.loads(geojson_result.text)
                    return gpd.GeoDataFrame.from_features(data)
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

