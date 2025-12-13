# GOSTrocks API Docstrings

## dataMisc

### `download_WSF(extent, wsf_url='https://download.geoservice.dlr.de/WSF2019/files/WSF2019_cog.tif', out_file='')`

**Description:**

Download the World Settlement Footprint (WSF) dataset from DLR and optionally clip to an extent.

**Parameters:**

- `extent` (*shapely.geometry.Polygon*): Polygon to clip the WSF dataset to.
- `wsf_url` (*str*, optional): WSF download link, defaults to `https://download.geoservice.dlr.de/WSF2019/files/WSF2019_cog.tif`.
- `out_file` (*str*, optional): Output path for the clipped file; empty string skips writing.

---

### `aws_search_ntl(bucket='globalnightlight', prefix='composites', unsigned=True, verbose=False)`

**Description:**

Get a list of nighttime lights files from the open AWS bucket (`https://registry.opendata.aws/wb-light-every-night/`).

**Parameters:**

- `bucket` (*str*, optional): Bucket to search for imagery, defaults to `globalnightlight`.
- `prefix` (*str*, optional): Prefix storing images; not required for LEN, defaults to `composites`.
- `unsigned` (*bool*, optional): Access bucket without credentials, defaults to `True`.
- `verbose` (*bool*, optional): Print additional support messages, defaults to `False`.

---

### `get_geoboundaries(iso3, level, geo_api='https://www.geoboundaries.org/api/current/gbOpen/{iso3}/{adm}/')`

**Description:**

Download administrative boundaries from GeoBoundaries.

**Parameters:**

- `iso3` (*bool*): ISO3 code of the country to download.
- `level` (*str*): Admin code to download in format `ADM1` or `ADM2`.
- `geo_api` (*str*, optional): Template URL for GeoBoundaries API, defaults to `https://www.geoboundaries.org/api/current/gbOpen/{iso3}/{adm}/`.

**Returns:**

- `gpd.GeoDataFrame`: Spatial data representing the administrative boundaries.

---

### `get_fathom_vrts(return_df=False)`

**Description:**

Get a list of VRT files of Fathom data from the GOST S3 bucket using the stored list bundled with the function.

**Parameters:**

- `return_df` (*bool*, optional): If `True`, return a pandas dataframe with the VRT files and their components, defaults to `False`.

---

### `get_worldcover(df, download_folder, worldcover_vrt='WorldCover.vrt', version='v200', print_command=False, verbose=False)`

**Description:**

Download ESA globcover from AWS and optionally build a VRT.

**Parameters:**

- `df` (*geopandas.GeoDataFrame*): Data frame used to select tiles based on the dataframe `unary_union`.
- `download_folder` (*str*): Path to folder to download tiles.
- `worldcover_vrt` (*str*, optional): Name of the VRT file to create, defaults to `WorldCover.vrt`.
- `version` (*str*, optional): Version of WorldCover to download, defaults to `v200` (other option `v100`).
- `print_command` (*bool*, optional): If `True`, print the `awscli` commands; otherwise use boto3 to download, defaults to `False`.
- `verbose` (*bool*, optional): Print more updates during processing, defaults to `False`.

---

### `gdf_esri_service(url, layer=0, verify_ssl=True)`

**Description:**

Download a GeoDataFrame from an ESRI service.

**Parameters:**

- `url` (*str*): URL to the ESRI service without the layer number.
- `layer` (*int*, optional): Layer number to download, defaults to `0`.
- `verify_ssl` (*bool*, optional): Verify SSL certificates, defaults to `True`.

**Returns:**

- `gpd.GeoDataFrame`: GeoDataFrame of the data.
- `str`: Reference article URL for the extraction method.

---

### `get_acled_creds()`

**Description:**

Get the ACLED credentials from a `.acled` file in the user's home directory.

**Parameters:**

- None

**Returns:**

- `dict`: Dictionary with email and API key for ACLED.

---

### `acled_search(api_key, email, bounding_box=None, iso3=None, start_date=None, fields=[])`

**Description:**

Search the ACLED API for data based on either a bounding box, ISO3 code, or start date (`https://apidocs.acleddata.com/acled_endpoint.html`).

**Parameters:**

- `api_key` (*str*): ACLED API key found on your ACLED dashboard.
- `email` (*str*): ACLED email found on your ACLED dashboard.
- `bounding_box` (*list[float]*, optional): Bounding box defined as `minx, miny, maxx, maxy`.
- `iso3` (*str*, optional): Numeric ISO code for the country, for example `pycountry.countries.get(alpha_3=iso3).numeric`.
- `start_date` (*str*, optional): Starting date to search for events, format `YYYY-MM-DD`.
- `fields` (*list*, optional): Additional fields to request, defaults to `[]`.

