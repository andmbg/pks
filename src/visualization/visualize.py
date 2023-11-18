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


def _lt(x: str, y: str) -> bool:
    """
    Helper: compare keys even when they contain asterisks.
    * couns as "less than zero".
    """
    # einfach:
    try:
        if int(x) < int(y):
            return True

    # Handarbeit:
    except ValueError:
        testing_range = min(len(x), len(y))

        for i in range(testing_range):
            if x[i] == y[i]:
                continue

            if x[i] in "0123456789" and y[i] == "*":
                return False

            if x[i] == "*" and y[i] in "0123456789":
                return True

        return False


def _desaturate_brighten(hex_color, sat, bri):
    """
    :param hex_color: str of form "#000000"
    :param sat: target absolute saturation (0..1)
    :param bri: brightening: 0=no change; 1=white
    """
    # Convert hex to RGB
    rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))

    # Convert RGB to HLS
    h, l, s = colorsys.rgb_to_hls(
        rgb_color[0] / 255.0, rgb_color[1] / 255.0, rgb_color[2] / 255.0)

    # Desaturate the color
    s *= sat

    # brighten
    bdiff = 1 - l
    l = l + bri*bdiff

    # Convert back to RGB
    r, g, b = colorsys.hls_to_rgb(h, l, s)

    # Convert RGB to hex
    desaturated_hex_color = "#{:02x}{:02x}{:02x}".format(
        int(r * 255), int(g * 255), int(b * 255))

    return desaturated_hex_color


def make_df_colormap(df: pd.DataFrame, keycolumn: str = "key") -> dict:
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


def color_map_from_color_column(df):
    return {k: grp.color.iloc[0] for k, grp in df.groupby("key")}


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

    clickData = input_json

    # identifying location:
    # variables from the clickData:
    clickData = clickData["points"][0]
    entry = clickData["entry"]
    label = clickData["label"]
    path_match = re.search(r"([0-9*]{6})/$", clickData["currentPath"])

    path_leaf = path_match[1] if path_match is not None else "root"

    # use those vars for the decision logic:
    if entry == "":
        location = label

    else:
        if entry == label:
            if path_leaf is None:
                location = "root"

            else:
                location = path_leaf

        elif _lt(entry, label):
            location = label

    return location


def get_sunburst(df, colormap):

    # count children of each key for information in the plot:
    key_children_dict = df.groupby("parent").agg(len).key.to_dict()
    df["nchildren"] = df.key.apply(lambda k: key_children_dict.get(k, 0))

    hovertemplate = """
                <b>%{customdata[1]}</b><br><br>
                %{customdata[0]}<br>
                (%{customdata[2]} Unterschlüssel)
                <extra></extra>"""
    hovertemplate = re.sub(r"([ ]{2,})|(\n)", "", hovertemplate)

    fig = px.sunburst(
        df,
        names='key',
        parents='parent',
        color='key',
        color_discrete_map=colormap,
        hover_data=['label', 'key', 'nchildren'],
        maxdepth=2,
    ).update_layout(margin=dict(t=15, r=15, b=15, l=15),
                    plot_bgcolor="#ffffff",
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=700
                    ).update_traces(hovertemplate=hovertemplate,
                                    leaf_opacity=1,
                                    ).update_coloraxes(showscale=False)

    return fig


def get_presence_chart(df, keys, colormap, xaxis="year", yaxis="key", label_annot="shortlabel", label_hover="label", newname="label_change"):
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
    df = df.loc[df.key.isin(keys)].copy()

    df["firstlabel"] = df[label_annot]

    # delete label were equal to previous:
    # df = df.assign(label=df.apply(
    #     lambda row: row[label_annot] if row[newname] else "Eintrag vorhanden", axis=1))

    df2 = pd.DataFrame()

    for i, grp in df.groupby([yaxis, "state"]):
        this_group = grp.sort_values(xaxis)

        firstlabel_list = this_group["firstlabel"].values
        firstlabel_list[1:] = ""
        this_group["firstlabel"] = firstlabel_list

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
                customdata=np.stack((grp[label_hover], grp["count"]), axis=-1),
                hovertemplate="<b>%{customdata[0]}</b> (%{x}):<br><br>%{customdata[1]:,i} Fälle<extra></extra>"
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
    # fig.update_yaxes(autorange="reversed")

    # adapt height to number of keys displayed (space them evenly):
    r = len(keys)  # "rows"
    fig.update_layout(margin=dict(t=41 + 45 + 45, b=44 - 20),
                      height=155 + 45 * r + 10,  # 45 per table row, 155 framing, 10 nudging
                      yaxis_range=[r-.5, -.5],
                      xaxis_showgrid=False,
                      yaxis_showgrid=False,
                      plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)",
                      font_size=15)

    return fig


