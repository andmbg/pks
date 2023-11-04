import re
import logging

import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, callback

from src.data.import_data_pks import hierarchize_data
from src.visualization.visualize import sunburst_location, get_colormap, get_keypicker


def get_df_colors(year=2022):
    df = data_bund_hr.loc[data_bund_hr.year==year]
    colors = {k: grp.color.iloc[0] for k, grp in df.groupby("key")}
    return df, colors

    
data_raw = pd.read_parquet("data/processed/pks.parquet")
all_years = data_raw.year.unique()
data_bund = data_raw.loc[data_raw.state == "Bund"]

# For each year, produce an independent hierarchy. This is necessary, as the hierarchy relationships
# in the "crime catalogue" change across years, and contradictory relationships disable plotting:
data_bund_hr = pd.concat([hierarchize_data(grp) for _, grp in data_bund.groupby("year")])

app = Dash(__name__)

hovertemplate = """
                <b>%{customdata[1]}</b><br><br>
                %{customdata[0]}<br>
                <extra>%{customdata[2]} Fälle</extra>"""
hovertemplate = re.sub(r"([ ]{2,})|(\n)", "", hovertemplate)

# initial sunburst plot:
df, colors = get_df_colors(2022)
keypicker = get_keypicker(df=df, colormap=colors, hovertemplate=hovertemplate)

app.layout = html.Div([

    html.Div([
        dcc.Dropdown(
            id="datepicker",
            options=[{"label": y, "value": y} for y in all_years],
            value='2022',
            placeholder='Jahr',
        ),

        dcc.Graph(
            id='fig-keypicker',
            figure=keypicker
        ),

    ], style={"flex": 1}),

    html.Div([
        dcc.Graph(
            id='fig-timeseries'
        ),
    ], style={"flex": 1}),

    html.Div(id="show_clickData")

], style={"display": "flex",
          "flex-flow": "row wrap",
          "align-items": "center",  # rechter Plot vertikal zentriert
          })

@callback(Output("fig-keypicker", "figure"),
          Input("datepicker", "value"))
def update_key_picker(year):
    df, colors = get_df_colors(year)
    keypicker = get_keypicker(df=df, colormap=colors, hovertemplate=hovertemplate)
    return keypicker


@callback(Output("fig-timeseries", "figure"),
          Input("fig-keypicker", "clickData"),
          Input("datepicker", "value"),
          )
def update_ts_keys(input_json, year):

    key = sunburst_location(input_json)

    # just special syntax for when parent is None:
    if key == "root" or key is None:
        child_keys = data_bund_hr.loc[data_bund_hr.parent.isna()].key.values
    else:
        child_keys = data_bund_hr.loc[data_bund_hr.parent == key].key.values

    # filter to the selected key and children
    # note, we are using the children determined in the data_one df to filter
    # the overall dataframe!
    df_plot = data_bund_hr.loc[(data_bund_hr.key.isin(child_keys)) & (data_bund_hr.year == year)]

    fig = px.bar(
        df_plot,
        y="key",
        x="count",
        color="key",
        # color_discrete_map=colormap,
        orientation="h",
        height=500,
        # width=700,
    )

    fig.update_layout(paper_bgcolor="#eeeeee")

    return (fig)


@callback(Output("show_clickData", "children"),
          Input("fig-timeseries", "clickData"))
def update_clickData(input_json):

    return str(input_json)


if __name__ == '__main__':
    app.run(debug=True)
