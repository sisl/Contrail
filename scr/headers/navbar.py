import dash_bootstrap_components as dbc
from dash import html

from app import app

DASHBOARD_LOGO = app.get_asset_url('dashboard_logo.png')

def Navbar():
    navbar = dbc.Navbar([
        html.A(
            dbc.Row(
                [
                    dbc.Col(html.Img(src=DASHBOARD_LOGO, height="30px")),
                    dbc.Col(dbc.NavbarBrand("Encounter GUI", className="ml-2")),
                ],
                align="center",
                no_gutters=True,
            ),
            href="/",
        ),
        # dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
        dbc.Collapse(id="navbar-collapse", children=[
            dbc.Row([
                dbc.Nav([
                    dbc.Col(dbc.NavItem(dbc.NavLink("Home", href="/home"))),
                    # dbc.Col(dbc.NavItem(dbc.NavLink("Features", href="#"))),
                    # dbc.Col(dbc.NavItem(dbc.NavLink("About", href="#")))
                    dbc.Col(dbc.NavItem(dbc.NavLink("Settings", href="/settings")))
                    ], className='navbar-nav')
                ],
                align='center',
                no_gutters=True)
            ], navbar=True, is_open=False, className="ml-auto flex-nowrap mt-3 mt-md-0",)],
        color='primary',
        dark=True)
    
    return navbar