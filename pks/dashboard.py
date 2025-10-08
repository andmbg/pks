import sys
from pathlib import Path

import pandas as pd
from dash import (
    Dash,
    dcc,
    html,
    Input,
    Output,
    State,
    callback,
    dash_table,
    clientside_callback,
    no_update,
)
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from loguru import logger

from pks.src.i18n import translate_string as t, translate_series
from pks.src.data.import_data_pks import hierarchize_data
from pks.src.visualization.visualize import (
    empty_plot,
    sunburst_location,
    get_sunburst,
    get_presence_chart,
    get_ts_clearance,
    get_ts_states,
    color_map_from_color_column,
)

# import from config relatively, so it remains portable:
dashapp_rootdir = Path(__file__).resolve().parents[1]
sys.path.append(str(dashapp_rootdir))

from config import MAXKEYS, language_codes

logger.remove()
logger.add(sys.stderr, level="INFO")

# Pre-load data to RAM at startup for faster plot rendering:
data_raw_all = {}
data_bund_all = {}

for language in language_codes:
    data_raw_all[language] = pd.read_parquet(
        dashapp_rootdir / "data" / "processed" / f"pks_{language}.parquet"
    )
    data_bund_all[language] = (
        data_raw_all[language].copy().loc[data_raw_all[language].state == "Bund"]
    )
    data_bund_all[language] = hierarchize_data(data_bund_all[language])

years_coverage = (
    data_bund_all["de"].year.min(),
    data_bund_all["de"].year.max(),
)


#                                   Layout
# -----------------------------------------------------------------------------


