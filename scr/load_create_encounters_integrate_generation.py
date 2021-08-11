from logging import error, lastResort
from types import new_class
from typing import Container
import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
from dash_bootstrap_components._components.Col import Col
from dash_bootstrap_components.themes import SANDSTONE

import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from pkg_resources import resource_filename, resource_string

import plotly.express as px
import plotly.graph_objects as go

import pandas as pd
import numpy as np
import collections
from scipy.interpolate import PchipInterpolator

import json
import pymap3d as pm
import re

from read_file import *
import base64

#external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', dbc.themes.BOOTSTRAP]
#external_stylesheets = [dbc.themes.FLATLY]
app = dash.Dash(__name__)


def calculate_horizontal_vertical_speeds_df(df):
    dataf = df.copy()
    hor_speeds = []
    ver_speeds = []
    for ac_id in set(df['ac_id']):
        ac_id_data = df.loc[df['ac_id'] == ac_id]
        move_over_time = (np.roll(ac_id_data, -1, axis=0) - ac_id_data)[:-1]
        hor_speed = np.sqrt(move_over_time.xEast ** 2 + move_over_time.yNorth ** 2) / move_over_time['time'] * 3600
        hor_speeds += (np.append(0.0, round(hor_speed, 4))).tolist()
        ver_speed = move_over_time.zUp / move_over_time['time']
        ver_speeds += (np.append(0.0, round(ver_speed, 4))).tolist()
    dataf.loc[:, 'horizontal_speed'] = hor_speeds
    dataf.loc[:, 'vertical_speed'] = ver_speeds
    return dataf


M_TO_NM = 0.000539957; NM_TO_M = 1/M_TO_NM
FT_TO_M = .3048; M_TO_FT = 1/FT_TO_M
FT_TO_NM = FT_TO_M*M_TO_NM
NM_TO_FT = 1/FT_TO_NM 

COLOR_LIST = ['blue', 'orange', 'green', 'red', 'black', 'purple']
DASHBOARD_LOGO = app.get_asset_url('dashboard_logo.png')

map_iconUrl = "https://dash-leaflet.herokuapp.com/assets/icon_plane.png"
map_marker = dict(rotate=True, markerOptions=dict(icon=dict(iconUrl=map_iconUrl, iconAnchor=[16, 16])))
map_patterns = [dict(repeat='15', dash=dict(pixelSize=0, pathOptions=dict(color='#000000', weight=5, opacity=0.9))),
                dict(offset='100%', repeat='0%', marker=map_marker)]

graph_card_style = {'width':'30rem', 'height':'32rem'}

