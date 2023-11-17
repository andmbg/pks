import re

import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc

from src.data.import_data_pks import hierarchize_data
from src.visualization.visualize import (
    sunburst_location,
    get_keypicker,
    get_existence_chart,
    get_timeseries,
    color_map_from_color_column
)

# how many keys we want displayed at most at the same time:
MAXKEYS = 5

data_raw = pd.read_parquet("data/processed/pks.parquet")
all_years = data_raw.year.unique()
data_bund = data_raw.loc[data_raw.state == "Bund"]

# infer key hierarchy from key numbers:
data_bund = hierarchize_data(data_bund)

catalog = data_bund[["key", "label", "parent"]].drop_duplicates(subset="key")
catalog.label = catalog.label.str.replace("<br>", "\n")

ts_key_selection = []
reset_n_clicks_old = 0

hovertemplate = """
                <b>%{customdata[1]}</b><br><br>
                %{customdata[0]}<br>
                (%{customdata[2]} Unterschlüssel)
                <extra></extra>"""
hovertemplate = re.sub(r"([ ]{2,})|(\n)", "", hovertemplate)

# initial sunburst plot:
keypicker = get_keypicker(
    catalog,
    colormap=color_map_from_color_column(data_bund),
    hovertemplate=hovertemplate
)


app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])


# Sunburst:
fig_keypicker = dcc.Graph(
    id='fig-keypicker',
    figure=keypicker
)

# DataTable
table_search = dash_table.DataTable(
    id="table-textsearch",
    columns=[
        {"name": "Schlüssel", "id": "key", "type": "text"},
        {"name": "Suchen:", "id": "label", "type": "text"},
    ],
    data=catalog.to_dict("records"),
    filter_action="native",
    page_size=10,
    style_data={
        # "midWidth": "150px", "maxWidth": "150px",
        # "width": {"key": "10px", "label": "200px"},
        "overflow": "hidden",
        "textOverflow": "ellipsis",
    }
)

# Presence
fig_presence = dcc.Graph(
    id='fig-key-presence'
)

# Reset
button_reset = html.Button(
    "Leeren",
    id="reset",
    n_clicks=0
)

# Timeseries
fig_timeseries = dcc.Graph(
    id="fig-timeseries",
    style={"height": "600px"}
)


app.layout = dbc.Container(
    [
        # Store
        dcc.Store(id="keystore"),
        
        dbc.Tabs(
            [
                dbc.Tab([fig_keypicker], label="Blättern", tab_id="keypicker"),
                dbc.Tab([table_search], label="Suchen", tab_id="textsearch"),
            ],
            id="tabs",
            active_tab="keypicker",
        ),
        
        html.Div(id="tabdata",
                 style={"height": "50px"}),
        
        html.Div([fig_presence]),
        
        html.Div([button_reset]),
        
        html.Div([fig_timeseries])
    ]
)


# Update Presence chart
# ---------------------
@callback(Output("fig-key-presence", "figure"),
          Input("fig-keypicker", "clickData"),
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
    
    fig = get_existence_chart(data_bund, selected_keys, colormap)

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
        if len(ts_key_selection) <= MAXKEYS:
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

    if keylist == []:
        selected_keys_states = {"state": "Bund", "key": "000000"}
        df_ts = data_bund.loc[(data_bund.state.eq("Bund")) & (
            data_bund.key.eq("000000"))].reset_index()
        df_ts["count"] = 0
        df_ts["clearance"] = 0

    else:
        # for now, focus only on Bund:
        selected_keys_states = [{"state": "Bund", "key": i} for i in keylist]

        # select only keys that are in the selection:
        df_ts = pd.concat([
            data_bund.loc[(data_bund.state.eq(i["state"])) & (data_bund.key.eq(i["key"]))] for i in selected_keys_states
        ]).reset_index()

    #
    # df_ts = df_ts[["key", "state", "year",
    #                "label", "count", "clearance", "color"]]
    df_ts["unsolved"] = df_ts["count"] - df_ts.clearance

    # remove years in which cases = 0 (prevent div/0)
    if keylist != []:
        df_ts = df_ts.loc[df_ts["count"].gt(0)]
        df_ts["clearance_rate"] = df_ts.apply(lambda r: round(
            r["clearance"] / r["count"] * 100, 1), axis=1)

    # ...unless we have a reset:
    else:
        df_ts["clearance_rate"] = 0

    df_ts = pd.melt(df_ts,
                    id_vars=["key", "state", "year",
                             "label", "color", "clearance_rate", "count"],
                    value_vars=["clearance", "unsolved"],
                    )

    timeseries = get_timeseries(df_ts)

    return timeseries


if __name__ == '__main__':
    app.run(debug=True)