# define app layout:
def make_main_content(language):

    # Line chart on states:
    fig_ts_states = dcc.Graph(
        id="fig-ts-states",
        # style={"height": "600px"},
        figure=empty_plot(
            t(
                "Schlüssel/Delikte auswählen, um hier<br>den Ländervergleich zu sehen!",
                language,
            ),
            language,
        ),
    )

    # # Reset button:
    # button_reset = dmc.Button(t("Leeren", language), id="reset", n_clicks=0)

    data_raw = data_raw_all[language]
    data_bund = data_bund_all[language]

    # catalog is used for the key picker and table:
    catalog = data_bund[["key", "label", "parent", "sectionwidth"]].drop_duplicates(
        subset="key"
    )
    catalog.label = catalog.label.str.replace("<br>", " ")
    catalog["label_key"] = catalog.apply(
        lambda row: row.label + " (" + row.key + ")", axis=1
    )

    #          define dash elements outside the layout for legibility:
    # -----------------------------------------------------------------------------

    # Presence chart:
    fig_presence = dcc.Graph(
        id="fig-key-presence",
    )

    # Bar chart on clearance:
    fig_ts_clearance = dcc.Graph(
        id="fig-ts-clearance",
        figure=empty_plot(
            t(
                f"Bis zu {MAXKEYS} Schlüssel/Delikte<br>"
                "auswählen, um sie hier zu vergleichen!",
                language,
            ),
            language,
        ),
    )

    # Intro text
    with open(dashapp_rootdir / "pks" / "src" / "prose" / "intro.md", "r") as file:
        md_intro = dcc.Markdown(t(file.read(), language))

    # Prose between the selector area and clearance timeseries:
    with open(
        dashapp_rootdir / "pks" / "src" / "prose" / "post_selection_pre_clearance.md",
        "r",
    ) as file:
        md_post_selection = dcc.Markdown(t(file.read(), language))

    # Prose between the two timeseries:
    with open(
        dashapp_rootdir / "pks" / "src" / "prose" / "post_clearance_pre_states.md", "r"
    ) as file:
        md_between_ts = dcc.Markdown(t(file.read(), language))

    # Text following dashboard:
    with open(
        dashapp_rootdir / "pks" / "src" / "prose" / "post_states.md", "r"
    ) as file:
        md_post_ts = dcc.Markdown(t(file.read(), language))

    layout = [
        dmc.Grid(
            dmc.GridCol(
                [md_intro],
                span=dict(base=12, lg=8),
                offset=dict(lg=2),
            )
        ),
        # browsing area
        dmc.Grid(
            [
                dmc.GridCol(
                    [
                        dmc.Tabs(
                            [
                                dmc.TabsList(
                                    [
                                        dmc.TabsTab(
                                            t("Blättern", language),
                                            value="keypicker",
                                        ),
                                        dmc.TabsTab(
                                            t("Suchen", language),
                                            value="textsearch",
                                        ),
                                    ]
                                ),
                                dmc.TabsPanel(
                                    [
                                        dcc.Graph(
                                            id="fig-sunburst",
                                            figure=get_sunburst(
                                                catalog,
                                                colormap=color_map_from_color_column(
                                                    data_bund
                                                ),
                                                language=language,
                                            ),
                                        )
                                    ],
                                    value="keypicker",
                                ),
                                dmc.TabsPanel(
                                    [
                                        dash_table.DataTable(
                                            id="table-textsearch",
                                            columns=[
                                                {
                                                    "name": t(
                                                        "Suchen:",
                                                        language,
                                                    ),
                                                    "id": "label_key",
                                                    "type": "text",
                                                },
                                            ],
                                            data=catalog.to_dict("records"),
                                            filter_action="native",
                                            page_size=15,
                                            style_cell={
                                                "overflow": "hidden",
                                                "textOverflow": "ellipsis",
                                                "maxWidth": 0,
                                                "fontSize": 16,
                                                "font-family": "sans-serif",
                                            },
                                            css=[
                                                {
                                                    "selector": ".dash-spreadsheet tr",
                                                    "rule": "height: 45px;",
                                                },
                                            ],
                                        )
                                    ],
                                    value="textsearch",
                                ),
                            ],
                            id="tabs",
                            value="keypicker",
                        )
                    ],
                    span=dict(
                        xs=6,
                        lg=6,
                    ),
                ),
                dmc.GridCol(
                    [html.Div([fig_presence])],
                    span=dict(
                        xs=6,
                        lg=6,
                    ),
                ),
                dmc.GridCol([], span=1),
            ],
        ),
        # DEBUG: see what comes out of the sunburst clickdata:
        # dbc.Row([
        #     dbc.Col([
        #         html.Div(id="location")
        #     ])
        # ]),
        # ---------------------------------------------------
        # prose after selection
        dmc.Grid(
            [
                dmc.GridCol(
                    md_post_selection,
                    span=dict(lg=8, sm=10),
                    offset=dict(lg=2, sm=1),
                ),
            ],
        ),
        # clearance timeseries
        dmc.Grid(
            [
                dmc.GridCol(fig_ts_clearance, span=12),
            ],
            # style={"height": "750px"},
        ),
        # # reset button
        # dmc.Grid(
        #     [
        #         dmc.GridCol(
        #             html.Center([button_reset]),
        #             span=dict(lg=8, sm=12),
        #             offset=dict(lg=2),
        #         ),
        #     ],
        # ),
        # prose between timeseries
        dmc.Grid(
            [
                dmc.GridCol(
                    md_between_ts,
                    span=dict(lg=8, sm=12),
                    offset=dict(lg=2),
                ),
            ],
        ),
        # states timeseries
        dmc.Grid(
            [
                dmc.GridCol(
                    fig_ts_states,
                    span=12,
                )
            ],
        ),
        # post-dashboard text
        dmc.Grid(
            dmc.GridCol(
                md_post_ts,
                span=dict(xs=12, lg=8),
                offset=dict(lg=2),
            ),
        ),
        # row: Footer
        dmc.Grid(
            dmc.GridCol(
                html.Center(
                    f"Quelle: PKS Bundeskriminalamt, Berichtsjahre {years_coverage[0]} "
                    f"bis {years_coverage[1]}. "
                    "Es gilt die Datenlizenz Deutschland – Namensnennung – Version 2.0",
                    style={"height": "200px"},
                ),
                span=dict(lg=6, sm=12),
                offset=dict(lg=3),
            )
        ),
    ]

    return layout, data_bund, data_raw


# Persistent controls (should not change upon language switch):
theme_toggle = dmc.Switch(
    offLabel=DashIconify(
        icon="radix-icons:sun",
        width=15,
        color=dmc.DEFAULT_THEME["colors"]["yellow"][8],
    ),
    onLabel=DashIconify(
        icon="radix-icons:moon",
        width=15,
        color=dmc.DEFAULT_THEME["colors"]["yellow"][6],
    ),
    id="color-scheme-switch",
    persistence=True,
    color="grey",
    size="md"
)
theme_store = dcc.Store(id="theme-store", data={"colorScheme": "light"})