**Returns:**

- `pd.DataFrame`: Results of the search converted into a DataFrame.

**Raises:**

- `ValueError`: If the API call fails for any reason.

---

## ghslMisc

### `combine_ghsl_annual(ghsl_files, built_thresh=0.1, ghsl_files_labels=[], out_file='')`

**Description:**

Combine annual GHSL TIFF files into a single raster showing earliest built-up year per pixel.

**Parameters:**

- `ghsl_files` (*list[str]*): GHSL annual files to process.
- `built_thresh` (*float*, optional): Minimum percent built to be considered built, defaults to `0.1`.
- `ghsl_files_labels` (*list*, optional): Values to assign in output raster; if empty, numbers are extracted from filenames, defaults to `[]`.
- `out_file` (*str*, optional): Location to write output integer file; empty string skips writing.

**Returns:**

- `list`: Combined GHSL values and rasterio profile.

---

## mapMisc

### `fetch_wb_style(json_url='https://wbg-vis-design.vercel.app/colors.json')`

**Description:**

Fetch the World Bank style JSON file from the internet.

**Parameters:**

- `json_url` (*str*, optional): URL to the World Bank style JSON file, defaults to `https://wbg-vis-design.vercel.app/colors.json`.

**Returns:**

- `dict`: JSON content containing World Bank style.

---

### `static_map_vector(v_data, map_column, colormap='Reds', edgecolor='darker', reverse_colormap=False, thresh=None, legend_loc='upper right', figsize=(10, 10), out_file='', set_title=True, add_basemap=True, add_wb_borders_lines=True, iso3='', bbox=None, **kwargs)`

**Description:**

Simple plot of vector data with optional basemap and styling controls.

**Parameters:**

- `v_data` (*geopandas.GeoDataFrame*): Input GeoDataFrame to map.
- `map_column` (*str*): Column label in `v_data` to map.
- `colormap` (*str*, optional): Name of colour ramp to send to matplotlib, defaults to `Reds`.
- `edgecolor` (*str*, optional): Edge colour for polygons (`match`, `darker`, or explicit colour), defaults to `darker`.
- `reverse_colormap` (*bool*, optional): Reverse the colormap, defaults to `False`.
- `thresh` (*list*, optional): Thresholds to categorize values in `v_data[map_column]`; defaults to equal-interval six classes.
- `legend_loc` (*str*, optional): Legend placement passed to `ax.legend`, defaults to `upper right`.
- `figsize` (*tuple*, optional): Size of image, defaults to `(10, 10)`.
- `out_file` (*str*, optional): Path to create output image; empty string skips writing.
- `set_title` (*bool*, optional): Whether to set title of plot, defaults to `True`.
- `add_basemap` (*bool*, optional): Whether to add a basemap from `contextily`, defaults to `True`.
- `add_wb_borders_lines` (*bool*, optional): Whether to add World Bank borders and lines, defaults to `True`.
- `iso3` (*str*, optional): ISO3 country code to filter World Bank borders and lines, defaults to empty string.
- `bbox` (*tuple*, optional): Bounding box to set map extent in CRS of `v_data`, defaults to `None`.
- `**kwargs`: Additional keyword arguments forwarded to plotting utilities.

**Returns:**

- `matplotlib.pyplot`: Matplotlib object containing the map.

---

### `static_map_raster(r_data, colormap='magma', reverse_colormap=False, thresh=None, legend_loc='upper right', figsize=(10, 10), out_file='')`

**Description:**

Simple plot of raster data for the first band of a raster dataset.

**Parameters:**

- `r_data` (*rasterio.RasterDatasetReader*): Raster data to map.
- `colormap` (*str*, optional): Name of colour ramp to send to matplotlib, defaults to `magma`.
- `reverse_colormap` (*bool*, optional): Reverse the colormap, defaults to `False`.
- `thresh` (*list[int]*, optional): Thresholds to categorize values, defaults to equal-interval six classes.
- `legend_loc` (*str*, optional): Legend placement, defaults to `upper right`.
- `figsize` (*tuple*, optional): Size of image, defaults to `(10, 10)`.
- `out_file` (*str*, optional): Path to create output image; empty string skips writing.

**Returns:**

- `matplotlib.pyplot`: Matplotlib object containing the map.

---

## misc

### `get_folder_size(folder_path)`

**Description:**

Get the total size of a folder in bytes.

**Parameters:**

