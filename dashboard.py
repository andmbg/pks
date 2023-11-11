import re
import logging

import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, callback

from src.data.import_data_pks import hierarchize_data
from src.visualization.visualize import sunburst_location, get_keypicker, get_existence_chart, get_timeseries

# how many keys we want displayed at most at the same time:
MAXKEYS = 5

def get_df_colors(year):
    df = data_bund_hr.loc[data_bund_hr.year.eq(year)]
    colors = {k: grp.color.iloc[0] for k, grp in df.groupby("key")}
    return df, colors


data_raw = pd.read_parquet("data/processed/pks.parquet")
data_raw["selection_color"] = ""
all_years = data_raw.year.unique()
data_bund = data_raw.loc[data_raw.state == "Bund"]

ts_key_selection = []

# For each year, produce an independent hierarchy. This is necessary, as the hierarchy relationships
# in the "crime catalogue" change across years, and contradictory relationships disable plotting:
data_bund_hr = pd.concat([hierarchize_data(grp)
                         for _, grp in data_bund.groupby("year")])

# globally hierarchized:
data_bund_hr_all = hierarchize_data(data_bund)
allyears = list(data_bund_hr_all.year.drop_duplicates().values)


app = Dash(__name__)

hovertemplate = """
                <b>%{customdata[1]}</b><br><br>
                %{customdata[0]}<br>
                <extra>%{customdata[2]} Fälle</extra>"""
hovertemplate = re.sub(r"([ ]{2,})|(\n)", "", hovertemplate)

# initial sunburst plot:
df, colors = get_df_colors(2022)
keypicker = get_keypicker(df=df, colormap=colors, hovertemplate=hovertemplate)
# timeseries = get_timeseries(df)

app.layout = html.Div([
    
    html.Div([
        dcc.Dropdown(
            id="yearpicker",
            options=[{"label": y, "value": y} for y in all_years],
            value=2022,
            placeholder='Jahr',
        ),

        dcc.Graph(
            id='fig-keypicker',
            figure=keypicker
        ),

    ], style={"flex": 1}),

    html.Div([
        dcc.Graph(
            id='fig-key-presence'
        ),
    ], style={"flex": 1}),

    html.Div([
        dcc.Graph(
            id="fig-timeseries",
            style={"height": "600px"}
        ),
    ], style={"width": "100%"}),
    
    dcc.Store(id="keystore"),

], style={"display": "flex",
          "flexFlow": "row wrap",
          "alignItems": "center",  # rechter Plot vertikal zentriert
          })




# Update Sunburst plot
# --------------------
@callback(Output("fig-keypicker", "figure"),
          Input("yearpicker", "value"))
def update_key_picker(year):
    """
    Sunburst chart: year
    """
    df, colors = get_df_colors(year)
    keypicker = get_keypicker(df=df, colormap=colors,
                              hovertemplate=hovertemplate)
    return keypicker




# Update Presence chart
# ---------------------
@callback(Output("fig-key-presence", "figure"),
          Input("fig-keypicker", "clickData"),
        #   Input("yearpicker", "value")
          )
def update_key_presence(input_json):
    """
    Presence chart
    """

    key = sunburst_location(input_json)
    colormap = {k: grp.color.iloc[0] for k, grp in data_bund_hr_all.groupby("key")}

    if key == "root" or key is None:  # just special syntax for when parent is None
        child_keys = data_bund_hr_all.loc[data_bund_hr_all.parent.isna()].key.unique()
    else:
        child_keys = data_bund_hr_all.loc[data_bund_hr_all.parent == key].key.unique()

    fig = get_existence_chart(data_bund_hr_all, child_keys, colormap)

    return (fig)



# Update key store from presence chart
# ------------------------------------
@callback(Output("keystore", "data", allow_duplicate=True),
          Input("fig-key-presence", "clickData"),
          prevent_initial_call=True)
def update_keystore_from_presencechart(input_json):

    global ts_key_selection
    selected_key = input_json["points"][0]["y"]
    
    if len(ts_key_selection) < MAXKEYS:
        ts_key_selection.append(selected_key)
    
    return ts_key_selection




# Update key store from time series
# ---------------------------------
@callback(Output("keystore", "data"),
          Input("fig-timeseries", "clickData"),
          prevent_initial_call=True)
def update_keystore_from_timeseries(input_json):
    
    global ts_key_selection
    key_to_deselect = input_json["points"][0]["x"][0:6]
    ts_key_selection.remove(key_to_deselect)
    
    return ts_key_selection    




# Update timeseries from keystore
# -------------------------------
@callback(Output("fig-timeseries", "figure"),
          Input("keystore", "data"),
          prevent_initial_call=True)
def update_ts_from_keystore(keylist):

    # for now, focus only on Bund:
    selected_keys_states = [{"state": "Bund", "key": i} for i in keylist]
    
    df_ts = pd.concat([
        data_bund_hr_all.loc[(data_bund_hr_all.state.eq(i["state"])) & (data_bund_hr_all.key.eq(i["key"]))] for i in selected_keys_states
    ])

    df_ts = df_ts[["key", "state", "year",
                   "label", "count", "clearance", "color"]]
    df_ts["unsolved"] = df_ts["count"] - df_ts["clearance"]
    df_ts = pd.melt(df_ts,
                    id_vars=["key", "state", "year", "label", "color"],
                    value_vars=["count", "unsolved"],
                    )

    timeseries = get_timeseries(df_ts)

    return timeseries


if __name__ == '__main__':
    app.run(debug=True)
