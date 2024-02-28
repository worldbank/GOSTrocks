import os
import logging

import rasterio  # v1.0.21 (latest v1.2.10)

import pandas as pd  # v1.0.3 (latest v1.4.1)
import geopandas as gpd  # v0.6.3 (latest v0.10.2)


from pyproj.crs.crs import CRS

try:
    pass
except:
    print("METADATA Library: Could not import arcgis libraries")

vector_file_types = [".shp", ".kml", ".geojson"]
raster_file_types = [".TIF", ".tif", ".tiff", ".geotiff", ".geotif"]


### TODO:
# 1. Add searching through ESRI geodatabases
# 2. Add support to include tables (xlsx, csv)


class metadata_gost:
    """Create standardized metadata for folders of geospatial data"""

    def __init__(self, input_dir, output_dir, type="Folder"):
        """Create standardized metadata for folders of geospatial data

        :param input_dir: Folder to search for geospatial layers
        :type input_dir: str
        :param output_dir: Where to create output metadata files
        :type output_dir: str
        :param type: What we are searching, defaults to "Folder"
        :type type: str, optional
        """
        self.input_dir = input_dir
        if not os.path.exists(input_dir):
            raise (ValueError("Input directory does not exist"))
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def get_layers(self):
        """Iterate through self.input_dir and get list of vector and raster data"""
        vector_files = []
        raster_files = []

        for root, dirs, files in os.walk(self.input_dir):
            for f in files:
                file_type = os.path.splitext(f)[-1]
                if file_type in vector_file_types:
                    vector_files.append(os.path.join(root, f))
                if file_type in raster_file_types:
                    raster_files.append(os.path.join(root, f))
        self.vector_files = vector_files
        self.raster_files = raster_files
        return {"vector": vector_files, "raster": raster_files}

    def write_metadata(
        self,
        out_file,
        layer_metadata=None,
        field_metadata=None,
        dataset_id="",
        dataset_title="",
        country="",
        abstract="",
        purpose="",
        creation_date="",
        release_date="",
        owner="",
        email="",
    ):
        # create first sheet of baseline info
        base_info = {
            "dataset ID": dataset_id,
            "dataset title": dataset_title,
            "country": country,
            "abstract": abstract,
            "purpose": purpose,
            "creation date": creation_date,
            "release date": release_date,
            "owner name": owner,
            "owner email": email,
        }
        base_pd = pd.DataFrame([base_info]).transpose()
        if layer_metadata is None:
            layer_metadata = self.metaPD
        if field_metadata is None:
            field_metadata = self.fieldsPD

        with pd.ExcelWriter(
            out_file, engine="openpyxl", mode="w", if_sheet_exists="replace"
        ) as writer:
            base_pd.to_excel(writer, "dataset info", encoding="utf8")
            layer_metadata.to_excel(writer, "layer_summaries", encoding="utf8")
            field_metadata.to_excel(writer, "field_summaries", encoding="utf8")

    def generate_metadata(self, vector_files=None, raster_files=None):
        """Generate metadata for vector and raster files

        Args:
            vector_files [optional, list] - list of paths to vector_files, if none, defaults to list generated through get_list_of_layers
            raster_files [optional, list] - list of paths to raster_files, if none, defaults to list generated through get_list_of_layers

        Returns:
            [geopandas DataFrame]

        Details:
            Standard Fields
                layer_name - name of layer (filename without extension)
                data_type  - vector, raster, or table
                crs_name
                crs_code
                num_dimensions - Number of fields in dataset, or bands in raster dataset
                min_lon
                max_lon
                min_lat
                max_lat
            Vector Fields:
                vector_shape_type
                vector_object_count
                table_num_rows
            Raster Fields:
                raster_width
                raster_height

            Manual Input
                layer_label
                description
                source_name
                source_url
                data_process_summary
        """
        if vector_files is None:
            vector_files = self.vector_files
        if raster_files is None:
            raster_files = self.raster_files

        metadata = []
        field_defs = []
        for vector_file in vector_files:
            try:
                cur_meta = vector_file_metadata(vector_file, in_folder=self.input_dir)
                metadata.append(cur_meta.get_metadata())
                field_defs.append(cur_meta.get_field_summaries())
            except:
                logging.error(f"Cannot log {vector_file}")

        for raster_file in raster_files:
            try:
                cur_meta = raster_file_metadata(raster_file, in_folder=self.input_dir)
                metadata.append(cur_meta.get_metadata())
            except:
                logging.error(f"Cannot log {raster_file}")

        metaPD = pd.DataFrame(metadata)
        metaPD["layer_label"] = ""
        metaPD["description"] = ""
        metaPD["source_name"] = ""
        metaPD["source_url"] = ""
        metaPD["data_process_summary"] = ""
        self.metaPD = metaPD
        try:
            del final
        except:
            pass
        for cur_fields in field_defs:
            cur_pd = pd.DataFrame(cur_fields)
            try:
                final = final.append(cur_pd)
            except:
                final = cur_pd
        try:
            fieldsPD = final.reset_index()
            self.fieldsPD = fieldsPD
        except:
            fieldsPD = None
            self.fieldsPD = None
        self.metaPD.sort_values(["folder", "layer_name"], inplace=True)
        self.fieldsPD.sort_values(["layer_name", "field_name"], inplace=True)

        return {"metadata": metaPD, "fields": fieldsPD}


