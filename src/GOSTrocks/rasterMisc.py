import sys
import os
import inspect
import json
import rasterio
import pyproj

import pandas as pd
import geopandas as gpd
import numpy as np

from shapely.geometry import box, shape
from shapely import wkt
from affine import Affine
from rasterio import features
from rasterio.mask import mask
from rasterio.features import rasterize, MergeAlg
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.merge import merge
from rasterio.io import MemoryFile
from contextlib import contextmanager

curPath = os.path.realpath(
    os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])
)
if curPath not in sys.path:
    sys.path.append(curPath)

from misc import tPrint


def merge_rasters(
    in_rasters, merge_method="first", dtype="", out_file="", boolean_gt_0=False
):
    """Merge a list of rasters into a single raster file

    Args:
        in_rasters (list of rasters): List of rasters to process as string paths
        merge_method (str, optional): merge method. Defaults to 'first'.
        dtype (str, optional): dtype to convert final raster to. Defaults to '', which maintains input raster type
        out_file (str, optional): Path to create output raster. Defaults to '', which creates no raster
        boolean_gt_0 (str, optional): If true, converts merged result to binary 0, 1 of values greater than 0, Defaults to False
    """

    opened_tiffs = [rasterio.open(x) for x in in_rasters]
    merged, out_transform = merge(opened_tiffs, method=merge_method)
    if boolean_gt_0:
        merged = (merged > 0) * 1
        dtype = "uint8"
    if dtype != "":
        merged = merged.astype(dtype)

    # Create a new raster file with the merged data
    metadata = opened_tiffs[0].meta.copy()
    metadata.update(
        {
            "height": merged.shape[1],
            "width": merged.shape[2],
            "transform": out_transform,
            "dtype": "uint8",
        }
    )
    if out_file != "":
        with rasterio.open(out_file, "w", **metadata) as dst:
            dst.write(merged)
    return (merged, metadata)


@contextmanager
def create_rasterio_inmemory(src, curData):
    """Create a rasterio object in memory from a numpy array

    :param src: data dictionary describing the rasterio template i.e. - rasterio.open().profile
    :type src: rasterio metadata dictionary
    :param curData: numpy array from which to create rasterio object
    :type curData: numpy array
    """
    with MemoryFile() as memFile:
        with memFile.open(**src) as dataset:
            try:
                dataset.write(curData)
            except:
                dataset.write_band(1, curData)
            del curData

        with memFile.open() as dataset:
            yield dataset


def vectorize_raster(
    inR, bad_vals=[]
):  # TODO out_file='', smooth=False, smooth_window=3, bad_vals=None):
    """convert input raster data to a geodatframe

    :param inR: input raster data to vectorize
    :type inR: rasterio.datasetReader
    :param bad_vals: list of values to ignore in conversion
    :type bad_vals: list of int
    :returns: geopandas data frame of [idx, value (from raster), and geometry]
    :rtype: geopandas.GeoDataFrame
    """

    data = inR.read()
    ## TODO add smoothing option
    # if smooth:
    ## TODO add bad value filtering
    idx = 0
    all_vals = []
    for cShape, value in features.shapes(data, transform=inR.transform):
        if value not in bad_vals:
            all_vals.append([idx, value, shape(cShape)])
            # shape(geojson.loads(json.dumps(cShape)))
            idx += 1

    return gpd.GeoDataFrame(
        all_vals, columns=["idx", "value", "geometry"], geometry="geometry", crs=inR.crs
    )