language_toggle = dmc.Switch(
    offLabel="DE",
    onLabel="EN",
    id="language-switch",
    persistence=True,
    color="grey",
    size="md",
)
language_store = dcc.Store(id="language-store", data="de")

keystore = dcc.Store(id="keystore", data=[])

# Title
with open(dashapp_rootdir / "pks" / "src" / "prose" / "title.md", "r") as file:
    md_title = html.Center(dcc.Markdown(t(file.read(), language), id="md-title"))


app = Dash(
    __name__,
    # routes_pathname_prefix=route,
    # relevant for standalone launch, not used by main flask app:
)

starting_content, _, _ = make_main_content("de")

app.layout = html.Div(
    id="main-layout",
    children=[
        dmc.MantineProvider(
            id="mantine-provider",
            theme={"colorScheme": "light"},
            children=[
                dmc.Container(
                    [
                        dmc.Paper(
                            dmc.Grid(
                                [
                                    dmc.GridCol(
                                        [
                                            theme_toggle,
                                            theme_store,
                                            language_toggle,
                                            language_store,
                                            keystore,
                                        ],
                                        span=2,
                                        style={
                                            "display": "flex",
                                            "justifyContent": "flex-end",
                                            "alignItems": "center",
                                            "gap": "1rem",
                                        }
                                    ),
                                    dmc.GridCol(
                                        [
                                            md_title,
                                        ],
                                        span=dict(base=10, lg=8),
                                        style={
                                            "margin-bottom": "0",
                                        }
                                    ),
                                ],
                            ),
                        ),
                        html.Div(id="main-content", children=starting_content),
                    ],
                    size="xl",
                ),
            ],
        )
    ],
)


def init_dashboard(route):

    main_content, data_bund, data_raw = make_main_content("de")
    init_callbacks(app, data_raw)

    return app  # .server