app.layout = html.Div([
    #   memory store reverts to the default on every page refresh
    dcc.Store(id='memory-data', data=[{}]),
    dcc.Store(id='session', data={'ref_lat': 40.63993,
                                  'ref_long': -73.77869,
                                  'ref_alt': 12.7}),

    dcc.Loading(parent_className='loading_wrapper', 
            children=[dcc.Store(id='generated-encounters', data={})],
            type='circle',
            style={'margin-top':'250px'}),   


    dbc.Navbar([
            html.A(
                dbc.Row(
                    [
                        dbc.Col(html.Img(src=DASHBOARD_LOGO, height="30px")),
                        dbc.Col(dbc.NavbarBrand("Encounter GUI", className="ml-2")),
                    ],
                    align="center",
                    no_gutters=True,
                ),
                href="http://127.0.0.1:8332/",
            ),
            # dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
            dbc.Collapse(id="navbar-collapse", children=[
                dbc.Row([
                    dbc.Nav([
                        dbc.Col(dbc.NavItem(dbc.NavLink("Home", href="http://127.0.0.1:8332/"))),
                        # dbc.Col(dbc.NavItem(dbc.NavLink("Features", href="#"))),
                        # dbc.Col(dbc.NavItem(dbc.NavLink("About", href="#")))
                        ], className='navbar-nav')
                    ],
                    align='center',
                    no_gutters=True)
                ], navbar=True, is_open=False, className="ml-auto flex-nowrap mt-3 mt-md-0",)],
        color='primary',
        dark=True),

    html.Br(),
    html.Br(),

    #load waypoints, gen and save buttons
    dbc.Container(
        dbc.Row([
            dbc.Col(
                html.Label([
                        dcc.Upload(id='load-waypoints', children = 
                        dbc.Button('Load Waypoints (.dat)', id='load-waypoints-button', n_clicks=0, outline=False, color="primary", className="ml-2")),#, style={'margin-left':'10px'}))
                    ]),
                width={"size": 'auto', "order": 1}),

            dbc.Col(dbc.Button('Generate Encounter Set', id='gen-encounters-button', n_clicks=0, outline=False, color="warning", className="ml-2"), #, style={'margin-left':'15px'}), 
                width={'size':'auto', 'order':2}),

            dbc.Col([
                    dbc.Button('Save Waypoints (.dat) or Model (.json)', id='save-button', n_clicks=0, outline=False, color="success", className="ml-2"), #, style={'margin-left':'130px'}),
                    dcc.Download(id='download-waypoints'),
                    dcc.Download(id='download-model')],
                    width={"size": 'auto', "order": 3}), #, 'offset':5}),

            
        ],
        align='start',
        no_gutters=True
        ),
        fluid=True

    ),

    html.Br(),

    # Encounter and AC ID dropdown menus
    dbc.Container(
        dbc.Row([
            dbc.Col(dcc.Dropdown(id='encounter-ids', placeholder="Select an encounter ID",  className='ml-2', multi=False), #, style={'margin-left':'4px'}),
                    width={"size": 2, "order": 1}),

            dbc.Col(dcc.Dropdown(id='ac-ids', placeholder="Select AC ID(s)", multi=True,  className='ml-2'),
                    width={"size": 2, "order": 2}),

           
            dbc.Col([
                html.Div(id='ref-card-div', children=[
                    dbc.Card(className='ml-6', children=[
                        dbc.CardBody(className='card-body-m-0', children=[
                            dbc.Row(className='', children=[
                                dbc.Col(html.Div(id='ref-point-output', className='ml-1', children=['Reference Point: ']), width='auto'),
                                dbc.Col(dbc.Button('Set Reference Point', id='set-ref-point', className='ml-7', n_clicks=0, outline=False, color='primary'), width='auto')
                            ], 
                            justify='between',
                            align='center')
                        ],
                        style={'padding':'.3rem'})
                    ],
                    color='light',
                    style={'width':'40.3rem', 'height':'3rem'})
                ])
            ],
            width={"size": 'auto', "order": 4, 'offset':2},
            align='right')  
        ],
        align='right',
        justify='center',
        no_gutters=True),
    fluid=True
    ),

    html.Br(),

    dbc.Container([
        dbc.Row([
            #dbc.Col(width=2),
            dbc.Col(className='', children=[  
                
                dbc.Container([
                    # navigation tabs
                    dbc.Row([

                        # dbc.ListGroup(id='tabs', children=[
                            
                        #     dbc.ListGroupItem(id='tab1', children="2d Graphs", active=True),
                        #     dbc.ListGroupItem(id='tab2', children="3d Graph"),
                        #     dbc.ListGroupItem(id='tab4', children="Log Histograms"),
                        # ], horizontal=True,
                        #    className="mb-2", style={'width':'100%'})

                        html.Div([
                            dbc.Tabs(id="tabs",
                                    children=[
                                        dbc.Tab(id='tab-1', tab_id='tab-1', label='2d Graphs'), # label_style={'color':'#2c3e50'}), #, style={'height':'1rem', 'line-height':'.5rem'}),
                                        dbc.Tab(id='tab-2',tab_id='tab-2', label='3d Graph'),#  tab_style={'background':'#2c3e50'}), #, style={'height':'1rem', 'line-height':'.5rem'}),
                                        #dcc.Tab(id='tab3', label='Map', value='tab-3'),
                                        dbc.Tab(id='tab-4', tab_id='tab-4',label='Log Histograms') #, style={'height':'1rem', 'line-height':'.5rem', 'width':'10rem'}),
                                    ],
                                    active_tab='tab-1'),
                        ])
                    ],
                    no_gutters=True),
                
                    dbc.Row(className='', children=[
                        dbc.Col(className='col-scrollable', children=[
                            html.Div(id='tab-1-graphs', children= [
                                dbc.Container([    
                                    dbc.Row([ 
                                        dbc.Col(className='pr-2', children=[
                                            dbc.Card(className='card-small-graphs', children=[
                                                dbc.CardBody([
                                                    dbc.Row([
                                                        dbc.Col(html.H5("xEast vs yNorth", className="card-title-1"))
                                                    ],justify='center'),

                                                    dbc.Row([
                                                        dbc.Col(dcc.Graph(id='editable-graph-xy-slider', figure=px.line()))
                                                    ],justify='center')
                                                ])
                                            ], 
                                            color='primary',
                                            style=graph_card_style),
                                        ], 
                                        width='auto'),

                                        dbc.Col(
                                            dbc.Card([
                                                dbc.CardBody([
                                                    dbc.Row([
                                                        dbc.Col(html.H5("Time vs Horizontal Distance", className="card-title-1"))
                                                    ],
                                                    justify='center'),

                                                    dbc.Row([
                                                        dbc.Col(dcc.Graph(id='editable-graph-tdistxy-slider', figure=px.line()))
                                                    ],
                                                    justify='center')
                                                ])
                                            ],
                                            color='primary',
                                            style=graph_card_style
                                        ),
                                        width='auto')
                                    ], 
                                    no_gutters=True)
                                ], 
                                fluid=True),

                                html.Br(),

                                dbc.Container([
                                    dbc.Row([
                                        dbc.Col(className='pr-2', children=[
                                            dbc.Card([
                                                dbc.CardBody([
                                                    dbc.Row([
                                                        dbc.Col(html.H5("Time vs zUp", className="card-title-1"))
                                                    ],justify='center'),

                                                    dbc.Row([
                                                        dbc.Col(dcc.Graph(id='editable-graph-tz-slider', figure=px.line(), className='six columns'))
                                                    ],justify='center')
                                                ])
                                            ], color='primary',
                                            style=graph_card_style),
                                        ], width='auto'),
                                        
                                        dbc.Col(children=[
                                            dbc.Card([
                                                dbc.CardBody([
                                                    dbc.Row([
                                                        dbc.Col(html.H5("Time vs Vertical Distance", className="card-title-1"))
                                                    ],justify='center'),

                                                    dbc.Row([
                                                        dbc.Col(dcc.Graph(id='editable-graph-tdistz-slider', figure=px.line(), className='two columns'))
                                                    ],justify='center')
                                                ])
                                            ], color='primary',
                                            style=graph_card_style),
                                        ], width='auto')
                                    ], no_gutters=True)
                                ], fluid=True),

                                html.Br(),

                                dbc.Container([
                                    dbc.Row([
                                        dbc.Col(className='pr-2', children=[
                                            dbc.Card([
                                                dbc.CardBody([
                                                    dbc.Row([
                                                        dbc.Col(html.H5("Time vs Horizontal Speed", className="card-title-1"))
                                                    ],justify='center'),

                                                    dbc.Row([
                                                        dbc.Col(dcc.Graph(id='editable-graph-tspeedxy-slider', figure=px.line()))
                                                    ],justify='center')
                                                ])
                                            ], color='primary',
                                            style=graph_card_style),
                                        ], width='auto'),

                                        dbc.Col(children=[
                                            dbc.Card([
                                                dbc.CardBody([
                                                    dbc.Row([
                                                        dbc.Col(html.H5("Time vs Vertical Speed", className="card-title-1"))
                                                    ],justify='center'),

                                                    dbc.Row([
                                                        dbc.Col(dcc.Graph(id='editable-graph-tspeedz-slider', figure=px.line(), className='ten columns'))
                                                    ],justify='center')
                                                ])
                                            ], color='primary',
                                            style=graph_card_style),
                                        ], width='auto')

                                    ], no_gutters=True)
                                ], fluid=True)

                            ], style={'width':'63rem', 'height':'20rem'}),

                            html.Div(id='tab-2-graphs', children=[
                                dbc.Row([
                                    dbc.Col(className='pr-4', children=[
                                        dbc.Card([
                                                dbc.CardBody([
                                                    dbc.Row([
                                                        dbc.Col(html.H5("xEast vs yNorth vs zUp", className="card-title-1"))
                                                    ],justify='center'),

                                                    dbc.Row([
                                                        dbc.Col(dcc.Graph(id='editable-graph-xyz-slider', figure=px.line_3d()))
                                                    ],justify='center')
                                                ])
                                            ], 
                                            color='primary',
                                            style={'width':'60.5rem', 'height':'48rem'}
                                        )
                                    ])
                                ], 
                                no_gutters=True,
                                style={'margin-left':'15px'})
                            ], 
                            style={'display':'none'}),

                            html.Div(id='tab-4-graphs', children=[
                                dbc.Row([
                                    dbc.Col(className='pr-2', children=[
                                        dbc.Card([
                                            dbc.CardBody([
                                                dbc.Row([
                                                    dbc.Col(html.H5("AC 1: xEast vs yNorth", className="card-title-1"))
                                                ],justify='center'),

                                                dbc.Row([
                                                    dbc.Col(dcc.Graph(id='log-histogram-ac-1-xy', figure=px.density_heatmap())) #'data':[go.Figure(data=go.Heatmap(x=[],y=[],z=[], colorscale=[[0, "#FFFFFF"], [1, "#19410a"]]), layout=go.Layout(title='AC 1: xEast yNorth Count'))]}
                                                ],justify='center')
                                            ])
                                        ],
                                        color='primary',
                                        style={'width':'30rem', 'height':'33rem'}),
                                    ],
                                    width='auto'),

                                    dbc.Col(className='pr-2', children=[
                                        dbc.Card([
                                            dbc.CardBody([
                                                dbc.Row([
                                                    dbc.Col(html.H5("AC 1: Time vs zUp", className="card-title-1"))
                                                ],justify='center'),

                                                dbc.Row([
                                                    dbc.Col(dcc.Graph(id='log-histogram-ac-1-tz', figure=px.density_heatmap()))
                                                ],justify='center')
                                            ])
                                        ],
                                        color='primary',
                                        style={'width':'30rem', 'height':'33rem'}),
                                    ], 
                                    width='auto')
                                ],
                                no_gutters=True,
                                style={'margin-left':'15px'}),

                                html.Br(),

                                dbc.Row([
                                    dbc.Col(className='pr-2', children=[
                                        dbc.Card([
                                            dbc.CardBody([
                                                dbc.Row([
                                                    dbc.Col(html.H5("AC 2: xEast vs yNorth", className="card-title-1"))
                                                ],justify='center'),

                                                dbc.Row([
                                                    dbc.Col(dcc.Graph(id='log-histogram-ac-2-xy', figure=px.density_heatmap())) #'data':[go.Figure(data=go.Heatmap(x=[],y=[],z=[], colorscale=[[0, "#FFFFFF"], [1, "#19410a"]]), layout=go.Layout(title='AC 1: xEast yNorth Count'))]},
                                                ],justify='center')
                                            ])
                                        ],
                                        color='primary',
                                        style={'width':'30rem', 'height':'33rem'}),
                                    ],
                                    width='auto'),

                                    dbc.Col(className='pr-2', children=[
                                        dbc.Card([
                                            dbc.CardBody([
                                                dbc.Row([
                                                    dbc.Col(html.H5("AC 2: Time vs zUp", className="card-title-1"))
                                                ],justify='center'),

                                                dbc.Row([
                                                    dbc.Col(dcc.Graph(id='log-histogram-ac-2-tz', figure=px.density_heatmap()))
                                                ],justify='center')
                                            ])
                                        ],
                                        color='primary',
                                        style={'width':'30rem', 'height':'33rem'}),
                                    ],
                                    width='auto')
                                ],
                                no_gutters=True,
                                style={'margin-left':'15px'})
                            ], 
                            style={'display':'none'})
                        ])
                    ],
                    style={'margin-left':'-2rem'}),

                    html.Br(),
                    html.Br(),
                    dbc.Row([
                        dbc.Col([
                                html.Div(id='slider-bar-div', children=[
                                    dbc.Container(
                                        dbc.Row([
                                            dbc.Col([
                                                html.Div(id='slider-drag-output', children='Time: ', style={'font-size': 15})
                                            ], width={'size':1, 'order':1}),
                                            dbc.Col([
                                                html.Div([dcc.Slider(id='slider', value=0, step=1)], id='slider-container', style={'width': '800px'})
                                            ], width={'size':'auto', 'order':2})
                                        ], 
                                        align='start',
                                        no_gutters=True
                                    ), 
                                    fluid=True)
                                ]),
                        ])
                    ])
                ], 
                fluid=True),
            ], 
            width='auto'),
            #style={'margin-left':'-20px'}),
            
            dbc.Col(className='pl-3', children=[
                html.Div(id='map-create-mode-div', children=[
                    dbc.Row([
                            dbc.Card(id='map-create-card', children=[
                                dbc.CardBody([
                                    # dbc.Row([
                                    #     #dbc.Col(html.H5("", className="card-title", style={'text-align':'center', 'color':'white'}), width='auto'),
                                    #     # dbc.Col(dbc.Button('Enter Create Mode', id='create-mode', n_clicks=0, color='light'),
                                    #     #     width={'size':'auto'}),
                                    #     # dbc.Col(dbc.Button('Exit Create Mode', id='exit-create-mode', n_clicks=0, style={'display':'none'}),
                                    #     #     width={'size':3, 'offset':0}),
                                    #     dbc.Col(dbc.Button('Set Reference Point', id='set-ref-point', n_clicks=0, outline=False, color='light', className="mr-0", style={'margin-bottom':'5px', 'width':'130px'}), 
                                    #         width={'size':'auto', 'offset':0})
                                    # ], 
                                    # align='left',
                                    # no_gutters=True,
                                    # style={'height':'1rem'}),

                                    dbc.Row([
                                        dbc.Col(dl.Map(id='map', children=[
                                                    dl.TileLayer(), 
                                                    dl.LayerGroup(id='polyline-layer', children=[]),
                                                    dl.LayerGroup(id='marker-layer', children=[], attribution='off')], 
                                                    doubleClickZoom=False,
                                                    style={'width':'37.7rem', 'height':'28rem'}))
                                    ],justify='center'),

                                    dbc.Row([
                                        dbc.Col([
                                            dbc.Button('Enter Create Mode', id='create-mode', n_clicks=0, color='warning', style={'margin-top':'10px'}),
                                            dbc.Button('Exit Create Mode', id='exit-create-mode', n_clicks=0, style={'display':'none', 'margin-top':'10px'})
                                        ],
                                        width={'size':'auto'}),
                                        # dbc.Col(dbc.Button('Exit Create Mode', id='exit-create-mode', n_clicks=0, style={'display':'none', 'margin-top':'10px'}),
                                        #     width={'size':5, 'offset':0}),
                                        # dbc.Col(dbc.Button('Set Reference Point', id='set-ref-point', n_clicks=0, outline=False, color='light', className="pl-0", style={'margin-top':'10px', 'width':'130px'}), 
                                        #     width={'size':'auto', 'offset':0}),
                                        dbc.Card(id='create-mode-card', children=[
                                            # html.H5("CREATE MODE", className="card-title", style={'text-align':'center', 'color':'primary', 'margin-top':'5px'}),
                                            # html.Hr(),
                                            dbc.CardBody([
                                                dbc.Row([
                                                    dbc.Col([
                                                        dbc.Button('Start New Nominal Path', id='create-new-button', className='ml-2', n_clicks=0, color='primary',# outline=True,
                                                            style={'display':'none'}), 
                                                    ], width=5),

                                                    # dbc.Col([
                                                    #     html.Div(id='create-mode-nom-path-div', children=[
                                                    #         html.Div(id='ac-input-title', children='Input AC ID:'),
                                                    #         dbc.Input(id="ac-index", type="number", placeholder="AC ID", debounce=False, min=1), 
                                                    #         html.Div(id='time-interval-title', children='Set Time Interval (s):'),
                                                    #         dbc.Input(id='time-interval-input', type='number', placeholder='1.0s',
                                                    #             debounce=True, pattern=u"^(\d+\.?\d?)$", value=1.0),
                                                    #         html.Div(id='zUp-title', children='Set zUp (ft):'),
                                                    #         dbc.Input(id='create-mode-zUp-input', type='number', placeholder='12ft',
                                                    #             debounce=True, pattern=u"^(\d+\.?\d?)$", value=12.0),
                                                    #     ], style={'display':'none'}),
                                                    # ]), 
                                                    # align='start',
                                                    # width=3),

                                                    dbc.Col([dbc.Button('Save Nominal Path', id='end-new-button', className='ml-4', n_clicks=0, color='primary', style={'display':'none'})
                                                    ], width=4)
                                                ],
                                                justify='between'),

                                                html.Br(),
                                                html.Hr(),

                                                html.Div(id='create-mode-nom-path-div', children=[
                                                    dbc.Row(className='ml-0', children=[
                                                        dbc.Col([
                                                            html.Div(id='ac-input-title', children='Input AC ID:'),
                                                            dbc.Input(id="ac-index", type="number", placeholder="AC ID", debounce=False, min=1) 
                                                        ]), 
                                                        dbc.Col([
                                                            html.Div(id='time-interval-title', children='Set Time Interval (s):'),
                                                            dbc.Input(id='time-interval-input', type='number', placeholder='1.0s',
                                                                debounce=True, pattern=u"^(\d+\.?\d?)$", value=1.0)
                                                        ]),
                                                        dbc.Col([
                                                            html.Div(id='zUp-title', children='Set zUp (ft):'),
                                                            dbc.Input(id='create-mode-zUp-input', type='number', placeholder='12ft',
                                                                debounce=True, pattern=u"^(\d+\.?\d?)$", value=12.0)
                                                        ])
                                                    ])
                                                ], style={'display':'none'}),

                                            ], style={'padding':'.5rem'})
                                        ], color='light',
                                        style={'width':'38rem', 'height':'10rem', 'margin-left':'15px', 'margin-top':'10px', 'display':'none'})
                                    ])
                                ]),
                            ],
                            color='primary',
                            style={'width':'40.3rem', 'height':'33rem'}
                        )
                    ])
                ], style={'display':'block'}),

                html.Br(),

                html.Div(id='data-table-div', children =[
                    dbc.Row([
                        dbc.Card(id='data-table-card', children=[
                            dbc.CardBody([
                                dbc.Row([
                                    dbc.Col(dbc.Button('Update Speeds', id='update-speeds-button', n_clicks=0, color='light'),
                                        width=3),
                                    dbc.Col(dbc.Button('Add Rows', id='add-rows-button', n_clicks=0, color='light'),
                                        width=3),
                                    dbc.Col(dbc.Button('DONE', id='done-add-rows-button', n_clicks=0, color='light', style={'display':'none'}),
                                        width=3), #, 'color':'white', 'background-color': '#5cb85c', 'border-color': '#5cb85c'}),)
                                ], 
                                align='right',
                                no_gutters=True),

                                dbc.Row([
                                    html.Div([dash_table.DataTable(
                                        id = 'editable-table',
                                        columns = [
                                        #{"name": 'Encounter ID', "id": 'encounter_id', 'editable': True, 'type':'numeric'},  # 'sortable': True
                                            {"name": 'AC ID', "id": 'ac_id', 'editable': True, 'type':'numeric'},
                                            {"name": 'Time (s)', "id": 'time', 'editable': True, 'type':'numeric', 'format': {'specifier': '.2~f'}},
                                            {"name": 'xEast (NM)', "id": 'xEast', 'editable': True, 'type':'numeric', 'format': {'specifier': '.2~f'}},
                                            {"name": 'yNorth (NM)', "id": 'yNorth', 'editable': True, 'type':'numeric', 'format': {'specifier': '.2~f'}},
                                            {"name": 'zUp   (ft)', "id": 'zUp', 'editable': True,'type':'numeric', 'format': {'specifier': '.2~f'}},
                                            {"name": 'Horizontal Speed (kt)', "id": 'horizontal_speed', 'editable': False, 'type':'numeric', 'format': {'specifier': '.2~f'}},
                                            {"name": 'Vertical Speed (ft/min)', "id": 'vertical_speed', 'editable': False, 'type':'numeric', 'format': {'specifier': '.2~f'}}],
                                        editable = True,
                                        row_deletable = True,
                                        data=[], #{'encounter_id':None, 'ac_id':None, 'time':None, 'xEast':None, 'yNorth':None, 'zUp':None, 'horizontal_speed':None, 'vertical_speed':None}],
                                        style_table={'width': '38.5rem', 'height': '35rem', 'display': "block", 'margin-left':'10px', 'overflowY': 'scroll'},
                                        style_cell={'fontSize':11, 'height':'auto', 'whiteSpace':'normal'})], 
                                    style={'margin-top':'10px'})
                                ])

                            ]),
                        ], 
                        color='primary',
                        style={'width':'40.3rem', 'height':'10rem'})
                    ])
                ], style={'display':'block'})

            ], 
            width='auto',
            style={'margin-left':'0px'})
        ], 
        no_gutters=True,
        style={'margin-left':'-10px'})
    ], 
    fluid=True),
    
    # slider bar
    # html.Div(id='slider-bar-div', children=[
    #     dbc.Container(
    #         dbc.Row([
    #             dbc.Col([
    #                 html.Div(id='slider-drag-output', children='Time: ', style={'font-size': 15})
    #             ], width={'size':1, 'order':1}),
    #             dbc.Col([
    #                 html.Div([dcc.Slider(id='slider', value=0, step=1)], id='slider-container', style={'width': '800px'})
    #             ], width={'size':'auto', 'order':2})
    #         ], 
    #         align='start',
    #         no_gutters=True
    #     ), 
    #     fluid=True)
    # ]),

    # pop up window for setting reference point
    html.Div(id='ref-modal-div', children=[
        dbc.Modal([
            dbc.ModalHeader("Edit Reference Point"),
            html.Br(),
            html.Br(),
            dbc.Container([
                dbc.Row([
                    dbc.Col([
                        dbc.Row([
                            dbc.Input(id='ref-point-input', type='text', 
                            placeholder=f'latitude / longitutde / altitude: 0.0{chr(176)}/0.0{chr(176)}/0.0ft',
                            debounce=True,
                            pattern=u"^(\-?\d+\.\d+?)\/(\-?\d+\.\d+?)\/(\d+\.\d+?)$",
                            style={"margin-left": "15px"}),
                        ])
                        # dbc.Row([
                        #     html.Div(id='ref-point-output-2', children=['Reference Point: '],
                        #         style={"margin-left": "15px", "margin-top": "10px", 'font-size': '1em', 'display':'block'}),
                        # ])
                        
                    ], width=10),
                    dbc.Col([
                        dbc.Button('Clear', id='clear-ref-button', color='danger', n_clicks=0)
                    ], width=1)
                ])
            ], fluid=True),

            html.Br(),
            html.Br(),
            dbc.ModalFooter(children= [
                dbc.Button("CLOSE", id="close-ref-modal-button"),
                #dbc.Spinner(size='md', spinnerClassName='ml-auto', children=[html.Div(id='gen-spinner-output', children='nothin')]), #html.Div(id='gen-spinner-output')),
                dbc.Button("SET REF POINT", id="set-ref-button", color='success', className="ml-auto")
                ]
            ),
        ],
        id='ref-point-modal', is_open=False, size="md",
        backdrop='static',  # Modal to not be closed by clicking on backdrop
        centered=True,  # Vertically center modal 
        keyboard=True,  # Close modal when escape is pressed
        fade=False)
        #style={"max-width": "none", "width": "50%"})
    ]),


    # pop-up window for generation
    html.Div(id='gen-modal-div', children=[
        dbc.Modal([
            dbc.ModalHeader("Generate an Encounter Set"),

            html.Br(),
            html.Div([
                html.Label([
                    dcc.Upload(id='load-model', children = 
                            dbc.Button('Load Model (.json)', id='load-model-button', n_clicks=0))
                ])
            ], style={"margin-left": "20px", 'display':'inline-block'}),
            html.Br(),
            dcc.Markdown(("---")),
            html.Br(),
            
            # mean (nominal paths)
            dcc.Markdown(("""Mean:"""), style={'font-weight': 'bold', "margin-left": "20px"}),
            html.Div([
                html.Div([
                    dcc.Markdown(("""Select an Encounter:"""), style={"margin-left": "20px"}),
                    dcc.Dropdown(id='nominal-path-enc-ids', 
                        options=[], multi=False, value=[],
                        style={"margin-left": "10px", "width": "105%"}),
                ], style={"margin-left": "20px"}),
                html.Div([
                    dcc.Markdown(("""Select at least one Nominal Path:"""), style={"margin-left": "20px"}),
                    dcc.Dropdown(id='nominal-path-ac-ids', 
                        options=[], multi=True, value=[],
                        style={"margin-left": "12px", "width": "100%"}),
                ], style={"margin-left": "30px"})
            ], className  = 'row'),
            

            # covariance
            html.Br(),
            dcc.Markdown(("""Covariance:"""), style={'font-weight': 'bold', "margin-left": "20px"}),
            html.Div([
                dcc.Markdown(("""Select one type:"""), style={"margin-left": "5px"}),
                dcc.RadioItems(id='cov-radio', options=[
                    {'label': 'Diagonal', 'value': 'cov-radio-diag'},
                    {'label': 'Exponential Kernel', 'value': 'cov-radio-exp'}],
                    value='cov-radio-exp',
                    inputStyle={"margin-right": "5px"},
                    labelStyle={'display': 'inline-block', "margin-right": "10px"},
                    style={"margin-left": "15px"}),
            ], style={"margin-left": "20px"}, className  = 'row'),
            
            html.Div([
                html.Div([
                    dcc.Markdown(("""Enter Parameters:"""), style={"margin-left": "20px"}),
                    dbc.Row([
                        dbc.Col(dbc.Input(id='diag-sigma-input-hor', type='text', placeholder='default sigma_hor = 0.05',
                        debounce=True, pattern=u"^(0?\.?\d+)$", value=0.05),
                        width=2),
                        dbc.Col(dbc.Input(id='diag-sigma-input-ver', type='text', placeholder='default sigma_ver = 10.0',
                        debounce=True, pattern=u"^(0?\.?\d+)$", value=10.0),
                        width=2)
                    ], 
                    no_gutters=True,
                    style={'margin-left':'20px'})

                ], style={"margin-left": "20px"})
            ], id='cov-diag-input-container', style={"display":"none"}, className  = 'row'),

            html.Div([
                html.Div([
                    dcc.Markdown(("""Enter Parameters:"""), style={"margin-left": "20px"}),
                    dbc.Row([
                        dbc.Col(dbc.Input(id='exp-kernel-input-a', type='text', placeholder='param_a',
                            debounce=True, pattern=u"^(0?\.?\d+)$", value=15.0),
                            width=2),
                        dbc.Col(dbc.Input(id='exp-kernel-input-b', type='text', placeholder='param_b',
                            debounce=True, pattern=u"^(0?\.?\d+)$", value=1.0),
                            width=2),
                        dbc.Col(dbc.Input(id='exp-kernel-input-c', type='text', placeholder='param_c',
                            debounce=True, pattern=u"^(0?\.?\d+)$", value=100.0),
                            width=2)
                    ], 
                    no_gutters=True,
                    style={"margin-left": "20px"})

                ], style={"margin-left": "20px"}),
            ], id='cov-exp-kernel-input-container', style={"display":"block"}, className  = 'row'), #, "margin-bottom":"10px"})

            
            # number of encounter sets to generate
            html.Br(),
            dcc.Markdown(("""Number of Encounters to Generate:"""), style={'font-weight': 'bold',"margin-left": "20px"}),
            dbc.Input(id='num-encounters-input', type='text', placeholder='',
                debounce=True,# value=100,
                pattern=u"^(\d+)$",
                style={"margin-left": "20px", "width": "40%"}),
            
            
            # generation progress bar
            html.Br(),

            html.Br(),

            dbc.ModalFooter(children= [
                dbc.Button("CLOSE", id="close-button"),
                #dbc.Spinner(size='md', spinnerClassName='ml-auto', children=[html.Div(id='gen-spinner-output', children='nothin')]), #html.Div(id='gen-spinner-output')),
                dbc.Button("GENERATE", id="generate-button", color='success', className="ml-auto")
                ]
            ),
        ],
        id='gen-modal', is_open=False, size="lg",
        backdrop=True,  # Modal to not be closed by clicking on backdrop
        centered=True,  # Vertically center modal 
        keyboard=True,  # Close modal when escape is pressed
        fade=True,
        style={"max-width": "none", "width": "50%"})
    ]),

    # pop up window for saving
    html.Div(id='save-div', children=[
        dbc.Modal([
            dbc.ModalHeader("Save Generated Encounter Set", style={'font-size':'1000px'}), # className='w-100'),
            html.Br(),
            html.Div([
                dcc.Markdown(("""Select Files to Save: """), style={'font-size': '1em', "margin-left": "5px"}),
                dcc.Checklist(id='file-checklist', options=[
                    {'label': 'Generated Waypoints (.dat)', 'value': 'dat-item'},
                    {'label': 'Model (.json)', 'value': 'json-item'}],
                    value=['dat-item'],
                    inputStyle={"margin-right": "8px"},
                    labelStyle={'display': 'block',"margin-right": "10px", 'margin-top':'3px', 'font-size': '1em'},
                    style={"margin-left": "10px"}),
            ], style={"margin-left": "20px"}, className  = 'row'),
            html.Br(),
            html.Div([
                html.Div([
                    dcc.Markdown(("""Save waypoints as:"""), style={"margin-left": "20px", "font-size":"1em"}),
                    dcc.Input(id='save-dat-filename', type='text', placeholder='filename.dat',
                        debounce=True, pattern=u"\w+\.dat", value='generated_waypoints.dat',
                        style={"margin-left": "20px", "width": "70%", "font-size":"1em"}),
                ], style={"margin-left": "20px"})
            ], id='save-dat-div', className  = 'row', style={'display':'none'}),
            html.Div([
                html.Div([
                    dcc.Markdown(("""Save model as:"""), style={"margin-left": "20px", "font-size":"1em", "margin-top":"5px"}),
                    dcc.Input(id='save-json-filename', type='text', placeholder='filename.json',
                        debounce=True, pattern=u"\w+\.json", value='generation_model.json',
                        style={"margin-left": "20px", "width": "70%", "font-size":"1em"}),
                ], style={"margin-left": "20px", "margin-top":"15px"})
            ], id='save-json-div', className='row', style={'display':'none'}),
            html.Br(),
            dbc.ModalFooter(children= [
                dbc.Button("CLOSE", id="close-save-button"),
                dbc.Button("SAVE", id="save-filename-button", className="ml-auto")
                ]
            ),
        ],
        id='save-modal', is_open=False, size="lg",
        backdrop=True,  # Modal to not be closed by clicking on backdrop
        centered=True,  # Vertically center modal 
        keyboard=True,  # Close modal when escape is pressed
        fade=True,
        style={"max-width": "none", "width": "50%"})
    ]),

    # style
    html.Br(), html.Br(),
]) 