- `folder_path` (*str*): Path to the folder.

**Returns:**

- `int`: Total size of the folder in bytes.

---

### `loggingInfo(lvl=logging.INFO)`

**Description:**

Set the logging level.

**Parameters:**

- `lvl` (*int*, optional): Logging level to set, defaults to `logging.INFO`.

**Returns:**

- *None*: This function sets configuration and returns nothing.

---

### `tPrint(s)`

**Description:**

Print the time along with the message.

**Parameters:**

- `s` (*str*): Message to print.

**Returns:**

- *None*: This function prints output and returns nothing.

---

### `drange(start, stop, step)`

**Description:**

Generate a range object with decimal points.

**Parameters:**

- `start` (*float*): Starting value of the range.
- `stop` (*float*): End value of the range.
- `step` (*float*): Step size for the range.

**Returns:**

- *float*: Next value in the range.

---

### `getHistIndex(hIdx, val)`

**Description:**

Get the index of a specific value within a list of histogram values.

**Parameters:**

- `hIdx` (*list*): List of histogram values.
- `val` (*float*): Value to search for.

**Returns:**

- `int`: Index in `hIdx` where `val` falls.

---

### `listSum(inD)`

**Description:**

Get the total value of a list.

**Parameters:**

- `inD` (*list*): List of numbers.

**Returns:**

- `float`: Total value of the list.

---

### `getHistPer(inD)`

**Description:**

Convert list of values into percentage of a total.

**Parameters:**

- `inD` (*list*): List of numbers.

**Returns:**

- `list`: Percentages corresponding to the input values.

---

### `createFishnet(xmin, xmax, ymin, ymax, gridHeight, gridWidth, type='POLY', crsNum=4326, outputGridfn='')`

**Description:**

Create a vector fishnet inside the defined range.

**Parameters:**

- `xmin` (*float*): Minimum x-coordinate of the fishnet.
- `xmax` (*float*): Maximum x-coordinate of the fishnet.
- `ymin` (*float*): Minimum y-coordinate of the fishnet.
- `ymax` (*float*): Maximum y-coordinate of the fishnet.
- `gridHeight` (*float*): Height of each grid cell.
- `gridWidth` (*float*): Width of each grid cell.
- `type` (*str*, optional): Geometry type of the fishnet, defaults to `POLY`.
- `crsNum` (*int*, optional): Coordinate reference system number, defaults to `4326`.
- `outputGridfn` (*str*, optional): Path to the output grid file; empty string skips writing.

**Returns:**

- `gpd.GeoDataFrame`: GeoDataFrame containing the fishnet grid.

---

### `explodeGDF(indf)`

**Description:**

Convert multi-part geometries into separate rows in a GeoDataFrame.

**Parameters:**

- `indf` (*geopandas.GeoDataFrame*): Input GeoDataFrame with possible multi-part geometries.

**Returns:**

- `gpd.GeoDataFrame`: GeoDataFrame with exploded geometries.

---

## ntlMisc

### `extract_monthly_ntl(aoi, out_folder, sel_files=[])`

**Description:**

Extract monthly nighttime lights imagery from AWS S3 for an area of interest and save to an output folder.

**Parameters:**

- `aoi` (*geopandas.GeoDataFrame*): Polygonal area of interest to extract imagery for.
- `out_folder` (*str*): Path to the folder to save extracted imagery.
- `sel_files` (*list*, optional): Files to extract; defaults to all returned from `gostrocks.dataMisc.aws_search_ntl()`.

**Returns:**

- *None*: Writes output and returns nothing.

---

### `read_raster_box(curRaster, geometry, bandNum=1)`

**Description:**

Read a section of a rasterio object with a specified geometry.

**Parameters:**

- `curRaster` (*rasterio.DatasetReader*): Raster file to read from.
- `geometry` (*shapely.geometry*): Geometry to read from raster.
- `bandNum` (*int*, optional): Band in `curRaster` to read, defaults to `1`.

**Returns:**

- `numpy.ndarray`: Array of raster values from `curRaster` within `geometry`.

---

### `calc_annual(df, extent, agg_method='MEAN')`

**Description:**

Combine monthly nighttime lights images into an annual composite.

**Parameters:**

- `df` (*pandas.DataFrame*): Data frame of images with columns `YEAR`, `MONTH`, `PATH`.
- `extent` (*shapely.Polygon*): Area to extract imagery from.
- `agg_method` (*str*, optional): Aggregation method, defaults to `MEAN`.

---

### `generate_annual_composites(aoi, agg_method='MEAN', sel_files=[], out_folder='')`

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

