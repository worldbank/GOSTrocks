import os, time, io, json, sys
import urllib3
import boto3
import rasterio

import geopandas as gpd
import pandas as pd
import numpy as np

from functools import reduce
from urllib3.exceptions import InsecureRequestWarning
from botocore import UNSIGNED
from botocore.config import Config
from tqdm.notebook import tqdm
from shapely.geometry import box, mapping

urllib3.disable_warnings(InsecureRequestWarning)

def tPrint(s):
    """prints the time along with the message"""
    print("%s\t%s" % (time.strftime("%H:%M:%S"), s))

s3_client = boto3.client('s3', verify=False)

sys.path.insert(0, "C:/WBG/Work/Code/GOSTrocks/src")

import GOSTrocks.dataMisc as dataMisc
import GOSTrocks.rasterMisc as rMisc

#Mute runtime warnings for cleaner output
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

def process_tile(tile, ghs_pop_file, scenario, year, s3_bucket, path_prefix, out_folder,
                 depth_thresh = [0, 15, 50]):
    """Processes a single tile for FATHOM flood depth data.

    Args:
        tile (str): The tile identifier.
        ghs_pop_file (str): Path to the GHS population raster file.
        scenario (str): The scenario name.
        year (int): The year of the scenario.
        s3_bucket (str): The S3 bucket name.
        path_prefix (str): The path prefix for the S3 bucket.
        out_folder (str): The local output folder.
        depth_thresh (list, optional): List of depth thresholds. Defaults to [0, 15, 50].

    Returns:
        None
    """
    with rasterio.Env(GDAL_HTTP_UNSAFESSL='YES'):
        tPrint(f"Processing tile: {tile} for scenario: {scenario}, year: {year}")
        pop_file_name = ghs_pop_file.split("_")[-3]
        fluvial_path = "s3://{bucket}/{path}/{tile}".format(bucket=s3_bucket, path=path_prefix.format(hazard="FLUVIAL", year=year, scenario=scenario), tile=tile)
        coastal_path = "s3://{bucket}/{path}/{tile}".format(bucket=s3_bucket, path=path_prefix.format(hazard="COASTAL", year=year, scenario=scenario), tile=tile)
        pluvial_path = "s3://{bucket}/{path}/{tile}".format(bucket=s3_bucket, path=path_prefix.format(hazard="PLUVIAL", year=year, scenario=scenario), tile=tile)
        ghs_r = rasterio.open(ghs_pop_file)

        fluvial_r = rasterio.open(fluvial_path)
        fluvial_meta = fluvial_r.meta.copy()
        
        # get boundaing box of the raster
        tile_box = box(*fluvial_r.bounds)
        
        # Turn the tile_box shape into a geodataframe and reproject to the same crs as the ghs raster
        tile_gdf = gpd.GeoDataFrame(geometry=[tile_box], crs=fluvial_r.crs)
        tile_gdf = tile_gdf.to_crs(ghs_r.crs)
        ghs_data, ghs_meta = rMisc.clipRaster(ghs_r, tile_gdf, None, True)
        with rMisc.create_rasterio_inmemory(ghs_meta, ghs_data) as ghs_local:                        
            try:
                fluvial_r = rasterio.open(fluvial_path)
                fluvial_meta = fluvial_r.meta.copy()    
                # Stack the rasters together and take the max value across the stack to get the combined flood depth
                fluvial_data = fluvial_r.read()
                pluvial_data = rasterio.open(pluvial_path).read()
                max_depth = np.maximum.reduce([fluvial_data, pluvial_data])
                try:
                    coastal_data = rasterio.open(coastal_path).read()
                    max_depth = np.maximum.reduce([max_depth, coastal_data])
                except:
                    pass                            
                for cDepth in depth_thresh:
                    out_file = os.path.join(out_folder, f"{tile[:-4]}_FATHOM_{year}_{scenario}_{cDepth}cm_{pop_file_name}m_proportion.tif")
                    if not os.path.exists(out_file):            
                        numerator = np.where(max_depth > cDepth, 1, 0)
                        denominator = np.where(max_depth > cDepth, 0, 1)
                        with rMisc.create_rasterio_inmemory(fluvial_meta, numerator[0,:,:]) as fathom_depth:
                            numerator_scaled, numerator_meta = rMisc.standardizeInputRasters(fathom_depth, ghs_local, resampling_type="sum")
                        with rMisc.create_rasterio_inmemory(fluvial_meta, denominator[0,:,:]) as fathom_depth:
                            denominator_scaled, denominator_meta = rMisc.standardizeInputRasters(fathom_depth, ghs_local, resampling_type="sum")
                        
                        results = numerator_scaled / (denominator_scaled + numerator_scaled)
                        numerator_meta.update({"dtype": rasterio.float32, "count": 1})                    
                        with rasterio.open(out_file, "w", **numerator_meta) as dest:
                            dest.write(results.astype(rasterio.float32))                                        
            except:
                pass                                                    

