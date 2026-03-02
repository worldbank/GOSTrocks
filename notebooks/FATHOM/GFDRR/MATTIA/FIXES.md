# Fixes to FATHOM_GFDRR_ThinkHazard – code review notes

Three issues were found in `gfdrr_helper.py` and the main processing notebook that
cause scores to diverge from the reference local workflow (`TH_FL_utils.py`).

---

## 1. Nodata pixels were included in the area calculation

When building the pixel mask, only pixels *outside* the administrative unit geometry
were excluded. Pixels inside the geometry carrying the raster nodata value (Fathom
stores `-32767`, or whichever value is recorded in the raster metadata) were left in,
and — critically — counted in the **denominator** when computing the flooded-area
fraction:

```python
# BEFORE – denominator includes nodata pixels
masked_data = np.ma.array(data=data, mask=mask.astype(bool))
frac_area_flooded = (area_flooded / masked_data.count()) * 100
```

For inland units this barely matters. For **coastal units** a large share of the
bounding box is ocean, stored as nodata. Including those pixels in the denominator
artificially deflates the flooded-area percentage — sometimes enough to push a unit
below the 3 % area threshold and drop its score.

**Fix:** the nodata value is read from raster metadata (fallback to `-32767`), a
nodata mask is built and combined with the geometry mask, and only the remaining
valid land pixels enter both numerator and denominator:

```python
nodata_value  = curRaster.nodata or -32767
nodata_mask   = (data == nodata_value) | (data < 0)
combined_mask = geom_mask.astype(bool) | nodata_mask
valid_values  = data[~combined_mask]
frac_area_flooded = (np.sum(valid_values > depth_threshold) / len(valid_values)) * 100
```

---

## 2. Boundary pixels were excluded (`all_touched=False`)

When rasterising the unit geometry, `all_touched=False` was used. Pixels whose
centre falls outside the polygon — even if the polygon boundary crosses them — are
excluded. For small administrative units this can silently discard a meaningful share
of valid pixels. The reference workflow uses `all_touched=True` throughout.

**Fix:** changed to `all_touched=True` in the `rasterize()` call.

---

## 3. The mean depth was computed over pre-filtered pixels, making the value threshold gate trivially true

This is the most consequential difference. Understanding it requires being precise
about which pixels belong to which category and what each metric is supposed to measure.

### Intended pixel classification

For each valid land pixel inside a unit (nodata excluded, see fix 1):

| Pixel value | Category | In `mean_val`? | In `frac_area_flooded` numerator? | In `frac_area_flooded` denominator? |
|---|---|---|---|---|
| = 0 cm | Dry land | No | No | **Yes** |
| > 0 cm and ≤ 50 cm | Shallow flood | **Yes** | No | **Yes** |
| > 50 cm | Deep flood | **Yes** | **Yes** | **Yes** |
| < 0 or nodata | Invalid | excluded | excluded | excluded |

In other words:

- **`mean_val`** is the mean depth of *all wet pixels* (depth > 0), including shallow
  ones below the 50 cm threshold. Dry pixels (depth = 0) do not contribute. This
  value can legitimately fall below 50 cm when flooding is predominantly shallow.
- **`frac_area_flooded`** is the share of *all valid land pixels* (wet + dry) whose
  depth exceeds 50 cm. The denominator is the full valid land area of the unit, not
  just the flooded portion.

### Intended scoring condition (per return period)

A return period adds +1 to the hazard score only when **both** of the following are
true simultaneously:

1. `mean_val >= 50 cm` — the average depth across **all wet pixels** is substantial.
   This filters out units where widespread but very shallow flooding raises the
   flooded-area fraction while actual depths are negligible.
2. `frac_area_flooded >= 3 %` — at least 3 % of the unit's valid land area is
   inundated to a depth **above** 50 cm. This filters out units where only a tiny
   pocket of deep water exists.

The two conditions are complementary and must both be satisfied: condition 1 guards
against shallow-but-widespread flooding passing on area alone; condition 2 guards
against deep-but-tiny flooding passing on depth alone.

### What the original code did instead

`mean_val` was computed as the mean of pixels **already filtered to depth > 50 cm**:

```python
# BEFORE – mean only over pixels that already exceed the threshold
mean_val = masked_data[masked_data > depth_threshold].mean()
```

By definition this value is always ≥ 50 cm whenever any above-threshold pixels exist.
Condition 1 could therefore never fail — it was trivially satisfied the moment any
pixel exceeded the threshold. The depth check provided no gate at all, and scoring
collapsed to the area condition only.

On top of that, `mean_val` was commented out of the returned dictionary and
`calculate_hazard_score()` — already present in `gfdrr_helper.py` but never called
from the notebook — was never invoked. So even the broken `mean_val` was not used:
the score was driven entirely by the area threshold.

### Fix

`mean_val` is now computed as the mean of **all wet pixels (depth > 0)**, including
those below 50 cm. This is the only definition that allows the depth check to
distinguish a unit with predominantly shallow flooding from one with genuinely deep
inundation:

```python
# AFTER – mean over all wet pixels (depth > 0); shallow pixels pull the mean down
wet      = valid_values[valid_values > 0]
mean_val = float(np.mean(wet)) if len(wet) > 0 else 0.0

# Area fraction: pixels above threshold / ALL valid land pixels (wet + dry)
area_flooded      = np.sum(valid_values > depth_threshold)
frac_area_flooded = (area_flooded / len(valid_values)) * 100
```

`mean_val` is now returned from `calculate_think_hazard_score()` alongside
`frac_area_flooded`, and `calculate_hazard_score()` is called in the notebook after
all return periods are processed, enforcing the dual-threshold gate:

```python
all_res_df[f'Hazard_score_{lbl}'] = all_res_df.apply(
    lambda row: calculate_hazard_score(
        VALUE_THRESHOLD, AREA_THRESHOLD,
        *[(row[f'mean_val_{lbl}_{rp}yr'], row[f'frac_area_flooded_{lbl}_{rp}yr'])
          for rp in return_periods]
    ), axis=1
)
```

`VALUE_THRESHOLD` (50 cm) and `AREA_THRESHOLD` (3 %) are declared explicitly at the
top of the processing cell.

---

## Summary

| | Before | After |
|---|---|---|
| Nodata handling | Not masked; inflates denominator for coastal units | Read from metadata; excluded from numerator and denominator |
| Boundary pixels | `all_touched=False` | `all_touched=True` |
| Mean depth population | Pixels with depth > 50 cm only (gate always true) | All wet pixels (depth > 0); shallow pixels can pull mean below threshold |
| Mean depth returned | Computed but discarded | Returned as `mean_val` column |
| Scoring gate | Area threshold only | Both `mean_val >= 50 cm` AND `frac_area_flooded >= 3 %` required per RP |

The intermediate columns (`mean_val_*` and `frac_area_flooded_*`) are preserved in
the output CSV for transparency and easier debugging.
