# osmMisc

## `class osmExtraction`

**Description:**

Wrapper around Osmosis for downloading and extracting OSM data (`https://wiki.openstreetmap.org/wiki/Osmosis`).

**Parameters:**

- None

**Returns:**

- `osmExtraction`: Instance configured for OSM extraction tasks.

---

## `osmExtraction.__init__(osmosisCmd='C\\WBG\\Anaconda\\Osmosis\\bin\\osmosis', tempFile='C\\WBG\\Anaconda\\Osmosis\\tempExecution.bat')`

**Description:**

Initialize an `osmExtraction` instance.

**Parameters:**

- `osmosisCmd` (*str*, optional): Path to the osmosis executable in the downloaded stable release.
- `tempFile` (*str*, optional): Temporary execution file used when building commands.

**Returns:**

- *None*: Constructor, no return value.

---

## `osmExtraction.extractAmmenities(inPbf, outFile, amenityList=['amenity.school'], bounds=[], execute=False)`

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

## `osmExtraction.extractBuildings(inPbf, outFile, bounds=[], execute=True)`

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

## `osmExtraction.extractBoundingBox(inPbf, inShp, outPbf, execute=True)`

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

## `osmExtraction.extractHighways(inPbf, outOSM, values=[1, 2, 3, 4], bounds=[], execute=True)`

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

## `summarizeOSM(grid, verbose=True, roadsOnly=False)`

**Description:**

Summarize OSM road length within each feature in the input grid (length projection uses Web Mercator).

**Parameters:**

- `grid` (*geopandas.GeoDataFrame*): Features that will receive the length summary for all roads.
- `verbose` (*bool*, optional): Print progress information, defaults to `True`.
- `roadsOnly` (*bool*, optional): Limit summary to road features, defaults to `False`.

---

## `convertOSMPBF_DataFrame(inOSM, layer)`

**Description:**

Convert an input OSM PBF to a GeoDataFrame.

**Parameters:**

- `inOSM` (*str*): Path to OSM PBF to convert.
- `layer` (*str*): Data layer to extract; choose from lines, points, multipolygons, or multilinestrings.

**Returns:**

- `geopandas.GeoDataFrame`: Extracted OSM data.

---
