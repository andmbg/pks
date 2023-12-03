from pathlib import Path

import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc

from .src.data.import_data_pks import hierarchize_data
from .src.data.config import MAXKEYS
from .src.visualization.visualize import (
    empty_plot,
    sunburst_location,
    get_sunburst,
    get_presence_chart,
    get_ts_clearance,
    get_ts_states,
    color_map_from_color_column,
)

# allow relative path definitions:
dashapp_rootdir = Path(__file__).resolve().parent.parent

def init_dashboard(server):

    data_raw = pd.read_parquet(dashapp_rootdir / "data" / "processed" / "pks.parquet")
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
        id='fig-key-presence',
    )

    # Reset button:
    button_reset = dbc.Button(
        "Leeren",
        id="reset",
        n_clicks=0
    )

    # Bar chart on clearance:
    fig_ts_clearance = dcc.Graph(
        id="fig-ts-clearance",
        style={"height": "600px"},
        figure=empty_plot(
            f"Bis zu {MAXKEYS} Schlüssel/Delikte<br>"
            "auswählen, um sie hier zu vergleichen!"
        )
    )

    # Line chart on states:
    fig_ts_states = dcc.Graph(
        id="fig-ts-states",
        style={"height": "600px"},
        figure=empty_plot(
            "Schlüssel/Delikte auswählen, um hier<br>den Ländervergleich zu sehen!"
        )
    )

    # Intro text
    with open(dashapp_rootdir / "pks" / "src" / "prose" / "intro.md", "r") as file:
        md_intro = dcc.Markdown(file.read())
    
    # Prose between the selector area and clearance timeseries:
    with open(dashapp_rootdir / "pks" / "src" / "prose" / "post_selection_pre_clearance.md", "r") as file:
        md_post_selection = dcc.Markdown(file.read())

    # Prose between the two timeseries:
    with open(dashapp_rootdir / "pks" / "src" / "prose" / "post_clearance_pre_states.md", "r") as file:
        md_between_ts = dcc.Markdown(file.read())
    
    # Text following dashboard:
    with open(dashapp_rootdir / "pks" / "src" / "prose" / "post_states.md", "r") as file:
        md_post_ts = dcc.Markdown(file.read())
        

    #                                   Layout
    # -----------------------------------------------------------------------------
    app = Dash(__name__,
        server=server,
        routes_pathname_prefix="/pks/",
        external_stylesheets=[dbc.themes.FLATLY],
    )

    # define app layout:
    app.layout = html.Div([

        dbc.Container(style={"paddingTop": "50px"},
                      children=[
            
            dcc.Store(id="keystore", data=[]),

            # Intro
            dbc.Row([
                dbc.Col([
                    md_intro
                    ],
                    xs={"size": 12},
                    lg={"size": 6, "offset": 3},
                ),
                ], style={"backgroundColor": "rgba(50,50,255, .1)",
                          "paddingTop": "50px",
                          },
            ),

            # browsing area
            dbc.Row([
                dbc.Col([
                    dbc.Tabs([
                        dbc.Tab(
                            [fig_sunburst],
                            label="Blättern",
                            tab_id="keypicker",
                        ),
                        dbc.Tab(
                            [table_search],
                            label="Suchen",
                            tab_id="textsearch",
                        ),
                    ],
                        id="tabs",
                        active_tab="keypicker",
                    )
                ],
                    xs={"size": 6},
                    lg={"size": 6},
                ),
                dbc.Col([
                    html.Div([fig_presence])
                ],
                    xs={"size": 6},
                    lg={"size": 6},
                ),
                dbc.Col([], width={"size": 1}),
            ],
                style={"backgroundColor": "rgba(50,50,255, .1)"}
            ),

            # prose after selection
            dbc.Row([
                dbc.Col(
                    dbc.Collapse(
                        md_post_selection,
                        id="collapsible-post_selection",
                        is_open=True,
                    ),
                    lg={"size": 6, "offset": 3},
                    sm=10,
                ),

                dbc.Col(
                    dbc.Button(
                        "Ausblenden",
                        id="button-collapse-post_selection",
                        n_clicks=0,
                    ),
                    lg=2,
                    align="center",
                ),
            ],
                style={
                    "backgroundColor": "rgba(255,200,0, .1)",
                    "paddingTop": "30px"
                    }
            ),

            # reset button
            dbc.Row(
                dbc.Col(
                    html.Center([button_reset]),
                    lg={"size": 6, "offset": 3},
                    sm=12,
                ),
                style={"backgroundColor": "rgba(255,200,0, .1)"},
            ),

            # clearance timeseries
            dbc.Row(
                dbc.Col(
                    fig_ts_clearance,
                    width=12
                ),
                style={"backgroundColor": "rgba(255,200,0,.1)"},
            ),
            
            # collapsible prose between timeseries
            dbc.Row([
                dbc.Col(
                    dbc.Collapse(
                        md_between_ts,
                        id="collapsible-post_ts",
                        is_open=True,
                    ),
                    lg={"size": 6, "offset": 3},
                    sm=10,
                ),

                dbc.Col(
                    dbc.Button(
                        "Ausblenden",
                        id="button-collapse-post_ts",
                        n_clicks=0,
                    ),
                    lg=2,
                    align="center"
                )
            ],
                style={
                    "backgroundColor": "rgba(255,100,0,.1)",
                    "paddingTop": "30px",
                    },
            ),

            # states timeseries
            dbc.Row(
                dbc.Col(
                    fig_ts_states,
                    width=12,
                    style={"backgroundColor": "rgba(255,100,0,.1)"},
                )
            ),
            
            # post-dashboard text
            dbc.Row(
                dbc.Col(
                    md_post_ts,
                    xs={"size": 12},
                    lg={"size": 6, "offset": 3}
                ),
                style={"backgroundColor": "rgba(0,0,0,.1)",
                       "paddingTop": "30px"}
            ),

            # row: Footer
            dbc.Row(
                dbc.Col(
                    html.Center(
                        "Quelle: PKS Bundeskriminalamt, Berichtsjahre 2013 bis 2022. "
                        "Es gilt die Datenlizenz Deutschland – Namensnennung – Version 2.0",
                        style={"height": "200px"}
                        ),
                    lg={"size": 6, "offset": 3},
                    sm=12,
                )
            ),
        ])
    ])
    
    init_callbacks(app, data_bund, data_raw)
    
    return app.server


