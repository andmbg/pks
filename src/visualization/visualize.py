import colorsys
import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def _css_rainbow(N=5, s=0.5, v=0.5):
    """
    Helper that gives N samples from the rainbow.
    """
    HSV_tuples = [(x * 1.0 / N, s, v) for x in range(N)]
    hex_out = []
    for rgb in HSV_tuples:
        rgb = map(lambda x: int(x * 255), colorsys.hsv_to_rgb(*rgb))
        hex_out.append('#%02x%02x%02x' % tuple(rgb))
    return hex_out


def get_colormap(df: pd.DataFrame, keycolumn: str = "key") -> dict:
    """
    Derive from a crime stats dataset a color map {"key": "CSS color} that
    for each key distributes CSS colors among its children such that they
    are maximally distinguishable visually. Used by plotly.
    """
    df_colored = pd.DataFrame()

    for _, group in df.groupby("parent", dropna=False):
        colors = _css_rainbow(len(group))
        group["keycolor"] = colors
        df_colored = pd.concat([df_colored, group])

    colormap = {k: v for k, v in zip(
        df_colored[keycolumn].values, df_colored["keycolor"].values)}

    return colormap


def sunburst_location(input_json: str):
    """
    Take the clickdata output of a sunburst plot and identify which item
    is currently active.

    :param input_json: str, the json string representing clickData sent
        by the sunburst plot
    :return: str, label of the active item in the plot
    """
    if input_json is None or input_json == "null":
        return "root"

    # clickData = json.loads(input_json)
    clickData = input_json

    # identifying location:
    # variables from the clickData:
    clickData = clickData["points"][0]
    entry = clickData["entry"]
    label = clickData["label"]
    path_match = re.search(r"([0-9]{6})/$", clickData["currentPath"])

    path_leaf = path_match[1] if path_match is not None else "root"

    # use those vars for the decision logic:
    if entry == "":
        location = label

    else:
        if int(entry) < int(label):
            location = label

        if entry == label:
            if path_leaf is None:
                location = "root"

            else:
                location = path_leaf

    return location


def get_keypicker(df, colormap, hovertemplate):

    return (
        px.sunburst(df,
                    names='key',
                    # values=,
                    parents='parent',
                    color='key',
                    color_discrete_map=colormap,
                    hover_data=['label', 'key', 'count'],
                    maxdepth=2,
                    height=700,
                    # width=700
                    )
        .update_layout(
            margin=dict(t=15, r=15, b=15, l=15),
            paper_bgcolor="#eeeeee")
        .update_traces(hovertemplate=hovertemplate)
        .update_coloraxes(showscale=False)
    )


def get_existence_chart(df, keys, xaxis="year", yaxis="key", labels="label", newname="label_change"):
    """
    Returns an existence chart indicating a set of keys and their existence through the years.
    
    :param df: PKS dataframe
    :param keys: list of keys that have been selected for display
    :param xaxis: name of the years attribute
    :param yaxis: name of the key attribute
    :param labels: name of the label attribute, to be displayed within the plot
    :param newname: name of the boolean attribute that signals if the current entry corresponds
        to a change in the label of the same key, compared to the previous year
    """
    df = df.loc[df.key.isin(keys)]
    
    # only label the first year using each unique label, rest is "":
    df = df.assign(label = df.apply(lambda row: row["label"] if row["label_change"] else "", axis=1))

    # ensure right order of dots:
    df = df.sort_values(["key", "year"])
    
    fig = go.Figure()

    # add each key
    for i, grp in df.groupby(yaxis):
        fig.add_trace(
            go.Scatter(
                x=grp[xaxis],
                y=grp[yaxis],
                text=grp[labels],
                mode="lines+markers+text",
                textposition="top right",
                marker=dict(size=12),
            )
        )

    # add markers for each time a new label is used (black circles):
    new_markers = df.loc[df[newname]]

    fig.add_trace(
        go.Scatter(
            x=new_markers[xaxis],
            y=new_markers[yaxis],
            mode="markers",
            marker=dict(color="black",
                        line_width=2,
                        size=12,
                        symbol="circle-open"),
            # hover
        )
    )

    fig.update_traces(showlegend=False)
    fig.update_xaxes(type="category")
    
    # adapt height to number of keys displayed (space them evenly):
    fig.update_layout(margin=dict(t=10, b=5, r=10),
                      height=55*len(keys)+15, width=1500,
                      yaxis_range=[-0.5, len(keys)])
    
    return fig