import re
import colorsys
from textwrap import wrap
import logging

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ...src.visualization.colormap import hsv_to_css, hsvtraj, max_nchildren


logging.basicConfig(
    filename="dashboard.log",
    filemode="w",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)


def num(number: float, separator: str = ".", magnitude: str = None, digits: int = 0, lang: str = "de", space: str = "&#x202F;"):
    """
    Display numbers in a friendly way.

    :param number: any float or integer
    :param magnitude: say if you want thousands (k), millions (M) or billions (G) - or none
    :param digits: how many digits after the decimal should be displayed (after division by magnitude)
    :param lang: German (de) or English (en). Defaults to German.
    :param space: character(s) between the number and magnitude string, if any. Defaults to "narrow non-breaking space".
    """
    magwords = {
        "k": {
            "div": 1000,
            "de": " Tsd.",
            "en": "k",
        },
        "M": {
            "div": 1e6,
            "de": " Mio.",
            "en": "m",
        },
        "G": {
            "div": 1e9,
            "de": " Mrd.",
            "en": "bn",
        },
        None: {
            "div": 1,
            "de": "",
            "en": "",
        }
    }

    # throw out nans
    if pd.isna(number):
        return ""

    if magnitude == "auto":
        if int(number) < 1e6:
            magnitude = None
        elif int(number) < 1e9:
            magnitude = "M"
        else:
            magnitude = "G"

    number = number / magwords[magnitude]["div"] if magnitude in magwords.keys() else number
    number = round(number, digits) if digits is not None else number

    if type(number) == pd.Series:
        number = number.iloc[0]


    # remove ,0 if so desired:
    if digits == 0 or number == int(number):
        number = int(number)

    # add thousand separator if so desired:
    if separator != "":
        numstring = "{:,}".format(number)

        if lang == "de":
            inter1 = numstring.replace(",", "§")  # thousand sep to placeholder
            inter2 = inter1.replace(".", ",")  # point to German comma
            numstring = inter2.replace("§", separator)  # placeholder to sep

    else:
        numstring = str(number)
        if lang == "de":
            numstring = numstring.replace(".", ",")

    suffix = magwords[magnitude][lang] if magnitude is not None else ""

    outstring = numstring + space + suffix

    return outstring


def _css_rainbow(N=5, s=1, v=0.75):
    """
    Helper that gives N samples from the rainbow.
    """
    HSV_tuples = [(x * 1.0 / N, s, v) for x in range(N)]
    hex_out = []
    for rgb in HSV_tuples:
        rgb = map(lambda x: int(x * 255), colorsys.hsv_to_rgb(*rgb))
        hex_out.append("#%02x%02x%02x" % tuple(rgb))
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
    rgb_color = tuple(int(hex_color[i : i + 2], 16) for i in (1, 3, 5))

    # Convert RGB to HLS
    h, l, s = colorsys.rgb_to_hls(
        rgb_color[0] / 255.0, rgb_color[1] / 255.0, rgb_color[2] / 255.0
    )

    # Desaturate the color
    s *= sat

    # brighten
    bdiff = 1 - l
    l = l + bri * bdiff

    # Convert back to RGB
    r, g, b = colorsys.hls_to_rgb(h, l, s)

    # Convert RGB to hex
    desaturated_hex_color = "#{:02x}{:02x}{:02x}".format(
        int(r * 255), int(g * 255), int(b * 255)
    )

    return desaturated_hex_color


def germanize_number(number):
    # Convert the number to a string
    number_str = str(number)

    # Reverse the string to make it easier to insert separators
    reversed_str = number_str[::-1]

    # Insert German thousand separators every three digits
    formatted_str = ""
    for i in range(0, len(reversed_str), 3):
        formatted_str += reversed_str[i : i + 3] + "."

    # Remove the trailing dot and reverse the string back
    formatted_number = formatted_str[:-1][::-1]

    return formatted_number


