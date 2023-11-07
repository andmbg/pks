import colorsys
import re

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _css_rainbow(N=5, s=1, v=.75):
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
    Derive from a crime stats dataset a color map {"key": "CSS color"} that
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
            margin=dict(t=15, r=15, b=15, l=15))
        .update_traces(hovertemplate=hovertemplate)
        .update_coloraxes(showscale=False)
    )


def get_existence_chart(df, keys, colormap, xaxis="year", yaxis="key", labels="label", newname="label_change"):
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

    df["firstlabel"] = df[labels]

    # delete label were equal to previous:
    df = df.assign(label=df.apply(
        lambda row: row[labels] if row[newname] else "Eintrag vorhanden", axis=1))

    df2 = pd.DataFrame()

    for i, grp in df.groupby([yaxis, "state"]):
        this_group = grp.sort_values(xaxis)
        this_group["firstlabel"].iloc[1:] = ""
        df2 = pd.concat([df2, this_group])
    
    df = df2.copy()
    
    # categorical y-axis:
    df.key = df.key.astype("str")
    
    # ensure right order of dots:
    df = df.sort_values(["key", "year"])

    fig = go.Figure()

    # add each key's line and points:
    for i, grp in df.groupby(yaxis):
        fig.add_trace(
            go.Scatter(
                x=grp[xaxis],
                y=grp[yaxis],
                text=grp["firstlabel"],
                mode="lines+markers+text",
                marker=dict(color=colormap[i], size=12),
                line_width=4,
                textposition="top right",
                customdata=np.stack((grp[labels], grp["count"]), axis=-1),
                hovertemplate="<b>%{y}</b> (%{x}):<br><br>%{customdata[0]},<br>%{customdata[1]} Fälle<extra></extra>"
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
                        size=18,
                        symbol="circle-open"),
            hoverinfo="skip"
        )
    )

    fig.update_traces(showlegend=False)
    fig.update_xaxes(type="category")

    # adapt height to number of keys displayed (space them evenly):
    fig.update_layout(margin=dict(t=10, b=5, r=10),
                      height=55*len(keys)+35,
                      yaxis_range=[-0.5, len(keys)],
                      plot_bgcolor="rgba(0,0,0,0)",
                      font_size=15)

    return fig


def get_timeseries(df):
    """
    :param df: Dataframe containing 1-n keys (only the data to be displayed - filter beforehand!)
    """
    colormap = {i: grp.loc[grp.index[0], "color"] for i, grp in df.groupby("key")}

    statemap = {
    "Brandenburg": "BB",
    "Berlin": "BE",
    "Baden-Württemberg": "BW",
    "Bayern": "BY",
    "Schleswig-Hostein": "SH",
    "Hamburg": "HH",
    "Bremen": "HB",
    "Mecklenburg-Vorpommern": "MV",
    "Niedersachsen": "NI",
    "Sachsen-Anhalt": "ST",
    "Nordrhein-Westfalen": "NW", 
    "Hessen": "HE",
    "Saarland": "SL",
    "Sachsen": "SN",
    "Thüringen": "TH",
    "Rheinland-Pfalz": "RP",
    "Bund": "D"
    }

    df = df.copy()
    
    df.state = df.state.apply(lambda x: statemap[x])
    df["keystate"] = df.key + "<br>" + df.state
    timerange = [min(df.year), max(df.year)]
    years = list(range(timerange[0], timerange[1]+1))
    # max bar height:
    counts1 = df.loc[df.variable.eq("count"), "value"].values
    counts2 = df.loc[df.variable.eq("unsolved"), "value"].values
    maxheight = pd.DataFrame({"a": counts1, "b": counts2}).apply(sum, axis=1).max()

    fig = make_subplots(cols=len(years), shared_yaxes=True,
                        horizontal_spacing=.01,
                        subplot_titles=years)

    # cross off every key from the TODO list the first time it gets plotted
    # (this may be later than the first year in consideration):
    legend_todo = set(df.keystate.unique())
    
    # iterate through years:
    for i, year in enumerate(years):
        year_grp = df.loc[df.year.eq(year)]
        
        
        # iterate through keys (within year):
        for j, key_grp in year_grp.groupby("keystate"):
            key_without_state = re.findall(pattern=r"^(......)", string=j)[0]
            
            committed = key_grp.loc[key_grp.variable.eq("count")]
            unsolved = key_grp.loc[key_grp.variable.eq("unsolved")]
            
            fig.add_trace(
                go.Bar(x=[j],
                    y=committed.value,
                    marker=dict(color=colormap[key_without_state]),
                    showlegend=( j in legend_todo ),
                    name=committed.label.iloc[0],
                    customdata=np.stack((committed["key"], committed["year"], committed["label"], unsolved["value"]), axis=-1),
                    hovertemplate="<b>%{customdata[2]}</b><br>(Schlüssel %{customdata[0]})<br><br>%{customdata[1]}:<br>%{y} Fälle,<br>%{customdata[3]} unaufgeklärt<extra></extra>"
                    ),
                col=i+1, row=1)
            
            # unsolved cases in grey:
            fig.add_trace(
                go.Bar(x=[j],
                    y=unsolved.value,
                    marker=dict(color="grey"),
                    showlegend=False,
                    hoverinfo="skip"
                    ),
                col=i+1, row=1)

            # cross off the key from the legend-TODO:
            legend_todo = legend_todo.difference({j})
            
    fig.update_layout(bargap=0.001,
                    barmode="stack",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=25),
                    legend=dict(yanchor="top",
                                xanchor="left",
                                y=.99,
                                x=.01),
                    height=900,
                    font_size=18
                    )
    
    fig.update_yaxes(gridcolor="rgba(.5,.5,.5,.5)",
                     range=[0, maxheight*1.2])

    # fig.update_traces(showlegend=False)
    
    return fig