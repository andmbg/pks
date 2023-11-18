import re

import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc

from src.data.import_data_pks import hierarchize_data
from src.data.config import MAXKEYS
from src.visualization.visualize import (
    empty_ts_clearance,
    sunburst_location,
    get_sunburst,
    get_presence_chart,
    get_ts_clearance,
    get_ts_states,
    color_map_from_color_column,
    empty_ts_states
)

data_raw = pd.read_parquet("data/processed/pks.parquet")
all_years = data_raw.year.unique()
data_bund = data_raw.loc[data_raw.state == "Bund"]

# infer key hierarchy from key numbers:
data_bund = hierarchize_data(data_bund)

# catalog is used for the key picker and table:
catalog = data_bund[["key", "label", "parent"]].drop_duplicates(subset="key")
catalog.label = catalog.label.str.replace("<br>", " ")
catalog["label_key"] = catalog.apply(
    lambda row: row.label + " (" + row.key + ")", axis=1)

ts_key_selection = []
reset_n_clicks_old = 0

# initial sunburst plot:
sunburst = get_sunburst(
    catalog,
    colormap=color_map_from_color_column(data_bund),
)

#          define dash elements outside the layout for legibility:
# -----------------------------------------------------------------------------

# Sunburst:
fig_sunburst = dcc.Graph(
    id='fig-sunburst',
    figure=sunburst
)

# DataTable for text search:
table_search = dash_table.DataTable(
    id="table-textsearch",
    columns=[
        {"name": "Suchen:", "id": "label_key", "type": "text"},
    ],
    data=catalog.to_dict("records"),
    filter_action="native",
    page_size=15,
    style_cell={
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "maxWidth": 0,
        "fontSize": 16,
        "font-family": "sans-serif"},
    css=[
        {"selector": ".dash-spreadsheet tr", "rule": "height: 45px;"},
    ]
)

# Presence chart:
fig_presence = dcc.Graph(
    id='fig-key-presence'
)

# Reset button:
button_reset = html.Button(
    "Leeren",
    id="reset",
    n_clicks=0
)

# Bar chart on clearance:
fig_ts_clearance = dcc.Graph(
    id="fig-ts-clearance",
    style={"height": "600px"},
    figure=empty_ts_clearance(all_years)
)

# Line chart on states:
fig_ts_states = dcc.Graph(
    id="fig-ts-states",
    style={"height": "600px"},
    figure=empty_ts_states()
)


#                                   Layout
# -----------------------------------------------------------------------------

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# define app layout:
app.layout = html.Div([
    # top row: browsing area
    dbc.Row([
        dcc.Store(id="keystore"),
        dbc.Col([], width={"size": 1}),
        dbc.Col([
            dbc.Tabs([
                dbc.Tab([fig_sunburst], label="Blättern", tab_id="keypicker"),
                dbc.Tab([table_search], label="Suchen", tab_id="textsearch")
            ],
                id="tabs",
                active_tab="keypicker",
            )
        ], width={"size": 5}),
        dbc.Col([
            html.Div([fig_presence])
        ], width={"size": 5}),
        dbc.Col([], width={"size": 1}),
    ], style={"backgroundColor": "rgba(50,50,255, .1)"}),

    # row 2: reset button
    dbc.Row([
        dbc.Col([
            html.Div([button_reset])
        ], width={"size": 1}
        )], justify="center",
        style={"backgroundColor": "rgba(255,200,0,.1)"}
    ),

    # row 3: clearance timeseries
    dbc.Row([
        dbc.Col([
            html.Div([fig_ts_clearance])
        ], width={"size": 6, "offset": 3},
        )], style={"backgroundColor": "rgba(255,200,0,.1)"}
    ),

    # row 4: states timeseries
    dbc.Row([dbc.Col([fig_ts_states],
                     width={"size": 6, "offset": 3}
            )], style={"backgroundColor": "rgba(255,100,0,.1)"})
])


#                                  Callbacks
# -----------------------------------------------------------------------------

# Update Presence chart
@callback(Output("fig-key-presence", "figure"),
          Input("fig-sunburst", "clickData"),
          Input("table-textsearch", "derived_viewport_data"),
          Input("tabs", "active_tab"))
def update_presence_chart(keypicker_parent, table_data, active_tab):
    """
    Presence chart
    """
    if active_tab == "keypicker":
        key = sunburst_location(keypicker_parent)

        if key == "root" or key is None:  # just special syntax for when parent is None
            child_keys = data_bund.loc[data_bund.parent.isna(
            )].key.unique()
        else:
            child_keys = data_bund.loc[data_bund.parent == key].key.unique(
            )
        selected_keys = child_keys

    elif active_tab == "textsearch":
        selected_keys = []
        for element in table_data:
            selected_keys.append(element["key"])

    colormap = {k: grp.color.iloc[0]
                for k, grp in data_bund.groupby("key")}

    fig = get_presence_chart(data_bund, selected_keys, colormap)

    return (fig)


# Update key store
# ----------------
@callback(Output("keystore", "data", allow_duplicate=True),
          Input("fig-key-presence", "clickData"),
          Input("reset", "n_clicks"),
          prevent_initial_call=True)
def update_keystore(click_data, reset_trigger):

    global ts_key_selection
    global reset_n_clicks_old

    if reset_trigger > reset_n_clicks_old:
        ts_key_selection = []
        reset_n_clicks_old = reset_trigger

    else:
        selected_key = click_data["points"][0]["y"]
        if len(ts_key_selection) < MAXKEYS:
            ts_key_selection.append(selected_key)

    return ts_key_selection


# Update key store from time series
# ---------------------------------
@callback(Output("keystore", "data"),
          Input("fig-ts-clearance", "clickData"),
          prevent_initial_call=True)
def update_keystore_from_timeseries(input_json):

    global ts_key_selection
    key_to_deselect = input_json["points"][0]["x"][0:6]
    ts_key_selection.remove(key_to_deselect)

    return ts_key_selection


# Update clearance timeseries from keystore
# -----------------------------------------
@callback(Output("fig-ts-clearance", "figure"),
          Input("keystore", "data"),
          prevent_initial_call=True)
def update_clearance_from_keystore(keylist):

    if keylist == []:
        return empty_ts_clearance(all_years)

    # filter on selected keys:
    df_ts = data_bund.loc[data_bund.key.isin(keylist)].reset_index()

    # remove years in which cases = 0 (prevent div/0):
    df_ts = df_ts.loc[df_ts["count"].gt(0)]

    # prepare transformed columns for bar display:
    df_ts["unsolved"] = df_ts["count"] - df_ts.clearance
    df_ts["clearance_rate"] = df_ts.apply(
        lambda r: round(r["clearance"] / r["count"] * 100, 1),
        axis=1)

    # prepare long shape for consumption by plotting function:
    df_ts = pd.melt(
        df_ts,
        id_vars=["key", "state", "year", "shortlabel", "label",
                 "color", "clearance_rate", "count"],
        value_vars=["clearance", "unsolved"],
    )

    fig = get_ts_clearance(df_ts)

    return fig


# Update state timeseries from keystore
# -------------------------------------
@callback(Output("fig-ts-states", "figure"),
          Input("keystore", "data"),
          prevent_initial_call=True)
def update_states_from_keystore(keylist):

    if keylist == []:
        return empty_ts_states()

    # filter on selected keys:
    df_ts = data_raw.loc[data_raw.key.isin(keylist)].reset_index()
    
    fig = get_ts_states(df_ts)
    
    return fig


if __name__ == '__main__':
    app.run(debug=True)