print('\n*****START OF CODE*****\n')


#########################################################################################
#########################################################################################

def interpolate_df_time(df, ac_ids_selected):
    df_interp = pd.DataFrame()
    min_values_list, max_values_list = [], []

    for ac_id in ac_ids_selected:
        df_ac = df.loc[df['ac_id'] == ac_id]
        df_ac = df_ac.apply(pd.to_numeric, errors='coerce').fillna(0).sort_values('time')
        # print('df_ac[time]', df_ac['time'])

        df_ac_interp = pd.DataFrame()
        df_ac_interp['time'] = np.arange(int(min(df_ac['time'])), int(max(df_ac['time'])+1))
        df_ac_interp['ac_id'] = [ac_id]*len(df_ac_interp['time'])
        df_ac_interp['xEast'] = PchipInterpolator(df_ac['time'], df_ac['xEast'])(df_ac_interp['time'])
        df_ac_interp['yNorth'] = PchipInterpolator(df_ac['time'], df_ac['yNorth'])(df_ac_interp['time'])
        df_ac_interp['zUp'] = PchipInterpolator(df_ac['time'], df_ac['zUp'])(df_ac_interp['time'])
        if 'horizontal_speed' in df_ac.columns:
            df_ac_interp['horizontal_speed'] = PchipInterpolator(df_ac['time'], df_ac['horizontal_speed'])(df_ac_interp['time'])
        if 'vertical_speed' in df_ac.columns:
            df_ac_interp['vertical_speed'] = PchipInterpolator(df_ac['time'], df_ac['vertical_speed'])(df_ac_interp['time'])

        df_interp = df_interp.append(df_ac_interp, ignore_index=True)   

        if 'horizontal_speed' in df_ac.columns:
            min_values_list.append([min(df_ac_interp['time']), min(df_ac_interp['xEast']), min(df_ac_interp['yNorth']), min(df_ac_interp['zUp']), \
                min(df_ac['horizontal_speed']), min(df_ac['vertical_speed'])])
            max_values_list.append([max(df_ac_interp['time']), max(df_ac_interp['xEast']), max(df_ac_interp['yNorth']), max(df_ac_interp['zUp']), \
                max(df_ac_interp['horizontal_speed']), max(df_ac_interp['vertical_speed'])])
        else:
            min_values_list.append([min(df_ac_interp['time']), min(df_ac_interp['xEast']), min(df_ac_interp['yNorth']), min(df_ac_interp['zUp'])])
            max_values_list.append([max(df_ac_interp['time']), max(df_ac_interp['xEast']), max(df_ac_interp['yNorth']), max(df_ac_interp['zUp'])])
            
    return df_interp, min_values_list, max_values_list
    
    