### `map_viirs(cur_file, out_file='', class_bins=[-10, 0.5, 1, 2, 3, 5, 10, 15, 20, 30, 40, 50], text_x=0, text_y=5, dpi=100)`

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

### `run_zonal(inD, ntl_files=[], minval=0.1, verbose=False, calc_sd=True)`

**Description:**

Run zonal statistics against a series of nighttime lights files.

**Parameters:**

- `inD` (*gpd.GeoDataFrame*): Input GeoDataFrame to summarize results within.
- `ntl_files` (*list*, optional): NTL files to summarize; defaults to searching S3 using `dataMisc.aws_search_ntl()`.
- `minval` (*float*, optional): Minimum value to summarize; values below become `0`, defaults to `0.1`.
- `verbose` (*bool*, optional): Print additional information, defaults to `False`.
- `calc_sd` (*bool*, optional): Calculate standard deviation alongside summary stats, defaults to `True`.

---

## osmMisc

### `class osmExtraction`

**Description:**

Wrapper around Osmosis for downloading and extracting OSM data (`https://wiki.openstreetmap.org/wiki/Osmosis`).

**Parameters:**

- None

**Returns:**

- `osmExtraction`: Instance configured for OSM extraction tasks.

---

### `osmExtraction.__init__(osmosisCmd='C\\WBG\\Anaconda\\Osmosis\\bin\\osmosis', tempFile='C\\WBG\\Anaconda\\Osmosis\\tempExecution.bat')`

**Description:**

Initialize an `osmExtraction` instance.

**Parameters:**

- `osmosisCmd` (*str*, optional): Path to the osmosis executable in the downloaded stable release.
- `tempFile` (*str*, optional): Temporary execution file used when building commands.

**Returns:**

- *None*: Constructor, no return value.

---

### `osmExtraction.extractAmmenities(inPbf, outFile, amenityList=['amenity.school'], bounds=[], execute=False)`

**Description:**

Read input OSM PBF, extract amenities, and write to shapefile.

**Parameters:**

- `inPbf` (*str*): Path to input PBF.
- `outFile` (*str*): Path to output shapefile.
- `amenityList` (*list[str]*, optional): Amenity definitions to extract, defaults to `["amenity.school"]`.
- `bounds` (*list*, optional): Bounds of area to extract; if empty covers entire input area.
- `execute` (*bool*, optional): If `False`, return osmosis command instead of executing, defaults to `False`.

**Returns:**

- *Any*: Returns either an osmosis command or execution result.

---

### `osmExtraction.extractBuildings(inPbf, outFile, bounds=[], execute=True)`

**Description:**

Read input OSM PBF, extract buildings, and write to shapefile.

**Parameters:**

- `inPbf` (*str*): Path to input PBF.
- `outFile` (*str*): Path to output shapefile.
- `bounds` (*list*, optional): Bounds of area to extract; if empty covers entire input area.
- `execute` (*bool*, optional): If `False`, return osmosis command instead of executing, defaults to `True`.

**Returns:**

- *Any*: Returns either an osmosis command or execution result.

---

### `osmExtraction.extractBoundingBox(inPbf, inShp, outPbf, execute=True)`

**Description:**

Extract a bounding box from an input PBF based on an input shapefile.

**Parameters:**

- `inPbf` (*str*): Path to input PBF.
- `inShp` (*str | geopandas.GeoDataFrame*): Path to AOI shapefile or GeoDataFrame.
- `outPbf` (*str*): Path to output PBF.
- `execute` (*bool*, optional): If `False`, return osmosis command instead of executing, defaults to `True`.

**Returns:**

- *Any*: Returns either an osmosis command or execution result.

---

### `osmExtraction.extractHighways(inPbf, outOSM, values=[1, 2, 3, 4], bounds=[], execute=True)`

**Description:**

Extract highways (roads) from input OSM PBF, optionally limited by OSMLR class.

**Parameters:**

- `inPbf` (*str*): Path to input OSM PBF file.
- `outOSM` (*str*): Path to output OSM PBF file.
- `values` (*list[int]*, optional): OSMLR classes to extract, defaults to `[1, 2, 3, 4]`.
- `bounds` (*list*, optional): Boundary to extract; if empty covers entire input area.
- `execute` (*bool*, optional): If `False`, return osmosis command instead of executing, defaults to `True`.

**Returns:**

- *Any*: Returns either an osmosis command or execution result.

---

### `summarizeOSM(grid, verbose=True, roadsOnly=False)`

**Description:**

Summarize OSM road length within each feature in the input grid (length projection uses Web Mercator).

**Parameters:**