def make_df_colormap(df):
    """
    From the PKS dataset, create a colormap (dict) that follows some rules:
    - children of a parent key are spread over a gamut around the parent's hue
    - width of gamut and some other parameters can be set here

    :param df: the dataset
    """
    MAX_GAMUT = 0.75  # how wide the child spectrum may become under the parent with most children
    MIN_GAMUT = 0.03  # if nchildren=2, their minimum gamut
    # exponent of hue curve from MIN to MAX;
    # 2 means the gamut grows late with family size
    # .5 means small groups have stronger contrast in them
    # 1 is linear
    GAMUT_EXP = 1

    df = df.copy().drop_duplicates(subset="key")

    df["h"] = None
    df["s"] = None
    df["v"] = None

    # an index that for every family size returns a reasonable gamut width among children:
    gam_unit = list(
        np.arange(0, (1 + 1 / max_nchildren(df)), 1 / (max_nchildren(df) - 1))
    )
    gam_curvature = [i**GAMUT_EXP for i in gam_unit]
    gam_curve = [MIN_GAMUT + (MAX_GAMUT - MIN_GAMUT) * i for i in gam_curvature]

    # set lvl 1:
    n1 = len(df.loc[df.level.eq(1)])
    colors_1 = hsvtraj(n1, sa=1, sb=0.7, va=0.5, vb=0.7)
    df.loc[df.level.eq(1), "h"] = [i[0] for i in colors_1]
    df.loc[df.level.eq(1), "s"] = [i[1] for i in colors_1]
    df.loc[df.level.eq(1), "v"] = [i[2] for i in colors_1]

    # set lvl >1 recursively:
    for lv_parent, grp in df.loc[df.level.gt(1)].groupby(
        ["level", "parent"], sort=True
    ):
        parent_row = df.loc[df.key.eq(lv_parent[1])]
        parent_hue = parent_row["h"].iloc[0]

        nchildren = len(grp)

        gamut = gam_curve[nchildren - 1]

        if lv_parent[1] == "622000":
            logging.debug(f"n={nchildren}; parent_hue={parent_hue}; gamut={gamut}")

        childrens_hsv = hsvtraj(
            n=nchildren,
            ha=parent_hue - 0.5 * gamut,
            hb=parent_hue + 0.5 * gamut,
            sa=0.6,
            sb=1,
            va=1,
            vb=0.6,
        )

        df.loc[((df.level.eq(lv_parent[0])) & (df.parent.eq(lv_parent[1]))), "h"] = [
            i[0] for i in childrens_hsv
        ]
        df.loc[((df.level.eq(lv_parent[0])) & (df.parent.eq(lv_parent[1]))), "s"] = [
            i[1] for i in childrens_hsv
        ]
        df.loc[((df.level.eq(lv_parent[0])) & (df.parent.eq(lv_parent[1]))), "v"] = [
            i[2] for i in childrens_hsv
        ]

    df.loc[df.level.gt(0), "color"] = df.loc[df.level.gt(0)].apply(
        lambda x: hsv_to_css(x.h, x.s, x.v), axis=1
    )
    df = df.drop(["h", "s", "v"], axis=1)

    return df[["key", "color"]].set_index("key").to_dict()["color"]


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
    if entry == "Straftaten":
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

    # wrap long labels in hover data:
    df.label = df.apply(lambda x: "<br>".join(wrap(x.label, 80)), axis=1)

    # change display name of root node:
    df.loc[df.key.eq("------"), "key"] = "Straftaten"
    df.loc[df.parent.eq("------"), "parent"] = "Straftaten"
    # set root color to transparent:
    colormap["Straftaten"] = "rgba(0,0,0,0)"

    hovertemplate = """
                <b>%{customdata[1]}</b><br><br>
                %{customdata[0]}<br>
                (%{customdata[2]} Unterschlüssel)
                <extra></extra>"""
    hovertemplate = re.sub(r"([ ]{2,})|(\n)", "", hovertemplate)

    fig = (
        px.sunburst(
            df,
            names="key",
            parents="parent",
            color="key",
            color_discrete_map=colormap,
            hover_data=["label", "key", "nchildren"],
            maxdepth=3,
            branchvalues="total",
            values="sectionwidth",
        )
        .update_layout(
            margin=dict(t=15, r=15, b=15, l=15),
            plot_bgcolor="#ffffff",
            paper_bgcolor="rgba(255,255,255,0)",
            height=700,
            font_size=18,
        )
        .update_traces(
            hovertemplate=hovertemplate,
            leaf_opacity=1,
        )
        .update_coloraxes(showscale=False)
    )

    return fig


