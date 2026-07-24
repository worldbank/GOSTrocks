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
                 out_s3_prefix = None):
    """Processes a single tile for FATHOM flood depth data.

    Args:
        tile (str): The tile identifier.
        ghs_pop_file (str): Path to the GHS population raster file.
        scenario (str): The scenario name.
        year (int): The year of the scenario.
        s3_bucket (str): The S3 bucket name.
        path_prefix (str): The path prefix for the S3 bucket.
        out_folder (str): The local output folder.
        out_s3_prefix (str, optional): The S3 prefix for the output files; if set, will copy local files to S3 then delete local files. Defaults to None.

    Returns:
        None
    """
    with rasterio.Env(GDAL_HTTP_UNSAFESSL='YES'):
        tPrint(f"Processing tile: {tile} for scenario: {scenario}, year: {year}")
        pop_file_name = ghs_pop_file.split("_")[-3]
        fluvial_path = "s3://{bucket}/{path}/{tile}".format(bucket=s3_bucket, path=path_prefix.format(hazard="FLUVIAL", year=year, scenario=scenario), tile=tile)
        coastal_path = "s3://{bucket}/{path}/{tile}".format(bucket=s3_bucket, path=path_prefix.format(hazard="COASTAL", year=year, scenario=scenario), tile=tile)
        pluvial_path = "s3://{bucket}/{path}/{tile}".format(bucket=s3_bucket, path=path_prefix.format(hazard="PLUVIAL", year=year, scenario=scenario), tile=tile)
        try:
            fluvial_r = rasterio.open(fluvial_path)
        except:
            tPrint(f"Tile {tile} not found for scenario: {scenario}, year: {year}")
            return
        fluvial_meta = fluvial_r.meta.copy()
        
        
        ghs_r = rasterio.open(ghs_pop_file)      
        # get boundaing box of the raster
        tile_box = box(*fluvial_r.bounds)
        # Turn the tile_box shape into a geodataframe and reproject to the same crs as the ghs raster
        tile_gdf = gpd.GeoDataFrame(geometry=[tile_box], crs=fluvial_r.crs)
        tile_gdf = tile_gdf.to_crs(ghs_r.crs)
        ghs_data, ghs_meta = rMisc.clipRaster(ghs_r, tile_gdf, None, True)

        with rMisc.create_rasterio_inmemory(ghs_meta, ghs_data) as ghs_local:                        
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

            out_file = os.path.join(out_folder, f"{tile[:-4]}_FATHOM_{year}_{scenario}_combo_{pop_file_name}m_proportion.tif")
            process = True                        
            if out_s3_prefix:
                s3_key = f"{out_s3_prefix}/{os.path.basename(out_file)}"
                try:
                    s3_client.head_object(Bucket=s3_bucket, Key=s3_key)                    
                    process = False  # File already exists on S3, skip processing
                except:
                    pass  # File does not exist on S3, continue processing
            else:
                try:
                    xx = rasterio.open(out_file)
                    process = False
                except:
                    pass
            if process:
                ghs_meta.update({"dtype": rasterio.float32, "count": 5})  
                '''
                Band 1: % of cells with no flood risk == number of cells = 0
                Band 2: % of cells with flood risk between 0-15cm == number of cells > 0 and <= 15
                Band 3: % of cells with flood risk between 15-50cm == number of cells > 15 and <= 50
                Band 4: % of cells with flood risk between 50-150cm == number of cells > 50 and <= 150
                Band 5: % of cells with flood risk over 150 cm == number of cells > 150 and < 10000 
                '''                  
                with rasterio.open(out_file, "w", **ghs_meta) as dest:
                    band1 = np.where(max_depth == 0, 1, 0)
                    band2 = np.where((max_depth > 0) & (max_depth <= 15), 1, 0)
                    band3 = np.where((max_depth > 15) & (max_depth <= 50), 1, 0)
                    band4 = np.where((max_depth > 50) & (max_depth <= 150), 1, 0)
                    band5 = np.where((max_depth > 150) & (max_depth < 10000), 1, 0)
                    denominator = np.where(max_depth >= 0, 1, 0)

                    with rMisc.create_rasterio_inmemory(fluvial_meta, denominator[0,:,:]) as fathom_depth:
                        denominator_scaled, denominator_meta = rMisc.standardizeInputRasters(fathom_depth, ghs_local, resampling_type="sum")
                                            
                    for i, numerator in enumerate([band1, band2, band3, band4, band5], start=1):
                        with rMisc.create_rasterio_inmemory(fluvial_meta, numerator[0,:,:]) as fathom_depth:
                            numerator_scaled, numerator_meta = rMisc.standardizeInputRasters(fathom_depth, ghs_local, resampling_type="sum")
                    
                        results = numerator_scaled / (denominator_scaled + numerator_scaled)
                        dest.write_band(i, results[0,:,:].astype(rasterio.float32))

                if out_s3_prefix:
                    del dest
                    s3_key = f"{out_s3_prefix}/{os.path.basename(out_file)}"
                    try:
                        s3_client.upload_file(out_file, s3_bucket, s3_key)
                        os.remove(out_file)
                    except Exception as e:
                        tPrint(f"Failed to upload {out_file} to S3: {str(e)}")