def init_callbacks(app, data_raw):

    # DEBUG: display sunburst clickdata:
    # @app.callback(
    #     Output("location", "children"),
    #     Input("fig-sunburst", "clickData")
    # )
    # def update_location(clickdata):
    #     return(sunburst_location(clickdata))
    # ---------------------------------

    clientside_callback(
        """
        (switchOn) => {
        document.documentElement.setAttribute('data-mantine-color-scheme', switchOn ? 'dark' : 'light');
        return window.dash_clientside.no_update
        }
        """,
        Output("color-scheme-switch", "id"),
        Input("color-scheme-switch", "checked"),
    )

    clientside_callback(
        """
    (switchOn) => {
        // Return styles for DataTable
        if (switchOn) {
            return [
                {
                    backgroundColor: "#22223b",
                    color: "#f8f8f2",
                    fontWeight: "bold"
                },
                {
                    backgroundColor: "#2a2a40",
                    color: "#f8f8f2"
                }
            ];
        } else {
            return [
                {
                    backgroundColor: "#f8f9fa",
                    color: "#22223b",
                    fontWeight: "bold"
                },
                {
                    backgroundColor: "#ffffff",
                    color: "#22223b"
                }
            ];
        }
    }
    """,
        Output("table-textsearch", "style_header"),
        Output("table-textsearch", "style_data"),
        Input("color-scheme-switch", "checked"),
    )

    @app.callback(
        Output("language-store", "data"),
        Output("md-title", "children"),
        Input("language-switch", "checked"),
    )
    def update_language_store(language_switch_checked):
        language = "en" if language_switch_checked else "de"
        with open(dashapp_rootdir / "pks" / "src" / "prose" / "title.md", "r") as file:
            title_text = t(file.read(), language)
        return language, title_text

    @app.callback(
        Output("main-content", "children"),
        Input("language-store", "data"),
    )
    def update_main_content(language):
        content, _, _ = make_main_content(language)
        return content

    # Update Presence chart
    @app.callback(
        Output("fig-key-presence", "figure"),
        Input("fig-sunburst", "clickData"),
        Input("table-textsearch", "derived_viewport_data"),
        Input("tabs", "value"),
        Input("color-scheme-switch", "checked"),
        Input("language-store", "data"),
    )
    def update_presence_chart(
        keypicker_parent, table_data, active_tab, color_theme_switch, language
    ):
        """
        Presence chart - the pearl chains to the right that let you pick keys.
        """
        # Load the correct dataset for the selected language
        data_bund = data_bund_all[language]

        if active_tab == "keypicker":
            key = sunburst_location(keypicker_parent)

            if key == "root" or key is None:  # special case: parent is None
                child_keys = data_bund.loc[data_bund.parent.eq("------")].key.unique()
            else:
                child_keys = data_bund.loc[data_bund.parent == key].key.unique()
            selected_keys = child_keys

        elif active_tab == "textsearch":
            selected_keys = [element["key"] for element in table_data]

        colormap = {k: grp.color.iloc[0] for k, grp in data_bund.groupby("key")}

        fig = get_presence_chart(data_bund, selected_keys, colormap, language)
        template = "plotly_dark" if color_theme_switch else "plotly"
        fig.update_layout(template=template)

        return fig

    # Update key store
    # ----------------

    @app.callback(
        Output("keystore", "data", allow_duplicate=True),
        State("keystore", "data"),
        Input("fig-key-presence", "clickData"),
        prevent_initial_call=True,
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
        prevent_initial_call=True,
    )
    def update_keystore_from_timeseries(click_clearance, keyselection_old):
        if not click_clearance:
            return keyselection_old

        key_to_remove = click_clearance["points"][0]["x"][0:6]
        keyselection_new = keyselection_old
        keyselection_new.remove(key_to_remove)

        return keyselection_new

    # # Reset key store
    # # ----------------------------------

    # @app.callback(
    #     Output("keystore", "data", allow_duplicate=True),
    #     Input("reset", "n_clicks"),
    #     prevent_initial_call=True,
    # )
    # def reset_keystore(clickevent):
    #     return []

    # Update clearance timeseries from keystore
    # -----------------------------------------

    @app.callback(
        Output("fig-ts-clearance", "figure"),
        Input("keystore", "data"),
        Input("color-scheme-switch", "checked"),
        Input("language-store", "data"),
        prevent_initial_call=True,
    )
    def update_clearance_from_keystore(keylist, color_theme_switch, language):

        template = "plotly_dark" if color_theme_switch else "plotly"

        if keylist == []:
            return empty_plot(
                t(
                    f"Bis zu {MAXKEYS} Schlüssel/Delikte<br>"
                    "auswählen, um sie hier zu vergleichen!",
                    language,
                ),
                language,
            ).update_layout(template=template)

        # Load the correct dataset for the selected language
        data_bund = data_bund_all[language]

        # filter on selected keys:
        df_ts = data_bund.loc[data_bund.key.isin(keylist)].reset_index()

        # remove years in which cases = 0 (prevent div/0):
        df_ts = df_ts.loc[df_ts["count"].gt(0)]

        # prepare transformed columns for bar display:
        df_ts["unsolved"] = df_ts["count"] - df_ts.clearance
        df_ts["clearance_rate"] = df_ts.apply(
            lambda r: round(r["clearance"] / r["count"] * 100, 1), axis=1
        )

        # prepare long shape for consumption by plotting function:
        df_ts = pd.melt(
            df_ts,
            id_vars=[
                "key",
                "state",
                "year",
                "shortlabel",
                "label",
                "color",
                "clearance_rate",
                "count",
            ],
            value_vars=["clearance", "unsolved"],
        )

        fig = get_ts_clearance(df_ts, language)
        template = "plotly_dark" if color_theme_switch else "plotly"
        fig.update_layout(template=template)

        return fig

    # Update state timeseries from keystore
    # -------------------------------------

    @app.callback(
        Output("fig-ts-states", "figure"),
        Input("keystore", "data"),
        Input("color-scheme-switch", "checked"),
        Input("language-store", "data"),
        prevent_initial_call=True,
    )
    def update_states_from_keystore(keylist, color_theme_switch, language):

        template = "plotly_dark" if color_theme_switch else "plotly"

        if not keylist:
            return empty_plot(
                t(
                    "Schlüssel/Delikte auswählen, um hier<br>den Ländervergleich zu sehen!",
                    language,
                ),
                language,
            ).update_layout(template=template)

        data_raw = data_raw_all[language]

        # filter on selected keys:
        df_ts = data_raw.loc[data_raw.key.isin(keylist)].reset_index()

        fig = get_ts_states(df_ts, language)
        template = "plotly_dark" if color_theme_switch else "plotly"
        fig.update_layout(template=template)

        return fig