def get_list_of_processed_tiles(out_folder=None, s3_path=None, scenario="PERCENTILE50", year=2020, depth_thresh=[0]):
    """Returns a list of tiles that have already been processed and saved in the output folder.

    Args:
        out_folder (str): The local output folder where processed tiles are saved.
        s3_path (str): The S3 path prefix for the FATHOM data.
        scenario (str): The scenario name.
        year (int): The year of the scenario.
        depth_thresh (list, optional): List of depth thresholds. Defaults to [0, 15, 50].
    """
    if not out_folder and not s3_path:
        raise ValueError("Either out_folder or s3_path must be provided.")
    
    if out_folder:
        processed_tiles = []
        for cDepth in depth_thresh:
            pattern = f"_FATHOM_{year}_{scenario}_{cDepth}cm_"
            for file in os.listdir(out_folder):
                if pattern in file and file.endswith(".tif"):
                    processed_tiles.append(file.split("_FATHOM_")[0] + ".tif")
        return list(set(processed_tiles))
    
    if s3_path:
        paginator = s3_client.get_paginator('list_objects_v2')
        processed_tiles = []
        s3_bucket = s3_path.split('/')[2]
        prefix = '/'.join(s3_path.split('/')[3:])
        print (f"Checking S3 bucket: {s3_bucket} with prefix: {prefix}")
        for cDepth in depth_thresh:
            pattern = f"_FATHOM_{year}_{scenario}_{cDepth}cm_"
            for page in paginator.paginate(Bucket=s3_bucket, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        if pattern in key and key.endswith(".tif"):
                            processed_tiles.append(key.split("/")[-1].split("_FATHOM_")[0] + ".tif")
        return list(set(processed_tiles))

def main():
    local_folder = "C:/WBG/Work/Projects/FATHOM_COLLAPSE"
    out_folder = os.path.join(local_folder, "FATHOM_summaries")
    map_folder = os.path.join(local_folder, "FATHOM_maps")
    for tF in [out_folder, map_folder]:
        if not os.path.exists(tF):
            os.makedirs(tF)

    ghs_pop_files = [
        "C:\\WBG\\Work\\data\\URBAN\\SMOD_POP\\GHS_POP_E2025_GLOBE_R2023A_54009_1000_V1_0.tif", 
        #"C:\\WBG\\Work\\data\\URBAN\\SMOD_POP\\GHS_POP_E2030_GLOBE_R2023A_54009_100_V1_0.tif"
    ]

    s3_bucket = "wbg-geography01"
    s3_prefix = "FATHOM"
    return_period = 100

    # Use the S3 client to get a list of VRT files in the specified bucket and prefix
    response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=s3_prefix)
    vrt_files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.vrt')]

    # Turn the list of vrt files into a dataframe
    vrt_breakdown = [[x] + x.split('-') for x in vrt_files]
    vrt_df = pd.DataFrame(vrt_breakdown, columns=["path", 'prefix', 'res', 'offset', 'return_period', 'hazard', 'defended', 'metric', 'year', 'scenario', 'version', "other"])
    vrt_df = vrt_df.loc[:, ['return_period', 'hazard', 'defended', 'year', 'scenario', "path"]]

    # Focus on just the 100-year return period for now
    vrt_df = vrt_df[vrt_df['return_period'] == f"1in{return_period}"]
    # Drop the undefended models
    vrt_df = vrt_df[vrt_df['defended'] == "DEFENDED"]

    # Get a list of all tiles in one scenario
    path_prefix = "FATHOM/v31/FLOOD_MAP-1ARCSEC-NW_OFFSET-1in100-{hazard}-DEFENDED-DEPTH-{year}-{scenario}-v3.1"

    # get a list of all tif files in the s3 bucket for the specified hazard, year, and scenario
    paginator = s3_client.get_paginator('list_objects_v2')
    tif_files = []
    for page in paginator.paginate(Bucket=s3_bucket, Prefix=path_prefix.format(hazard="FLUVIAL", year=2020, scenario="PERCENTILE50")):
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                # Check for .tif or .tiff extensions
                if key.lower().endswith(('.tif', '.tiff')):
                    tif_files.append(key.split('/')[-1])  # Get just the filename

    print(f"Total tiles to process: {len(tif_files)}")

    ghs_pop_file = ghs_pop_files[0]  # Use the first GHS population file for this example
    pop_file_name = ghs_pop_file.split("_")[-3]
    ghs_r = rasterio.open(ghs_pop_file)        

    scenarios = ['PERCENTILE50'] #vrt_df['scenario'].unique()        
    years = ['2020'] #vrt_df['year'].unique()
    depth_thresh = [0,15,50]
    
    all_args = []

    for tile in tif_files:
        cur_args = [tile, ghs_pop_file, scenarios[0], years[0], s3_bucket, path_prefix, out_folder, depth_thresh]
        all_args.append(cur_args)
        
    # Use multiprocessing to process tiles in parallel
    from multiprocessing import Pool, cpu_count
    num_processes = min(cpu_count() - 1, len(all_args))
    with Pool(num_processes) as pool:
        pool.starmap(process_tile, all_args)

def test_file_count(out_folder, s3_path, scenario="PERCENTILE50", year=2020, depth_thresh=[0]):
    """Tests the number of processed files in the output folder against the expected number from S3.

    Args:
        out_folder (str): The local output folder where processed tiles are saved.
        s3_path (str): The S3 path prefix for the FATHOM data.
        scenario (str): The scenario name.
        year (int): The year of the scenario.
        depth_thresh (list, optional): List of depth thresholds. Defaults to [0].
    """
    processed_tiles_local = get_list_of_processed_tiles(out_folder=out_folder, scenario=scenario, year=year, depth_thresh=depth_thresh)
    processed_tiles_s3 = get_list_of_processed_tiles(s3_path=s3_path, scenario=scenario, year=year, depth_thresh=depth_thresh)

    print(f"Number of processed tiles locally: {len(processed_tiles_local)}")
    print(f"Number of processed tiles on S3: {len(processed_tiles_s3)}")

if __name__ == "__main__":
    test_file_count(r"C:\WBG\Work\Projects\FATHOM_COLLAPSE\FATHOM_summaries",
                    r"s3://wbg-geography01/FATHOM/v31_scaled_GHS_Pop/1000m")
    main()
