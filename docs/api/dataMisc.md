# dataMisc

## `download_WSF(extent, wsf_url='https://download.geoservice.dlr.de/WSF2019/files/WSF2019_cog.tif', out_file='')`

**Description:**

Download the World Settlement Footprint (WSF) dataset from DLR and optionally clip to an extent.

**Parameters:**

- `extent` (*shapely.geometry.Polygon*): Polygon to clip the WSF dataset to.
- `wsf_url` (*str*, optional): WSF download link, defaults to `https://download.geoservice.dlr.de/WSF2019/files/WSF2019_cog.tif`.
- `out_file` (*str*, optional): Output path for the clipped file; empty string skips writing.

---

## `aws_search_ntl(bucket='globalnightlight', prefix='composites', unsigned=True, verbose=False)`

**Description:**

Get a list of nighttime lights files from the open AWS bucket (`https://registry.opendata.aws/wb-light-every-night/`).

**Parameters:**

- `bucket` (*str*, optional): Bucket to search for imagery, defaults to `globalnightlight`.
- `prefix` (*str*, optional): Prefix storing images; not required for LEN, defaults to `composites`.
- `unsigned` (*bool*, optional): Access bucket without credentials, defaults to `True`.
- `verbose` (*bool*, optional): Print additional support messages, defaults to `False`.

---

## `get_geoboundaries(iso3, level, geo_api='https://www.geoboundaries.org/api/current/gbOpen/{iso3}/{adm}/')`

**Description:**

Download administrative boundaries from GeoBoundaries.

**Parameters:**

- `iso3` (*bool*): ISO3 code of the country to download.
- `level` (*str*): Admin code to download in format `ADM1` or `ADM2`.
- `geo_api` (*str*, optional): Template URL for GeoBoundaries API, defaults to `https://www.geoboundaries.org/api/current/gbOpen/{iso3}/{adm}/`.

**Returns:**

- `gpd.GeoDataFrame`: Spatial data representing the administrative boundaries.

---

## `get_fathom_vrts(return_df=False)`

**Description:**

Get a list of VRT files of Fathom data from the GOST S3 bucket using the stored list bundled with the function.

**Parameters:**

- `return_df` (*bool*, optional): If `True`, return a pandas dataframe with the VRT files and their components, defaults to `False`.

---

## `get_worldcover(df, download_folder, worldcover_vrt='WorldCover.vrt', version='v200', print_command=False, verbose=False)`

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

## `gdf_esri_service(url, layer=0, verify_ssl=True)`

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

## `get_acled_creds()`

**Description:**

Get the ACLED credentials from a `.acled` file in the user's home directory.

**Parameters:**

- None

**Returns:**

- `dict`: Dictionary with email and API key for ACLED.

---

## `acled_search(api_key, email, bounding_box=None, iso3=None, start_date=None, fields=[])`

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
