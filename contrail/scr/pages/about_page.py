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
        dbc.Card(className='card-about-page ml-2', children=[
            dbc.CardBody([
                dbc.Row([
                    html.H5(id='mit-license', children=["For detailed documentation on this tool, please visit our github repository:\n"], className="card-title-1"),
                ],
                justify='center',
                no_gutters=True),

                dbc.Row(className='mt-2', children=[
                    dcc.Link("https://github.com/sisl/Contrail", href='https://github.com/sisl/Contrail', target='_blank', className="github-link"),
                ],
                justify='center',
                no_gutters=True)
            ])
        ])
])