def get_list_of_processed_tiles(out_folder=None, s3_path=None, 
                                scenario="PERCENTILE50", year=2020, depth_thresh=[0, 15, 50],
                                copy_to_s3=False):
    """Returns a list of tiles that have already been processed and saved in the output folder.

    Args:
        out_folder (str): The local output folder where processed tiles are saved.
        s3_path (str): The S3 path prefix for the FATHOM data.
        scenario (str): The scenario name.
        year (int): The year of the scenario.
        depth_thresh (list, optional): List of depth thresholds. Defaults to [0, 15, 50].
        copy_to_s3 (bool): If True, copy files from out_folder to S3 if they don't exist on S3.
    """
    if not out_folder and not s3_path:
        raise ValueError("Either out_folder or s3_path must be provided.")
    
    # Get processed tiles from local folder
    local_tiles = []
    if out_folder and os.path.exists(out_folder):
        for cDepth in depth_thresh:
            pattern = f"_FATHOM_{year}_{scenario}_{cDepth}cm_"
            for file in os.listdir(out_folder):
                if pattern in file and file.endswith(".tif"):
                    local_tiles.append(file)
        local_tiles = list(set(local_tiles))
    
    # Get processed tiles from S3
    s3_tiles = []
    if s3_path:
        paginator = s3_client.get_paginator('list_objects_v2')
        s3_bucket = s3_path.split('/')[2]
        prefix = '/'.join(s3_path.split('/')[3:])
        print(f"Checking S3 bucket: {s3_bucket} with prefix: {prefix}")
        for cDepth in depth_thresh:
            pattern = f"_FATHOM_{year}_{scenario}_{cDepth}cm_"
            for page in paginator.paginate(Bucket=s3_bucket, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        if pattern in key and key.endswith(".tif"):
                            s3_tiles.append(key.split("/")[-1])
        s3_tiles = list(set(s3_tiles))   
   
    # Return based on what was requested
    if out_folder and s3_path:
        return list(set(local_tiles + s3_tiles))
    elif out_folder:
        return local_tiles
    else:
        return s3_tiles


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
    years = [2020]  #vrt_df['year'].unique()
    depth_thresh = [0,15,50,150]
    
    all_args = []
    
    for tile in tif_files:
        for scenario in scenarios:
            for year in years:
                #cur_out_folder = f"s3://{s3_bucket}/{s3_prefix}/v31_scaled_GHS_Pop/{pop_file_name}m/COMBO/"
                cur_out_folder = os.path.join(out_folder, f"{pop_file_name}m", "COMBO")
                if not os.path.exists(cur_out_folder):
                    os.makedirs(cur_out_folder)
                out_s3_prefix = f"FATHOM/v31_scaled_GHS_Pop/{pop_file_name}m/COMBO/{scenario}/{year}"
                cur_args = [tile, ghs_pop_file, scenario, year, s3_bucket, path_prefix, cur_out_folder, out_s3_prefix]
                all_args.append(cur_args)
        
    #process_tile(*all_args[0])  # Process the first tile for testing

    # Use multiprocessing to process tiles in parallel
    from multiprocessing import Pool, cpu_count
    num_processes = min(cpu_count() - 1, len(all_args))
    with Pool(num_processes) as pool:
        pool.starmap(process_tile, all_args)
    
def test_file_count(out_folder, s3_path, scenario="PERCENTILE50", year=2020, depth_thresh=[0], copy_to_s3=False):
    """Tests the number of processed files in the output folder against the expected number from S3.

    Args:
        out_folder (str): The local output folder where processed tiles are saved.
        s3_path (str): The S3 path prefix for the FATHOM data.
        scenario (str): The scenario name.
        year (int): The year of the scenario.
        depth_thresh (list, optional): List of depth thresholds. Defaults to [0].
    """
    processed_tiles_local = get_list_of_processed_tiles(out_folder=out_folder, scenario=scenario, year=year, depth_thresh=depth_thresh)
    tPrint(f"Number of processed tiles locally: {len(processed_tiles_local)}")
    processed_tiles_s3 = get_list_of_processed_tiles(s3_path=s3_path, scenario=scenario, year=year, depth_thresh=depth_thresh)
    tPrint(f"Number of processed tiles on S3: {len(processed_tiles_s3)}")

    if copy_to_s3 and out_folder and s3_path:
        missing_tiles = [tile for tile in processed_tiles_local if tile not in processed_tiles_s3]
        if missing_tiles:
            print(f"Found {len(missing_tiles)} tiles to copy to S3")
            s3_bucket = s3_path.split('/')[2]
            prefix = '/'.join(s3_path.split('/')[3:])
            for tile in tqdm(missing_tiles, desc="Uploading to S3"):
                local_file_path = os.path.join(out_folder, tile)
                s3_key = f"{prefix}/{tile}"
                try:
                    s3_client.upload_file(local_file_path, s3_bucket, s3_key)                    
                except Exception as e:
                    print(f"Failed to upload {tile}: {str(e)}")
        else:
            print("All local tiles already exist on S3")      

    print(f"Number of processed tiles locally: {len(processed_tiles_local)}")
    print(f"Number of processed tiles on S3: {len(processed_tiles_s3)}")

if __name__ == "__main__":
    #test_file_count(r"C:\WBG\Work\Projects\FATHOM_COLLAPSE\FATHOM_summaries",
    #                r"s3://wbg-geography01/FATHOM/v31_scaled_GHS_Pop/1000m",
    #                copy_to_s3=True)
    main()