def project_raster(srcRst, dstCrs, output_raster=""):
    """project raster to destination crs

    Args:
        srcRst (_type_): _description_
        dstCrs (_type_): _description_
        output_raster (_type_): _description_
    """
    transform, width, height = calculate_default_transform(
        srcRst.crs, dstCrs, srcRst.width, srcRst.height, *srcRst.bounds
    )
    kwargs = srcRst.meta.copy()
    kwargs.update(
        {"crs": dstCrs, "transform": transform, "width": width, "height": height}
    )

    # open destination raster
    dstRst = np.zeros([kwargs["count"], width, height], kwargs["dtype"])

    # reproject and save raster band data
    for i in range(1, srcRst.count + 1):
        reproject(
            source=rasterio.band(srcRst, i),
            destination=dstRst,
            # src_transform=srcRst.transform,
            src_crs=srcRst.crs,
            # dst_transform=transform,
            dst_crs=dstCrs,
            resampling=Resampling.nearest,
        )

    if output_raster != "":
        with rasterio.open(output_raster, "w", *kwargs) as out_raster:
            out_raster.write(dstRst)

    return [dstRst, kwargs]


def clipRaster(inR, inD, outFile=None, crop=True):
    """Clip input raster

    :param inR: rasterio object to clip
    :type inR: rasterio.DatasetReader
    :param inD: geopandas polygonal dataframe to use for clip clip extent based on crop param
    :type inD: geopandas.GeoDataFrame
    :param outFile: string path to write output raster, default is '' which writes nothing
    :type outFile: string
    :param crop: determine wether to clip based on bounding box (False) or unary_union (True). Default is True
    :type crop: Boolean
    :return: array of [numpy array of data, and rasterio metadata]
    :rtype: array
    """
    if inD.crs != inR.crs:
        inD = inD.to_crs(inR.crs)
        inD = inD.buffer(0)
    out_meta = inR.meta.copy()

    def getFeatures(gdf):
        # Function to parse features from GeoDataFrame in such a manner that rasterio wants them
        return [json.loads(gdf.to_json())["features"][0]["geometry"]]

    if crop:
        tD = gpd.GeoDataFrame([[1]], geometry=[inD.unary_union])
    else:
        tD = gpd.GeoDataFrame([[1]], geometry=[box(*inD.total_bounds)])

    coords = getFeatures(tD)
    out_img, out_transform = mask(inR, shapes=coords, crop=True, all_touched=True)
    out_meta.update(
        {
            "driver": "GTiff",
            "height": out_img.shape[1],
            "width": out_img.shape[2],
            "transform": out_transform,
        }
    )
    if outFile:
        with rasterio.open(outFile, "w", **out_meta) as dest:
            dest.write(out_img)
    return [out_img, out_meta]