class raster_file_metadata:
    def __init__(self, path, in_folder=""):
        self.path = path
        self.layer_name = os.path.splitext((os.path.basename(path)))[0]
        if in_folder == "":
            self.dir_name = os.path.dirname(path)
        else:
            self.dir_name = os.path.dirname(path).replace(in_folder, "")
        self.data_type = "Raster"

        curR = rasterio.open(path)

        cur_crs = CRS.from_wkt(curR.crs.wkt)
        self.crs_name = cur_crs.name
        self.crs_code = curR.crs.to_epsg()

        rShape = curR.shape
        if len(rShape) == 2:
            self.num_dimensions = 1
            self.raster_width = curR.shape[0]
            self.raster_height = curR.shape[1]
        else:
            self.num_dimensions = curR.shape[0]
            self.raster_width = curR.shape[1]
            self.raster_height = curR.shape[2]

        self.raster_res = curR.res[0]
        b = curR.bounds
        self.min_lon = b[0]
        self.min_lat = b[1]
        self.max_lon = b[2]
        self.max_lat = b[3]

    def get_metadata(self):
        return {
            "layer_name": self.layer_name,
            "folder": self.dir_name,
            "data_type": self.data_type,
            "crs_name": self.crs_name,
            "crs_code": self.crs_code,
            "num_dimensions": self.num_dimensions,
            "min_lon": self.min_lon,
            "max_lon": self.max_lon,
            "min_lat": self.min_lat,
            "max_lat": self.max_lat,
            "raster_width": self.raster_width,
            "raster_height": self.raster_height,
            "raster_res": self.raster_res,
        }


class vector_file_metadata:
    def __init__(self, path, in_folder=""):
        self.path = path
        self.in_folder = ""
        self.layer_name = os.path.splitext((os.path.basename(path)))[0]
        if in_folder == "":
            self.dir_name = os.path.dirname(path)
        else:
            self.dir_name = os.path.dirname(path).replace(in_folder, "")
        self.data_type = "Vector"

        curD = gpd.read_file(path)
        self.curD = curD
        self.crs_name = curD.crs.name
        self.crs_code = curD.crs.to_epsg()
        self.num_dimensions = curD.shape[1]
        self.vector_object_count = curD.shape[0]

        b = curD.total_bounds
        self.min_lon = b[0]
        self.min_lat = b[1]
        self.max_lon = b[2]
        self.max_lat = b[3]
        self.vector_shape_type = curD.geom_type.value_counts().index[0]

    def get_field_summaries(self):
        """Generate field metadata
        layer_name
        field_name
        field_label
        definition
        domain
        type
        num_unique_values
        first_10_unique_values
        """
        cur_field_defs = []
        for idx, col in self.curD.iteritems():
            cur_defs = {
                "layer_name": self.layer_name,
                "field_name": idx,
                "type": col.dtype,
                "field_label": "",
                "definition": "",
                "domain": "",
                "num_unique_values": len(col.unique()),
                "first_10_unique_values": col.values[:10],
            }
            cur_field_defs.append(cur_defs)
        return cur_field_defs

    def get_metadata(self):
        return {
            "layer_name": self.layer_name,
            "data_type": self.data_type,
            "crs_name": self.crs_name,
            "crs_code": self.crs_code,
            "num_dimensions": self.num_dimensions,
            "min_lon": self.min_lon,
            "max_lon": self.max_lon,
            "min_lat": self.min_lat,
            "max_lat": self.max_lat,
            "vector_shape_type": self.vector_shape_type,
            "vector_object_count": self.vector_object_count,
        }
