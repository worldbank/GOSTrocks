import requests

import contextily as ctx
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors

from rasterio.plot import show
from matplotlib.patches import Patch
from shapely.geometry import box
from . import dataMisc as dMisc


# TODO: make this work
def fetch_wb_style(json_url="https://wbg-vis-design.vercel.app/colors.json"):
    """Fetches the World Bank style JSON file from the internet

    :param json_url: URL to the World Bank style JSON file, defaults to https://wbg-vis-design.vercel.app/colors.json
    :type json_url: str, optional
    :return: JSON file containing World Bank style
    :rtype: dict
    """
    resp = requests.get(json_url, verify=False)
    resp.raise_for_status()
    return resp.json()


def static_map_vector(
    v_data,
    map_column,
    colormap="Reds",
    edgecolor="darker",
    reverse_colormap=False,
    thresh=None,
    legend_loc="upper right",
    figsize=(10, 10),
    out_file="",
    set_title=True,
    add_basemap=True,
    add_wb_borders_lines=True,
    iso3="",
    bbox=None,
    **kwargs,
):
    """Simple plot of vector data

    Parameters
    ----------
    v_data : geopandas.GeoDataFrame
        Input geopandas dataset to map
    map_column : str
        Column label in v_data to map
    colormap : str, optional
        Name of colour ramp to send to matplotlib.pyplot, by default "Reds"
    edgecolor : str, optional
        Optional parameter to change edge colour of polygons.
        Optional values are match, darker, or a single provided colour, defaults to 'darker'
    reverse_colormap : bool, optional
        Optionally reverse the colormap colorramp, defaults to False
    thresh : list, optional
        List of thresholds to categorize values in v_data[map_column], defaults to equal interval 6 classes
    legend_loc : str, optional
        Where to place legend in plot, plugs into ax.legend, defaults to "upper right"
    figsize : tuple, optional
        Size of image, defaults to (10, 10)
    out_file : str, optional
        Path to create output image, defaults to '', which creates no output file
    set_title : bool, optional
        Whether to set title of plot, defaults to True
    add_basemap : bool, optional
        Whether to add a basemap from contextily, defaults to True
    add_wb_borders_lines : bool, optional
        Whether to add World Bank borders and lines from contextily, defaults to True
    iso3 : str, optional
        ISO3 country code to filter World Bank borders and lines, defaults to ""
    bbox : tuple, optional
        Bounding box to set map extent in crs of v_data, defaults to None, which is extent of v_data

    Returns
    -------
    matplotlib.pyplot
        Matplotlib object containing all maps
    """
    adm0_color = "dimgrey"
    linewidth = 0.5
    geom_type = v_data["geometry"].geom_type.iloc[0]

    # if v_data.crs.to_epsg() != 3857:
    #    v_data = v_data.to_crs(3857)
    # classify the data into categories if threshold is defined
    try:
        if thresh:
            v_data["tomap"] = pd.cut(
                v_data[map_column], thresh, labels=list(range(0, len(thresh) - 1))
            )
        else:
            v_data["tomap"] = pd.cut(v_data[map_column], 6, labels=[0, 1, 2, 3, 4, 5])
    except Exception:
        print("Error mapping specified column, defaulting to index")
        map_column = "fake_index"
        v_data[map_column] = list(v_data.index)
        v_data["tomap"] = pd.cut(v_data[map_column], 6, labels=[0, 1, 2, 3, 4, 5])
    fig, ax = plt.subplots(figsize=figsize)
    cm = plt.cm.get_cmap(colormap)
    if reverse_colormap:
        cm = cm.reversed()
    all_labels = []
    v_data["r_val"] = np.nan
    v_data["g_val"] = np.nan
    v_data["b_val"] = np.nan
    v_data["a_val"] = np.nan
    for label, mdata in v_data.groupby("tomap", observed=False):
        if mdata.shape[0] > 0:
            color = cm(label / v_data["tomap"].max())
            # Determine edge color
            if edgecolor == "match":
                c_edge = color
            elif edgecolor == "darker":
                c_edge = (color[0] * 0.7, color[1] * 0.7, color[2] * 0.7, color[3])
            else:
                c_edge = edgecolor
            # If adding the WB boundaries, we need the line width to be 0 so the international boundaries show through
            if add_wb_borders_lines:
                linewidth = 0
            if geom_type == "Point":
                mdata.plot(
                    color=color, ax=ax, label=label, edgecolor=c_edge, markersize=300
                )
            elif geom_type == "Polygon":
                mdata.plot(
                    color=color,
                    ax=ax,
                    label=label,
                    edgecolor=c_edge,
                    linewidth=linewidth,
                )
            else:  # should handle lines; not yet tested
                mdata.plot(
                    color=color,
                    ax=ax,
                    label=label,
                    edgecolor=c_edge,
                    linewidth=linewidth,
                )
            try:
                cLabel = f"{round(mdata[map_column].min())} - {round(mdata[map_column].max())}"
            except Exception:
                cLabel = "LABEL"
            cur_patch = mpatches.Patch(color=color, label=cLabel)
            all_labels.append(cur_patch)

            v_data.loc[mdata.index, "r_val"] = color[0]
            v_data.loc[mdata.index, "g_val"] = color[1]
            v_data.loc[mdata.index, "b_val"] = color[2]
            v_data.loc[mdata.index, "a_val"] = color[3]

    if add_basemap:
        try:
            ctx.add_basemap(ax, source=ctx.providers.Stamen.TonerBackground)
        except Exception:
            print("Error adding basemap")

    if add_wb_borders_lines:
        wb_gad_service = "https://services.arcgis.com/iQ1dY19aHwbSDYIF/arcgis/rest/services/World_Bank_Global_Administrative_Divisions/FeatureServer"
        if "adm0" in kwargs.keys():
            adm0 = kwargs["adm0"]
        else:
            adm0 = dMisc.gdf_esri_service(wb_gad_service, layer=1, verify_ssl=False)

        # Fetch the NDLSA polygons
        if "adm0_ndlsa" in kwargs.keys():
            adm0_ndlsa = kwargs["adm0_ndlsa"]
        else:
            adm0_ndlsa = dMisc.gdf_esri_service(
                wb_gad_service, layer=3, verify_ssl=False
            )

        if "adm0_lines" in kwargs.keys():
            adm0_lines = kwargs["adm0_lines"]
        else:
            adm0_lines = dMisc.gdf_esri_service(
                wb_gad_service, layer=4, verify_ssl=False
            )

        # remove the defined iso3 if provided
        if iso3 != "":
            adm0 = adm0.loc[adm0["ISO_A3"] != iso3]
        if adm0.crs != v_data.crs:
            adm0 = adm0.to_crs(v_data.crs)
        adm0.plot(ax=ax, facecolor=adm0_color, edgecolor=adm0_color, linewidth=0.5)

        # NDLSAs need to be plotted the same color as the adm0 polygons
        # EXCEPT those that intersect with v_data, where the values need to be halfway between
        # adm0 and the v_data fill colour
        adm0_rgba = mcolors.to_rgba(adm0_color)
        adm0_ndlsa["r_val"] = adm0_rgba[0]
        adm0_ndlsa["g_val"] = adm0_rgba[1]
        adm0_ndlsa["b_val"] = adm0_rgba[2]
        adm0_ndlsa["a_val"] = adm0_rgba[3]

        adm0_ndlsa_buffer = adm0_ndlsa.copy()
        adm0_ndlsa_buffer["geometry"] = adm0_ndlsa_buffer.geometry.buffer(0.01)
        adm0_ndlsa = adm0_ndlsa.to_crs(v_data.crs)

        if adm0_ndlsa_buffer.crs != v_data.crs:
            adm0_ndlsa = adm0_ndlsa.to_crs(v_data.crs)
            adm0_ndlsa_buffer = adm0_ndlsa_buffer.to_crs(v_data.crs)

        if v_data.crs != adm0_ndlsa.crs:
            v_data = v_data.to_crs(adm0_ndlsa.crs)
        ndlsa_bad_colours = gpd.sjoin(
            adm0_ndlsa_buffer, v_data, how="inner", predicate="intersects"
        )
        new_colours = ndlsa_bad_colours.groupby("FID").apply(
            lambda row: row.loc[
                :, ["r_val_right", "g_val_right", "b_val_right", "a_val_right"]
            ].mean()
        )
        new_colours.set_index("FID", inplace=True)

        adm0_ndlsa.set_index("FID", inplace=True)
        adm0_ndlsa.loc[new_colours.index, "r_val"] = new_colours["r_val_right"]
        adm0_ndlsa.loc[new_colours.index, "g_val"] = new_colours["g_val_right"]
        adm0_ndlsa.loc[new_colours.index, "b_val"] = new_colours["b_val_right"]
        adm0_ndlsa.loc[new_colours.index, "a_val"] = new_colours["a_val_right"]

        # add all the NDLSA polygons, coloured appropriately
        color_list = adm0_ndlsa.apply(
            lambda row: (row["r_val"], row["g_val"], row["b_val"], row["a_val"]), axis=1
        ).tolist()
        # For each item get the average between itself and the adm0 colour
        color_list = [
            (
                (row["r_val"] + adm0_rgba[0]) / 2,
                (row["g_val"] + adm0_rgba[1]) / 2,
                (row["b_val"] + adm0_rgba[2]) / 2,
                (row["a_val"] + adm0_rgba[3]) / 2,
            )
            for idx, row in adm0_ndlsa.iterrows()
        ]
        # return([color_list, ndlsa_bad_colours, adm0_ndlsa])

        adm0_ndlsa.plot(ax=ax, color=color_list, edgecolor=color_list, linewidth=0.5)

        if adm0_lines.crs != v_data.crs:
            adm0_lines = adm0_lines.to_crs(v_data.crs)

        for label, mdata in adm0_lines.groupby("Style"):
            if label == "Solid":
                mdata.plot(ax=ax, color="black", linewidth=1)
            elif label == "Dashed":
                mdata.plot(ax=ax, color="black", linewidth=1, linestyle=(3, (4, 4)))
            elif label == "Dotted":
                mdata.plot(ax=ax, color="black", linewidth=1, linestyle=(1, (1, 4)))
            elif label == "Tightly Dashed":
                mdata.plot(ax=ax, color="black", linewidth=1, linestyle=(3, (3, 3)))

        # Set extent to v_data
        ax.set_xlim(v_data.total_bounds[0], v_data.total_bounds[2])
        ax.set_ylim(v_data.total_bounds[1], v_data.total_bounds[3])

    bounds = v_data.total_bounds
    if bbox is not None:
        ax.set_xlim(bbox[0], bbox[2])
        ax.set_ylim(bbox[1], bbox[3])
        bounds = bbox

    ax.legend(handles=all_labels, loc=legend_loc)
    ocean = gpd.GeoDataFrame(geometry=[box(*bounds)], crs=v_data.crs)
    ocean.plot(ax=ax, color="midnightblue", zorder=0)
    # ax = ax.set_axis_off()

    if set_title:
        plt.title(map_column)

    if out_file != "":
        plt.savefig(out_file, dpi=300, bbox_inches="tight")

    return [plt, fig, ax]


