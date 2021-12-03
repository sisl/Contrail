import dash_bootstrap_components as dbc
from dash import html
from dash import dcc

from app import app

DASHBOARD_LOGO = app.get_asset_url('dashboard_logo.png')

def Navbar():
    navbar = dbc.Navbar([
        html.A(
            dbc.Row(
                [
                    dbc.Col(html.Img(src=DASHBOARD_LOGO, height="30px")),
                    dbc.Col(dbc.NavbarBrand("CONTRAIL", className="ml-2")),
                ],
                align="center",
                no_gutters=True,
            ),
            href="/",
        ),
        dbc.Collapse(id="navbar-collapse", children=[
            dbc.Row([
                dbc.Nav([
                    dbc.Row([
                        dbc.Col(dbc.NavItem(dbc.NavLink("Home", href="/home"))),

                        # NOTE: the settings page is a work in progress, will allow users
                        # to set the actual path for uploading and downloading files
                        #dbc.Col(dbc.NavItem(dbc.NavLink("Settings", href="/settings"))),
                        
                        dbc.Col(dbc.NavItem(dbc.NavLink("About", href="/about"))),
                        dbc.Col([
                                dcc.Loading(parent_className='loading_wrapper', 
                                children=[dcc.Store(id='generated-data', data={})],
                                type='circle',
                                color='#fff',
                                className="col-auto offset-4 mt-4-5")
                            ])
                        ])
                    ], 
                    className='navbar-nav')
                ],
                align='left',
                no_gutters=True,
                className="flex-nowrap mt-3 mt-md-0")
            ], 
            navbar=True, 
            is_open=False)],
        color='primary',
        dark=True)
    
    return navbar