def get_presence_chart(
    df,
    keys,
    colormap,
    xaxis="year",
    yaxis="key",
    label_annot="shortlabel",
    label_hover="label",
    newname="label_change",
):
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

    # for hover, break long labels:
    df["hoverlabel"] = df[label_hover].apply(lambda x: "<br>".join(wrap(x, width=60)))

    fig = go.Figure()

    # add each key's line and points:
    for i, grp in df.groupby(yaxis):
        fig.add_trace(
            go.Scatter(
                x=grp[xaxis],
                y=grp[yaxis],
                # text=grp["firstlabel"],
                mode="lines+markers",
                marker=dict(color=colormap[i], size=12),
                line_width=4,
                # textposition="top right",
                customdata=np.stack(
                    (grp["hoverlabel"], grp["count"].apply(germanize_number)), axis=-1
                ),
                hovertemplate="<b>%{customdata[0]}</b> (%{x}):<br><br>%{customdata[1]} Fälle<extra></extra>",
            )
        )

    # add markers for each time a new label is used (black circles):
    new_markers = df.loc[df[newname]]

    fig.add_trace(
        go.Scatter(
            x=new_markers[xaxis],
            y=new_markers[yaxis],
            mode="markers",
            marker=dict(
                color="rgba(255,255,255,.7)",
                line_width=2,
                line_color="white",
                size=18,
                symbol="circle",
            ),
            hoverinfo="skip",
        )
    )

    # annotation
    # for annotations, fix x position to leftmost year:
    annot_x = df.year.min()

    for i, grp in df.groupby(yaxis):
        annot = grp.iloc[0]

        fig.add_trace(
            go.Scatter(
                x=[annot_x],
                y=[annot[yaxis]],
                mode="text",
                text=annot["firstlabel"],
                textposition="top right",
                textfont=dict(size=18),
            )
        )

    fig.update_traces(showlegend=False)
    fig.update_xaxes(dtick=1)
    # fig.update_yaxes(autorange="reversed")

    # adapt height to number of keys displayed (space them evenly):
    r = len(keys)  # "rows"
    fig.update_layout(
        margin=dict(t=41 + 45 + 45, b=44 - 20),
        height=155 + 45 * r + 10,  # 45 per table row, 155 framing, 10 nudging
        yaxis_range=[r - 0.5, -0.5],
        xaxis_showgrid=False,
        yaxis_showgrid=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_size=15,
    )

    return fig


def get_ts_clearance(df):
    """
    :param df: Dataframe containing 1..n keys (only the data to be displayed - filter beforehand!)
    """
    # colormap = {i: grp.loc[grp.index[0], "color"] for i, grp in df.groupby("key")}
    colormap = color_map_from_color_column(df)

    years = list(range(min(df.year), max(df.year) + 1))

    # max bar height:
    # counts1 = df.loc[df.variable.eq("count"), "value"].values
    # counts2 = df.loc[df.variable.eq("unsolved"), "value"].values
    # maxheight = pd.DataFrame({"a": counts1, "b": counts2}).apply(sum, axis=1).max()
    maxheight = df["count"].max() * 1.4

    fig = make_subplots(
        cols=len(years),
        shared_yaxes=True,
        shared_xaxes=True,
        horizontal_spacing=0.01,
        subplot_titles=years,
    )

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

            customdata = np.stack(
                (
                    committed["key"],
                    committed["year"],
                    committed["label"],
                    unsolved["value"].apply(germanize_number),
                    committed["clearance_rate"],
                    committed["count"].apply(germanize_number),
                ),
                axis=-1,
            )

            hovertemplate_committed = "<br>".join(
                [
                    "Schlüssel %{customdata[0]}",
                    "<b>%{customdata[2]}</b><br>",
                    "<b>Fälle im Jahr %{customdata[1]}: %{customdata[5]}</b>",
                    "Unaufgeklärt: %{customdata[3]}",
                    "Aufklärungsrate: %{customdata[4]} %<extra></extra>",
                ]
            )

            hovertemplate_unsolved = "<br>".join(
                [
                    "Schlüssel %{customdata[0]}",
                    "<b>%{customdata[2]}</b><br>",
                    "Fälle im Jahr %{customdata[1]}: %{customdata[5]}",
                    "<b>Unaufgeklärt: %{customdata[3]}</b>",
                    "Aufklärungsrate: %{customdata[4]} %<extra></extra>",
                ]
            )

            fig.add_trace(
                go.Bar(
                    x=[j],
                    y=committed["value"],
                    marker=dict(color=colormap[j]),
                    showlegend=(j in legend_todo),
                    legendgroup=j,
                    name=committed.shortlabel.iloc[0],
                    customdata=customdata,
                    hovertemplate=hovertemplate_committed,
                ),
                col=i + 1,
                row=1,
            )

            # unsolved cases in grey:
            fig.add_trace(
                go.Bar(
                    x=[j],
                    y=unsolved.value,
                    marker=dict(color=_desaturate_brighten(colormap[j], 0.25, 0.5)),
                    showlegend=False,
                    legendgroup=j,
                    customdata=customdata,
                    hovertemplate=hovertemplate_unsolved,
                ),
                col=i + 1,
                row=1,
            )

            # cross off the key from the legend-TODO:
            legend_todo = legend_todo.difference({j})

    fig.update_layout(
        bargap=0.001,
        barmode="stack",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=60, r=20),
        legend=dict(
            yanchor="top",
            xanchor="left",
            y=0.99,
            x=0.01,
            bgcolor="rgba(0,0,0, .1)",
            bordercolor="white",
            borderwidth=0,
        ),
        font_size=18,
        title="Jahresvergleich Fälle und Aufklärung",
        height=750,
        yaxis=dict(
            ticks="outside",
            ticklen=3,
            tickcolor="black",
            tickwidth=1.5,
        )
    )

    fig.update_yaxes(
        gridcolor="rgba(.5,.5,.5,.5)",
        range=[0, maxheight],
    )

    return fig


