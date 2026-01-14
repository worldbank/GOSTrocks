import rasterio

import numpy as np

from .misc import tPrint


def combine_ghsl_annual(
    ghsl_files, built_thresh=0.1, ghsl_files_labels=[], out_file=""
):
    """Combine the annual tiffs from GHSL into a single raster.
    The output raster will have the minimum value of all the years for each pixel.
    This is useful for creating a raster that shows the earliest year that a pixel was built up.

    Parameters
    ----------
    ghsl_files : list of strings
        list of ghsl annual files to process
    built_thresh : float, optional
        minimum percent built to be considered built in a single pixel, defaults to 0.1 which is 10%, by default 0.1
    ghsl_files_labels : list, optional
        list of numbers to define values in output raster, defaults to [] which means numbers will be extracted from the files, by default []
    out_file : str, optional
        location to write output integer file, defaults to '' which does not write anything, by default ""

    Returns
    -------
    list of [numpy array, dictionary]
        numpy array of the combined ghsl values, and the rasterio profile
    """
    # open all the ghsl files, extract data and labels
    ghsl_rasters = []
    ghsl_years = []
    idx = 0
    for ghsl_file in ghsl_files:
        cur_r = rasterio.open(ghsl_file)
        out_meta = cur_r.profile.copy()
        cur_d = cur_r.read()[0, :, :]
        cur_d[cur_d == cur_r.profile["nodata"]] = 0
        if len(ghsl_files_labels) > 0:
            cur_year = ghsl_files_labels[idx]
        cur_year = ghsl_file.split("_")[-7][1:]

        # Convert built area to dataset with single value of the current year
        cur_d = ((cur_d >= built_thresh) * int(cur_year)).astype(float)
        cur_d[cur_d == 0] = np.nan

        ghsl_rasters.append(cur_d)
        ghsl_years.append(cur_year)

        tPrint(f"*** {idx} completed {cur_year}")
        idx += 1

    # stack the ghsl files
    all_ghsl = np.dstack(ghsl_rasters)
    ghsl_final = np.nanmin(all_ghsl, axis=2)

    ghsl_int = ghsl_final.astype(int)
    ghsl_int[ghsl_int < 0] = int(out_meta["nodata"])

    # write output
    if out_file != "":
        with rasterio.open(out_file, "w", **out_meta) as out_r:
            out_r.write_band(1, ghsl_int)

    return [ghsl_int, out_meta]
