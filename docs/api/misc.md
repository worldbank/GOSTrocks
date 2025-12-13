# misc

## `get_folder_size(folder_path)`

**Description:**

Get the total size of a folder in bytes.

**Parameters:**

- `folder_path` (*str*): Path to the folder.

**Returns:**

- `int`: Total size of the folder in bytes.

---

## `loggingInfo(lvl=logging.INFO)`

**Description:**

Set the logging level.

**Parameters:**

- `lvl` (*int*, optional): Logging level to set, defaults to `logging.INFO`.

**Returns:**

- *None*: This function sets configuration and returns nothing.

---

## `tPrint(s)`

**Description:**

Print the time along with the message.

**Parameters:**

- `s` (*str*): Message to print.

**Returns:**

- *None*: This function prints output and returns nothing.

---

## `drange(start, stop, step)`

**Description:**

Generate a range object with decimal points.

**Parameters:**

- `start` (*float*): Starting value of the range.
- `stop` (*float*): End value of the range.
- `step` (*float*): Step size for the range.

**Returns:**

- *float*: Next value in the range.

---

## `getHistIndex(hIdx, val)`

**Description:**

Get the index of a specific value within a list of histogram values.

**Parameters:**

- `hIdx` (*list*): List of histogram values.
- `val` (*float*): Value to search for.

**Returns:**

- `int`: Index in `hIdx` where `val` falls.

---

## `listSum(inD)`

**Description:**

Get the total value of a list.

**Parameters:**

- `inD` (*list*): List of numbers.

**Returns:**

- `float`: Total value of the list.

---

## `getHistPer(inD)`

**Description:**

Convert list of values into percentage of a total.

**Parameters:**

- `inD` (*list*): List of numbers.

**Returns:**

- `list`: Percentages corresponding to the input values.

---

## `createFishnet(xmin, xmax, ymin, ymax, gridHeight, gridWidth, type='POLY', crsNum=4326, outputGridfn='')`

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

## `explodeGDF(indf)`

**Description:**

Convert multi-part geometries into separate rows in a GeoDataFrame.

**Parameters:**

- `indf` (*geopandas.GeoDataFrame*): Input GeoDataFrame with possible multi-part geometries.

**Returns:**

- `gpd.GeoDataFrame`: GeoDataFrame with exploded geometries.

---
