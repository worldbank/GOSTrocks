import sys, os
import math

import geopandas as pd

def polsby_popper(cShape):
    """ Calculate the Polsby-Popper score for a given shape
        https://fisherzachary.github.io/public/r-output.html
    Parameters
    ----------
    cShape : Shapely Polygon
        shape for which to calculate share metrics
    """
    area = cShape.area
    perimeter = cShape.length
    polsby_popper = 4 * math.pi * (area / (perimeter**2))
    return(polsby_popper)

def schwartzberg(cShape):
    """ Calculate the Schwartzberg score for a given shape
        https://fisherzachary.github.io/public/r-output.html
    Parameters
    ----------
    cShape : Shapely Polygon
        shape for which to calculate share metrics
    """
    p = cShape.length
    a = cShape.area    
    return (1/(p/(2*math.pi*math.sqrt(a/math.pi))))
    