def rasterizeDataFrame(
    inD,
    outFile,
    idField="",
    templateRaster="",
    templateMeta="",
    nCells=0,
    res=0,
    mergeAlg="REPLACE",
    re_proj=False,
    nodata=np.nan,
):
    """Convert input geopandas dataframe into a raster file

    :param inD: input data frame to rasterize
    :type inD: gpd.GeoDataFrame
    :param outFile: output file to create from rasterized dataframe, defaults to '' which creates no file
    :type outFile: string
    :param idField: field in inD to rasterize, defaults to '' which sets everything to 1
    :type idField: str, optional
    :param templateRaster: raster upon which to base raster creation, defaults to ''. If no template is provided, nCells or res need to be defined
    :type templateRaster: str, optional
    :param templateMeta: raster metadata used to create output raster, defaults to ''. If no template is provided, nCells or res need to be defined
    :type templateMeta: str, optional
    :param nCells: number of cells in width and height, defaults to 0
    :type nCells: int, optional
    :param res: resolution of output raster in units of the crs, defaults to 0
    :type res: int, optional
    :param mergeAlg: Method of aggregating overlapping features, defaults to "REPLACE"; options are "REPLACE" or "ADD"
    :type mergeAlg: str, optional
    :param re_proj: option to reproject inD to templateRaster if CRS do not match, defaults to False
    :type re_proj: bool, optional
    :return:  dict of metadata used to create output raster and burned raster values
    :rtype: dict of {'meta':new raster metadata, 'vals': values in new raster}
    """
    ###Parameter checking
    if nCells <= 0 and res <= 0 and templateRaster == "" and templateMeta == "":
        raise (ValueError("Must define one of nCells or res"))
    if nCells > 0 and res > 0 and templateRaster == "" and templateMeta == "":
        raise (ValueError("Cannot define both nCells and res"))

    # Set VALUE field equal to idField
    inD["VALUE"] = 1
    inD["VALUE"] = inD["VALUE"].astype("int16")
    if idField != "":
        inD["VALUE"] = inD[idField]

    # set merge algorithm for overlapping features
    if mergeAlg == "REPLACE":
        mAlg = MergeAlg.replace
    elif mergeAlg == "ADD":
        mAlg = MergeAlg.add
    else:
        raise (ValueError("MergeAlg must be one of REPLACE or ADD"))

    if templateRaster != "":
        inR = rasterio.open(templateRaster)
        cMeta = inR.profile.copy()
        cMeta.update(count=1)
        nTransform = cMeta["transform"]
        if inD.crs != inR.crs:
            if not re_proj:
                raise (
                    ValueError(
                        "input CRS do not match: inD - %s, templateRaster - %s"
                        % (inD.crs, inR.crs)
                    )
                )
            inD = inD.to_crs(inR.crs)
    elif templateMeta != "":
        cMeta = templateMeta
        nTransform = cMeta["transform"]
        if inD.crs != cMeta["crs"]:
            if not re_proj:
                raise (
                    ValueError(
                        "input CRS do not match: inD - %s, templateRaster - %s"
                        % (inD.crs, inR.crs)
                    )
                )
            inD = inD.to_crs(cMeta["crs"])
    else:
        bounds = inD.total_bounds
        if nCells > 0:
            height = nCells
            width = nCells
        if res > 0:
            height = int(round((bounds[3] - bounds[1]) / res))
            width = int(round((bounds[2] - bounds[0]) / res))

        b = inD.total_bounds
        nTransform = rasterio.transform.from_bounds(
            b[0], b[1], b[2], b[3], width, height
        )
        if inD.crs.__class__ == pyproj.crs.crs.CRS:
            crs = {"init": "epsg:%s" % inD.crs.to_epsg()}
        else:
            crs = inD.crs
        cMeta = {
            "count": 1,
            "crs": crs,
            "dtype": inD["VALUE"].dtype,
            "driver": "GTiff",
            "transform": nTransform,
            "height": height,
            "width": width,
            "nodata": nodata,
        }
    shapes = ((row.geometry, row.VALUE) for idx, row in inD.iterrows())
    burned = features.rasterize(
        shapes=shapes,
        out_shape=(cMeta["height"], cMeta["width"]),
        transform=nTransform,
        dtype=cMeta["dtype"],
        merge_alg=mAlg,
        fill=nodata,
    )
    if outFile:
        try:
            with rasterio.open(outFile, "w", **cMeta) as out:
                out.write_band(1, burned)
        except:
            print("Error writing raster")
    return {"meta": cMeta, "vals": burned}


def polygonizeArray(data, curRaster):
    """Convert input array (data) to a geodataframe

    :param data: numpy array of raster data. ie - rasterio.open().read()
    :type data: np.array
    :param curRaster: template raster object
    :type curRaster: rasterio.DatasetReader
    :return: geodataframe with columns row, col, val, geometry
    :rtype: gpd.GeoDataFrame
    """
    # Calculate resolution of cells
    b = curRaster.bounds
    ll = curRaster.xy(*curRaster.index(*b[0:2]), "ll")
    xmin = ll[0]
    ymin = ll[1]
    xRes = curRaster.res[0]
    yRes = curRaster.res[1]
    crs = curRaster.crs
    # create a dataframe equal to the size of the array
    outArray = pd.DataFrame()
    outArray["id"] = list(range(0, (data.shape[0] * data.shape[1])))
    rowVals = []
    colVals = []
    actualvals = []
    for row in range(0, data.shape[0]):
        for col in range(0, data.shape[1]):
            rowVals.append(row)
            colVals.append(col)
            actualvals.append(data[row, col])
    outArray["row"] = rowVals
    outArray["col"] = colVals
    outArray["vals"] = actualvals

    # Create a polygon covering each cell
    def getPolygon(x):
        llX = xmin + (xRes * x["col"])
        llY = ymin + (yRes * x["row"])
        A = "%s %s" % (llX, llY)
        B = "%s %s" % (llX, llY + yRes)
        C = "%s %s" % (llX + xRes, llY + yRes)
        D = "%s %s" % (llX + xRes, llY)
        return wkt.loads("POLYGON((%s,%s,%s,%s,%s))" % (A, B, C, D, A))

    outArray["geometry"] = outArray.apply(getPolygon, axis=1)
    outGeo = gpd.GeoDataFrame(outArray, geometry="geometry")
    outGeo.crs = crs
    return outGeo