def get_ts_clearance(df):
    """
    :param df: Dataframe containing 1..n keys (only the data to be displayed - filter beforehand!)
    """
    # colormap = {i: grp.loc[grp.index[0], "color"] for i, grp in df.groupby("key")}
    colormap = color_map_from_color_column(df)

    years = list(range(min(df.year), max(df.year)+1))

    # max bar height:
    # counts1 = df.loc[df.variable.eq("count"), "value"].values
    # counts2 = df.loc[df.variable.eq("unsolved"), "value"].values
    # maxheight = pd.DataFrame({"a": counts1, "b": counts2}).apply(sum, axis=1).max()
    maxheight = df["count"].max() * 1.2

    fig = make_subplots(cols=len(years), shared_yaxes=True,
                        horizontal_spacing=.01,
                        subplot_titles=years)

    # cross off every key from the TODO list the first time it gets plotted
    # (this may be later than the first year in consideration):
    legend_todo = set(df.key.unique())

    # iterate through years:
    for i, year in enumerate(years):
        year_grp = df.loc[df.year.eq(year)]

        # iterate through keys (within year):
        for j, key_grp in year_grp.groupby("key"):

            committed = key_grp.loc[key_grp.variable.eq("clearance")]
            unsolved = key_grp.loc[key_grp.variable.eq("unsolved")]

            customdata = np.stack((
                committed["key"],
                committed["year"],
                committed["shortlabel"],
                unsolved["value"],
                committed["clearance_rate"],
                committed["count"],
            ), axis=-1)

            hovertemplate = "<br>".join([
                "%{customdata[2]}",
                "(Schlüssel %{customdata[0]})",
                "Fälle im Jahr %{customdata[1]}: %{customdata[5]}",
                "Unaufgeklärt: %{customdata[3]}",
                "Aufklärungsrate: %{customdata[4]} %<extra></extra>"
            ])

            fig.add_trace(
                go.Bar(x=[j],
                       y=committed["value"],
                       marker=dict(color=colormap[j]),
                       showlegend=(j in legend_todo),
                       legendgroup=j,
                       name=committed.shortlabel.iloc[0],
                       customdata=customdata,
                       hovertemplate=hovertemplate,
                       ),
                col=i+1, row=1)

            # unsolved cases in grey:
            fig.add_trace(
                go.Bar(x=[j],
                       y=unsolved.value,
                       marker=dict(color=_desaturate_brighten(
                           colormap[j], 0.25, .5)),
                       showlegend=False,
                       legendgroup=j,
                       customdata=customdata,
                       hovertemplate=hovertemplate,
                       ),
                col=i+1, row=1)

            # cross off the key from the legend-TODO:
            legend_todo = legend_todo.difference({j})

    fig.update_layout(bargap=0.001,
                      barmode="stack",
                      plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)",
                      margin=dict(t=25, r=20),
                      legend=dict(yanchor="top",
                                  xanchor="left",
                                  y=.99,
                                  x=.01,
                                  bgcolor="rgba(255,255,255,.5)"),
                      height=600,
                      font_size=18
                      )

    fig.update_yaxes(gridcolor="rgba(.5,.5,.5,.5)",
                     range=[0, maxheight*1.2])

    # fig.update_traces(showlegend=False)

    return fig


def empty_timeseries(years):
    """
    What gets displayed if user presses the reset btn.
    """
    years = years.astype(str)

    fig = make_subplots(cols=len(years), shared_yaxes=True,
                        horizontal_spacing=.01,
                        subplot_titles=years)

    for i, year in enumerate(years):
        fig.add_trace(
            go.Bar(x=[0],
                   y=[0]),
            col=i+1, row=1)

    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)",
                      margin=dict(t=25, r=20),
                      height=900,
                      font_size=18,
                      showlegend=False,
                      )

    fig.update_yaxes(gridcolor="rgba(.5,.5,.5,.5)",
                     range=[0, 1],
                     showticklabels=False)

    fig.update_xaxes(showticklabels=False)

    return fig


def get_ts_states(df):

    colormap = {
        "Bund": "rgba(31, 119, 180, 0.3)",
        "Baden-Württemberg": "rgba(255, 127, 14, 0.3)",
        "Bayern": "rgba(44, 160, 44, 0.3)",
        "Berlin": "rgba(214, 39, 40, 0.3)",
        "Brandenburg": "rgba(148, 103, 189, 0.3)",
        "Bremen": "rgba(140, 86, 75, 0.3)",
        "Hamburg": "rgba(227, 119, 194, 0.3)",
        "Hessen": "rgba(127, 127, 127, 0.3)",
        "Niedersachsen": "rgba(188, 189, 34, 0.3)",
        "Mecklenburg-Vorpommern": "rgba(23, 190, 207, 0.3)",
        "Nordrhein-Westfalen": "rgba(174, 199, 232, 0.3)",
        "Rheinland-Pfalz": "rgba(255, 187, 120, 0.3)",
        "Saarland": "rgba(152, 223, 138, 0.3)",
        "Sachsen": "rgba(255, 152, 150, 0.3)",
        "Sachsen-Anhalt": "rgba(197, 176, 213, 0.3)",
        "Schleswig-Holstein": "rgba(196, 156, 148, 0.3)",
        "Thüringen": "rgba(219, 219, 141, 0.3)"
    }

    fig = make_subplots(rows=1, cols=2)

    for col, key in enumerate(df.key.unique(), start=1):
        for state, grp in df.loc[df.key.eq(key)].groupby("state"):
            trace = go.Scatter(
                x=grp.year,
                y=grp.freq,
                name=state,
                legendgroup=state,
                showlegend=col == 1,
                mode="lines",
                line=dict(color=colormap[state],
                          width=3)
            )
            fig.add_trace(trace=trace, row=1, col=col)

    return fig


def empty_ts_states():
    fig = make_subplots(rows=1, cols=5,
                        horizontal_spacing=0.01)

    for col in range(5):
        trace = go.Scatter()
        fig.add_trace(trace=trace, row=1, col=col+1)

    fig.update_yaxes(ticklabelposition="inside top", title=None)

    return fig
