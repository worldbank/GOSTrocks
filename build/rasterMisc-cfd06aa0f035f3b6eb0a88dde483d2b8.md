# rasterMisc

## `merge_rasters(in_rasters, merge_method='first', dtype='', out_file='', boolean_gt_0=False, gdal_unssafe=False, compress=False)`

**Description:**

Merge a list of rasters into a single raster file.

**Parameters:**

- `in_rasters` (*list*): Rasters to merge.
- `merge_method` (*str*, optional): Merge method, defaults to `first`.
- `dtype` (*str*, optional): Data type for output raster; empty string derives from input.
- `out_file` (*str*, optional): Output path; empty string keeps result in memory.
- `boolean_gt_0` (*bool*, optional): Convert values greater than `0` to boolean, defaults to `False`.
- `gdal_unssafe` (*bool*, optional): Use GDAL unsafe operations, defaults to `False`.
- `compress` (*bool*, optional): Apply compression to output raster, defaults to `False`.

**Returns:**

- `tuple`: Merged raster and its metadata.

---

## `create_rasterio_inmemory(src, curData)`

**Description:**

Create a rasterio object in memory from a numpy array.

**Parameters:**

- `src` (*rasterio.metadata*): Metadata for the rasterio object.
- `curData` (*numpy.ndarray*): Data to write to the rasterio object.

**Returns:**

- `rasterio.DatasetReader`: In-memory rasterio dataset.

---

## `vectorize_raster(inR, bad_vals=[])`

**Description:**

Convert input raster data to a GeoDataFrame.

**Parameters:**

- `inR` (*rasterio.DatasetReader*): Input raster data to vectorize.
- `bad_vals` (*list*, optional): Values to ignore in conversion, defaults to `[]`.

**Returns:**

- `geopandas.GeoDataFrame`: GeoDataFrame containing the vectorized raster data.

---

## `project_raster(srcRst, dstCrs, output_raster='')`

**Description:**

Project a raster to a destination CRS.

**Parameters:**

- `srcRst` (*rasterio.DatasetReader*): Input raster to reproject.
- `dstCrs` (*int*): CRS to project to.
- `output_raster` (*str*, optional): File to write to; empty string skips writing.

**Returns:**

- `tuple`: Reprojected raster and its metadata.

---

## `clipRaster(inR, inD, outFile=None, crop=True)`

**Description:**

Clip input raster to a provided GeoDataFrame.

**Parameters:**

- `inR` (*rasterio.DatasetReader*): Input raster to clip.
- `inD` (*geopandas.GeoDataFrame*): GeoDataFrame containing the clipping geometry.
- `outFile` (*str*, optional): File to write the clipped raster to, defaults to `None`.
- `crop` (*bool*, optional): Crop raster to the `unary_union` of GeoDataFrame (`True`) or bounding box (`False`), defaults to `True`.

**Returns:**

- `tuple`: Clipped raster and its metadata.

---

## `rasterizeDataFrame(inD, outFile, idField='', templateRaster='', templateMeta='', nCells=0, res=0, mergeAlg='REPLACE', re_proj=False, nodata=np.nan, smooth=False, smooth_sigma=50)`

**Description:**

Convert input GeoDataFrame into a raster file.

**Parameters:**

- `inD` (*gpd.GeoDataFrame*): Input data frame to rasterize.
- `outFile` (*str*): Output file to create from rasterized dataframe; empty string skips writing.
- `idField` (*str*, optional): Field in `inD` to rasterize; empty string sets all values to `1`.
- `templateRaster` (*str*, optional): Raster used to base raster creation; if none, `nCells` or `res` must be defined.
- `templateMeta` (*str*, optional): Raster metadata used to create output raster.
- `nCells` (*int*, optional): Number of cells in width and height, defaults to `0`.
- `res` (*int*, optional): Resolution of output raster in units of the CRS, defaults to `0`.
- `mergeAlg` (*str*, optional): Method of aggregating overlapping features (`REPLACE` or `ADD`), defaults to `REPLACE`.
- `re_proj` (*bool*, optional): Reproject `inD` to `templateRaster` if CRS do not match, defaults to `False`.
- `nodata` (*number*, optional): Value to set as nodata in output raster, defaults to `np.nan`.
- `smooth` (*bool*, optional): Smooth raster output using `scipy.ndimage.gaussian_filter`, defaults to `False`.
- `smooth_sigma` (*int*, optional): Sigma value for gaussian smoothing, defaults to `50`.

