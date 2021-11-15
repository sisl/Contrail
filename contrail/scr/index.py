'''Links up all of the individual pages that make up this Dash application.

Embeds the constant page components (navbar, UPDATE ACCORDINGLY) into every page
for the app. 

See module app.py for app specific server and rendering.
See module navbar.py for navbar specific layout and callbacks.
See module home_page.py for home page specific layout and callbacks.
See module settings_page.py for settings page specific layout and callbacks.

Callbacks:

    display_page(url.pathname) -> page_content.children

Functions:

Misc Variables:

'''

import dash

from dash import dcc
from dash import html

from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate

import dash_bootstrap_components as dbc

from app import app
from headers import navbar
from pages import home_page, settings_page

### Page container ###
page_container = html.Div(children=[
    # represents the URL bar, doesn't render anything
    dcc.Location(
        id='url',
        refresh=False,
    ),

    dcc.Store(id='memory-data', data={}),

    dcc.Store(id='ref-data', data={'ref_lat': 40.63993,
                                'ref_long': -73.77869,
                                'ref_alt': 12.7}),

    navbar.Navbar(),
    html.Br(),
    # content will be rendered in this element
    html.Div(id='page-content')
    ]
)

### Serves app layout ###
app.layout = page_container

### Assemble all possible layouts ###
app.validation_layout = html.Div(
    children = [
        page_container,
        home_page.layout,
        settings_page.layout,
    ]
)

### Update Page Container ###
@app.callback(Output('page-content','children'), Input('url','pathname'))
def display_page(pathname):
    if pathname == '/':
        return home_page.layout
    elif pathname == '/home':
        return home_page.layout
    elif pathname == '/settings':
        return settings_page.layout
    else:
        return '404'