def zonalStats(
    inShp,
    inRaster,
    bandNum=1,
    mask_A=None,
    reProj=False,
    minVal="",
    maxVal="",
    verbose=False,
    rastType="N",
    unqVals=[],
    weighted=False,
    allTouched=False,
    calc_sd=False,
    return_df=False,
):
    """Run zonal statistics against an input shapefile. Returns array of SUM, MIN, MAX, and MEAN

    :param inShp: input geospatial data to summarize raster
    :type inShp: string path to file of gpd.GeoDataFrame
    :param inRaster: input raster to summarize
    :type inRaster: string path to file or rasterio.DatasetReader
    :param bandNum: band in raster to analyze, defaults to 1
    :type bandNum: int, optional
    :param mask_A: mask the raster data using an identical shaped boolean mask, defaults to None
    :type mask_A: np.array, optional
    :param reProj: whether to reproject data to match, if not, raise a ValueError if CRS mismatch between inShp and inRaster, defaults to False
    :type reProj: bool, optional
    :param minVal: if defined, will only calculate statistics on values above this number, defaults to ''
    :type minVal: number, optional
    :param maxVal: if defined, will only calculate statistics on values below this number, defaults to ''
    :type maxVal: number, optional
    :param verbose: provide additional text updates, defaults to False
    :type verbose: bool, optional
    :param rastType: Type of raster, defaults to 'N' as numerical or 'C' as categorical. If 'C' is used, you should provide unqVals
    :type rastType: str, optional
    :param unqVals: List of unique values to search for in raster, defaults to []
    :type unqVals: list of int, optional
    :param weighted: apply weighted zonal calculations. This will determine the % overlap for each
        raster cell in the defined AOI. Will apply weights in calculations of numerical statistics, defaults to False
    :type weighted: bool, optional
    :param allTouched: whether to include all cells touched in raster calculation, passed to rasterio rasterize function, defaults to False
    :type allTouched: bool, optional
    :param calc_sd: include the standard deviation in calculation, defaults to False
    :type calc_sd: bool, optional
    :param return_df: if true, return result as data frame; defaults to False
    :type return_df: boolean, optional
    :raises ValueError: If CRS mismatch between inShp and inRaster
    :return: array of zonal results - one entry for every feature in inShp. Each entry is SUM, MIN, MAX, MEAN, SD (optional)
    :rtype: array
    """
    if isinstance(inShp, str):
        inVector = gpd.read_file(inShp)
    else:
        inVector = inShp
    if isinstance(inRaster, str):
        curRaster = rasterio.open(inRaster, "r")
    else:
        curRaster = inRaster

    # If mask is not none, apply mask
    if mask_A is not None:
        curRaster.write_mask(mask_A)

    outputData = []
    if inVector.crs != curRaster.crs:
        if reProj:
            inVector = inVector.to_crs(curRaster.crs)
        else:
            raise ValueError("Input CRS do not match")
    fCount = 0
    tCount = len(inVector["geometry"])
    # generate bounding box geometry for raster bbox
    b = curRaster.bounds
    rBox = box(b[0], b[1], b[2], b[3])
    for idx, row in inVector.iterrows():
        geometry = row["geometry"]
        fCount = fCount + 1
        try:
            # This test is used in case the geometry extends beyond the edge of the raster
            #   I think it is computationally heavy, but I don't know of an easier way to do it
            if not rBox.contains(geometry):
                geometry = geometry.intersection(rBox)
            try:
                if fCount % 1000 == 0 and verbose:
                    tPrint("Processing %s of %s" % (fCount, tCount))
                # get pixel coordinates of the geometry's bounding box
                ul = curRaster.index(*geometry.bounds[0:2])
                lr = curRaster.index(*geometry.bounds[2:4])
                # read the subset of the data into a numpy array
                window = (
                    (float(lr[0]), float(ul[0] + 1)),
                    (float(ul[1]), float(lr[1] + 1)),
                )

                if mask_A is not None:
                    data = curRaster.read(bandNum, window=window, masked=True)
                else:
                    data = curRaster.read(bandNum, window=window, masked=False)

                if weighted:
                    allTouched = True
                    # Create a grid of the input raster (data)
                    rGrid = polygonizeArray(data, geometry.bounds, curRaster)
                    # Clip the grid by the input geometry
                    rGrid["gArea"] = rGrid.area
                    rGrid["newArea"] = rGrid.intersection(geometry).area
                    # Store the percent overlap
                    rGrid["w"] = rGrid["newArea"] / rGrid["gArea"]
                    newData = data
                    for idx, row in rGrid.iterrows():
                        newData[row["row"], row["col"]] = (
                            data[row["row"], row["col"]] * row["w"]
                        )
                    data = newData

                """
                # Mask out no-data in data array
                if 'nodata' in curRaster.profile.keys():
                    no_data_val = curRaster.profile['nodata']
                    #data[data == no_data_val] = np.nan
                    data[data == no_data_val] = 0
                """

                # create an affine transform for the subset data
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
                    all_touched=allTouched,
                    dtype=np.uint8,
                )

                # create a masked numpy array
                masked_data = np.ma.array(data=data, mask=mask.astype(bool))
                if rastType == "N":
                    if minVal != "" or maxVal != "":
                        if minVal != "":
                            masked_data = np.ma.masked_where(
                                masked_data < minVal, masked_data
                            )
                        if maxVal != "":
                            masked_data = np.ma.masked_where(
                                masked_data > maxVal, masked_data
                            )
                        if masked_data.count() > 0:
                            results = [
                                np.nansum(masked_data),
                                np.nanmin(masked_data),
                                np.nanmax(masked_data),
                                np.nanmean(masked_data),
                            ]
                        else:
                            results = [-1, -1, -1, -1]
                    else:
                        results = [
                            np.nansum(masked_data),
                            np.nanmin(masked_data),
                            np.nanmax(masked_data),
                            np.nanmean(masked_data),
                        ]
                    if calc_sd:
                        try:
                            results.append(np.std(masked_data))
                        except:
                            results.append(-1)
                if rastType == "C":
                    if len(unqVals) > 0:
                        masked_unq = np.unique(masked_data, return_counts=True)
                        xx = dict(
                            [
                                x
                                for x in list(zip(masked_unq[0], masked_unq[1]))
                                if x[0] != "masked"
                            ]
                        )
                        results = [xx.get(i, 0) for i in unqVals]
                    else:
                        results = np.unique(masked_data, return_counts=True)
                outputData.append(results)
            except Exception as e:
                if verbose:
                    print(e)
                if rastType == "N":
                    outputData.append([-1, -1, -1, -1])
                else:
                    outputData.append([-1 for x in unqVals])
        except:
            print("Error processing %s" % fCount)
    if return_df:
        cols = ["SUM", "MIN", "MAX", "MEAN"]
        if calc_sd:
            cols.append("SD")
        outputData = pd.DataFrame(outputData, columns=cols)
    return outputData


