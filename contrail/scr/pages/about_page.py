import warnings
warnings.filterwarnings("ignore")

import dash
import dash_bootstrap_components as dbc

from dash import dcc
from dash import html



import dash_leaflet as dl

# Import Dash Instance #
from app import app

layout = html.Div([
    dbc.Container([

        dbc.Row([
            html.Div(id='mit-license', children=["INCLUDE IMPORTANT LICENSING INFO ABOUT THE PRODUCT HERE\n"]),
        ],
        align='left',
        justify='center',
        no_gutters=True),
        dbc.Row([
            html.Div(id='description', children=["any copyright stuff here\n"]),
        ],
        align='left',
        justify='center',
        no_gutters=True)
    ])
])