@app.callback(Output('slider-drag-output', 'children'),
              Output('slider', 'value'),
              Output('editable-graph-xy-slider', 'figure'),
              Output('editable-graph-tz-slider', 'figure'),
              Output('editable-graph-tspeedxy-slider', 'figure'),
              Output('editable-graph-tspeedz-slider', 'figure'),
              Output('editable-graph-xyz-slider', 'figure'),
              Output('editable-graph-tdistxy-slider', 'figure'),
              Output('editable-graph-tdistz-slider', 'figure'),
              Output('slider', 'min'),
              Output('slider', 'max'),
              Input('slider', 'value'),
              Input('editable-table', 'data'),
              State('encounter-ids', 'value'),
              State('ac-ids', 'value'),
              State('add-rows-button', 'n_clicks'),
              State('done-add-rows-button', 'n_clicks'), 
             )
def update_graph_slider(t_value, data, encounter_id_selected, ac_ids_selected, add_rows_n_clicks, done_add_rows_n_clicks):
    if data is None:
        return dash.no_update
    if add_rows_n_clicks > 0 and done_add_rows_n_clicks == 0:
        return dash.no_update

    if data == [] or encounter_id_selected is None or encounter_id_selected == [] or ac_ids_selected == []:
        return 'Time: ', 0, {}, {}, {}, {}, {}, {}, {}, 0, 100
    
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if ctx == 'editable-table' or ctx == 'slider':

        df = pd.DataFrame(data)        
        df_interp, min_values_list, max_values_list = interpolate_df_time(df, ac_ids_selected)
        
        if ctx == 'editable-table':
            t_value = np.min(np.array(min_values_list), axis=0)[0]

        # plot 2D/3D slider graphs
        fig_xy = px.line()#title='xEast vs yNorth')
        fig_tz = px.line()#title='Time vs zUp')
        fig_tspeedxy = px.line()#title='Time vs Horizontal Speed')
        fig_tspeedz = px.line()#title='Time vs Vertical Speed')
        fig_xyz = px.line_3d()#title='xEast vs yNorth vs zUp')
        fig_tdistxy = px.line()#title='Time vs Horizontal Distance')
        fig_tdistz = px.line()#title='Time vs Vertical Distance')
    
        df_x = None; df_y = None
        for i, ac_id in enumerate(ac_ids_selected):
            df_ac_interp = df_interp.loc[df_interp['ac_id'] == ac_id]
            fig_xy.add_scatter(x=df_ac_interp['xEast'], y=df_ac_interp['yNorth'], 
                               mode='lines', marker={'color':COLOR_LIST[i]}, name='AC '+str(ac_id))
            fig_tz.add_scatter(x=df_ac_interp['time'], y=df_ac_interp['zUp'], 
                               mode='lines', marker={'color':COLOR_LIST[i]}, name='AC '+str(ac_id), showlegend=False)
            fig_tspeedxy.add_scatter(x=df_ac_interp['time'], y=df_ac_interp['horizontal_speed'], 
                               mode='lines', marker={'color':COLOR_LIST[i]}, name='AC '+str(ac_id), showlegend=False)
            fig_tspeedz.add_scatter(x=df_ac_interp['time'], y=df_ac_interp['vertical_speed'], 
                               mode='lines', marker={'color':COLOR_LIST[i]}, name='AC '+str(ac_id), showlegend=False)
            fig_xyz.add_scatter3d(x=df_ac_interp['xEast'], y=df_ac_interp['yNorth'], z=df_ac_interp['zUp'],
                               mode='lines', marker={'color':COLOR_LIST[i]}, name='AC '+str(ac_id))

            df_ac_slider = df_ac_interp.loc[df_ac_interp['time'] == t_value]
            fig_xy.add_scatter(x=df_ac_slider['xEast'], y=df_ac_slider['yNorth'],
                               mode='markers', marker={'size':10, 'color':COLOR_LIST[i]}, showlegend=False)
            fig_tz.add_scatter(x=df_ac_slider['time'], y=df_ac_slider['zUp'],
                               mode='markers', marker={'size':10, 'color':COLOR_LIST[i]}, showlegend=False)
            fig_tspeedxy.add_scatter(x=df_ac_slider['time'], y=df_ac_slider['horizontal_speed'],
                               mode='markers', marker={'size':10, 'color':COLOR_LIST[i]}, showlegend=False)
            fig_tspeedz.add_scatter(x=df_ac_slider['time'], y=df_ac_slider['vertical_speed'],
                               mode='markers', marker={'size':10, 'color':COLOR_LIST[i]}, showlegend=False)
            fig_xyz.add_scatter3d(x=df_ac_slider['xEast'], y=df_ac_slider['yNorth'], z=df_ac_slider['zUp'],
                               mode='markers', marker={'size':7, 'color':COLOR_LIST[i]}, showlegend=False)           

            if i == 0: df_x = df_ac_interp
            elif i == 1: df_y = df_ac_interp
                
        # plot hor/ver distance graphs
        if df_x is not None and df_y is not None:
            df_dist = pd.merge(df_x, df_y, on='time')    
            df_dist['dist_xy'] = np.sqrt((df_dist['xEast_x']-df_dist['xEast_y'])**2 + (df_dist['yNorth_x']-df_dist['yNorth_y'])**2)
            df_dist['dist_z'] = np.abs(df_dist['zUp_x']-df_dist['zUp_y'])

            fig_tdistxy.add_scatter(x=df_dist['time'], y=df_dist['dist_xy'], mode='lines', marker={'color':'gray'}, showlegend=False)
            fig_tdistz.add_scatter(x=df_dist['time'], y=df_dist['dist_z'], mode='lines', marker={'color':'gray'}, showlegend=False)

            df_dist_slider = df_dist.loc[df_dist['time'] == t_value]
            fig_tdistxy.add_scatter(x=df_dist_slider['time'], y=df_dist_slider['dist_xy'], 
                                    mode='markers', marker={'size':10, 'color':'gray'}, showlegend=False)
            fig_tdistz.add_scatter(x=df_dist_slider['time'], y=df_dist_slider['dist_z'], 
                                    mode='markers', marker={'size':10, 'color':'gray'}, showlegend=False)  

        # update layout of graphs
        if min_values_list == [] and max_values_list == []:
            return 'Time: ', 0, {}, {}, {}, {}, {}, {}, {}, 0, 100

        min_values = np.min(np.array(min_values_list), axis=0)
        max_values = np.max(np.array(max_values_list), axis=0)

        margin = dict(l=50, r=20, b=50, t=20, pad=0)
    
        fig_xy.update_layout(# title_font_family="Times New Roman",
            xaxis_title = 'xEast (NM)', xaxis_range = [min(min_values[1],min_values[2])-0.2, 
                                                       max(max_values[1], max_values[2])+0.2],
            yaxis_title = 'yNorth (NM)', yaxis_range = [min(min_values[1],min_values[2])-0.2, 
                                                       max(max_values[1], max_values[2])+0.2],
            #width=490,
            margin=margin)        
        fig_tz.update_layout(
            xaxis_title='Time (s)', xaxis_range=[min_values[0]-2, max_values[0]+2],
            yaxis_title='zUp (ft)', yaxis_range=[min_values[3]-50, max_values[3]+50],
            margin=margin)
        fig_tspeedxy.update_layout(
            xaxis_title='Time (s)', xaxis_range=[min_values[0]-2, max_values[0]+2],
            yaxis_title='Speed (kt)', yaxis_range=[min_values[4]-10, max_values[4]+10],
            margin=margin)
        fig_tspeedz.update_layout(
            xaxis_title='Time (s)', xaxis_range=[min_values[0]-2, max_values[0]+2],
            yaxis_title='Speed (ft/s)', yaxis_range=[min_values[5]-5, max_values[5]+5],
            margin=margin)
        fig_xyz.update_layout(
            scene = {'xaxis': {'title':'xEast (NM)', 
                               'range':[min(min_values[1],min_values[2])-0.2, max(max_values[1], max_values[2])+0.2]},
                    'yaxis': {'title':'yNorth (NM)',
                              'range':[min(min_values[1],min_values[2])-0.2, max(max_values[1], max_values[2])+0.2]},
                    'zaxis': {'title':'zUp (ft)',
                              'range':[min_values[3]-50, max_values[3]+50]}},
            width=920, height=700, margin=dict(l=0, r=0, b=30, t=20, pad=0))
        fig_tdistxy.update_layout(
            xaxis_title = 'Time (s)', 
            yaxis_title = 'Distance (NM)',
            margin=margin),
        fig_tdistz.update_layout(
            xaxis_title = 'Time (s)', 
            yaxis_title = 'Distance (ft)',
            margin=margin),

        return 'Time: {} (s)'.format(t_value), t_value, fig_xy, fig_tz, fig_tspeedxy, fig_tspeedz, fig_xyz, fig_tdistxy, fig_tdistz, min_values[0], max_values[0]


# ##########################################################################################
##########################################################################################
def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    if '.dat' in filename:
        [encounters, num_ac, num_encounters] = load_waypoints(filename)
        encounters_df = waypoints_to_df(encounters, num_encounters, num_ac)
        return encounters_df
       
    
@app.callback(Output('memory-data', 'data'),
              [Input('load-waypoints-button', 'n_clicks'),
               Input('load-waypoints', 'contents'),
               Input('create-mode', 'n_clicks'),
               Input('end-new-button', 'n_clicks'),
               Input('exit-create-mode', 'n_clicks'),
               Input('generated-encounters', 'data'),
               Input('load-model', 'contents')],
              [State('load-waypoints', 'filename'),
               State('editable-table', 'data')])
