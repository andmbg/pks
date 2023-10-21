import re
import logging

import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, callback

from src.data.parents import add_level_parent
from src.visualization.dashboard_fns import sunburst_location

# import_data("data/raw", "data/processed/pks2.csv")
data = pd.read_csv("data/processed/pks.csv")

# Katalog aus Daten erstellen

# wir müssen uns auf ein Jahr beschränken, um eine Katalog-Hierarchie zu erstellen,
# da die PKS über die Jahre hinweg Änderungen erfährt:
data = data.loc[(data.Jahr == 2021) & (data.Bundesland == "Bund")]

# Hierarchie aus Ziffern ableiten:
data = add_level_parent(data)
data = data.assign(one=1)

app = Dash(__name__)

hovertemplate = """
                <b>%{customdata[1]}</b><br><br>
                %{customdata[0]}<br>
                <extra>%{customdata[2]} Fälle</extra>"""
hovertemplate = re.sub(r"([ ]{2,})|(\n)", "", hovertemplate)

keypicker = px.sunburst(data,
                        names='Schlüssel',
                        values='one',
                        parents='parent',
                        color='Schlüssel',
                        hover_data=['Straftat', 'Schlüssel', 'Fallzahl'],
                        maxdepth=2,
                        height=1000,
                        width=1000)

keypicker.update_layout(margin=dict(t=15, r=15, b=15, l=15))
keypicker.update_traces(hovertemplate=hovertemplate)
keypicker.update_coloraxes(showscale=False)

app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),

    html.Div(children='''
        Dash: A web application framework for your data.
    '''),

    dcc.Graph(
        id='fig-keypicker',
        figure=keypicker
    ),

    html.Div(id='clickdata'),

    dcc.Graph(
        id='fig-timeseries'
    ),

])


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
        x="Schlüssel",
        y="Fallzahl"
    )
    
    return(fig)


if __name__ == '__main__':
    app.run(debug=True)
