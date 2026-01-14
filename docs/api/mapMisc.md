# mapMisc

## `fetch_wb_style(json_url='https://wbg-vis-design.vercel.app/colors.json')`

**Description:**

Fetch the World Bank style JSON file from the internet.

**Parameters:**

- `json_url` (*str*, optional): URL to the World Bank style JSON file, defaults to `https://wbg-vis-design.vercel.app/colors.json`.

**Returns:**

- `dict`: JSON content containing World Bank style.

---

## `static_map_vector(v_data, map_column, colormap='Reds', edgecolor='darker', reverse_colormap=False, thresh=None, legend_loc='upper right', figsize=(10, 10), out_file='', set_title=True, add_basemap=True, add_wb_borders_lines=True, iso3='', bbox=None, **kwargs)`

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

## `static_map_raster(r_data, colormap='magma', reverse_colormap=False, thresh=None, legend_loc='upper right', figsize=(10, 10), out_file='')`

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