def update_memory_data(upload_n_clicks, waypoints_contents, create_n_clicks, end_new_n_clicks, exit_create_n_clicks, generated_data, model_contents, filename, data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'create-mode' and create_n_clicks > 0:
        return [{}]
    elif ctx == 'end-new-button' and end_new_n_clicks > 0:  ## NEED TO FIX (ctx == 'exit-create-mode' ?)
        return data  ## NEED TO FIX
    
    # elif ctx == 'load-waypoints-button' and upload_n_clicks > 0:
    #     return [{}]
    elif ctx == 'load-waypoints' and upload_n_clicks > 0:
        if waypoints_contents is None or not filename:
            return [{}]

        df = parse_contents(waypoints_contents, filename) 

        if 0 in set(df['encounter_id']):
            df['encounter_id'] += 1
        if 0 in set(df['ac_id']):
            df['ac_id'] += 1
        
        df['xEast'] = df['xEast'] * FT_TO_NM  #np.around(df['xEast'] * FT_TO_NM, decimals=4)
        df['yNorth'] = df['yNorth'] * FT_TO_NM  #np.around(df['yNorth'] * FT_TO_NM, decimals=4)
        return df.to_dict('records')

    elif ctx == 'generated-encounters':
        if data is not None:
            return generated_data

    elif ctx == 'load-model':
        if model_contents is not None:
            content_type, content_string = model_contents.split(',')
        
            if 'json' in content_type:
                data = []
                model = json.loads(base64.b64decode(content_string))
                mean = model['mean']
                for ac in range(1, mean['num_ac']+1):
                    ac_traj = mean[str(ac)]['waypoints']
                    for waypoint in ac_traj:
                        data += [{'encounter_id':0, 'ac_id': ac, 'time':waypoint['time'], 
                                 'xEast':waypoint['xEast'], 'yNorth':waypoint['yNorth'],
                                 'zUp':waypoint['zUp'], 'horizontal_speed':0, 'vertical_speed':0}]  ##NEED CHANGE : speeds
                return data

    return dash.no_update


@app.callback([Output('editable-table', 'data'),
               Output('editable-table', 'columns')],
              [Input('load-waypoints-button', 'n_clicks'),
               Input('load-waypoints', 'contents'),
               Input('encounter-ids', 'value'),
               Input('ac-ids', 'value'),
               Input('update-speeds-button', 'n_clicks'),
               Input('add-rows-button', 'n_clicks'),
               Input('done-add-rows-button', 'n_clicks'),
               Input('create-mode', 'n_clicks'),
               Input('create-new-button', 'n_clicks'),
               Input('end-new-button', 'n_clicks'),
               Input('gen-encounters-button', 'n_clicks'),
               Input('marker-layer', 'children')],
              [State('editable-table', 'data'),
               State('editable-table', 'columns'),
               State('ac-index', 'value'),
               State('time-interval-input', 'value'),
               State('create-mode-zUp-input', 'value'),
               State('memory-data', 'data'),
               State('session', 'data')])
def update_data_table(upload_n_clicks, waypoints_contents, encounter_id_selected, ac_ids_selected, update_speeds_n_clicks, add_rows_n_clicks, done_add_rows_n_clicks,\
                      create_n_clicks, start_new_n_clicks, end_new_n_clicks, gen_n_clicks, current_markers, data, columns, ac_value, interval, zUp_input, memory_data, ref_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'load-waypoints' and upload_n_clicks > 0:
        return [], columns
        
    if ctx == 'encounter-ids':
        if encounter_id_selected is None or encounter_id_selected == []:
            return [], columns
        else:
            # encounter IDs have been updated or loaded in
            df = pd.DataFrame(memory_data)
            df_filtered = df.loc[df['encounter_id'] == encounter_id_selected]
            df_filtered = calculate_horizontal_vertical_speeds_df(df_filtered)
            return df_filtered.to_dict('records'), columns
    
    if ctx == 'ac-ids':
        if encounter_id_selected is None or encounter_id_selected == []:
            print('Select an encounter ID.')
            return dash.no_update, dash.no_update
        else:
            # AC IDs have been updated or loaded in
            df = pd.DataFrame(memory_data)
            # df_filtered = df.query('encounter_id in @encounter_id_selected')
            df_filtered = df.loc[(df['encounter_id'] == encounter_id_selected) & (df['ac_id'].isin(ac_ids_selected))]
            df_filtered = calculate_horizontal_vertical_speeds_df(df_filtered)
            return df_filtered.to_dict('records'), columns 

    elif ctx == 'create-mode' and create_n_clicks > 0 and end_new_n_clicks == 0:
        # wipe all data
        return [], columns

    elif ctx == 'update-speeds-button' and update_speeds_n_clicks > 0:
        df = pd.DataFrame(data) #.apply(pd.to_numeric, errors='coerce').fillna(0)
        df = calculate_horizontal_vertical_speeds_df(df)
        return df.to_dict('records'), columns

    elif ctx == 'add-rows-button' and create_n_clicks == 0:
        if add_rows_n_clicks > 0:
            # add an empty row
            data.append({col["id"]: '' for col in columns})
        return data, columns
    elif ctx == 'done-add-rows-button' and done_add_rows_n_clicks > 0:
        df = pd.DataFrame(data).apply(pd.to_numeric, errors='coerce').fillna(0)
        df = calculate_horizontal_vertical_speeds_df(df)
        return df.to_dict('records'), columns

    else:
        if ctx == 'create-new-button' and start_new_n_clicks > 0:
            pass
            
        elif ctx == 'marker-layer' and create_n_clicks > 0 and start_new_n_clicks > 0:
            if ac_value is None or not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_alt'] or not interval or not zUp_input:
                return dash.no_update, dash.no_update
            
            if len(data) != len(current_markers):
                timestep = 0
                if len(data) > 0:
                    df = pd.DataFrame(data)
                    if ac_value in df['ac_id'].tolist():
                        df_ac = df.loc[df['ac_id'] == ac_value]
                        last_timestep = max(df_ac['time'])
                        timestep = last_timestep+interval
                    
                # in creative mode and user has created another marker 
                # we add each marker to the data as it is created 
                # so we only have to grab last marker in the list
                pos = current_markers[-1]['props']['position']
                xEast, yNorth, zUp = pm.geodetic2enu(pos[0], pos[1], zUp_input*FT_TO_M, 
                                                     ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M,
                                                     ell=pm.Ellipsoid('wgs84'), deg=True)
                marker_dict = {'encounter_id': 0, 'ac_id': ac_value, 'time': timestep, 
                               'xEast': xEast*M_TO_NM, 'yNorth': yNorth*M_TO_NM, 'zUp': zUp_input, 'horizontal_speed': 0, 'vertical_speed': 0}  
                data.append(marker_dict)
            else:
                # an already existing marker was dragged
                # and therefore its position in data table needs to get updated

                # FIXME: there must be a more efficient way to do this
                # because right now I touch all data points instead of the one that
                # is explicitly changed.
                for i, data_point in enumerate(data):
                    pos = current_markers[i]['props']['position']
                    xEast, yNorth, zUp = pm.geodetic2enu(pos[0], pos[1], zUp_input*FT_TO_M, 
                                                         ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M,
                                                         ell=pm.Ellipsoid('wgs84'), deg=True)
                    data_point['xEast'] = xEast*M_TO_NM
                    data_point['yNorth'] = yNorth*M_TO_NM
                    data_point['zUp'] = zUp_input #*M_TO_FT

            return data, columns
        
        elif ctx == 'end-new-button':
            if end_new_n_clicks > 0: 
                if data != []:
                    df = pd.DataFrame(data) #.apply(pd.to_numeric, errors='coerce').fillna(0)
                    df = calculate_horizontal_vertical_speeds_df(df)
                    return df.to_dict('records'), columns
        
        return dash.no_update, dash.no_update


@app.callback([Output('editable-table','style_table'),
               Output('update-speeds-button', 'style'),
               Output('add-rows-button', 'style'),
               Output('done-add-rows-button', 'style'),
               Output('add-rows-button', 'n_clicks'),
               Output('done-add-rows-button', 'n_clicks'),
               Output('data-table-div', 'style')],
              [Input('add-rows-button', 'n_clicks'),
               Input('done-add-rows-button', 'n_clicks'),
               Input('tabs','active_tab')]) 
def toggle_data_table_buttons(add_rows_n_clicks, done_add_rows_n_clicks, active_tab):

    table_on = {'width': '39rem', 'height': '35rem', 'margin-left': "10px", 'display': "block", 'overflowY': 'scroll'}
    speeds_button_on = {'margin-left':'15px', 'display':'block'}
    add_row_button_on = {'margin-left':'15px', 'display': 'block'}
    done_button_on = {'margin-left':'10px', 'display':'block', 'color':'white', 'background-color': '#5cb85c', 'border-color': '#5cb85c'}
    off = {'display': "none"}
    on = {'display': "block"}
    reset_add_rows_n_clicks, reset_done_add_rows_n_clicks = add_rows_n_clicks, done_add_rows_n_clicks

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]   

    if ctx == 'tabs':
        if active_tab == 'tab-4':
            return off, off, off, off, reset_add_rows_n_clicks, reset_done_add_rows_n_clicks, off
        return table_on, speeds_button_on, add_row_button_on, off, reset_add_rows_n_clicks, reset_done_add_rows_n_clicks, on
    if ctx == 'add-rows-button' and add_rows_n_clicks > 0:
        return table_on, off, add_row_button_on, done_button_on, reset_add_rows_n_clicks, 0, on
    if ctx == 'done-add-rows-button' and done_add_rows_n_clicks > 0:
        return table_on, speeds_button_on, add_row_button_on, off, 0, reset_done_add_rows_n_clicks, on

    return dash.no_update

@app.callback(Output('data-table-card', 'style'),
                Input('editable-table', 'data'),
                [State('data-table-card', 'style'),
                State('editable-table', 'style_table')],
                preventInitialCallback=True)
def adjust_height_of_data_table_card(data, card_style, table_style):
    if len(data) != 0:
        if 'height' in table_style.keys():
            val = table_style['height'].split('r')[0]
            new_height = int(val) + 5
            card_style['height'] = str(new_height) + 'rem'

    return card_style



@app.callback(Output('update-speeds-button', 'disabled'),
              Output('add-rows-button', 'disabled'),
              Input('editable-table', 'data'))
def toggle_data_table_speeds_button(data):
    if data is None or data == []:
        return True, True
    return False, False


# ##########################################################################################
# ##########################################################################################
@app.callback(Output('encounter-ids', 'options'),
              [Input('memory-data', 'data'),
               Input('create-mode', 'n_clicks'),
               Input('end-new-button', 'n_clicks')],
              [State('encounter-ids', 'options')])
def update_encounter_dropdown(memory_data, create_n_clicks, end_new_n_clicks, options):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    # print('\n--update_encounter_dropdown--')
    # print('ctx: ', ctx)
    
    if ctx == 'memory-data':
        if memory_data == [{}]: #or memory_data == []
            return []
        df = pd.DataFrame(memory_data)
        encounter_ids = df['encounter_id'].unique()
        options = [{'value': encounter_id, 'label': 'Encounter '+ str(int(encounter_id))} for encounter_id in encounter_ids]
        return options
    elif ctx == 'create-mode' and create_n_clicks > 0:
        if memory_data is not [{}]: #and memory_data != []
            return []
    
    elif ctx == 'end-new-button' and end_new_n_clicks > 0:
        encounter_value = 0
        # if encounter_value is not None:
        new_option = {'value': encounter_value, 'label': 'Encounter '+ str(encounter_value)}
        if options is None or options == []:
            options = [new_option]
        elif new_option not in options:
            options.append(new_option)
        return options
    return dash.no_update


@app.callback(Output('ac-ids', 'options'),
              [Input('load-waypoints-button', 'n_clicks'),
               Input('create-mode', 'n_clicks'),
               Input('encounter-ids', 'value'),
               Input('end-new-button', 'n_clicks')],
              [State('ac-index', 'value'),
               State('ac-ids', 'options'),
               State('create-new-button', 'n_clicks'),
               State('generate-button', 'n_clicks'),
               State('editable-table', 'data'),
               State('memory-data', 'data')])
def update_ac_dropdown(upload_n_clicks, create_n_clicks, encounter_id_selected, end_new_n_clicks, ac_value, options, start_new_n_clicks, generate_n_clicks, data, memory_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    
    # print('\n--update_ac_dropdown--')
    # print('ctx: ', ctx)
    # print(encounter_id_selected)

    # if not encounter_id_selected and ac_value is None:
    #     return dash.no_update
    
    if ctx == 'load-waypoints-button' and upload_n_clicks > 0:
        return []  

    elif ctx == 'encounter-ids':
        if encounter_id_selected == []:
            return []
        else:
        #if (upload_n_clicks > 0 and end_new_n_clicks == 0) or generate_n_clicks > 0:
            df = pd.DataFrame(memory_data)
            df_filtered = df.loc[df['encounter_id'] == encounter_id_selected]
            ac_ids = df_filtered['ac_id'].unique()
            dropdown_options = [{'value': ac_id, 'label': 'AC '+ str(ac_id)} for ac_id in ac_ids]
            return dropdown_options
    
    elif ctx == 'create-mode':
        if create_n_clicks > 0 and start_new_n_clicks == 0 and end_new_n_clicks == 0:
            return []  

    elif ctx == 'end-new-button' and end_new_n_clicks > 0:
        if ac_value is not None:
            new_option = {'value': ac_value, 'label': 'AC '+ str(ac_value)}
            if options is None or options == []:
                options = [new_option]
            elif new_option not in options:
                options.append(new_option)
            else:
                print('AC ID already taken. Select a new one.')
            return options
        else:
            print('Enter an AC ID.')
    
    return dash.no_update


@app.callback([Output('encounter-ids', 'value'),
               Output('ac-ids', 'value')],
              [Input('encounter-ids', 'value'),
               Input('load-waypoints-button', 'n_clicks'),
               Input('create-mode', 'n_clicks'),
               Input('create-new-button', 'n_clicks'),
               Input('end-new-button', 'n_clicks'),
               Input('generate-button', 'n_clicks'),
               Input('session', 'data')],
               [State('ac-index', 'value'),
               State('ac-ids', 'value'),
               State('memory-data', 'data')])
def update_dropdowns_value(encounter_id_selected, upload_n_clicks, create_n_clicks, start_new_n_clicks, end_new_n_clicks, generate_n_clicks, ref_data, ac_value, ac_selected, memory_data): #encounter_value, 
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    # print('\n--update_dropdowns_value--')
    # print('ctx: ', ctx)
    
    if ctx == 'load-waypoints-button' and upload_n_clicks > 0:
        return [], []
    elif ctx == 'encounter-ids':
        if encounter_id_selected is None or encounter_id_selected == []:
            return [], []
        df = pd.DataFrame(memory_data)
        df_filtered = df.loc[df['encounter_id'] == encounter_id_selected]
        ac_ids = df_filtered['ac_id'].unique()
        return encounter_id_selected, [ac_id for ac_id in ac_ids]

    elif ctx == 'create-mode' and create_n_clicks > 0:
        return [], []

    elif ctx == 'create-new-button' and start_new_n_clicks > 0:
        return dash.no_update, ac_selected

    elif ctx == 'end-new-button' and end_new_n_clicks > 0:
        if ac_value is None: #not encounter_value 
            print("Enter an AC ID to create new nominal path")
        else:
            ac_selected.append(ac_value)
            return 0, ac_selected #[encounter_value], 

    elif ctx == 'generate-button':
        # entered generation mode - clear dropdown values
        if generate_n_clicks > 0:
            return [], []

    elif ctx == 'session':
        if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
            # no trajectories should be selected if there isn't a ref point
            return [], []

    return dash.no_update, dash.no_update


@app.callback([Output('encounter-ids', 'disabled'),
               Output('ac-ids', 'disabled')],
              [Input('create-mode', 'n_clicks'),
               Input('exit-create-mode', 'n_clicks'),
               Input('create-new-button', 'n_clicks'),
               Input('end-new-button', 'n_clicks'),
               Input('load-waypoints-button', 'n_clicks'),
               Input('session', 'data')])
def creative_mode_disable_dropdowns(create_n_clicks, exit_create_n_clicks, start_new_n_clicks, end_new_n_clicks, upload_n_clicks, ref_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

         
    # if ctx == 'create-mode' and start_new_n_clicks == 0:
    #     return True, True
    if ctx == 'create-new-button' and start_new_n_clicks > 0:
        return True, True
    elif ctx == 'end-new-button' and end_new_n_clicks > 0:
        return False, False
    # elif exit_create_n_clicks > 0:
    #     return False, False
    elif ctx == 'load-waypoints-button' and upload_n_clicks > 0:
        return False, False
        
    elif ctx == 'session':
        if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
            # no trajectories should be selected if there isn't a ref point
            return True, True
        else:
            return False, False

    return dash.no_update, dash.no_update


# ##########################################################################################
# ##########################################################################################
# @app.callback(Output('tabs', 'active_tab'),
#               Input('create-mode', 'n_clicks'))
# def creative_mode_switch_tabs(n_clicks):
#     if n_clicks > 0:
#         return 'tab-3'
    # return dash.no_update
    
    
# @app.callback([Output('tab1','disabled'),
#                Output('tab2', 'disabled')],
#               [Input('create-mode', 'n_clicks'),
#                Input('create-new-button', 'n_clicks'),
#                Input('end-new-button', 'n_clicks'),
#                Input('exit-create-mode', 'n_clicks'),
#                Input('load-waypoints-button', 'n_clicks')])
# def creative_mode_disable_tabs(create_n_clicks, start_new_n_clicks, end_new_n_clicks, exit_create_n_clicks, upload_n_clicks):
#     ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
#     if ctx == 'load-waypoints-button' and upload_n_clicks > 0:
#         return False, False
#     else:
#         if create_n_clicks > 0 and start_new_n_clicks > 0:
#             return True, True
#         elif end_new_n_clicks > 0 or exit_create_n_clicks > 0:
#             return False, False
#     return dash.no_update, dash.no_update


@app.callback([Output('create-mode', 'n_clicks'),
               Output('exit-create-mode', 'n_clicks'),
               Output('create-new-button', 'n_clicks'),
               Output('end-new-button', 'n_clicks'),
               Output('create-mode', 'style'),
               Output('create-new-button', 'style'),
               Output('exit-create-mode', 'style'),
               Output('create-mode-nom-path-div', 'style'),
               Output('end-new-button', 'style'),
               Output('create-mode-card', 'style'),
               Output('map-create-card', 'style')],
              [Input('load-waypoints-button', 'n_clicks'),
               Input('create-mode', 'n_clicks'), 
               Input('exit-create-mode', 'n_clicks'),
               Input('create-new-button', 'n_clicks'),
               Input('end-new-button', 'n_clicks')],
              [State('create-mode', 'style'),
               State('create-new-button', 'style'),
               State('exit-create-mode', 'style'),
               State('create-mode-nom-path-div', 'style'),
               State('end-new-button', 'style'),
               State('create-mode-card', 'style'),
               State('map-create-card', 'style')])
def toggle_create_mode(upload_n_clicks, create_n_clicks, exit_create_n_clicks, start_new_n_clicks, end_new_n_clicks, create_style, start_new_style, exit_create_style, create_mode_div_style, end_new_style, create_card_style, map_create_style):
    reset_create_clicks, reset_exit_create_clicks = create_n_clicks, exit_create_n_clicks
    reset_start_new_clicks, reset_end_new_clicks = start_new_n_clicks, end_new_n_clicks

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if create_n_clicks > 0:
        if ctx == 'create-mode':
            reset_exit_create_clicks = 0 
            create_style['display'] = 'none'
            exit_create_style['display'], start_new_style['display'] = 'block', 'block'
            create_card_style['display'] = 'block'
            map_create_style['height']  = '44rem'
            
            # exit_create_style['display'] = 'block'

        if ctx == 'create-new-button' and start_new_n_clicks > 0:
            reset_end_new_clicks = 0
            # ac_style['display'], end_new_style['display'] = 'block', 'block'
            # interval_style['display'], zUp_style['display'] = 'block', 'block'
            create_mode_div_style['display'] = 'block'
            end_new_style['display'] = 'block'
            create_card_style['display'] = 'block'
            #map_create_style['height']  = '50rem'
            
        if ctx == 'end-new-button' and end_new_n_clicks > 0:
            reset_start_new_clicks = 0
            # ac_style['display'], end_new_style['display'] = 'none', 'none'
            # interval_style['display'], zUp_style['display'] = 'none', 'none'
            create_mode_div_style['display'] = 'none'
            end_new_style['display'] = 'none'
            #create_card_style['display'] = 'none'
            #map_create_style['height']  = '33rem'
            
        if ctx == 'exit-create-mode' and exit_create_n_clicks > 0:
            reset_create_clicks = 0
            reset_start_new_clicks, reset_end_new_clicks = 0, 0
            # exit_create_style['display'], start_new_style['display'], end_new_style['display'] ='none', 'none', 'none'
            # ac_style['display'], interval_style['display'], zUp_style['display'] = 'none', 'none', 'none'
            start_new_style['display'], exit_create_style['display'] = 'none', 'none'
            create_mode_div_style['display'] = 'none'
            end_new_style['display'] = 'none'
            create_card_style['display'] = 'none'
            map_create_style['height']  = '33rem'
            create_style['display'] = 'block'
            
            
        if ctx == 'load-waypoints-button' and upload_n_clicks > 0:
            reset_create_clicks, reset_exit_create_clicks = 0, 0
            reset_start_new_clicks, reset_end_new_clicks = 0, 0
            # exit_create_style['display'], start_new_style['display'], end_new_style['display'] ='none', 'none', 'none'
            # ac_style['display'], interval_style['display'], zUp_style['display'] = 'none', 'none', 'none'
            start_new_style['display'], exit_create_style['display'] = 'none', 'none'
            create_mode_div_style['display'] = 'none'
            end_new_style['display'] = 'none'
            create_card_style['display'] = 'none'
            map_create_style['height']  = '33rem'
            
    return reset_create_clicks, reset_exit_create_clicks, reset_start_new_clicks, reset_end_new_clicks,\
            create_style, start_new_style, exit_create_style, create_mode_div_style, end_new_style, create_card_style, map_create_style


@app.callback(Output('ac-index', 'value'),
              Input('exit-create-mode', 'n_clicks'),
              Input('load-waypoints-button', 'n_clicks'),
              State('ac-ids', 'options'))
def exit_creative_mode_reset_ac_index(exit_n_clicks, upload_n_clicks, options):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if ctx == 'exit-create-mode' and exit_n_clicks > 0:
        return None    
    if ctx == 'load-waypoints-button' and upload_n_clicks > 0: 
        return None
    return dash.no_update


# ##########################################################################################
# ##########################################################################################
@app.callback([Output('map', 'center'),
               Output('map', 'zoom')],
              Input('session', 'data'))
def center_map_around_ref_input(ref_data):
    if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
        # ref point was cleared - so reset to center of US and zoom out
        return (39,-98), 4
    return (ref_data['ref_lat'], ref_data['ref_long']), 11.5


@app.callback(Output('polyline-layer', 'children'),
              [Input('editable-table', 'data'),
              Input('session', 'data')],
              State('polyline-layer', 'children'))    
def update_map(data, ref_data, current_polylines):
    if data is None:
        return dash.no_update

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'editable-table' or ctx == 'session':
        # data has changed - must update map polylines
        new_polylines = []
        
        if  not ref_data['ref_lat']\
            or not ref_data['ref_long']\
            or not ref_data['ref_long']\
            or len(data)==0:
            # either no ref point or no data, save computation time
            return new_polylines

        aggregation = collections.defaultdict(lambda: collections.defaultdict(list))
        for row in data:
            if row.get('xEast') != '' and row.get('yNorth') != '' and row.get('zUp') != '':        
                a = aggregation[float(row.get('ac_id'))]
                a['name'], a['color'] = 'AC '+ str(row['ac_id']), row['ac_id']

                a['xEast'].append(float(row.get('xEast')))
                a['yNorth'].append(float(row.get('yNorth')))
                a['zUp'].append(float(row.get('zUp')))
        
        data_group = [x for x in aggregation.values()]
            
        for data_id in data_group:
            lat_lng_dict = []
            for i in range(len(data_id['xEast'])):
                lat, lng, alt = pm.enu2geodetic(data_id['xEast'][i]*NM_TO_M, data_id['yNorth'][i]*NM_TO_M, data_id['zUp'][i]*FT_TO_M, 
                                                ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M, 
                                                ell=pm.Ellipsoid('wgs84'), deg=True)
                lat_lng_dict.append([lat, lng])
            
            new_polylines.append(dl.PolylineDecorator(positions=lat_lng_dict, patterns=map_patterns))
        
        return new_polylines
    
    return current_polylines


@app.callback(Output('marker-layer', 'children'),
                [Input("map", "dbl_click_lat_lng"),
                 Input('create-new-button', 'n_clicks'),
                 Input('encounter-ids', 'options'),
                 Input('ac-ids', 'value'),
                 Input(dict(tag="marker", index=ALL), 'children'),
                 Input('session', 'data'),
                 Input('exit-create-mode', 'n_clicks')],
                [State('marker-layer', 'children'),
                 State('ac-index', 'value'),
                 State('load-waypoints-button', 'n_clicks'),
                 State('create-mode', 'n_clicks')])
def create_markers(dbl_click_lat_lng, start_new_n_clicks, encounter_options, ac_ids, current_marker_tools, ref_data, exit_create_n_clicks, current_markers, ac_value,  upload_n_clicks, create_n_clicks): 
    ctx = dash.callback_context
    if not ctx.triggered or not ctx.triggered[0]['value']:
        return dash.no_update
    ctx = ctx.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'map':
        if create_n_clicks > 0 and start_new_n_clicks > 0:
            if ac_value is not None:
                if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
                    return dash.no_update

                xEast, yNorth, zUp = pm.geodetic2enu(dbl_click_lat_lng[0], dbl_click_lat_lng[1], ref_data['ref_alt']*FT_TO_M, 
                                                    ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M,
                                                    ell=pm.Ellipsoid('wgs84'), deg=True)

                current_markers.append(dl.Marker(id=dict(tag="marker", index=len(current_markers)), 
                                        position=dbl_click_lat_lng,
                                        children=dl.Tooltip("({:.3f}, {:.3f})".format(*[xEast, yNorth])), 
                                        draggable=True))
            else:
                print('Enter an AC ID.')
        
    elif ctx == 'create-new-button' and start_new_n_clicks > 0:
        return []

    elif ctx == 'exit-create-mode':
        if exit_create_n_clicks:
            return []

    elif ctx == 'session':
        if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
            return []

    elif upload_n_clicks > 0:
        if ctx == 'encounter-ids' or ctx == 'ac-ids':
            # clear markers if more than one trajectory is active
            if len(encounter_options) > 1 or len(ac_ids) > 1:
                return []

    return current_markers


@app.callback(Output(dict(tag="marker", index=ALL), 'draggable'),
              Input('create-new-button', 'n_clicks'),
              [State(dict(tag="marker", index=ALL), 'draggable')])
def toggle_marker_draggable(create_n_clicks, draggable):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if ctx == 'create-new-button' and create_n_clicks > 0:
        return [True] * len(draggable)
    elif ctx == 'create-new-button' and create_n_clicks == 0:
        return [False] * len(draggable)
    return dash.no_update


@app.callback(Output(dict(tag="marker", index=ALL), 'children'),
              [Input(dict(tag="marker", index=ALL), 'position')],
              [State(dict(tag="marker", index=ALL), 'children'), 
              State('session', 'data')])
def update_marker(new_positions, current_marker_tools, ref_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
 
    if len(ctx) > 0:
        if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
            return dash.no_update

        index = json.loads(ctx)['index']
        pos = new_positions[index]
        xEast, yNorth, zUp = pm.geodetic2enu(pos[0], pos[1], ref_data['ref_alt']*FT_TO_M, 
                                            ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M,
                                            ell=pm.Ellipsoid('wgs84'), deg=True)
        current_marker_tools[index] = dl.Tooltip("({:.3f}, {:.3f})".format(*[xEast, yNorth]))
    return current_marker_tools


# ##########################################################################################
# ##########################################################################################
@app.callback(Output('ref-point-modal', 'is_open'),
                [Input('set-ref-point', 'n_clicks'),
                Input('close-ref-modal-button', 'n_clicks'),
                Input('set-ref-button', 'n_clicks')])
def toggle_ref_point_modal(open_modal_n_clicks, close_n_clicks, set_ref_n_clicks):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'set-ref-point':
        if open_modal_n_clicks > 0:
            return True
    elif ctx == 'close-ref-modal-button':
        if close_n_clicks > 0:
            return False
    elif ctx == 'set-ref-button':
        if set_ref_n_clicks > 0:
            return False
    
    return dash.no_update


@app.callback([Output('ref-point-output', 'children'),
                Output('session', 'data')],
                [Input('set-ref-button', 'n_clicks'),
                Input('clear-ref-button', 'n_clicks')],
                [State('ref-point-input', 'value'),
                State('ref-point-input', 'pattern'),
                State('session', 'data')])
def set_ref_point_data(set_n_clicks, clear_n_clicks, ref_point_value, pattern, ref_data):
    patt = re.compile(pattern)
    

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if ctx == 'set-ref-button':
        if set_n_clicks > 0 and ref_point_value:
            p = patt.match(ref_point_value)
            if p:
                vals = p.groups()
                ref_data['ref_lat'] = float(vals[0])
                ref_data['ref_long'] = float(vals[1])
                ref_data['ref_alt'] = float(vals[2])
            else:
                return '!!invalid format!!', ref_data

    elif ctx == 'clear-ref-button':
        if clear_n_clicks > 0:
            ref_data['ref_lat'] = None
            ref_data['ref_long'] = None
            ref_data['ref_alt'] = None
            return 'Reference Point: ', ref_data

    ref = 'Reference Point: ', ref_data['ref_lat'], chr(176), "/ ", ref_data['ref_long'], chr(176), '/ ', ref_data['ref_alt'], 'ft'
    
    return ref, ref_data


@app.callback(Output('ref-point-input', 'value'),
                Input('clear-ref-button', 'n_clicks'))
def reset_ref_point_value(clear_n_clicks):
    if clear_n_clicks > 0:
        return ''
    return dash.no_update


@app.callback([Output('ref-point-input', 'disabled'),
               Output('clear-ref-button', 'disabled'),
               Output('set-ref-button', 'disabled')],
              [Input('create-mode', 'n_clicks'),
              Input('create-new-button', 'n_clicks'),
              Input('end-new-button', 'n_clicks'),
               Input('exit-create-mode', 'n_clicks'),
               Input('load-waypoints-button', 'n_clicks')])
def disable_ref_inputs(create_n_clicks, start_new_n_clicks, end_new_n_clicks, exit_create_n_clicks, upload_n_clicks):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if ctx == 'load-waypoints-button' and upload_n_clicks > 0:
        return False, False, False
    if ctx == 'create-new-button':
        if start_new_n_clicks > 0:
            return True, True, True
    elif ctx == 'end-new-button':
        if end_new_n_clicks > 0:
            return False, False, False

    # if create_n_clicks > 0:
    #     return True, True, True
    # if exit_create_n_clicks > 0:
    #     return False, False, False
        
    return dash.no_update, dash.no_update, dash.no_update


# ##########################################################################################
# ##########################################################################################
@app.callback(Output('gen-modal', 'is_open'),
                [Input('gen-encounters-button', 'n_clicks'),
                Input('close-button', 'n_clicks'),
                Input('generate-button', 'n_clicks')])
def toggle_gen_modal(gen_n_clicks, close_n_clicks, generate_n_clicks):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'gen-encounters-button':
        if gen_n_clicks > 0:
            return True
    elif ctx == 'close-button':
        if close_n_clicks > 0:
            return False
    elif ctx == 'generate-button':
        if generate_n_clicks > 0:
            return False
    
    return dash.no_update

@app.callback(Output('nominal-path-enc-ids', 'options'),
              Input('encounter-ids', 'options'))
def set_nominal_enc_id_options(encounter_options):
    if encounter_options is not None:
        return encounter_options
    
    return dash.no_update


@app.callback(Output('nominal-path-ac-ids', 'options'),
              Input('nominal-path-enc-ids', 'value'),
              State('memory-data','data'))
def set_nominal_ac_ids_options(encounter_id_selected, memory_data):
    if encounter_id_selected != [] and memory_data != [{}]:
        df = pd.DataFrame(memory_data)
        df_filtered = df.loc[df['encounter_id'] == encounter_id_selected]
        ac_ids = df_filtered['ac_id'].unique()
        dropdown_options = [{'value': ac_id, 'label': 'AC '+ str(ac_id)} for ac_id in ac_ids]
        return dropdown_options

    return []

@app.callback([Output('nominal-path-enc-ids','value'),
               Output('nominal-path-ac-ids','value')],
               [Input('gen-encounters-button', 'n_clicks'),
               Input('load-model', 'contents')],
               State('nominal-path-ac-ids','options'))
def reset_nominal_dropdown_values(gen_n_clicks, contents, ac_options):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'gen-encounters-button':
        if gen_n_clicks > 0:
            return [], []
    elif ctx == 'load-model':
        if contents is not None:
            content_type, content_string = contents.split(',')
            if 'json' in content_type:
                model = json.loads(base64.b64decode(content_string))
                return 0, [ac for ac in range(1, model['mean']['num_ac']+1)]

    return dash.no_update, dash.no_update


# #########################################################################################
# #########################################################################################
@app.callback([Output('cov-radio','value'),
                Output('diag-sigma-input-hor', 'value'),
                Output('diag-sigma-input-ver', 'value'),
                Output('exp-kernel-input-a', 'value'),
                Output('exp-kernel-input-b', 'value'),
                Output('exp-kernel-input-c', 'value'),
                Output('num-encounters-input', 'value')],
                Input('load-model', 'contents'))
def load_in_model(contents):
    if contents is not None:
        content_type, content_string = contents.split(',')
        
        if 'json' in content_type:
            model = json.loads(base64.b64decode(content_string))

            cov = model['covariance']
            if cov['type'] == 'diagonal':
                if 'sigma_hor' in cov.keys() and 'sigma_ver' in cov.keys():
                    return 'cov-radio-diag', cov['sigma_hor'], cov['sigma_ver'], None, None, None, None

            elif cov['type'] == 'exponential kernel':
                if 'a' in cov.keys() and 'b' in cov.keys() and 'c' in cov.keys():
                    return 'cov-radio-exp', None, None, cov['a'], cov['b'], cov['c'], None

    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update


@app.callback(Output('cov-diag-input-container', 'style'),
              Output('cov-exp-kernel-input-container', 'style'),
              Input('cov-radio', 'value'))
def toggle_covariance_type(cov_radio_value):
    on = {'display': 'block'}
    off = {'display': 'none'}
    
    if cov_radio_value == 'cov-radio-diag':
        return on, off
    elif cov_radio_value == 'cov-radio-exp':
        return off, on
    else:
        print("Select a covariance matrix type.") 
                        
    
def exp_kernel_func(inputs, param_a, param_b, param_c): 
    inputs = np.array(inputs)
    N = inputs.shape[0]*inputs.shape[1]

    K_mean = inputs.reshape((N,))
    K_cov = np.zeros((N, N))  
    
    param_a, param_b, param_c = float(param_a), float(param_b), float(param_c)
    
    for i, inputs_i in enumerate(inputs):
        for j, inputs_j in enumerate(inputs):
            if i == j or i < j:           
                [x_i,y_i,z_i] = inputs_i
                [x_j,y_j,z_j] = inputs_j
                
                dist_xy = [[(x_i-x_j)**2, (x_i-y_j)**2], 
                           [(y_i-x_j)**2, (y_i-y_j)**2]]
                K_cov[3*i:3*i+2, 3*j:3*j+2] = np.exp(-(param_b * np.power(dist_xy, 2)) / (2 * param_a**2))
                
                dist_z = [(z_i-z_j)]
                K_cov[3*i+2, 3*j+2] = np.exp(-(param_c * np.power(dist_z, 2)) / (2 * param_a**2))

                if i != j:
                    K_cov[3*j:3*j+3, 3*i:3*i+3] = np.transpose(K_cov[3*i:3*i+3, 3*j:3*j+3])

    return K_mean, K_cov


def generation_error_found(memory_data, nom_ac_ids, num_encounters, cov_radio_value, 
                 sigma_hor, sigma_ver, exp_kernel_a, exp_kernel_b, exp_kernel_c) -> bool:
    error = False
    if memory_data == [{}]: # or memory_data == []:
        print('Must create a nominal encounter or load a waypoint file')
        error = True
    if not nom_ac_ids:
        print("Must select at least one nominal path")
        error = True
    if not num_encounters:
        print('Must input number of encounters to generate')
        error = True    
    if cov_radio_value == 'cov-radio-diag':
        if not sigma_hor or not sigma_ver:
            print('Must input all sigma values.')
            error = True
    elif cov_radio_value == 'cov-radio-exp':
        if not exp_kernel_a or not exp_kernel_b or not exp_kernel_c:
            print('Must input all parameter values.')
            error = True
    
    return error


@app.callback(Output('generated-encounters', 'data'),
              Input('generate-button', 'n_clicks'),
              [State('nominal-path-enc-ids', 'value'),
               State('nominal-path-ac-ids', 'value'),
               State('cov-radio', 'value'),
               State('diag-sigma-input-hor', 'value'),
               State('diag-sigma-input-ver', 'value'),
               State('exp-kernel-input-a', 'value'),
               State('exp-kernel-input-b', 'value'),
               State('exp-kernel-input-c', 'value'),
               State('num-encounters-input', 'value'),
               State('memory-data', 'data')])
def generate_encounters(gen_n_clicks, nom_enc_id, nom_ac_ids, cov_radio_value, sigma_hor, sigma_ver, exp_kernel_a, exp_kernel_b, exp_kernel_c, num_encounters, memory_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'generate-button':
        if gen_n_clicks > 0:

            # error checking
            if generation_error_found(memory_data, nom_ac_ids, num_encounters, cov_radio_value, 
                                        sigma_hor, sigma_ver, exp_kernel_a, exp_kernel_b, exp_kernel_c):
                return {}

            df_memory_data = pd.DataFrame(memory_data) 
            df = df_memory_data.loc[df_memory_data['encounter_id'] == nom_enc_id]

            generated_data = []
            for ac in nom_ac_ids:
                ac_df = (df.loc[df['ac_id'] == ac]).to_dict('records')
                
                # mean (nominal path) saved in enc_id=0
                generated_data += [{'encounter_id': 0, 'ac_id': ac, 'time': waypoint['time'],
                                   'xEast': waypoint['xEast'], 'yNorth': waypoint['yNorth'], 'zUp': waypoint['zUp']} 
                                   for waypoint in ac_df]
                                   
                # generate samples    
                kernel_inputs = [[waypoint['xEast'], waypoint['yNorth'], waypoint['zUp']] for waypoint in ac_df]
                ac_time = [waypoint['time'] for waypoint in ac_df]
                
                if cov_radio_value == 'cov-radio-diag':
                    cov = [ [sigma_hor, 0, 0], 
                            [0, sigma_hor, 0], 
                            [0, 0, sigma_ver] ]
                    waypoints_list = [np.random.multivariate_normal(mean,cov,int(num_encounters)) for mean in kernel_inputs]
                    generated_data += [{'encounter_id': enc_id+1, 'ac_id': ac, 'time': ac_time[i], 
                                        'xEast': waypoint[0], 'yNorth': waypoint[1], 'zUp': waypoint[2]} 
                                       for i,waypoints in enumerate(waypoints_list) for enc_id, waypoint in enumerate(waypoints)]

                    
                elif cov_radio_value == 'cov-radio-exp':                    
                    mean, cov = exp_kernel_func(kernel_inputs, exp_kernel_a, exp_kernel_b, exp_kernel_c)
                    waypoints_list = np.random.multivariate_normal(mean,cov,int(num_encounters))
                    waypoints_list = np.reshape(waypoints_list, (waypoints_list.shape[0], -1, 3))                
                    generated_data += [{'encounter_id': enc_id+1, 'ac_id': ac, 'time': ac_time[i], 
                                        'xEast': waypoint[0], 'yNorth': waypoint[1], 'zUp': waypoint[2]} 
                                       for enc_id, waypoints in enumerate(waypoints_list) for i, waypoint in enumerate(waypoints)]

                
            # if we need them to be sorted...
            # generated_data = sorted(generated_data, key=lambda k: k['encounter_id'])
            return generated_data

    return dash.no_update


@app.callback(Output('log-histogram-ac-1-xy', 'figure'),
              Output('log-histogram-ac-1-tz', 'figure'),
              Output('log-histogram-ac-2-xy', 'figure'),
              Output('log-histogram-ac-2-tz', 'figure'),
              Input('generated-encounters', 'data'),
              State('ac-ids', 'value'))
def on_generation_update_log_histograms(generated_data, ac_ids_selected):
    if generated_data == {}:
        return px.density_heatmap(), px.density_heatmap(), \
            px.density_heatmap(), px.density_heatmap()

    df = pd.DataFrame(generated_data)

    df_ac_1_interp = pd.DataFrame()
    df_ac_2_interp = pd.DataFrame()
    for enc_id in set(df['encounter_id']):
        print(enc_id)
        df_enc = df.loc[df['encounter_id'] == enc_id]
        
        df_enc_ac1_interp, _, _ = interpolate_df_time(df_enc, [1])
        df_ac_1_interp = df_ac_1_interp.append(df_enc_ac1_interp, ignore_index=True)
        df_enc_ac2_interp, _, _ = interpolate_df_time(df_enc, [2])
        df_ac_2_interp = df_ac_2_interp.append(df_enc_ac2_interp, ignore_index=True)   

    print("that took a while")

    viridis = px.colors.sequential.gray #Blues
    colors = viridis
    # colors = [  [0, viridis[0]],
    #             [1./10000, viridis[3]],
    #             [1./1000, viridis[5]],
    #             [1./100, viridis[7]],
    #             [1./10, viridis[9]],
    #             [1., viridis[11]]   ]
    
    fig_1_xy = px.density_heatmap(df_ac_1_interp, x='xEast', y='yNorth', nbinsx=100, nbinsy=100, 
                            title='AC 1: xEast vs yNorth', labels={'xEast':'xEast (NM)', 'yNorth':'yNorth (NM)'}, color_continuous_scale=colors)
    fig_1_tz = px.density_heatmap(df_ac_1_interp, x='time', y='zUp', nbinsx=100, nbinsy=100, 
                            # nbinsx=nbin_time_ac_1, nbinsy=nbin_zUp_ac_1, 
                            title='AC 1: Time vs zUp', labels={'time':'Time (s)', 'zUp':'zUp (ft)'}, color_continuous_scale=colors)

    fig_2_xy = px.density_heatmap(df_ac_2_interp, x='xEast', y='yNorth', nbinsx=100, nbinsy=100, 
                            title='AC 2: xEast vs yNorth', labels={'xEast':'xEast (NM)', 'yNorth':'yNorth (NM)'}, color_continuous_scale=colors)
    fig_2_tz = px.density_heatmap(df_ac_2_interp, x='time', y='zUp', nbinsx=100, nbinsy=100,
                            # nbinsx=nbin_time_ac_2, nbinsy=nbin_zUp_ac_2, 
                            title='AC 2: Time vs zUp', labels={'time':'Time (s)', 'zUp':'zUp (ft)'}, color_continuous_scale=colors)
    return fig_1_xy, fig_1_tz, fig_2_xy, fig_2_tz


# ##########################################################################################
# ##########################################################################################
@app.callback(Output('save-modal','is_open'),
                [Input('save-button', 'n_clicks'),
                Input('close-save-button', 'n_clicks'),
                Input('save-filename-button', 'n_clicks')])
def toggle_save_modal(save_n_clicks, close_n_clicks, save_file_n_clicks):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    
    if ctx == 'save-button':
        if save_n_clicks > 0:
            return True
    elif ctx == 'close-save-button':
        if close_n_clicks > 0:
            return False
    elif ctx == 'save-filename-button':
        if save_file_n_clicks > 0:
            return False

    return dash.no_update

@app.callback([Output('save-dat-div','style'),
                Output('save-json-div', 'style')],
                Input('file-checklist', 'value'))
def toggle_filename_inputs(checked_values):
    off = {'display':'none'}
    on = {'display':'inline-block'}
    
    if checked_values:
        if 'dat-item' in checked_values:
            if 'json-item' in checked_values:
                return on, on
            else:
                return on, off
        elif 'json-item' in checked_values:
            return off, on
    else:
        return off, off

    return dash.no_update, dash.no_update


@app.callback(Output('download-waypoints', 'data'),
                Input('save-filename-button', 'n_clicks'),
                [State('generated-encounters', 'data'),
                State('nominal-path-enc-ids', 'options'),
                State('nominal-path-ac-ids', 'options'),
                State('save-dat-filename', 'value'),
                State('file-checklist', 'value')],
                prevent_initial_call=True)
def on_click_save_dat_file(save_n_clicks, generated_data, nom_enc_ids, nom_ac_ids, dat_filename, files_to_save):
    
    if save_n_clicks > 0:
        if generated_data:
            if 'dat-item' in files_to_save:
                file_name = dat_filename if dat_filename else 'generated_waypoints.dat'
                file = open(file_name, mode='wb')

                df = pd.DataFrame(generated_data)

                # num encounters and num ac ids
                num_enc = len(nom_enc_ids) - 1
                np.array(num_enc, dtype=np.uint32).tofile(file)
                np.array(len(nom_ac_ids), dtype=np.uint32).tofile(file)

                for enc in range(1, len(nom_enc_ids)+1):
                    df_enc = df.loc[df['encounter_id'] == enc]
                    
                    # write initial waypoints to file first
                    df_initial = (df_enc.loc[df_enc['time'] == 0]).to_dict('records')
                    np.array([(initial['xEast'] * NM_TO_FT,\
                            initial['yNorth'] * NM_TO_FT,\
                            initial['zUp']) for initial in df_initial],\
                            dtype=np.dtype('float64, float64, float64')\
                            ).tofile(file)

                    # then write update waypoints to file
                    df_updates = df_enc.loc[df_enc['time'] != 0]
                    for ac in nom_ac_ids:
                        df_ac_updates = (df_updates.loc[df_updates['ac_id'] == ac['value']]).to_dict('records')
                        
                        np.array(len(df_ac_updates), dtype=np.uint16).tofile(file)
                        
                        np.array([(update['time'],\
                                update['xEast'] * NM_TO_FT,\
                                update['yNorth'] * NM_TO_FT,\
                                update['zUp']) for update in df_ac_updates],\
                                dtype=np.dtype('float64, float64, float64, float64')\
                                ).tofile(file)

                file.close()

                return dcc.send_file(file_name)
        else:
            print('Must generate an encounter set')

    return dash.no_update

@app.callback(Output('download-model', 'data'),
                Input('save-filename-button', 'n_clicks'),
                [State('generated-encounters', 'data'),
                State('cov-radio', 'value'),
                State('diag-sigma-input-hor', 'value'),
                State('diag-sigma-input-ver', 'value'),
                State('exp-kernel-input-a', 'value'),
                State('exp-kernel-input-b', 'value'),
                State('exp-kernel-input-c', 'value'),
                State('save-json-filename', 'value'),
                State('file-checklist', 'value')],
                prevent_initial_call=True)
def on_click_save_json_file(save_n_clicks, generated_data, cov_radio_val, sigma_hor, sigma_ver, a, b, c, json_filename, files_to_save):

    if save_n_clicks > 0:
        if generated_data:
            if 'json-item' in files_to_save:
                model_json = {}

                df = pd.DataFrame(generated_data) 
                df_enc = df.loc[df['encounter_id'] == 0]
                ac_ids = df_enc['ac_id'].unique()
            
                model_json['mean'] = {'num_ac': len(ac_ids)}

                for i, ac in enumerate(ac_ids):
                    ac_df = (df_enc.loc[df_enc['ac_id'] == ac]).to_dict('records')
                    model_json['mean'][i+1] = { 'num_waypoints': len(ac_df), 
                                                'waypoints': [] }
                    for waypoint in ac_df:
                        model_json['mean'][i+1]['waypoints'] += [{'time':  waypoint['time'], 
                                                'xEast':  waypoint['xEast'],
                                                'yNorth': waypoint['yNorth'],
                                                'zUp':    waypoint['zUp']}]
    
                if cov_radio_val == 'cov-radio-diag':
                    model_json['covariance'] = {
                        'type': 'diagonal',
                        'sigma_hor': sigma_hor,
                        'sigma_ver': sigma_ver}

                elif cov_radio_val == 'cov-radio-exp':
                    model_json['covariance'] = {
                        'type': 'exponential kernel',
                        'a': a,
                        'b': b,
                        'c': c,
                    }

                # script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
                # file_name = json_filename if json_filename else 'generation_model.json'
                # rel_path = "generated_models/"+file_name
                # abs_file_path = os.path.join(script_dir, rel_path)

                file_name = json_filename if json_filename else 'generation_model.json'
                with open(file_name, 'w') as outfile:
                    json.dump(model_json, outfile, indent=4)

                return dcc.send_file(file_name)
        else:
            print('Must generate an encounter set')

    return dash.no_update



# ##########################################################################################
# ##########################################################################################
@app.callback([Output('tab-1-graphs', 'style'), 
              Output('tab-2-graphs', 'style'), 
              #Output('tab-3-graphs', 'style'),
              Output('tab-4-graphs','style')],            
              Input('tabs', 'active_tab'))
def render_content(active_tab):
    # easy on-off toggle for rendering content
    on = {'display': 'block'}
    off = {'display': 'none'}

    if active_tab == 'tab-1':
        return on, off, off #, off
    elif active_tab == 'tab-2':
        return off, on, off #, off
    elif active_tab == 'tab-3':
        return off, off, off # on, off
    elif active_tab == 'tab-4':
        return off, off, on #, on
    
    if not active_tab:
        print("No tab actively selected")
    else:
        print("invalid tab")

    return dash.no_update

    
@app.callback([Output('slider-drag-output', 'hidden'),
              Output('slider-container', 'hidden')],
              Input('tabs','active_tab'))
def toggle_slider(active_tab):
    if active_tab == 'tab-3' or active_tab == 'tab-4':
        return True, True
    return False, False

@app.callback(Output('map-create-mode-div', 'style'),
                Input('tabs', 'active_tab'))
def toggle_map_create_mode_div(active_tab):
    on = {'display': 'block'}
    off = {'display': 'none'}

    if active_tab == 'tab-1' or active_tab == 'tab-2':
        return on
    elif active_tab == 'tab-4':
        return off

    return on

# @app.callback(Output('map-table-col', 'className'),
#                 Input('tabs','active_tab'))
# def adjust_margins_on_active_tab(active_tab):
#     if active_tab == 'tab-2':
#         return 'pl-5'

#     return 'pl-4'


if __name__ == '__main__':
    app.run_server(debug=True, port=8332)
    