def standardizeInputRasters(inR1, inR2, inR1_outFile="", resampling_type="nearest"):
    """Standardize inR1 to inR2: changes crs, extent, and resolution.

    :param inR1: rasterio object for raster to be modified
    :type inR1: ratserio.DatasetReader
    :param inR2: rasterio object to be standardized to
    :type inR12 ratserio.DatasetReader
    :param inR1_outfile: path to create output raster file of standardized inR1, default is '', which means nothing is written
    :type inR1: string
    :param resampling_type: how to perfrom spatial resampling; options are nearest (default), cubic, or sum
    :type resampling_type: string
    :return: array of numpy array, and rasterio metadata
    :rtype: array
    """
    if inR1.crs != inR2.crs:
        bounds = gpd.GeoDataFrame(
            pd.DataFrame([[1, box(*inR2.bounds)]], columns=["ID", "geometry"]),
            geometry="geometry",
            crs=inR2.crs,
        )
        bounds = bounds.to_crs(inR1.crs)
        b2 = bounds.total_bounds
        boxJSON = [
            {
                "type": "Polygon",
                "coordinates": [
                    [
                        [b2[0], b2[1]],
                        [b2[0], b2[3]],
                        [b2[2], b2[3]],
                        [b2[2], b2[1]],
                        [b2[0], b2[1]],
                    ]
                ],
            }
        ]
    else:
        b2 = inR2.bounds
        boxJSON = [
            {
                "type": "Polygon",
                "coordinates": [
                    [
                        [b2.left, b2.bottom],
                        [b2.left, b2.top],
                        [b2.right, b2.top],
                        [b2.right, b2.bottom],
                        [b2.left, b2.bottom],
                    ]
                ],
            }
        ]
    # Clip R1 to R2
    # Get JSON of bounding box
    out_img, out_transform = mask(inR1, boxJSON, crop=True)
    out_img[out_img < 0] = 0
    out_meta = inR1.meta.copy()
    # Re-scale resolution of R1 to R2
    newArr = np.empty(shape=(1, inR2.shape[0], inR2.shape[1]))

    if resampling_type == "cubic":
        resampling_type = Resampling.cubic
    elif resampling_type == "nearest":
        resampling_type = Resampling.nearest
    elif resampling_type == "sum":
        resampling_type = Resampling.sum
    reproject(
        out_img,
        newArr,
        src_transform=out_transform,
        dst_transform=inR2.transform,
        src_crs=inR1.crs,
        dst_crs=inR2.crs,
        resampling=resampling_type,
    )
    out_meta.update(
        {
            "driver": "GTiff",
            "height": newArr.shape[1],
            "width": newArr.shape[2],
            "transform": inR2.transform,
            "crs": inR2.crs,
        }
    )
    if inR1_outFile != "":
        with rasterio.open(inR1_outFile, "w", **out_meta) as dest:
            dest.write(newArr.astype(out_meta["dtype"]))
    return [newArr.astype(out_meta["dtype"]), out_meta]


