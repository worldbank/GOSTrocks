import itertools
import math

import pandas as pd
import numpy as np

from operator import itemgetter
from scipy.spatial import cKDTree

from shapely.geometry import Polygon


def polsby_popper(cShape):
    """Calculate the Polsby-Popper score for a given shape
        https://fisherzachary.github.io/public/r-output.html
    Parameters
    ----------
    cShape : Shapely Polygon
        shape for which to calculate share metrics
    """
    area = cShape.area
    perimeter = cShape.length
    polsby_popper = 4 * math.pi * (area / (perimeter**2))
    return polsby_popper


def schwartzberg(cShape):
    """Calculate the Schwartzberg score for a given shape
        https://fisherzachary.github.io/public/r-output.html
    Parameters
    ----------
    cShape : Shapely Polygon
        shape for which to calculate share metrics
    """
    p = cShape.length
    a = cShape.area
    return 1 / (p / (2 * math.pi * math.sqrt(a / math.pi)))


def ckdnearest(gdfA, gdfB, gdfB_cols=["ID"]):
    """Calculate nearest object in gdfB for each object in gdfA; should work for varied geometry types

    Parameters
    ----------
    gdfA : geopandas.GeoDataFrame
        GeoDataFrame containing geometries to find nearest match for
    gdfB : geopandas.GeoDataFrame
        GeoDataFrame containing geometries to find nearest match from
    gdfB_cols : list of string, optional
        Columns from gdfB to attach to gdfA, by default ["ID"]

    Returns
    -------
    geopandas.GeoDataFrame
        gdfA with ID column from gdfB (defined by GDFB_cols) and distance to nearest geometry in gdfB
    """

    if gdfA.geometry.iloc[0].__class__ == Polygon:
        A = np.concatenate(
            [np.array(geom.coords) for geom in gdfA.geometry.exterior.to_list()]
        )
    else:
        A = np.concatenate([np.array(geom.coords) for geom in gdfA.geometry.to_list()])

    if gdfB.geometry.iloc[0].__class__ == Polygon:
        B = [np.array(geom.coords) for geom in gdfB.geometry.exterior.to_list()]
    else:
        B = [np.array(geom.coords) for geom in gdfB.geometry.to_list()]

    B_ix = tuple(
        itertools.chain.from_iterable(
            [itertools.repeat(i, x) for i, x in enumerate(list(map(len, B)))]
        )
    )
    B = np.concatenate(B)
    ckd_tree = cKDTree(B)
    dist, idx = ckd_tree.query(A, k=1)
    idx = itemgetter(*idx)(B_ix)
    gdf = pd.concat(
        [
            gdfA,
            gdfB.loc[idx, gdfB_cols].reset_index(drop=True),
            pd.Series(dist, name="dist"),
        ],
        axis=1,
    )
    gdf = gdf.dropna(subset=["geometry"])
    return gdf
