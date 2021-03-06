import dash_bootstrap_components as dbc
from dash import html
from dash import dcc
import dash_daq as daq

import warnings
warnings.filterwarnings("ignore")

from app import app

DASHBOARD_LOGO = app.get_asset_url('contrail_logo.png')

def Navbar():
    navbar = dbc.Navbar([
        html.A(
            dbc.Row(
                [
                    dbc.Col(className='mt--1 ml-2 mr-2', children=[
                        html.Img(src=DASHBOARD_LOGO, height="30px")
                    ])
                ],
                align="center",
                no_gutters=True,
            ),
            href="/",
        ),
        dbc.Collapse(id="navbar-collapse", children=[
                dbc.Nav(className='navbar-nav ml-4', children=[
                    dbc.NavItem(dbc.NavLink("Home", href="/home")),
                    dbc.NavItem(dbc.NavLink("About", href="/about")),
                    dbc.NavItem(className='ml-5 mt-3-5', children=[
                        dcc.Loading(parent_className='loading_wrapper', 
                                children=[dcc.Store(id='generated-data', data={})],
                                type='circle',
                                color='#fff')
                        ])
                    ])
            ], 
            navbar=True, 
            is_open=False)],
        color='primary',
        dark=True)
    
    return navbar