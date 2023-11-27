from typing import Union, Iterable
import functools

import pandas as pd
import jscatter
import ipywidgets
import traitlets
import matplotlib.colors as colors


def partition_by_sample(df, samples) -> list[pd.DataFrame]:
    eigs = []
    for sample in samples:
        eigs_df = df[df["sample"] == sample].reset_index().dropna()
        eigs.append(eigs_df)
    # create shared index for all dataframes
    index = functools.reduce(pd.Index.intersection, [df.index for df in eigs])
    return [df.loc[index] for df in eigs]

def extract_color_series(
    track_data: pd.DataFrame,
    field: str,
    color_kwargs: Union[dict, None],
):
    data = track_data[field]
    if color_kwargs is None:
        color_kwargs = {}
        if data.dtype.name in ("object", "category"):
            data = data.astype("category") # ensure categorical
            color_kwargs["map"] = dict(zip(data.cat.categories, jscatter.glasbey_dark))
        else:
            color_kwargs["norm"] = colors.Normalize(vmin=data.min(), vmax=data.max())
            color_kwargs["map"] = "viridis_r"
        return data, color_kwargs
    if color_kwargs and "relabel" in color_kwargs:
        data = data.map(color_kwargs["relabel"])
                    
    return data, color_kwargs

def init_dropdowns(
    xy_options,
    color_options,
    color_kwargs,
    scatters: Iterable[jscatter.Scatter]
):
    x = xy_options[0]
    x_dropdown = ipywidgets.Dropdown(options=xy_options, value=x, description="x:")

    def on_change_x(change):
        for scatter in scatters:
            scatter.x(change.new)

    y = xy_options[1]
    y_dropdown = ipywidgets.Dropdown(options=xy_options, value=y, description="y:")

    def on_change_y(change):
        for scatter in scatters:
            scatter.y(change.new)

    color = color_options[0]
    c_dropdown = ipywidgets.Dropdown(
        options=color_options, value=color, description="color:"
    )

    def on_change_color(change):
        field = change["new"]
        for scatter in scatters:
            track_data = scatter._data
            data, kwargs = extract_color_series(track_data, field, color_kwargs.get(field))
            scatter._data["_color"] = data
            scatter.color(by="_color", **kwargs)

    x_dropdown.observe(on_change_x, names=["value"])
    y_dropdown.observe(on_change_y, names=["value"])
    c_dropdown.observe(on_change_color, names=["value"])
    on_change_color(dict(new=color))

    return x_dropdown, y_dropdown, c_dropdown
    

def init_scatters(
    samples: Iterable[tuple[str, pd.DataFrame]],
    xy_options: list[str],
    color_options: list[str],
    color_kwargs: dict,
):
    jscatter.compose
    scatters = [jscatter.Scatter(x=xy_options[0], y=xy_options[1], data=data, opacity=0.5) for _, data in samples]

    synced = jscatter.compose([(scatter, name) for scatter, (name, _) in zip(scatters, samples)], sync_view=True, sync_selection=True, sync_hover=True)
    dropdowns = init_dropdowns(xy_options=xy_options, color_options=color_options, scatters=scatters, color_kwargs=color_kwargs)
    
    component = ipywidgets.VBox([synced, ipywidgets.HBox(dropdowns)])

    def extract_coords(ind):
        return scatters[0]._data.iloc[ind][["chrom", "start", "end"]]
    
    # we expose a single "selection" for this component, which the viewer can subscribe to
    component.add_traits(coords=traitlets.Any(extract_coords([])))
    
    ipywidgets.dlink(
        source=(scatters[0].widget, "selection"),
        target=(component, "coords"),
        transform=extract_coords,
    )
    
    return component
