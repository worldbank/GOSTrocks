# ghslMisc

## `combine_ghsl_annual(ghsl_files, built_thresh=0.1, ghsl_files_labels=[], out_file='')`

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
