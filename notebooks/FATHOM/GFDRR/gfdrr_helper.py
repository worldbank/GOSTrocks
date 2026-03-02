import os, logging

import rasterio

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

from affine import Affine
from rasterio.features import rasterize, MergeAlg

def map_flood(mapD, return_period, out_file):
    fig, axes = plt.subplots(nrows=1, ncols=3, figsize=(15, 6))
    flood_columns = [f"frac_area_flooded_CU_{return_period}yr", f"frac_area_flooded_FU_{return_period}yr", f"frac_area_flooded_PD_{return_period}yr"]
    flood_titles = ["Coastal", "Fluvial", "Pluvial"]
    flood_thresh = [0, 1, 3, 5, 10, 100]
    i = 0

    for col in flood_columns:
        ax = axes[i]
        if i ==1:
            legend_kwds={   
                'title': 'Fraction of Area Flooded (%)',     
                'ncol': 3,#len(flood_thresh)-1,
                'bbox_to_anchor': (1.2, 0.0), # Fine-tune the position relative to the plot
            }
        else:
            legend_kwds=None
        mapD.plot(column=col, ax=ax, legend=i==1, cmap='Blues', missing_kwds={"color": "lightgrey"},
                  scheme="UserDefined", classification_kwds={"bins": flood_thresh}, legend_kwds=legend_kwds)
        #ax.set_axis_off()
        ax.set_title(f'{flood_titles[i]} Flooding - {return_period}-Year Return Period')
        ax.set_facecolor('darkslategray')
        i += 1
    plt.tight_layout()
    plt.savefig(out_file)
    plt.close()

def calculate_think_hazard_score(inD, raster_path, depth_threshold, idx_col, 
                                 all_touched=False, min_val=None, max_val=None,
                                 no_data=None):
    """
    Calculate hazard score for a single administrative unit based on mean depth and area percentage.

    Args:
        inD: GeoDataFrame with geometry of the admin units
        raster_path: path to raster file (can be VRT or regular GeoTIFF)
        depth_threshold: minimum depth threshold for hazard scoring
    """
    with rasterio.Env(GDAL_HTTP_UNSAFESSL='YES'):
        curRaster = rasterio.open(raster_path)
        fCount = 0
        res = {}
        nodata_value = curRaster.nodata if no_data is None else no_data
        for idx, row in inD.iterrows():
            geometry = row["geometry"]
            fCount = fCount + 1
            ul = curRaster.index(*geometry.bounds[0:2])
            lr = curRaster.index(*geometry.bounds[2:4])
            # read the subset of the data into a numpy array
            window = (
                (float(lr[0]), float(ul[0] + 1)),
                (float(ul[1]), float(lr[1] + 1)),
            )
            try:
                data = curRaster.read(1, window=window)
                # Convert no data values to np.nan
                data = np.where(data == nodata_value, np.nan, data)
                # Apply min and max value filters if provided
                if min_val is not None:
                    data[data < min_val] = 0
                if max_val is not None:
                    data[data > max_val] = 0
                
                t = curRaster.transform
                shifted_affine = Affine(
                    t.a, t.b, t.c + ul[1] * t.a, t.d, t.e, t.f + lr[0] * t.e
                )

                # rasterize the geometry
                mask = rasterize(
                    [(geometry, 0)],
                    out_shape=data.shape,
                    transform=shifted_affine,
                    fill=1,
                    all_touched=all_touched,
                    dtype=np.uint8,
                )
                # Add to the mask areas that are nan in the data
                mask = np.where(np.isnan(data), 1, mask)

                # create a masked numpy array
                masked_data = np.ma.array(data=data, mask=mask.astype(bool))

                # calculate mean of values above threshold
                mean_val = masked_data[masked_data > 0].mean()
                # calculate area percentage above threshold
                area_flooded = (masked_data > depth_threshold).sum()

                res[idx] = {
                    idx_col: row[idx_col],
                    'frac_area_flooded': (area_flooded / masked_data.count()) * 100 if masked_data.count() > 0 else 0, 
                    'mean_val': mean_val if not np.isnan(mean_val) else 0,
                    #"area_flooded": area_flooded,
                    #"total_area": masked_data.count(),                    
                }
            except Exception as e:
                #print(f"Error processing geometry at index {idx}: {e}")
                res[idx] = {
                    idx_col: row[idx_col],
                    'frac_area_flooded': 0, 
                    #"area_flooded": 0,
                    #"total_area": 0,
                }
        return(pd.DataFrame.from_dict(res, orient='index'))
