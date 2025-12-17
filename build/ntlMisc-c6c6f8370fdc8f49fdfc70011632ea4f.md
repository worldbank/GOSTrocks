# ntlMisc

## `extract_monthly_ntl(aoi, out_folder, sel_files=[])`

**Description:**

Extract monthly nighttime lights imagery from AWS S3 for an area of interest and save to an output folder.

**Parameters:**

- `aoi` (*geopandas.GeoDataFrame*): Polygonal area of interest to extract imagery for.
- `out_folder` (*str*): Path to the folder to save extracted imagery.
- `sel_files` (*list*, optional): Files to extract; defaults to all returned from `gostrocks.dataMisc.aws_search_ntl()`.

**Returns:**

- *None*: Writes output and returns nothing.

---

## `read_raster_box(curRaster, geometry, bandNum=1)`

**Description:**

Read a section of a rasterio object with a specified geometry.

**Parameters:**

- `curRaster` (*rasterio.DatasetReader*): Raster file to read from.
- `geometry` (*shapely.geometry*): Geometry to read from raster.
- `bandNum` (*int*, optional): Band in `curRaster` to read, defaults to `1`.

**Returns:**

- `numpy.ndarray`: Array of raster values from `curRaster` within `geometry`.

---

## `calc_annual(df, extent, agg_method='MEAN')`

**Description:**

Combine monthly nighttime lights images into an annual composite.

**Parameters:**

- `df` (*pandas.DataFrame*): Data frame of images with columns `YEAR`, `MONTH`, `PATH`.
- `extent` (*shapely.Polygon*): Area to extract imagery from.
- `agg_method` (*str*, optional): Aggregation method, defaults to `MEAN`.

---

## `generate_annual_composites(aoi, agg_method='MEAN', sel_files=[], out_folder='')`

**Description:**

Collapse several monthly nighttime lights images into an annual composite.

**Parameters:**

- `aoi` (*geopandas.GeoDataFrame*): Polygonal dataframe to use for clip extent.
- `agg_method` (*str*, optional): Aggregation method, defaults to `MEAN`.
- `sel_files` (*list*, optional): NTL files to process; defaults to `[]` (uses `gostrocks.dataMisc.aws_search_ntl`).
- `out_folder` (*str*, optional): Output folder path; empty string skips writing.

**Returns:**

- *None*: Writes output and returns nothing.

---

## `map_viirs(cur_file, out_file='', class_bins=[-10, 0.5, 1, 2, 3, 5, 10, 15, 20, 30, 40, 50], text_x=0, text_y=5, dpi=100)`

**Description:**

Map VIIRS nighttime lights imagery and optionally create an output image.

**Parameters:**

- `cur_file` (*str*): Path to input GeoTIFF.
- `out_file` (*str*, optional): Path to create output image; empty string skips writing.
- `class_bins` (*list[float]*, optional): Breaks for applying colour ramp, defaults to `[-10, 0.5, 1, 2, 3, 5, 10, 15, 20, 30, 40, 50]`.
- `text_x` (*int*, optional): X position for year text, defaults to `0`.
- `text_y` (*int*, optional): Y position for year text, defaults to `5`.
- `dpi` (*int*, optional): Dots per inch for output image, defaults to `100`.

**Returns:**

- `matplotlib.pyplot`: Matplotlib object containing the map.

---

## `run_zonal(inD, ntl_files=[], minval=0.1, verbose=False, calc_sd=True)`

**Description:**

Run zonal statistics against a series of nighttime lights files.

**Parameters:**

- `inD` (*gpd.GeoDataFrame*): Input GeoDataFrame to summarize results within.
- `ntl_files` (*list*, optional): NTL files to summarize; defaults to searching S3 using `dataMisc.aws_search_ntl()`.
- `minval` (*float*, optional): Minimum value to summarize; values below become `0`, defaults to `0.1`.
- `verbose` (*bool*, optional): Print additional information, defaults to `False`.
- `calc_sd` (*bool*, optional): Calculate standard deviation alongside summary stats, defaults to `True`.

---