def empty_ts_clearance(years):
    """
    What gets displayed if user presses the reset btn.
    """
    years = years.astype(str)

    fig = make_subplots(
        cols=len(years), shared_yaxes=True, horizontal_spacing=0, subplot_titles=years
    )

    for i, year in enumerate(years):
        fig.add_trace(go.Bar(x=[0], y=[0]), col=i + 1, row=1)

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=60, r=20),
        font_size=18,
        showlegend=False,
        title="Jahresvergleich Fälle und Aufklärung",
    )

    fig.update_yaxes(gridcolor="rgba(.5,.5,.5,.5)", range=[0, 1], showticklabels=False)

    fig.update_xaxes(showticklabels=False)

    return fig


def get_ts_states(df):

    key_colormap = color_map_from_color_column(df)

    state_colormap = {
        "Bund": "rgba(0,0,0,0.9)",
        "Baden-Württemberg": "rgba(51, 160, 44, 0.8)",
        "Bayern": "rgba(227, 26, 28, 0.8)",
        "Berlin": "rgba(31, 120, 180, 0.8)",
        "Brandenburg": "rgba(106, 61, 154, 0.8)",
        "Bremen": "rgba(177, 89, 40, 0.8)",
        "Hamburg": "rgba(50, 0, 100, 0.8)",
        "Hessen": "rgba(253, 191, 111, 0.8)",
        "Niedersachsen": "rgba(251, 154, 153, 0.8)",
        "Mecklenburg-Vorpommern": "rgba(202, 178, 214, 0.8)",
        "Nordrhein-Westfalen": "rgba(255, 255, 153, 0.8)",
        "Rheinland-Pfalz": "rgba(255, 0, 50, 0.8)",
        "Saarland": "rgba(31, 31, 31, 0.8)",
        "Sachsen": "rgba(253, 191, 111, 0.8)",
        "Sachsen-Anhalt": "rgba(255, 140, 0, 0.8)",
        "Schleswig-Holstein": "rgba(44, 160, 44, 0.8)",
        "Thüringen": "rgba(144, 33, 33, 0.8)",
    }

    states_abbreviations = {
        "Bund": "DE",
        "Baden-Württemberg": "BW",
        "Bayern": "BY",
        "Berlin": "BE",
        "Brandenburg": "BB",
        "Bremen": "HB",
        "Hamburg": "HH",
        "Hessen": "HE",
        "Mecklenburg-Vorpommern": "MV",
        "Niedersachsen": "NI",
        "Nordrhein-Westfalen": "NW",
        "Rheinland-Pfalz": "RP",
        "Saarland": "SL",
        "Sachsen": "SN",
        "Sachsen-Anhalt": "ST",
        "Schleswig-Holstein": "SH",
        "Thüringen": "TH",
    }

    nkeys = df.key.nunique()
    bgcolor_data = []
    annotations = []

    fig = make_subplots(rows=nkeys, cols=1, vertical_spacing=0.01, shared_xaxes=True)

    for row, key in enumerate(df.key.unique(), start=1):

        df_key = df.loc[df.key.eq(key)]

        for state, grp in df_key.groupby("state"):

            customdata = grp.freq.apply(num, digits=1)

            # colour lines:
            fig.add_trace(
                go.Scatter(
                    x=grp.year,
                    y=grp.freq,
                    name=states_abbreviations[state],
                    showlegend=row == 1,
                    legendgroup=state,
                    mode="lines",
                    visible=True if state == "Bund" else "legendonly",
                    line=dict(
                        color=state_colormap[state],
                        width=4 if state == "Bund" else 2
                    ),
                    customdata=customdata,
                    hovertemplate="%{customdata}"
                ),
                row=row, col=1,
            )

            # white dots:
            fig.add_trace(
                go.Scatter(
                    x=grp.year,
                    y=grp.freq,
                    name=states_abbreviations[state],
                    showlegend=False,
                    legendgroup=state,
                    mode="markers",
                    visible=True if state == "Bund" else "legendonly",
                    marker=dict(
                        color="white",
                        line=dict(color="black", width=1),
                        size=8 if state == "Bund" else 4
                    ),
                    hoverinfo="skip",
                ),
                row=row, col=1,
            )

        # create manipulations that color our subplots differently (this is a hack
        # due to Plotly currently not offering varying bg colors per subplot)
        yref = "y" if row == 1 else "y" + str(row)

        # faint color background:
        bgcolor_data.append(
            dict(
                type="rect",
                yref=yref,
                xref="paper",
                y0=min(df_key.freq),
                y1=max(df_key.freq),
                x0=-0.001,
                x1=1,
                fillcolor=_desaturate_brighten(key_colormap[key], 0.7, 0.8),
                layer="below",
                line=dict(width=0),
            ),
        )
        # vertical color stripe at x=0:
        bgcolor_data.append(
            dict(
                type="rect",
                xref="paper",
                yref=yref,
                y0=min(df_key.freq),
                y1=max(df_key.freq),
                x0=-0.005,
                x1=0.0,
                fillcolor=key_colormap[key],
                layer="below",
                line=dict(width=0),
            )
        )

        # for each facet, prepare the Facet's Annotation Points (fap):
        # fap_max = df.loc[df.key.eq(key)].freq.min()
        # fap_min = df.loc[df.key.eq(key)].freq.max()
        # fap = np.linspace(fap_min, fap_max, num=10)[[0, 3, 6, 9]]

        # annotations.append(fap)

        fig.update_layout(
            {
                f"yaxis{row if row > 1 else ''}": {
                    "range": [df_key.freq.min(), df_key.freq.max()]
                }
            }
        )

    fig.update_yaxes(
        showgrid=True,
        zeroline=False,
        ticklen=5,
        ticks="outside",
        tickwidth=1.5,
        tickcolor="white",
    )

    fig.update_xaxes(showgrid=False)

    fig.update_layout(
        font_size=16,
        legend=dict(orientation="h", x=0, y=-0.15, yanchor="top"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,.5)",
        title=dict(
            text="Fälle je 100.000 Einwohner:innen im Ländervergleich",
            # y=1,
            # yanchor="top",
            # yref="container",
            # pad=dict(t=20),
        ),
        margin=dict(t=50),
        hovermode="x unified",
        # shade subplots according to their keys:
        shapes=bgcolor_data,
        height=nkeys * 350,
    )

    # replacement for y-axis - use annotations prepared above
    # each facet:
    for row, annots in enumerate(annotations):
        yref = "x" if row == 0 else "x" + str(row + 1)

        # three annotations
        for annot in annots:
            fig.add_annotation(
                xref=yref,
                yref="y",
                x=2013,
                y=annot,
                text="<b>" + str(int(annot)) + "</b>",
                font=dict(color="rgba(0,0,0,.3)"),
                showarrow=False,
                xanchor="left",
                col=1,
                row=row + 1,
            )

    return fig


def empty_ts_states():
    fig = go.Figure(go.Scatter())

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,.1)",
        title="Fälle je 100.000 Einwohner:innen im Ländervergleich",
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showticklabels=False,
    )
    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        showticklabels=False,
    )

    fig.add_annotation(
        text="Schlüssel/Delikt auswählen, um hier<br>den Ländervergleich zu sehen!",
        x=0.5,
        y=0.5,
        xanchor="center",
        yanchor="middle",
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=24),
    )

    return fig


def empty_plot(placeholder_text: str = "Hier könnte Ihre Werbung stehen!"):

    fig = go.Figure(go.Scatter())

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,.1)",
        title="Fälle je 100.000 Einwohner:innen im Ländervergleich",
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showticklabels=False,
    )
    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        showticklabels=False,
    )

    fig.add_annotation(
        text=placeholder_text,
        x=0.5,
        y=0.5,
        xanchor="center",
        yanchor="middle",
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=24),
    )

    return fig