- `grid` (*geopandas.GeoDataFrame*): Features that will receive the length summary for all roads.
- `verbose` (*bool*, optional): Print progress information, defaults to `True`.
- `roadsOnly` (*bool*, optional): Limit summary to road features, defaults to `False`.

---

### `convertOSMPBF_DataFrame(inOSM, layer)`

**Description:**

Convert an input OSM PBF to a GeoDataFrame.

**Parameters:**

- `inOSM` (*str*): Path to OSM PBF to convert.
- `layer` (*str*): Data layer to extract; choose from lines, points, multipolygons, or multilinestrings.

**Returns:**

- `geopandas.GeoDataFrame`: Extracted OSM data.

---

## rasterMisc

### `merge_rasters(in_rasters, merge_method='first', dtype='', out_file='', boolean_gt_0=False, gdal_unssafe=False, compress=False)`

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

### `create_rasterio_inmemory(src, curData)`

**Description:**

Create a rasterio object in memory from a numpy array.

**Parameters:**

- `src` (*rasterio.metadata*): Metadata for the rasterio object.
- `curData` (*numpy.ndarray*): Data to write to the rasterio object.

**Returns:**

- `rasterio.DatasetReader`: In-memory rasterio dataset.

---

### `vectorize_raster(inR, bad_vals=[])`

**Description:**

Convert input raster data to a GeoDataFrame.

**Parameters:**

- `inR` (*rasterio.DatasetReader*): Input raster data to vectorize.
- `bad_vals` (*list*, optional): Values to ignore in conversion, defaults to `[]`.

**Returns:**

- `geopandas.GeoDataFrame`: GeoDataFrame containing the vectorized raster data.

---

### `project_raster(srcRst, dstCrs, output_raster='')`

**Description:**

Project a raster to a destination CRS.

**Parameters:**

- `srcRst` (*rasterio.DatasetReader*): Input raster to reproject.
- `dstCrs` (*int*): CRS to project to.
- `output_raster` (*str*, optional): File to write to; empty string skips writing.

**Returns:**

- `tuple`: Reprojected raster and its metadata.

---

### `clipRaster(inR, inD, outFile=None, crop=True)`

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

### `rasterizeDataFrame(inD, outFile, idField='', templateRaster='', templateMeta='', nCells=0, res=0, mergeAlg='REPLACE', re_proj=False, nodata=np.nan, smooth=False, smooth_sigma=50)`

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

### `polygonizeArray(geometry, curRaster, bandNum=1)`

**Description:**

Convert cells of a rasterio object into a GeoDataFrame of polygons within the bounds of a geometry.

**Parameters:**

- `geometry` (*shapely.geometry*): Polygon inside which to create polygon grid.
- `curRaster` (*rasterio.DatasetReader*): Raster from which to create polygons.
- `bandNum` (*int*, optional): Band number to polygonize, defaults to `1`.

**Returns:**

- `geopandas.GeoDataFrame`: Grid of polygons with values from the raster and percentage overlap with geometry.

---

### `zonalStats(inShp, inRaster, bandNum=1, mask_A=None, reProj=False, minVal='', maxVal='', verbose=False, rastType='N', unqVals=[], weighted=False, allTouched=False, calc_sd=False, return_df=False)`

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

### `standardizeInputRasters(inR1, inR2, inR1_outFile='', resampling_type='nearest')`

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

### `jaccardIndex(inR1, inR2)`

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

## shapeMisc

### `polsby_popper(cShape)`

**Description:**

Calculate the Polsby-Popper score for a given shape.

**Parameters:**

- `cShape` (*shapely.Polygon*): Shape for which to calculate shape metrics.

---

### `schwartzberg(cShape)`

**Description:**

Calculate the Schwartzberg score for a given shape.

**Parameters:**

- `cShape` (*shapely.Polygon*): Shape for which to calculate shape metrics.

---

### `ckdnearest(gdfA, gdfB, gdfB_cols=['ID'])`

**Description:**

Calculate the nearest object in `gdfB` for each object in `gdfA`; works for varied geometry types.

**Parameters:**

- `gdfA` (*geopandas.GeoDataFrame*): GeoDataFrame containing geometries to find nearest match for.
- `gdfB` (*geopandas.GeoDataFrame*): GeoDataFrame containing geometries to match from.
- `gdfB_cols` (*list[str]*, optional): Columns from `gdfB` to attach to `gdfA`, defaults to `["ID"]`.

**Returns:**

- `geopandas.GeoDataFrame`: `gdfA` with columns from `gdfB` and distance to nearest geometry.

---