def init_callbacks(app, data_bund, data_raw):
    # Update Presence chart
    @app.callback(Output("fig-key-presence", "figure"),
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
    @app.callback(
        Output("keystore", "data", allow_duplicate=True),
        State("keystore", "data"),
        Input("fig-key-presence", "clickData"),
        prevent_initial_call=True
    )
    def update_keystore(keyselection_old, click_presence):

        if click_presence:
            key_selection_new = keyselection_old
            key_to_add = click_presence["points"][0]["y"]
            if len(key_selection_new) < MAXKEYS:
                key_selection_new.append(key_to_add)
            
            return key_selection_new


    # Update key store from time series
    # ---------------------------------
    @app.callback(
        Output("keystore", "data", allow_duplicate=True),
        Input("fig-ts-clearance", "clickData"),
        State("keystore", "data"),
        prevent_initial_call=True
    )
    def update_keystore_from_timeseries(click_clearance, keyselection_old):
        key_to_remove = click_clearance["points"][0]["x"][0:6]
        keyselection_new = keyselection_old
        keyselection_new.remove(key_to_remove)
        
        return keyselection_new


    # Reset key store
    # ----------------------------------
    @app.callback(
        Output("keystore", "data", allow_duplicate=True),
        Input("reset", "n_clicks"),
        prevent_initial_call=True
    )
    def reset_keystore(clickevent):
        return []


    # Update clearance timeseries from keystore
    # -----------------------------------------
    @app.callback(
        Output("fig-ts-clearance", "figure"),
        Input("keystore", "data"),
            prevent_initial_call=True)
    def update_clearance_from_keystore(keylist):

        if keylist == []:
            return empty_plot(
                f"Bis zu {MAXKEYS} Schlüssel/Delikte<br>"
                "auswählen, um sie hier zu vergleichen!"
            )

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
    @app.callback(Output("fig-ts-states", "figure"),
            Input("keystore", "data"),
            prevent_initial_call=True)
    def update_states_from_keystore(keylist):

        if keylist == []:
            return empty_plot(
                "Schlüssel/Delikte auswählen, um hier<br>den Ländervergleich zu sehen!"
            )

        # filter on selected keys:
        df_ts = data_raw.loc[data_raw.key.isin(keylist)].reset_index()

        fig = get_ts_states(df_ts)

        return fig


    @app.callback(
        Output("collapsible-post_selection", "is_open"),
        [Input("button-collapse-post_selection", "n_clicks")],
        [State("collapsible-post_selection", "is_open")],
    )
    def toggle_collapse_post_selection(n, is_open):
        if n:
            return not is_open
        return is_open


    @app.callback(
        Output("collapsible-post_ts", "is_open"),
        [Input("button-collapse-post_ts", "n_clicks")],
        [State("collapsible-post_ts", "is_open")],
    )
    def toggle_collapse_post_ts(n, is_open):
        if n:
            return not is_open
        return is_open