**Returns:**

- `dict`: Metadata used to create output raster and burned raster values.

---

## `polygonizeArray(geometry, curRaster, bandNum=1)`

**Description:**

Convert cells of a rasterio object into a GeoDataFrame of polygons within the bounds of a geometry.

**Parameters:**

- `geometry` (*shapely.geometry*): Polygon inside which to create polygon grid.
- `curRaster` (*rasterio.DatasetReader*): Raster from which to create polygons.
- `bandNum` (*int*, optional): Band number to polygonize, defaults to `1`.

**Returns:**

- `geopandas.GeoDataFrame`: Grid of polygons with values from the raster and percentage overlap with geometry.

---

## `zonalStats(inShp, inRaster, bandNum=1, mask_A=None, reProj=False, minVal='', maxVal='', verbose=False, rastType='N', unqVals=[], weighted=False, allTouched=False, calc_sd=False, return_df=False)`

**Description:**

Run zonal statistics against an input shapefile and raster.

**Parameters:**

- `inShp` (*str | gpd.GeoDataFrame*): Input geospatial data to summarize raster.
- `inRaster` (*str | rasterio.DatasetReader*): Input raster to summarize.
- `bandNum` (*int*, optional): Band in raster to analyze, defaults to `1`.
- `mask_A` (*np.array*, optional): Mask the raster data using an identical shaped boolean mask, defaults to `None`.
- `reProj` (*bool*, optional): Reproject data to match CRS; if `False`, raises error on mismatch, defaults to `False`.
- `minVal` (*number*, optional): Only calculate statistics on values above this number.
- `maxVal` (*number*, optional): Only calculate statistics on values below this number.
- `verbose` (*bool*, optional): Provide additional text updates, defaults to `False`.
- `rastType` (*str*, optional): Raster type, `N` numerical or `C` categorical; provide `unqVals` if categorical, defaults to `N`.
- `unqVals` (*list[int]*, optional): Unique values to search for in raster, defaults to `[]`.
- `weighted` (*bool*, optional): Apply weighted zonal calculations using percentage overlap, defaults to `False`.
- `allTouched` (*bool*, optional): Include all touched cells in raster calculation, defaults to `False`.
- `calc_sd` (*bool*, optional): Include standard deviation in calculation, defaults to `False`.
- `return_df` (*bool*, optional): If `True`, return result as data frame, defaults to `False`.

**Returns:**

- `array`: Zonal results for each feature in `inShp` (SUM, MIN, MAX, MEAN, SD optional).

**Raises:**

- `ValueError`: If CRS mismatch occurs between `inShp` and `inRaster`.

---

## `standardizeInputRasters(inR1, inR2, inR1_outFile='', resampling_type='nearest')`

**Description:**

Standardize `inR1` to `inR2` by changing CRS, extent, and resolution.

**Parameters:**

- `inR1` (*rasterio.DatasetReader | str*): Raster to be modified.
- `inR2` (*rasterio.DatasetReader*): Raster to standardize to.
- `inR1_outFile` (*str*, optional): Output path for standardized raster; empty string skips writing.
- `resampling_type` (*str*, optional): Spatial resampling method (`nearest`, `cubic`, `sum`), defaults to `nearest`.

**Returns:**

- `array`: Numpy array of standardized raster and rasterio metadata.

---

## `jaccardIndex(inR1, inR2)`

**Description:**

Calculate the Jaccard index on two binary input raster objects.

**Parameters:**

- `inR1` (*rasterio.DatasetReader*): Binary raster to compare; needs to be same shape as `inR2`.
- `inR2` (*rasterio.DatasetReader*): Binary raster to compare; needs to be same shape as `inR1`.

**Returns:**

- `float`: Index comparing similarity of input raster datasets.

**Raises:**

- `ValueError`: If `inR1` and `inR2` are different shapes.

---
