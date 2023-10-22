import re
import logging

import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, callback

from src.data.parents import add_parent
from src.visualization.visualize import sunburst_location, get_colormap

data = pd.read_parquet("data/processed/pks.parquet")

# Katalog aus Daten erstellen

# wir müssen uns auf ein Jahr beschränken, um eine Katalog-Hierarchie zu erstellen,
# da die PKS über die Jahre hinweg Änderungen erfährt:
data = data.loc[(data.Jahr == 2021) & (data.Bundesland == "Bund")]

# Hierarchie aus Ziffern ableiten:
data = add_parent(data)
data = data.assign(one=1)

app = Dash(__name__)

hovertemplate = """
                <b>%{customdata[1]}</b><br><br>
                %{customdata[0]}<br>
                <extra>%{customdata[2]} Fälle</extra>"""
hovertemplate = re.sub(r"([ ]{2,})|(\n)", "", hovertemplate)

colormap = get_colormap(data)

keypicker = px.sunburst(data,
                        names='Schlüssel',
                        # values='Fallzahl',
                        parents='parent',
                        color='Schlüssel',
                        color_discrete_map=colormap,
                        hover_data=['Straftat', 'Schlüssel', 'Fallzahl'],
                        maxdepth=2,
                        height=700,
                        # width=700
                        )

keypicker.update_layout(margin=dict(t=15, r=15, b=15, l=15),
                        paper_bgcolor="#eeeeee")
keypicker.update_traces(hovertemplate=hovertemplate)
keypicker.update_coloraxes(showscale=False)

app.layout = html.Div([

    html.Div([
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

], style={"display": "flex",
          "flex-flow": "row wrap",
          "align-items": "center",  # rechter Plot vertikal zentriert
          })


@callback(Output("fig-timeseries", "figure"),
          Input("fig-keypicker", "clickData"))
def update_timeseries(input_json):

    key = sunburst_location(input_json)

    if key == "root" or key is None:
        child_keys = data.loc[data.parent.isna()].Schlüssel.values
    else:
        child_keys = data.loc[data.parent == key].Schlüssel.values

    # filter to the selected key and children:
    df_plot = data.loc[data.Schlüssel.isin(child_keys)]

    fig = px.bar(
        df_plot,
        y="Schlüssel",
        x="Fallzahl",
        color="Schlüssel",
        color_discrete_map=colormap,
        orientation="h",
        height=500,
        # width=700,
    )

    fig.update_layout(paper_bgcolor="#eeeeee")

    return (fig)


if __name__ == '__main__':
    app.run(debug=True)
