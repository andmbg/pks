import re

import pandas as pd
from dash import Dash, dcc, html, Input, Output, callback, dash_table

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
catalog = data_bund[["key", "label"]].drop_duplicates(subset="key")
catalog.label = catalog.label.str.replace("<br>", "\n")

ts_key_selection = []
reset_n_clicks_old = 0

# infer key hierarchy from key numbers:
data_bund = hierarchize_data(data_bund)

app = Dash(__name__)

hovertemplate = """
                <b>%{customdata[1]}</b><br><br>
                %{customdata[0]}<br>
                (%{customdata[2]} Unterschlüssel)
                <extra></extra>"""
hovertemplate = re.sub(r"([ ]{2,})|(\n)", "", hovertemplate)

# initial sunburst plot:
keypicker = get_keypicker(
    data_bund,
    colormap=color_map_from_color_column(data_bund),
    hovertemplate=hovertemplate
)

app.layout = html.Div([

    html.Div([
        
        dcc.Graph(
            id='fig-keypicker',
            figure=keypicker
        ),

    ], style={"flex": 1}),
    
    html.Div([
        dash_table.DataTable(
            columns=[
                {"name": "Schlüssel", "id": "key", "type": "text"},
                {"name": "Delikt", "id": "label", "type": "text"},
            ],
            data=catalog.to_dict("records"),
            filter_action="native",
            style_table={
                "height": 10,
            },
            style_data={
                "width": {"key": "100px", "label": "200px"},# "midWidth": "150px", "maxWidth": "150px",
                "overflow": "hidden",
                "textOverflow": "ellipsis",
            }
        )
    ], style={"flex": 1, "backgroundColor": "#dddddd"}),

    html.Div([
        dcc.Graph(
            id='fig-key-presence'
        ),
    ], style={"flex": 1}),
    
    html.Div([
        html.Button("Leeren",
                    id="reset",
                    n_clicks=0)
    ]),

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


# Update Presence chart
# ---------------------
@callback(Output("fig-key-presence", "figure"),
          Input("fig-keypicker", "clickData"))
def update_presence_chart(input_json):
    """
    Presence chart
    """

    key = sunburst_location(input_json)
    colormap = {k: grp.color.iloc[0]
                for k, grp in data_bund.groupby("key")}

    if key == "root" or key is None:  # just special syntax for when parent is None
        child_keys = data_bund.loc[data_bund.parent.isna(
        )].key.unique()
    else:
        child_keys = data_bund.loc[data_bund.parent == key].key.unique(
        )

    fig = get_existence_chart(data_bund, child_keys, colormap)

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
        df_ts = data_bund.loc[(data_bund.state.eq("Bund")) & (data_bund.key.eq("000000"))].reset_index()
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