def jaccardIndex(inR1, inR2):
    """Calculate the jaccard index on two binary input raster objects; Reference: https://en.wikipedia.org/wiki/Jaccard_index

    :param inR1: binary rasterio raster object to compare; needs to be same shape as inR2
    :type inR1: rasterio.DatasetReader
    :param inR2: binary rasterio raster object to compare; needs to be same shape as inR1
    :type inR2: rasterio.DatasetReader
    :raises ValueError: if inR1 and inR2 are different shapes
    :return: index comparing similarity of input raster datasets
    :rtype: float
    """
    if inR1.shape != inR2.shape:
        print(inR1.shape)
        print(inR2.shape)
        raise ValueError("Shape of input rasters do not match")
    # Add the two rasters together and get the unique tabulation
    inC = inR1.read() + inR2.read()
    xx = np.unique(inC, return_counts=True)
    outDict = {}
    for itemIdx in range(0, len(xx[0])):
        outDict[xx[0][itemIdx]] = xx[1][itemIdx]

    # The resulting could have some weird numbers, but values 1 and 2 should be the focus.
    #   1 - Only one area defines it as urban
    #   2 - Both areas define cell as urban
    # Jaccard is ratio of 2 / 1+2
    try:
        jIdx = outDict[2] / float(outDict[2] + outDict[1])
        return jIdx
    except:
        return -1
