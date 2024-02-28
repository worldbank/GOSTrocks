import contextily as ctx
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import matplotlib.patches as mpatches

from matplotlib.patches import Patch


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
):
    """Simple plot of vector data; most arguments expect

    :param v_data: input geopandas dataset to map
    :type v_data: gpd.GeoDataFrame
    :param map_column: Column label in v_data to map
    :type map_column: str
    :param colormap: Name of colour ramp to send to matplotlib.pyplot, defaults to "Reds"
    :type colormap: str, optional
    :param edgecolor: Optional parameter to change edge colour of polygons.
                      Optional values are match, darker, or a single provided colour, defaults to 'darker'
    :type edgecolor: str, optional
    :param reverse_colormap: Optionally reverse the colormap colorramp, defaults to False
    :type reverse_colormap: bool, optional
    :param thresh: List of thresholds to categorize values in v_data[map_column], defaults to equal interval 6 classes
    :type thresh: List of int, optional
    :param legend_loc: Where to place legend in plot, plugs into ax.legend, defaults to "upper right"
    :type legend_loc: str, optional
    :param figsize: Size of image, defaults to (10,10)
    :type figsize: tuple, optional
    :param out_file: path to create output image, defaults to '', which creates no output file
    :type out_file: str, optional
    :return: matplotlib object containing all maps
    :rtype: matplotlib.pyplot
    """
    geom_type = v_data["geometry"].geom_type.iloc[0]

    if v_data.crs.to_epsg() != 3857:
        v_data = v_data.to_crs(3857)
    # classify the data into categories if threshold is defined
    try:
        if thresh:
            v_data["tomap"] = pd.cut(
                v_data[map_column], thresh, labels=list(range(0, len(thresh) - 1))
            )
        else:
            v_data["tomap"] = pd.cut(v_data[map_column], 6, labels=[0, 1, 2, 3, 4, 5])
    except:
        print("Error mapping specified column, defaulting to index")
        map_column = "fake_index"
        v_data[map_column] = list(v_data.index)
        v_data["tomap"] = pd.cut(v_data[map_column], 6, labels=[0, 1, 2, 3, 4, 5])
    fig, ax = plt.subplots(figsize=figsize)
    cm = plt.cm.get_cmap(colormap)
    if reverse_colormap:
        cm = cm.reversed()
    all_labels = []
    for label, mdata in v_data.groupby("tomap"):
        if mdata.shape[0] > 0:
            color = cm(label / v_data["tomap"].max())
            # Determine edge color
            if edgecolor == "match":
                c_edge = color
            elif edgecolor == "darker":
                c_edge = (color[0] * 0.7, color[1] * 0.7, color[2] * 0.7, color[3])
            else:
                c_edge = edgecolor

            if geom_type == "Point":
                mdata.plot(
                    color=color, ax=ax, label=label, edgecolor=c_edge, markersize=300
                )
            elif geom_type == "Polygon":
                mdata.plot(color=color, ax=ax, label=label, edgecolor=c_edge)
            else:  # should handle lines; not yet tested
                mdata.plot(color=color, ax=ax, label=label, edgecolor=c_edge)
            try:
                cLabel = f"{round(mdata[map_column].min())} - {round(mdata[map_column].max())}"
            except:
                cLabel = "LABEL"
            cur_patch = mpatches.Patch(color=color, label=cLabel)
            all_labels.append(cur_patch)
    try:
        ctx.add_basemap(
            ax, source=ctx.providers.Stamen.TonerBackground
        )  # zorder=-10, 'EPSG:4326'
    except:
        print("Error adding basemap")
    ax.legend(handles=all_labels, loc=legend_loc)
    ax = ax.set_axis_off()

    if set_title:
        plt.title(map_column)

    if out_file != "":
        plt.savefig(out_file, dpi=300, bbox_inches="tight")

    return plt


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

    :param r_data: Raster data to map, plots the first bad in the raster dataset
    :type r_data: rasterio.RasterDatasetReader
    :param colormap: Name of colour ramp to send to matplotlib.pyplot, defaults to "Reds"
    :type colormap: str, optional
    :param reverse_colormap: Optionally reverse the colormap colorramp, defaults to False
    :type reverse_colormap: bool, optional
    :param thresh: List of thresholds to categorize values in v_data[map_column], defaults to equal interval 6 classes
    :type thresh: List of int, optional
    :param legend_loc: Where to place legend in plot, plugs into ax.legend, defaults to "upper right"
    :type legend_loc: str, optional
    :param figsize: Size of image, defaults to (10,10)
    :type figsize: tuple, optional
    :param vector_mask: _description_, defaults to None
    :type vector_mask: _type_, optional
    :param out_file: path to create output image, defaults to '', which creates no output file
    :type out_file: str, optional
    :return: matplotlib object containing all maps
    :rtype: matplotlib.pyplot
    """

    map_data = r_data.read()[0, :, :]
    map_data = np.nan_to_num(map_data, neginf=0, posinf=2000)
    cm = plt.cm.get_cmap(colormap)
    if reverse_colormap:
        cm = cm.reversed()

    if thresh:
        map_data = np.digitize(map_data, thresh)
    fig, ax = plt.subplots(figsize=figsize)
    chm_plot = ax.imshow(map_data, cmap=cm)

    legend_labels = [[cm(0), "Low"], [cm(0.5), "Medium"], [cm(1), "High"]]
    if thresh:
        legend_labels = [[cm(x / max(thresh)), str(x)] for x in thresh]

    patches = [Patch(color=x[0], label=x[1]) for x in legend_labels]
    ax.legend(handles=patches, loc=legend_loc, facecolor="white")
    ax.set_axis_off()
    if out_file != "":
        plt.savefig(out_file, dpi=300, bbox_inches="tight")
    return plt
