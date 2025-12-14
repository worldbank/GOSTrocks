# shapeMisc

## `polsby_popper(cShape)`

**Description:**

Calculate the Polsby-Popper score for a given shape.

**Parameters:**

- `cShape` (*shapely.Polygon*): Shape for which to calculate shape metrics.

---

## `schwartzberg(cShape)`

**Description:**

Calculate the Schwartzberg score for a given shape.

**Parameters:**

- `cShape` (*shapely.Polygon*): Shape for which to calculate shape metrics.

---

## `ckdnearest(gdfA, gdfB, gdfB_cols=['ID'])`

**Description:**

Calculate the nearest object in `gdfB` for each object in `gdfA`; works for varied geometry types.

**Parameters:**

- `gdfA` (*geopandas.GeoDataFrame*): GeoDataFrame containing geometries to find nearest match for.
- `gdfB` (*geopandas.GeoDataFrame*): GeoDataFrame containing geometries to match from.
- `gdfB_cols` (*list[str]*, optional): Columns from `gdfB` to attach to `gdfA`, defaults to `["ID"]`.

**Returns:**

- `geopandas.GeoDataFrame`: `gdfA` with columns from `gdfB` and distance to nearest geometry.

---