def static_map_raster(
    r_data,
    colormap="magma",
    reverse_colormap=False,
    thresh=None,
    legend_loc="upper right",
    figsize=(10, 10),
    out_file="",
):
    """Simple plot of raster data

    Parameters
    ----------
    r_data : rasterio.RasterDatasetReader
        Raster data to map, plots the first band in the raster dataset
    colormap : str, optional
        Name of colour ramp to send to matplotlib.pyplot, defaults to "magma"
    reverse_colormap : bool, optional
        Optionally reverse the colormap color ramp, defaults to False
    thresh : list of int, optional
        List of thresholds to categorize values in v_data[map_column], defaults to equal interval 6 classes
    legend_loc : str, optional
        Where to place legend in plot, plugs into ax.legend, defaults to "upper right"
    figsize : tuple, optional
        Size of image, defaults to (10, 10)
    out_file : str, optional
        Path to create output image, defaults to '', which creates no output file
    Returns
    -------
    matplotlib.pyplot
        Matplotlib object containing all maps
    """

    map_data = r_data.read()[0, :, :]
    map_data = np.nan_to_num(map_data, neginf=0, posinf=2000)
    cm = plt.cm.get_cmap(colormap)
    if reverse_colormap:
        cm = cm.reversed()

    if thresh:
        map_data = np.digitize(map_data, thresh)
    fig, ax = plt.subplots(figsize=figsize)
    show(map_data, ax=ax, cmap=cm, transform=r_data.transform)

    legend_labels = [[cm(0), "Low"], [cm(0.5), "Medium"], [cm(1), "High"]]
    if thresh:
        legend_labels = [[cm(x / max(thresh)), str(x)] for x in thresh]

    patches = [Patch(color=x[0], label=x[1]) for x in legend_labels]
    if legend_loc:
        plt.legend(handles=patches, loc=legend_loc, facecolor="white")
    if out_file != "":
        plt.savefig(out_file, dpi=300, bbox_inches="tight")
    return [plt, fig, ax]
