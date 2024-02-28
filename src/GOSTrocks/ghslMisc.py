import sys
import os
import inspect
import rasterio

import numpy as np

from GOSTrocks.misc import tPrint

curPath = os.path.realpath(
    os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])
)
if curPath not in sys.path:
    sys.path.append(curPath)


def combine_ghsl_annual(
    ghsl_files, built_thresh=0.1, ghsl_files_labels=[], out_file=""
):
    """_summary_

    :param ghsl_files: list of ghsl annual files to process
    :type ghsl_files: list of strings (paths to ghsl files)
    :param built_thresh: minimum percetn built to be considered bult, defaults to 0.1 which is 10%
    :type built_thresh: float, optional
    :param ghsl_files_labels: list of numbers to define values in output raster, defaults to [] which means numbers will be extracted from the files.
    :type ghsl_files_labels: list of ints
    :param out_file: location to write output integer file, defaults to '' which does not write anything
    :type out_file: str, optional
    :returns: list of ghsl values and rasterio profile
    :rtype: list of [numpy array, dictionary]
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
