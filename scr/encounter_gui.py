import dash

from dash import dash_table
from dash import dcc
from dash import html

from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate

import dash_bootstrap_components as dbc
import dash_leaflet as dl

import collections

import plotly.express as px

import multiprocessing as mp
from itertools import repeat

import pandas as pd
from pandas.core.frame import DataFrame

import numpy as np

from scipy.interpolate import PchipInterpolator

import json
import base64
import pymap3d as pm
import re

from read_file import *
from generate_helpers import *
from parse_encounter_helpers import *
from memory_data_helpers import *

import time
import struct
import uuid

external_scripts = ['https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-MML-AM_CHTML']

app = dash.Dash(__name__, external_scripts=external_scripts)

def calculate_horizontal_vertical_speeds_df(df):
    dataf = df.copy()
    hor_speeds = []
    ver_speeds = []
    for ac_id in set(df['ac_id']):
        ac_id_data = df.loc[df['ac_id'] == ac_id]
        move_over_time = (np.roll(ac_id_data, -1, axis=0) - ac_id_data)[:-1]
        hor_speed = np.sqrt(move_over_time.xEast ** 2 + move_over_time.yNorth ** 2) / move_over_time['time'] * 3600
        hor_speeds += (np.append(0.0, round(hor_speed, 4))).tolist()
        ver_speed = move_over_time.zUp / move_over_time['time'] * 60
        ver_speeds += (np.append(0.0, round(ver_speed, 4))).tolist()
    dataf.loc[:, 'horizontal_speed'] = hor_speeds
    dataf.loc[:, 'vertical_speed'] = ver_speeds
    return dataf

def populate_lat_lng_xEast_yNorth(data, ref_data):
    for data_point in data:
        if data_point['xEast'] and data_point['yNorth']:
            # calculate lat long
            data_point['lat'], data_point['long'],_ = pm.enu2geodetic(data_point['xEast']*NM_TO_M, data_point['yNorth']*NM_TO_M,
                                         data_point['yNorth']*FT_TO_M if data_point['yNorth'] else ref_data['ref_alt']*FT_TO_M, 
                                         ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M, 
                                         ell=pm.Ellipsoid('wgs84'), deg=True)
        
        elif data_point['lat'] and data_point['long']:
            x, y,_ =  pm.geodetic2enu(data_point['lat'], data_point['long'],
                                         data_point['yNorth']*FT_TO_M if data_point['yNorth'] else ref_data['ref_alt']*FT_TO_M, 
                                         ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M, 
                                         ell=pm.Ellipsoid('wgs84'), deg=True)
            data_point['xEast'], data_point['yNorth'] = x*M_TO_NM, y*M_TO_NM
    return data


M_TO_NM = 0.000539957; NM_TO_M = 1/M_TO_NM
FT_TO_M = .3048; M_TO_FT = 1/FT_TO_M
FT_TO_NM = FT_TO_M*M_TO_NM
NM_TO_FT = 1/FT_TO_NM 
MB = 1000000

COLOR_LIST = ['blue', 'orange', 'green', 'red', 'black', 'purple']
DASHBOARD_LOGO = app.get_asset_url('dashboard_logo.png')

map_iconUrl = "https://dash-leaflet.herokuapp.com/assets/icon_plane.png"
map_marker = dict(rotate=True, markerOptions=dict(icon=dict(iconUrl=map_iconUrl, iconAnchor=[16, 16])))
map_patterns = [dict(repeat='15', dash=dict(pixelSize=0, pathOptions=dict(color='#000000', weight=5, opacity=0.9))),
                dict(offset='100%', repeat='0%', marker=map_marker)]

graph_card_style = {'width':'30rem', 'height':'32rem'}

def serve_layout():
    session_id = str(uuid.uuid4())

    return html.Div([
        #   memory store reverts to the default on every page refresh
        dcc.Store(id='session-id', data=session_id),

        dcc.Store(id='memory-data', data={}),

        dcc.Store(id='ref-data', data={'ref_lat': 40.63993,
                                    'ref_long': -73.77869,
                                    'ref_alt': 12.7}),

        dcc.Loading(parent_className='loading_wrapper', 
                children=[dcc.Store(id='generated-data', data={})],
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
                        width={"size": 'auto', "order": 3}),
            ],
            align='start',
            no_gutters=True
            ),
            fluid=True
        ),

        html.Br(),

        # Encounter and AC ID dropdown menus and Reference Point Div
        dbc.Container(
            dbc.Row([
                dbc.Col(dcc.Dropdown(id='encounter-ids', placeholder="Select an encounter ID",  className='m--15', multi=False), 
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
                    ],
                    style={'visibility':'visible'}),
                    html.Div(id='something', children='')
                ],
                width={"size": 'auto', "order": 4, 'offset':2},
                align='right')  
            ],
            align='left',
            justify='center',
            no_gutters=True),
        fluid=True
        ),

        html.Br(),

        dbc.Container([
            dbc.Row([
                dbc.Col(className='', children=[  
                    
                    dbc.Container([
                        # navigation tabs
                        dbc.Row([
                            html.Div([
                                dbc.Tabs(id="tabs",
                                        children=[
                                            dbc.Tab(id='tab-1', tab_id='tab-1', label='2d Graphs'), # label_style={'color':'#2c3e50'}), #, style={'height':'1rem', 'line-height':'.5rem'}),
                                            dbc.Tab(id='tab-2',tab_id='tab-2', label='3d Graph'),#  tab_style={'background':'#2c3e50'}), #, style={'height':'1rem', 'line-height':'.5rem'}),
                                            #dcc.Tab(id='tab3', label='Map', value='tab-3'),
                                            dbc.Tab(id='tab-4', tab_id='tab-4',label='Statistics') #, style={'height':'1rem', 'line-height':'.5rem', 'width':'10rem'}),
                                        ],
                                        active_tab='tab-1'),
                            ])
                        ],
                        no_gutters=True),
                    
                        dbc.Row([
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
                                                            dbc.Col(
                                                                dcc.Loading(parent_className='loading-graph-xy', 
                                                                children=[dcc.Graph(id='editable-graph-xy-slider', figure=px.line())],
                                                                type='circle',
                                                                color='white'
                                                                )  
                                                            )
                                                        ],justify='center')
                                                    ])
                                                ], 
                                                color='primary',
                                                style=graph_card_style),
                                            ], 
                                            width='auto'),
                                            dbc.Col([
                                                dbc.Card([
                                                    dbc.CardBody([
                                                        dbc.Row([
                                                            dbc.Col(html.H5("Time vs zUp", className="card-title-1"))
                                                        ],justify='center'),

                                                        dbc.Row([
                                                            dbc.Col(
                                                                dcc.Loading(parent_className='loading-graph-tz', 
                                                                children=[dcc.Graph(id='editable-graph-tz-slider', figure=px.line(), className='six columns')],
                                                                type='circle',
                                                                color='white'
                                                                )  
                                                            )
                                                        ],justify='center')
                                                    ])
                                                ], color='primary',
                                                style=graph_card_style),
                                            ], width='auto'),

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
                                                            dbc.Col(html.H5("Time vs Horizontal Distance", className="card-title-1"))
                                                        ],
                                                        justify='center'),

                                                        dbc.Row([
                                                            dbc.Col(
                                                                dcc.Loading(parent_className='loading-graph-tdistxy', 
                                                                children=[dcc.Graph(id='editable-graph-tdistxy-slider', figure=px.line())],
                                                                type='circle',
                                                                color='white'
                                                                ) 
                                                            )
                                                        ],
                                                        justify='center')
                                                    ])
                                                ],
                                                color='primary',
                                                style=graph_card_style
                                            )],
                                            width='auto'),
                                            
                                            dbc.Col(children=[
                                                dbc.Card([
                                                    dbc.CardBody([
                                                        dbc.Row([
                                                            dbc.Col(html.H5("Time vs Vertical Distance", className="card-title-1"))
                                                        ],justify='center'),

                                                        dbc.Row([
                                                            dbc.Col(
                                                                dcc.Loading(parent_className='loading-graph-tdistz', 
                                                                children=[dcc.Graph(id='editable-graph-tdistz-slider', figure=px.line(), className='two columns')],
                                                                type='circle',
                                                                color='white'
                                                                ) 
                                                            )
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
                                                            dbc.Col(
                                                                dcc.Loading(parent_className='loading-graph-tspeedxy', 
                                                                children=[dcc.Graph(id='editable-graph-tspeedxy-slider', figure=px.line())],
                                                                type='circle',
                                                                color='white'
                                                                ) 
                                                            )
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
                                                            dbc.Col(
                                                                dcc.Loading(parent_className='loading-graph-tspeedz', 
                                                                children=[dcc.Graph(id='editable-graph-tspeedz-slider', figure=px.line())],
                                                                type='circle',
                                                                color='white'
                                                                ) 
                                                            )
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
                                        dbc.Col(className='pr-3', children=[
                                            dbc.Card([
                                                    dbc.CardBody([
                                                        dbc.Row([
                                                            dbc.Col(html.H5("xEast vs yNorth vs zUp", className="card-title-1"))
                                                        ],justify='center'),

                                                        dbc.Row([
                                                            dbc.Col(
                                                                dcc.Loading(parent_className='loading-graph-xyz', 
                                                                children=[dcc.Graph(id='editable-graph-xyz-slider', figure=px.line_3d())],
                                                                type='circle',
                                                                color='white'
                                                                )    
                                                            )
                                                        ],justify='center')
                                                    ])
                                                ], 
                                                color='primary',
                                                style={'width':'60.5rem', 'height':'39rem'}
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
                                                        dbc.Col(
                                                            dcc.Loading(parent_className='loading-hist-ac-1-xy', 
                                                            children=[dcc.Graph(id='log-histogram-ac-1-xy', figure=px.density_heatmap())],
                                                            type='circle',
                                                            color='white'
                                                            ) 
                                                        )
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
                                                        dbc.Col(
                                                            dcc.Loading(parent_className='loading-hist-ac-1-tz', 
                                                            children=[dcc.Graph(id='log-histogram-ac-1-tz', figure=px.density_heatmap())],
                                                            type='circle',
                                                            color='white'
                                                            ) 
                                                        )
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
                                                        dbc.Col(
                                                            dcc.Loading(parent_className='loading-hist-ac-2-xy', 
                                                            children=[dcc.Graph(id='log-histogram-ac-2-xy', figure=px.density_heatmap())],
                                                            type='circle',
                                                            color='white'
                                                            ) 
                                                        )
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
                                                        dbc.Col(
                                                            dcc.Loading(parent_className='loading-hist-ac-2-tz', 
                                                            children=[dcc.Graph(id='log-histogram-ac-2-tz', figure=px.density_heatmap())],
                                                            type='circle',
                                                            color='white'
                                                            )    
                                                        )
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
                
                dbc.Col(className='pl-3', children=[
                    html.Div(id='map-create-mode-div', children=[
                        dbc.Row([
                                dbc.Card(id='map-create-card', children=[
                                    dbc.CardBody([
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
                                            dbc.Card(id='create-mode-card', children=[
                                                dbc.CardBody([
                                                    dbc.Row([
                                                        dbc.Col([
                                                            dbc.Button('Start New Nominal Path', id='create-new-button', className='ml-2', n_clicks=0, color='primary',# outline=True,
                                                                style={'display':'none'}), 
                                                        ], width=5),                                                  
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
                                                    ],
                                                    style={'display':'none'}),

                                                ],
                                                style={'padding':'.5rem'})
                                            ],
                                            color='light',
                                            style={'width':'38rem', 'height':'10rem', 'margin-left':'15px', 'margin-top':'10px', 'display':'none'})
                                        ])
                                    ]),
                                ],
                                color='primary',
                                style={'width':'40.3rem', 'height':'33rem'}
                            )
                        ])
                    ],
                    style={'display':'block'}),

                    html.Br(),

                    html.Div(id='data-table-div', children =[
                        dbc.Row([
                            dbc.Card(id='data-table-card', children=[
                                dbc.CardBody([
                                    dbc.Row([
                                        html.Div([dash_table.DataTable(
                                            id = 'editable-table',
                                            columns = [
                                                {"name": 'AC ID', "id": 'ac_id', 'editable': True, 'type':'numeric'},
                                                {"name": 'Time (s)', "id": 'time', 'editable': True, 'type':'numeric', 'format': {'specifier': '.2~f'}},
                                                {"name": 'xEast (NM)', "id": 'xEast', 'editable': True, 'type':'numeric', 'format': {'specifier': '.2~f'}},
                                                {"name": 'yNorth (NM)', "id": 'yNorth', 'editable': True, 'type':'numeric', 'format': {'specifier': '.2~f'}},
                                                {"name": f'latitude ({chr(176)})', "id": 'lat', 'editable': True, 'type':'numeric', 'format': {'specifier': '.3~f'}},
                                                {"name": f'longitude ({chr(176)})', "id": 'long', 'editable': True, 'type':'numeric', 'format': {'specifier': '.3~f'}},
                                                {"name": 'zUp/altitude   (ft)', "id": 'zUp', 'editable': True,'type':'numeric', 'format': {'specifier': '.2~f'}},
                                                {"name": 'Horizontal Speed  (kt)', "id": 'horizontal_speed', 'editable': False, 'type':'numeric', 'format': {'specifier': '.2~f'}},
                                                {"name": 'Vertical Speed (ft/min)', "id": 'vertical_speed', 'editable': False, 'type':'numeric', 'format': {'specifier': '.2~f'}}],
                                            editable = True,
                                            row_deletable = True,
                                            data=[], 
                                            style_table={'width': '38.5rem', 'display': "block", 'margin-left':'10px', 'overflowY': 'scroll'}, #'height': '35rem',
                                            style_cell={'fontSize':11, 'height':'auto', 'whiteSpace':'normal'})], 
                                        )
                                    ]),
                                ]),
                                dbc.CardFooter([
                                    dbc.Button('Add Row', id='add-rows-button', className='ml-0', n_clicks=0, color='light'),
                                    dbc.Button('DONE', id='done-add-rows-button', className='ml-1', n_clicks=0, color='light', style={'display':'none'}),
                                    dbc.Button('Update Speeds', id='update-speeds-button', className='ml-4', n_clicks=0, color='light')
                                ]),
                            ], 
                            color='primary',
                            style={'width':'40.3rem', 'height':'9rem'}),
                            
                        ])
                    ],
                    style={'display':'block'})

                ], 
                width='auto',
                style={'margin-left':'0px'})
            ], 
            no_gutters=True,
            style={'margin-left':'-10px'})
        ], 
        fluid=True),

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
                    dbc.Button("SET REF POINT", id="set-ref-button", color='success', className="ml-auto")
                    ]
                ),
            ],
            id='ref-point-modal', is_open=False, size="md",
            backdrop='static',  # Modal to not be closed by clicking on backdrop
            centered=True,  # Vertically center modal 
            keyboard=True,  # Close modal when escape is pressed
            fade=False)
        ]),

        # pop-up window for generation
        html.Div(id='gen-modal-div', children=[
            dbc.Modal([
                dbc.ModalHeader("Generate an Encounter Set"),

                html.Br(),
                html.Br(),
                html.Div([
                    html.Label([
                        dcc.Upload(id='load-model', children = 
                                dbc.Button('Load Model (.json)', id='load-model-button', n_clicks=0))
                    ])
                ], style={"margin-left": "20px", 'display':'inline-block', 'margin-top':'15px'}),
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
                    dcc.RadioItems(id='cov-radio', 
                        options=[{'label': 'Diagonal', 'value': 'cov-radio-diag'},
                                {'label': 'Exponential Kernel', 'value': 'cov-radio-exp'}],
                        # value='cov-radio-exp',
                        inputStyle={"margin-right": "5px"},
                        labelStyle={'display': 'inline-block', "margin-right": "10px"},
                        style={"margin-left": "15px"}),
                    
                    html.Span(
                        "?",
                        id="popover-target",
                        style={"textAlign": "center", "font-size": "12px", 'font-weight': "bold",
                                "border-radius": "90%", "height": "16px", "width": "16px", "color": "white", "background-color": "#727272", 
                                "cursor": "pointer", "display": "inline-block"
                        }, className="dot"),
                    dbc.Popover(
                        children=[dbc.PopoverBody("")],
                        id="popover-content",
                        style={"display": "none", 'width':'25rem'},
                        trigger="click", # is_open=False,
                        target="popover-target", placement="right"),
                    
                ], 
                style={"margin-left": "20px"}, className  = 'row'),

                
                html.Div(id='cov-diag-input-container', children=[
                    html.Div([
                        #dcc.Markdown(("""Enter Parameters:"""), style={"margin-left": "20px"}),
                        dbc.Row(className='', children=[
                            dbc.Col(className='', children=[
                                html.H5('$\sigma_h$', style={"color": "#3273F6"}),
                                dbc.Input(id='diag-sigma-input-hor', type='number', placeholder='default sigma_hor = 0.05', debounce=True, pattern=u"^(0?\.?\d+)$", value=0.05),
                            ], width=2),
                            dbc.Col(className='', children=[
                                html.H5('$\sigma_v$', style={"color": "#3273F6"}),
                                dbc.Input(id='diag-sigma-input-ver', type='number', placeholder='default sigma_ver = 10.0', debounce=True, pattern=u"^(0?\.?\d+)$", value=10.0),
                            ], width=2)
                        ], 
                        no_gutters=False)
                    ],
                    style={"margin-left": "35px"}) 
                ],
                style={"display":"none"}, className  = 'row'),

                html.Div(id='cov-exp-kernel-input-container', children=[
                    html.Div([
                        #dcc.Markdown(("""Enter Parameters:"""), style={"margin-left": "20px"}),
                        dbc.Row(className='', children=[
                            dbc.Col(className='', children=[
                                html.H5('$l$', style={"color": "#3273F6"}),
                                dbc.Input(id='exp-kernel-input-a', type='number', placeholder='param_a', debounce=True, pattern=u"^(0?\.?\d+)$", value=15.0),
                            ], width=2),
                            dbc.Col(className='', children=[
                                html.H5('$w_h$', style={"color": "#3273F6"}),
                                dbc.Input(id='exp-kernel-input-b', type='number', placeholder='param_b', debounce=True, pattern=u"^(0?\.?\d+)$", value=1.0),
                            ], width=2),
                            dbc.Col(className='', children=[
                                html.H5('$w_v$', style={"color": "#3273F6"}),
                                dbc.Input(id='exp-kernel-input-c', type='number', placeholder='param_c', debounce=True, pattern=u"^(0?\.?\d+)$", value=100.0),
                            ], width=2)
                        ], 
                        no_gutters=False)
                    ],
                    style={"margin-left": "35px"})
                ],
                style={"display":"none"}, className  = 'row'), #, "margin-bottom":"10px"}

                
                # number of encounter sets to generate
                html.Br(),
                dcc.Markdown(("""Number of Encounters to Generate:"""), style={'font-weight': 'bold',"margin-left": "20px"}),
                dbc.Input(id='num-encounters-input', type='number', placeholder='',
                    debounce=True,# value=100,
                    pattern=u"^(\d+)$",
                    style={'margin-left':'20px', "width": "40%"}),
                
                # generation progress bar
                html.Br(),

                html.Br(),

                dbc.ModalFooter(children=[
                    dbc.Button("CLOSE", id="close-button"),
                    #dbc.Spinner(size='md', spinnerClassName='ml-auto', children=[html.Div(id='gen-spinner-output', children='nothin')]), #html.Div(id='gen-spinner-output')),
                    dbc.Button("GENERATE", id="generate-button", color='success', className="ml-auto", n_clicks=0)
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
        html.Div(id='save-modal-div', children=[
            dbc.Modal([
                dbc.ModalHeader("Save Generated Encounter Set", style={'font-size':'1000px'}), # className='w-100'),
                html.Br(),
                html.Div([
                    dcc.Markdown(("""Select Files to Save: """), style={'font-size': '1em', "margin-left": "5px"}),
                    dcc.Checklist(id='file-checklist', options=[
                        {'label': 'Generated Waypoints (.dat)', 'value': 'dat-item'},
                        {'label': 'Model (.json)', 'value': 'json-item'}],
                        #value=['dat-item'],
                        inputStyle={"margin-right": "8px"},
                        labelStyle={'display': 'block',"margin-right": "10px", 'margin-top':'3px', 'font-size': '1em'},
                        style={"margin-left": "10px"}),
                ], style={"margin-left": "20px"}, className  = 'row'),
                html.Br(),
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            dcc.Markdown(("""Save waypoints as:"""), style={"margin-left": "20px", "font-size":"1em"}),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Input(id='save-dat-filename', type='text', placeholder='filename.dat',
                                        debounce=True, pattern=u"\w+\.dat", value='generated_waypoints.dat',
                                        style={"margin-left": "20px", "width": "100%", "font-size":"1em"})
                                ], width=6),
                                dbc.Col([
                                    dcc.RadioItems(id='dat-file-units', 
                                        options=[{'label': 'ENU', 'value': 'dat-units-enu'},
                                                {'label': 'GEO', 'value': 'dat-units-geo'}],
                                        value='dat-units-enu',
                                        inputStyle={"margin-right": "5px"},
                                        labelStyle={'display': 'inline-block', "margin-right": "10px"},
                                        style={'margin-left':'10px'})
                                ], width=4)
                            ]),
                        ])
                    ],
                    style={'margin-left':'0px'})
                ],
                id='save-dat-div', className  = 'row', style={'display':'none'}),
                html.Div([
                    html.Div([
                        dcc.Markdown(("""Save model as:"""), style={"margin-left": "20px", "font-size":"1em", "margin-top":"5px"}),
                        dbc.Input(id='save-json-filename', type='text', placeholder='filename.json',
                            debounce=True, pattern=u"\w+\.json", value='generation_model.json',
                            style={"margin-left": "20px", "width": "50%", "font-size":"1em"}),
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

app.layout = serve_layout()

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
        fig_xy = px.line()
        fig_tz = px.line()
        fig_tspeedxy = px.line()
        fig_tspeedz = px.line()
        fig_xyz = px.line_3d()
        fig_tdistxy = px.line()
        fig_tdistz = px.line()
    
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
            margin=margin,
            legend=dict(yanchor="top",y=0.99,xanchor="right",x=.99))        
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
            yaxis_title='Speed (ft/min)', yaxis_range=[min_values[5]-5, max_values[5]+5],
            margin=margin)
        fig_xyz.update_layout(
            scene = {'xaxis': {'title':'xEast (NM)', 
                               'range':[min(min_values[1],min_values[2])-0.2, max(max_values[1], max_values[2])+0.2]},
                    'yaxis': {'title':'yNorth (NM)',
                              'range':[min(min_values[1],min_values[2])-0.2, max(max_values[1], max_values[2])+0.2]},
                    'zaxis': {'title':'zUp (ft)',
                              'range':[min_values[3]-50, max_values[3]+50]}},
            width=930, height=565, margin=dict(l=0, r=0, b=80, t=0, pad=10))
        fig_tdistxy.update_layout(
            xaxis_title = 'Time (s)', 
            yaxis_title = 'Distance (NM)',
            margin=margin),
        fig_tdistz.update_layout(
            xaxis_title = 'Time (s)', 
            yaxis_title = 'Distance (ft)',
            margin=margin),

        return 'Time: {} (s)'.format(t_value), t_value, fig_xy, fig_tz, fig_tspeedxy, fig_tspeedz, fig_xyz, fig_tdistxy, fig_tdistz, min_values[0], max_values[0]


###########################################################################################
##########################################################################################


@app.callback(Output('memory-data', 'data'),
                [Input('load-waypoints', 'filename'),
               Input('create-mode', 'n_clicks'),
               Input('end-new-button', 'n_clicks'),
               Input('generated-data', 'data'),
               Input('ref-data', 'data'),
               Input('load-model', 'contents')],
               State('editable-table', 'data'),
               State('load-waypoints-button', 'n_clicks'),
               State('load-waypoints', 'contents'))
def update_memory_data(loaded_filename, create_n_clicks, end_new_n_clicks, generated_data, ref_data, model_contents, table_data, upload_n_clicks, waypoints_contents):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'create-mode' and create_n_clicks > 0:
        return {}

    elif ctx == 'end-new-button' and end_new_n_clicks > 0: 
        encounters_data, encounter_byte_indices, num_ac, num_encounters = convert_created_data(table_data)

        return {'encounters_data': str(encounters_data),
                'encounter_indices': encounter_byte_indices,
                'ac_ids': [ac for ac in range(1, num_ac+1)],
                'num_encounters': num_encounters,
                'type':'created'}
    
    elif ctx == 'load-waypoints' and upload_n_clicks > 0:
        if not loaded_filename:
            return {}

        encounter_byte_indices, num_ac, num_encounters = parse_dat_file_and_set_indices(loaded_filename) 

        return {'filename':loaded_filename,
                'encounter_indices': encounter_byte_indices,
                'ac_ids': [ac for ac in range(1, num_ac+1)],
                'num_encounters': num_encounters,
                'type':'loaded'}

            
    elif ctx == 'generated-data':
        if generated_data != {} and ref_data != {}:
            return {'filename': generated_data['filename'],
                    'encounter_indices':generated_data['encounter_indices'],
                    'ac_ids':generated_data['ac_ids'],
                    'num_encounters':generated_data['num_encounters'],
                    'type':'generated'}

    elif ctx == 'load-model':
        if model_contents is not None:
            encounters_data, encounter_byte_indices, num_ac, num_encounters = convert_json_file(model_contents)
    
            return {'encounters_data': str(encounters_data),
                    'encounter_indices': encounter_byte_indices,
                    'ac_ids': [ac for ac in range(1, num_ac+1)],
                    'num_encounters': num_encounters,
                    'type':'json'}
        
    elif ctx == 'ref-data':
        # reference point has changed
        if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_alt']:
            return dash.no_update

    return dash.no_update




@app.callback([Output('editable-table', 'data'),
               Output('editable-table', 'columns')],
              [Input('load-waypoints-button', 'n_clicks'),
               Input('encounter-ids', 'value'),
               Input('ac-ids', 'value'),
               Input('update-speeds-button', 'n_clicks'),
               Input('add-rows-button', 'n_clicks'),
               Input('done-add-rows-button', 'n_clicks'),
               Input('create-mode', 'n_clicks'),
               Input('create-new-button', 'n_clicks'),
               Input('end-new-button', 'n_clicks'),
               Input('marker-layer', 'children')],
              [State('editable-table', 'data'),
               State('editable-table', 'columns'),
               State('ac-index', 'value'),
               State('time-interval-input', 'value'),
               State('create-mode-zUp-input', 'value'),
               State('ref-data', 'data'),
               State('memory-data', 'data')])
def update_data_table(upload_n_clicks, encounter_id_selected, ac_ids_selected, update_speeds_n_clicks, add_rows_n_clicks, done_add_rows_n_clicks,\
                      create_n_clicks, start_new_n_clicks, end_new_n_clicks, current_markers, table_data, columns, ac_value, interval, zUp_input, ref_data,\
                      memory_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    # print('update_data_table: ', ctx)


    if ctx == 'load-waypoints' and upload_n_clicks > 0:
        return [], columns
        
    elif ctx == 'encounter-ids' or ctx == 'ac-ids':
        if encounter_id_selected is None or encounter_id_selected == []:
            return [], columns
        else:
            # encounter IDs or ac IDs have been updated or loaded in
            if ctx == 'encounter-ids':
                enc_data = parse_enc_data(memory_data, [encounter_id_selected], memory_data['ac_ids'], ref_data)
            else:
                # ac selected changed
                enc_data = parse_enc_data(memory_data, [encounter_id_selected], ac_ids_selected, ref_data)
            
            enc_data_df = pd.DataFrame(enc_data)
            enc_data_df_sorted = enc_data_df.sort_values(by=['ac_id', 'time'])
            enc_data_df = calculate_horizontal_vertical_speeds_df(enc_data_df_sorted)
            return enc_data_df.to_dict('records'), columns

    elif ctx == 'create-mode' and create_n_clicks > 0 and end_new_n_clicks == 0:
        # wipe all data
        return [], columns

    elif ctx == 'update-speeds-button' and update_speeds_n_clicks > 0:
        df = pd.DataFrame(table_data) #.apply(pd.to_numeric, errors='coerce').fillna(0)
        df = calculate_horizontal_vertical_speeds_df(df)
        return df.to_dict('records'), columns

    elif ctx == 'add-rows-button' and create_n_clicks == 0:
        if add_rows_n_clicks > 0:
            # add an empty row
            table_data.append({col["id"]: '' for col in columns})
        return table_data, columns
    elif ctx == 'done-add-rows-button' and done_add_rows_n_clicks > 0:
        # FIXME: we need to add an alert check here to make sure that the user
        # inputs xEast, yNorth and zUp at least so we can calculate horizontal vertical speeds
        data = populate_lat_lng_xEast_yNorth(table_data, ref_data)
        df = pd.DataFrame(data).apply(pd.to_numeric, errors='coerce').fillna(0)
        df = df.sort_values(by=['ac_id', 'time'])
        df = calculate_horizontal_vertical_speeds_df(df)
        return df.to_dict('records'), columns

    elif ctx == 'marker-layer' and create_n_clicks > 0 and start_new_n_clicks > 0:
        if ac_value is None\
            or not ref_data['ref_lat'] or not ref_data['ref_long']\
            or not ref_data['ref_alt'] or not interval or not zUp_input:
                return dash.no_update, dash.no_update
        
        
        df = pd.DataFrame(table_data)
        if 'ac_id' not in df.keys() or (len(df.loc[df['ac_id'] == ac_value]) != len(current_markers)):
            timestep = 0
            # if len(data) > 0:
            #     df = pd.DataFrame(data)
            if 'ac_id' in df.keys():
                if ac_value in df['ac_id'].tolist():
                    df_ac = df.loc[df['ac_id'] == ac_value]
                    last_timestep = max(df_ac['time'])
                    timestep = last_timestep+interval
                
            # in creative mode and user has created another marker 
            # we add each marker to the data as it is created 
            # so we only have to grab last marker in the list
            pos = current_markers[-1]['props']['position']
            xEast, yNorth, _ = pm.geodetic2enu(pos[0], pos[1], zUp_input*FT_TO_M, 
                                                    ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M,
                                                    ell=pm.Ellipsoid('wgs84'), deg=True)
            marker_dict = {'encounter_id': 0, 'ac_id': ac_value, 'time': timestep, 
                            'xEast': xEast*M_TO_NM, 'yNorth': yNorth*M_TO_NM,
                            'lat':pos[0], 'long':pos[1], 'zUp': zUp_input,
                            'horizontal_speed': 0, 'vertical_speed': 0}
            table_data.append(marker_dict)
        else:
            # an already existing marker was dragged
            # and therefore its position in data table needs to get updated

            df = pd.DataFrame(table_data)

            waypoint = 0
            for i, data_point in df.iterrows():
                if data_point['ac_id'] == ac_value:
                    pos = current_markers[waypoint]['props']['position']
                    xEast, yNorth, zUp = pm.geodetic2enu(pos[0], pos[1], zUp_input*FT_TO_M, 
                                                            ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M,
                                                            ell=pm.Ellipsoid('wgs84'), deg=True)
                    data_point['xEast'] = xEast*M_TO_NM
                    data_point['yNorth'] = yNorth*M_TO_NM
                    data_point['zUp'] = zUp_input
                    data_point['lat'] = pos[0]
                    data_point['long'] = pos[1]
                    df.at[i] = data_point
                    waypoint += 1

            table_data = df.to_dict('records')

        return table_data, columns
        
    elif ctx == 'end-new-button':
        if end_new_n_clicks > 0: 
            if table_data != []:
                df = pd.DataFrame(table_data) 
                df = calculate_horizontal_vertical_speeds_df(df)
                return df.to_dict('records'), columns
        
    return dash.no_update, dash.no_update


@app.callback(Output('editable-table','style_table'),
                [Input('editable-table','data'),
                Input('tabs','active_tab'),
                State('editable-table','style_table')])
def toggle_data_table_height(data, active_tab, table_style):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]   
    
    if ctx == 'tabs':
        if active_tab == 'tab-4':
            table_style['display'] = 'none'
        else:
            table_style['display'] = 'block'

        return table_style

    elif ctx == 'editable-table':
        height = 3 + (len(data) * 2)
        table_style['height'] = str(height) + 'rem' if height < 25 else '25rem'
        return table_style

    return dash.no_update


@app.callback(#[Output('editable-table','style_table'),
               [Output('update-speeds-button', 'style'),
               Output('add-rows-button', 'style'),
               Output('done-add-rows-button', 'style'),
               Output('add-rows-button', 'n_clicks'),
               Output('done-add-rows-button', 'n_clicks'),
               Output('data-table-div', 'style')],
              [Input('add-rows-button', 'n_clicks'),
               Input('done-add-rows-button', 'n_clicks'),
               Input('tabs','active_tab')])
               #State('editable-table','data')) 
def toggle_data_table_buttons(add_rows_n_clicks, done_add_rows_n_clicks, active_tab): #, data):

    #table_on = {'width': '39rem', 'height': str(len(data) * 2) + 'rem', 'margin-left': "10px", 'display': "block", 'overflowY': 'scroll'}
    speeds_button_on = {'margin-left':'15px', 'display':'inline-block'}
    add_row_button_on = {'margin-left':'15px', 'display': 'inline-block'}
    done_button_on = {'margin-left':'10px', 'display':'inline-block', 'color':'white', 'background-color': '#5cb85c', 'border-color': '#5cb85c'}
    off = {'display': "none"}
    on = {'display': "block"}
    reset_add_rows_n_clicks, reset_done_add_rows_n_clicks = add_rows_n_clicks, done_add_rows_n_clicks

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]   

    if ctx == 'tabs':
        if active_tab == 'tab-4':
            return off, off, off, reset_add_rows_n_clicks, reset_done_add_rows_n_clicks, off
        return speeds_button_on, add_row_button_on, off, reset_add_rows_n_clicks, reset_done_add_rows_n_clicks, on
    if ctx == 'add-rows-button' and add_rows_n_clicks > 0:
        return  off, add_row_button_on, done_button_on, reset_add_rows_n_clicks, 0, on
    if ctx == 'done-add-rows-button' and done_add_rows_n_clicks > 0:
        return speeds_button_on, add_row_button_on, off, 0, reset_done_add_rows_n_clicks, on

    # if ctx == 'editable-table':
    #     table_on['height'] = str(len(data) * 2) + 'rem'
    #     return table_on, speeds_button_on, add_row_button_on, off, dash.no_update, dash.no_update, on

    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update


@app.callback(Output('data-table-card', 'style'),
                Input('editable-table','style_table'),
                [State('data-table-card', 'style')],
                preventInitialCallback=True)
def adjust_height_of_data_table_card(table_style, card_style):
    if 'height' in table_style.keys():
        val = table_style['height'].split('r')[0]
        new_height = int(val) + 6
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
               Input('end-new-button', 'n_clicks')],
               State('encounter-ids', 'options'))
def update_encounter_dropdown(memory_data, end_new_n_clicks, options):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    # print('update_encounter_dropdown ctx: ', ctx)
    
    if ctx == 'memory-data':
        if memory_data == {}:
            return []

        num_encounters = memory_data['num_encounters']
        data_type = memory_data['type']

        if data_type == 'loaded': 
            # no encounter 0 or nominal path to account for
            enc_range = range(1, num_encounters+1)
        else: 
            enc_range = range(num_encounters)
            
        options = [{'value': encounter_id, 'label': 'Encounter '+ str(int(encounter_id)) if encounter_id != 0 else 'Nominal Encounter'} for encounter_id in enc_range]
        return options

    # elif ctx == 'create-mode' and create_n_clicks > 0:
    #     return []
    
    elif ctx == 'end-new-button' and end_new_n_clicks > 0:
        encounter_value = 0
        new_option = {'value': encounter_value, 'label': 'Encounter '+ str(encounter_value) if encounter_value != 0 else 'Nominal Encounter'}
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
               State('memory-data', 'data')])
def update_ac_dropdown(upload_n_clicks, create_n_clicks, encounter_id_selected, end_new_n_clicks, ac_value, options, start_new_n_clicks, memory_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    
    # print('update_ac_dropdown: ', ctx)

    if ctx == 'load-waypoints-button':
        if upload_n_clicks > 0:
            return []  

    elif ctx == 'encounter-ids':
        if encounter_id_selected == []:
            return []
        else:
            #if (upload_n_clicks > 0 and end_new_n_clicks == 0) or generate_n_clicks > 0 or load_model_n_clicks > 0:
            if memory_data != {}:
                dropdown_options = [{'value': ac_id, 'label': 'AC '+ str(ac_id)} for ac_id in memory_data['ac_ids']]
                return dropdown_options
    
    elif ctx == 'create-mode':
        if create_n_clicks > 0 and start_new_n_clicks == 0 and end_new_n_clicks == 0:
            return []  

    elif ctx == 'end-new-button':
        if end_new_n_clicks > 0:
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
               Input('ref-data', 'data')],
               [State('ac-index', 'value'),
               State('ac-ids', 'value'),
               State('memory-data', 'data')])
def update_dropdowns_value(encounter_id_selected, upload_n_clicks, create_n_clicks, start_new_n_clicks, end_new_n_clicks, generate_n_clicks, ref_data, ac_value, ac_selected,\
                            memory_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    # print('update_dropdowns_value: ', ctx)
    clear_enc_val, clear_ac_val = [], []
    
    if ctx == 'load-waypoints-button':
        if upload_n_clicks > 0:
            return clear_enc_val, clear_ac_val
    elif ctx == 'encounter-ids':
        if encounter_id_selected is None or encounter_id_selected == []:
            return clear_enc_val, clear_ac_val

        return encounter_id_selected, [ac_id for ac_id in memory_data['ac_ids']]

    elif ctx == 'create-mode' and create_n_clicks > 0:
        return clear_enc_val, clear_ac_val

    elif ctx == 'create-new-button' and start_new_n_clicks > 0:
        return dash.no_update, ac_selected

    elif ctx == 'end-new-button' and end_new_n_clicks > 0:
        if ac_value is None: 
            print("Enter an AC ID to create new nominal path")
        else:
            ac_selected.append(ac_value)
            return 0, ac_selected #[encounter_value], 

    elif ctx == 'generate-button':
        # entered generation mode - clear dropdown values
        if generate_n_clicks > 0:
            return clear_enc_val, clear_ac_val

    elif ctx == 'ref-data':
        return clear_enc_val, clear_ac_val

    return dash.no_update, dash.no_update


@app.callback([Output('encounter-ids', 'disabled'),
               Output('ac-ids', 'disabled')],
              [Input('create-new-button', 'n_clicks'),
               Input('end-new-button', 'n_clicks'),
               Input('load-waypoints-button', 'n_clicks'),
               Input('ref-data', 'data')])
def creative_mode_disable_dropdowns(start_new_n_clicks, end_new_n_clicks, upload_n_clicks, ref_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'create-new-button' and start_new_n_clicks > 0:
        return True, True
    elif ctx == 'end-new-button' and end_new_n_clicks > 0:
        return False, False
    elif ctx == 'load-waypoints-button' and upload_n_clicks > 0:
        return False, False
    elif ctx == 'ref-data':
        if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
            # no trajectories should be selected if there isn't a ref point
            return True, True
        else:
            return False, False

    return dash.no_update, dash.no_update


# ##########################################################################################
# ##########################################################################################

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
def toggle_create_mode(upload_n_clicks, create_n_clicks, exit_create_n_clicks, start_new_n_clicks, end_new_n_clicks,\
                        create_style, start_new_style, exit_create_style, create_mode_div_style, end_new_style, create_card_style, map_create_style):
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

        if ctx == 'create-new-button' and start_new_n_clicks > 0:
            reset_end_new_clicks = 0

            create_mode_div_style['display'] = 'block'
            end_new_style['display'] = 'block'
            create_card_style['display'] = 'block'
            
        if ctx == 'end-new-button' and end_new_n_clicks > 0:
            reset_start_new_clicks = 0

            create_mode_div_style['display'] = 'none'
            end_new_style['display'] = 'none'
            
        if ctx == 'exit-create-mode' and exit_create_n_clicks > 0:
            reset_create_clicks = 0
            reset_start_new_clicks, reset_end_new_clicks = 0, 0

            start_new_style['display'], exit_create_style['display'] = 'none', 'none'
            create_mode_div_style['display'] = 'none'
            end_new_style['display'] = 'none'
            create_card_style['display'] = 'none'
            map_create_style['height']  = '33rem'
            create_style['display'] = 'block'
            
            
        if ctx == 'load-waypoints-button' and upload_n_clicks > 0:
            reset_create_clicks, reset_exit_create_clicks = 0, 0
            reset_start_new_clicks, reset_end_new_clicks = 0, 0

            start_new_style['display'], exit_create_style['display'] = 'none', 'none'
            create_mode_div_style['display'] = 'none'
            end_new_style['display'] = 'none'
            create_card_style['display'] = 'none'
            map_create_style['height']  = '33rem'
            
    return reset_create_clicks, reset_exit_create_clicks, reset_start_new_clicks, reset_end_new_clicks,\
            create_style, start_new_style, exit_create_style, create_mode_div_style, end_new_style, create_card_style, map_create_style


@app.callback(Output('ac-index', 'value'),
              Input('exit-create-mode', 'n_clicks'),
              Input('load-waypoints-button', 'n_clicks'))
def exit_creative_mode_reset_ac_index(exit_n_clicks, upload_n_clicks):
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
              Input('ref-data', 'data'))
def center_map_around_ref_input(ref_data):
    if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
        # ref point was cleared - so reset to center of US and zoom out
        return (39,-98), 4
    return (ref_data['ref_lat'], ref_data['ref_long']), 11.5


@app.callback(Output('polyline-layer', 'children'),
              [Input('editable-table', 'data'),
              Input('ref-data', 'data')],
              State('polyline-layer', 'children'))    
def update_map(data, ref_data, current_polylines):
    if data is None:
        return dash.no_update

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'editable-table': # or ctx == 'ref-data':
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

    elif ctx == 'ref-data':
        return []
    
    return current_polylines


@app.callback(Output('marker-layer', 'children'),
                [Input("map", "dbl_click_lat_lng"),
                 Input('create-new-button', 'n_clicks'),
                 Input('encounter-ids', 'options'),
                 Input('ac-ids', 'value'),
                 Input(dict(tag="marker", index=ALL), 'children'),
                 Input('ref-data', 'data'),
                 Input('exit-create-mode', 'n_clicks')],
                [State('marker-layer', 'children'),
                 State('ac-index', 'value'),
                 State('load-waypoints-button', 'n_clicks'),
                 State('create-mode', 'n_clicks'),
                 State('create-mode-zUp-input', 'value')])
def create_markers(dbl_click_lat_lng, start_new_n_clicks, encounter_options, ac_ids, current_marker_tools, ref_data, exit_create_n_clicks, current_markers, ac_value,  upload_n_clicks, create_n_clicks, zUp_val): 
    ctx = dash.callback_context
    if not ctx.triggered or not ctx.triggered[0]['value']:
        return dash.no_update
    ctx = ctx.triggered[0]['prop_id'].split('.')[0]

    # print('create_markers: ', ctx)

    if ctx == 'map':
        if create_n_clicks > 0 and start_new_n_clicks > 0:
            if ac_value is not None and zUp_val is not None:
                if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
                    return dash.no_update

                lat, lng = dbl_click_lat_lng
                
                current_markers.append(dl.Marker(id=dict(tag="marker", index=len(current_markers)), 
                                        position=dbl_click_lat_lng,
                                        children=dl.Tooltip(f"({lat:.3f}{chr(176)}, {lng:.3f}{chr(176)})"), 
                                        draggable=True))
            else:
                print('Enter an AC ID.')
        
    elif ctx == 'create-new-button':
        if start_new_n_clicks > 0:
            return []

    elif ctx == 'exit-create-mode':
        if exit_create_n_clicks:
            return []

    elif ctx == 'ref-data':
        if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
            return []

    elif ctx == 'encounter-ids' or ctx == 'ac-ids':
        if upload_n_clicks > 0:
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
              State('ref-data', 'data')])
def update_marker(new_positions, current_marker_tools, ref_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
 
    if len(ctx) > 0:
        if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
            return dash.no_update

        index = json.loads(ctx)['index']
        lat, lng = new_positions[index]
        # xEast, yNorth, zUp = pm.geodetic2enu(pos[0], pos[1], ref_data['ref_alt']*FT_TO_M, 
        #                                     ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M,
        #                                     ell=pm.Ellipsoid('wgs84'), deg=True)
        # current_marker_tools[index] = dl.Tooltip("({:.3f}, {:.3f})".format(*[xEast, yNorth]))
        current_marker_tools[index] = dl.Tooltip(f"({lat:.3f}{chr(176)}, {lng:.3f}{chr(176)})")
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
                Output('ref-data', 'data')],
                [Input('set-ref-button', 'n_clicks'),
                Input('clear-ref-button', 'n_clicks')],
                [State('ref-point-input', 'value'),
                State('ref-point-input', 'pattern'),
                State('ref-data', 'data')])
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

    lat, lng, alt = ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']
    ref = f'Reference Point: {lat:.2f}{chr(176)}/{lng:.2f}{chr(176)}/{alt:.2f}ft'

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
              Input('memory-data','data'))
def set_nominal_ac_ids_options(encounter_id_selected, memory_data):
    if encounter_id_selected != [] and memory_data != {}:
        dropdown_options = [{'value': ac_id, 'label': 'AC '+ str(ac_id)} for ac_id in memory_data['ac_ids']]
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

      
@app.callback(Output('popover-content', 'children'),
              Output('popover-content', 'style'),
              Input('cov-radio', 'value'))
def render_popover_content(cov_radio_value):

    on = {"display": "block", "width": "25rem", #, "max-width": "300px",}
          "box-shadow": "0 3px 6px 0 rgba(0, 0, 0, 0.2), 0 4px 15px 0 rgba(0, 0, 0, 0.19)"}
    off = {"display": "none"}

    if cov_radio_value == 'cov-radio-diag':

        content = '$\\begin{equation*} \
                    \Sigma = \\begin{bmatrix} \
                        k(x_1, x\'_1) & k(x_1, y\'_1) & \\cdots  & k(x_1, z\'_n) \\\\ \
                        k(y_1, x\'_1) & k(y_1, y\'_1) &          & \\vdots       \\\\ \
                        \\vdots       &               & \\ddots  &               \\\\ \
                        k(z_n, x\'_1) & \\cdots       &          & k(z_n, z\'_n) \
                    \\end{bmatrix} \
                    \\\\ \\quad \\\\ \
                    \\text{For time-steps $i$ and $j$, } \\\\ \
                    \\begin{cases} \
                        k(x_i, x\'_j) = \sigma_h \\\\ \
                        k(y_i, y\'_j) = \sigma_h \\\\ \
                        k(z_i, z\'_j) = \sigma_v \\\\ \
                        \\text{0 otherwise.} \
                    \\end{cases} \
            \\end{equation*}$'

        popover_content = [
            dbc.PopoverHeader("Diagonal Covariance", style={"text-align":"center"}),
            dbc.PopoverBody(content, style={"margin-left":"10px"})]
        return popover_content, on


    elif cov_radio_value == 'cov-radio-exp':

        content = '$\\begin{equation*} \
                    K = \\begin{bmatrix} \
                        k(x_1, x\'_1) & k(x_1, y\'_1) & \\cdots  & k(x_1, z\'_n) \\\\ \
                        k(y_1, x\'_1) & k(y_1, y\'_1) &          & \\vdots       \\\\ \
                        \\vdots       &               & \\ddots  &               \\\\ \
                        k(z_n, x\'_1) & \\cdots       &          & k(z_n, z\'_n) \
                    \\end{bmatrix} \
                    \\\\ \\quad \\\\ \
                    \\text{For time-steps $i$ and $j$, } \\\\ \
                    \\begin{cases} \
                        \\text{Horizontal elements: } k(x_i, x\'_j) = \\exp \\Big( \\frac{-w_h (x_i - x\'_j)^2}{2 l^2} \\Big) \\\\ \
                        \\text{Vertical elements:   } k(z_i, z\'_j) = \\exp \\Big( \\frac{-w_v (z_i - z\'_j)^2}{2 l^2} \\Big) \\\\ \
                        \\text{Other elements:      } k(x_i, z\'_j) = 0 \\\\ \
                        x \\text{\'s and } y \\text{\'s are interchangable.}& \
                    \\end{cases} \
            \\end{equation*}$'

        popover_content = [
            dbc.PopoverHeader("Exponenetial Kernel Covariance", style={"text-align":"center"}),
            dbc.PopoverBody(content, style={"margin-left":"10px"})]
        return popover_content, on

    return "", off


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


@app.callback(Output('generated-data', 'data'),
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
               State('ref-data', 'data'),
               State('memory-data', 'data')])
def generate_encounters(gen_n_clicks, nom_enc_id, nom_ac_ids, cov_radio_value, sigma_hor, sigma_ver, exp_kernel_a, exp_kernel_b,\
                        exp_kernel_c, num_encounters, ref_data, memory_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'generate-button':
        if gen_n_clicks > 0:

            # print('\n--GENERATING--\n')

            # error checking
            if generation_error_found(memory_data['type'], nom_ac_ids, num_encounters, cov_radio_value, 
                                        sigma_hor, sigma_ver, exp_kernel_a, exp_kernel_b, exp_kernel_c):
                return {}

            nom_enc_data = parse_enc_data(memory_data, [nom_enc_id], nom_ac_ids, ref_data)
            df = pd.DataFrame(nom_enc_data)

            kernel_inputs = [ [ [waypoint['xEast'], waypoint['yNorth'], waypoint['zUp']] for waypoint in (df.loc[df['ac_id'] == ac]).to_dict('records')] for ac in nom_ac_ids]
            ac_times = [ [waypoint['time'] for waypoint in (df.loc[df['ac_id'] == ac]).to_dict('records')] for ac in nom_ac_ids]
            
            # print('len(kernel_inputs): ', len(kernel_inputs))
            # print('len(kernel_inputs[0]: ', len(kernel_inputs[0]))
            # print('len(kernel_inputs[1]: ', len(kernel_inputs[1]))
            # print('len(ac_times): ', len(ac_times))
            # print('len(ac_times[0]): ', len(ac_times[0]))
            # print('len(ac_times[0]): ', len(ac_times[1]))

            if cov_radio_value == 'cov-radio-diag':
                cov = [ [sigma_hor, 0, 0], 
                        [0, sigma_hor, 0], 
                        [0, 0, sigma_ver] ]

                generated_waypoints = np.array([ [np.random.multivariate_normal(mean,cov,num_encounters) for mean in ac] for ac in kernel_inputs])
                
                num_ac = len(generated_waypoints)
                num_waypoints = [len(generated_waypoints[0]), len(generated_waypoints[1])]
                
                # print(np.shape(generated_waypoints))
                # print(np.shape(generated_waypoints[0]))
                # print(np.shape(generated_waypoints[1]))
                # generated_waypoints[0] = np.reshape(generated_waypoints[0], (num_encounters, num_waypoints[0], 3))
                # generated_waypoints[1] = np.reshape(generated_waypoints[1], (num_encounters, num_waypoints[1], 3))
                # generated_waypoints[0] = np.reshape(generated_waypoints[0], (num_encounters, -1, 3))
                # generated_waypoints[1] = np.reshape(generated_waypoints[1], (num_encounters, -1, 3))

                generated_waypoints[0] = np.moveaxis(generated_waypoints[0], 0, 1)
                generated_waypoints[1] = np.moveaxis(generated_waypoints[1], 0, 1)

                # print(np.shape(generated_waypoints))
                # print(np.shape(generated_waypoints[0]))
                # print(np.shape(generated_waypoints[1]))


                generated_waypoints[0] = np.array([kernel_inputs[0]] + generated_waypoints[0].tolist())
                generated_waypoints[1] = np.array([kernel_inputs[1]] + generated_waypoints[1].tolist())

                # print(np.shape(generated_waypoints))
                # print(np.shape(generated_waypoints[0]))
                # print(np.shape(generated_waypoints[1]))
                
                # generated_waypoints = np.reshape(generated_waypoints, (generated_waypoints.shape[0], -1))

                # print('\nnum_encounters: ', num_encounters)
                # print('len(generated_waypoints): ', len(generated_waypoints))
                # print('len(generated_waypoints[0]): ', len(generated_waypoints[0]))
                # print('len(generated_waypoints[1]): ', len(generated_waypoints[1]))
                # print('\nlen(generated_waypoints[0][0]): ', len(generated_waypoints[0][0]))
                # print('len(generated_waypoints[1][0]): ', len(generated_waypoints[1][0]))
                # print('\nlen(generated_waypoints[0][0][0]): ', len(generated_waypoints[0][0][0]))
                # print('len(generated_waypoints[1][0][0]): ', len(generated_waypoints[1][0][0]))

                # reshaped_g_w = [ [ [[] for _ in range(num_waypoints[ac_id])] for _ in range(num_encounters+1)] for ac_id in range(num_ac)]
                # reshaped_g_w[0][0] = kernel_inputs[0]
                # reshaped_g_w[1][0] = kernel_inputs[1]


                # print('\nlen(reshaped_g_ws): ', len(reshaped_g_w))
                # print('len(reshaped_g_w[0]): ', len(reshaped_g_w[0]))
                # print('len(reshaped_g_w[1]): ', len(reshaped_g_w[1]))
                # print('\nlen(reshaped_g_w[0][0]): ', len(reshaped_g_w[0][1]))
                # print('len(reshaped_g_w[1][0]): ', len(reshaped_g_w[1][1]))

                # reshaped_g_w = [ [reshaped_g_w[i][k+1] + [waypoint] for j, waypoints in enumerate(ac_waypoints) for k, waypoint in enumerate(waypoints)] for i, ac_waypoints in enumerate(generated_waypoints)]

                # #reshaped_g_w = [ [reshaped_g_w[][] + [waypoints[k]] if  for j, waypoints in enumerate(ac_waypoints)] for i, ac_waypoints in enumerate(generated_waypoints)]




                # print("\nWITH VALUES")
                # print('\nlen(reshaped_g_ws): ', len(reshaped_g_w))
                # print('len(reshaped_g_w[0]): ', len(reshaped_g_w[0]))
                # print('len(reshaped_g_w[1]): ', len(reshaped_g_w[1]))
                # print('\nlen(reshaped_g_w[0][0]): ', len(reshaped_g_w[0][0]))
                # print('len(reshaped_g_w[1][0]): ', len(reshaped_g_w[1][0]))
                # print('\nlen(reshaped_g_w[0][0][0]): ', len(reshaped_g_w[0][0][0]))
                # print('len(reshaped_g_w[1][0][0]): ', len(reshaped_g_w[1][0][0]))

                # print()




                # print(type(generated_waypoints))
                # print(np.array(generated_waypoints))
                # print(type(generated_waypoints))
                # print(np.shape(generated_waypoints[0]))
                # print(np.shape(generated_waypoints[0][0]))


                # generated_waypoints = np.shape(generated_waypoints)
                # insert kernel inputs AKA nominal trajectory data
                # generated_waypoints = [nominal+generated for nominal, generated in zip(kernel_inputs,generated_waypoints)]
                
                


                # generated_waypoints[0] : AC1, generated_waypoints[1] : AC2
                # AC1[i], AC2[i] = num_encounters

            elif cov_radio_value == 'cov-radio-exp':     
                print("exp cov")    
                
            # waypoints_lists, ac_times = {}, {}

            # for ac in nom_ac_ids:
            #     ac_df = (df.loc[df['ac_id'] == ac]).to_dict('records')

            #     kernel_inputs = [[waypoint['xEast'], waypoint['yNorth'], waypoint['zUp']] for waypoint in ac_df]
            #     ac_times[ac] = [waypoint['time'] for waypoint in ac_df]
            #     encounters = None

                # if cov_radio_value == 'cov-radio-diag':
                #     cov = [ [sigma_hor, 0, 0], 
                #             [0, sigma_hor, 0], 
                #             [0, 0, sigma_ver] ]

            #         encounters = [[] for _ in range(num_encounters+1)]
            #         encounters[0] = kernel_inputs

            #         for i, mean in enumerate(kernel_inputs):
            #             gen_waypoints = np.random.multivariate_normal(mean,cov,num_encounters)

            #             for enc_id, waypoint in enumerate(gen_waypoints):
            #                 encounters[enc_id+1].append(waypoint.tolist())


            #     elif cov_radio_value == 'cov-radio-exp':                
            #         mean, cov = exp_kernel_func(kernel_inputs, exp_kernel_a, exp_kernel_b, exp_kernel_c)
            #         waypoints_list = np.random.multivariate_normal(mean,cov,num_encounters)
            #         waypoints_list = np.reshape(waypoints_list, (waypoints_list.shape[0], -1, 3))

            #         encounters = [kernel_inputs] + waypoints_list.tolist()
                    
            #     waypoints_lists[ac] = encounters

            generated_data_filename = 'generated_data.dat'
            enc_data_indices = stream_generated_data(generated_waypoints, ac_times, generated_data_filename, num_encounters)

            return {'filename':generated_data_filename,
                    'encounter_indices':enc_data_indices,
                    'ac_ids':nom_ac_ids,
                    'num_encounters': num_encounters+1,
                    'type':'generated'}

    return dash.no_update
                        

@app.callback([Output('log-histogram-ac-1-xy', 'figure'),
              Output('log-histogram-ac-1-tz', 'figure'),
              Output('log-histogram-ac-2-xy', 'figure'),
              Output('log-histogram-ac-2-tz', 'figure')],
              Input('generated-data', 'data'),
              State('ref-data', 'data'))
def on_generation_update_log_histograms(generated_data, ref_data):
    #if generated_data == {}:
    
    return px.density_heatmap(), px.density_heatmap(), px.density_heatmap(), px.density_heatmap()

    start = time.time()
    print('\n--CREATING HISTOGRAMS--\n')

    with open(generated_data['filename'], 'rb') as file:
        data = file.read()
        print('NUM ENC: ', generated_data['num_encounters'])
        print('SIZE OF GEN DATA: {:,}'.format(len(data)))

    #return px.density_heatmap(), px.density_heatmap(), px.density_heatmap(), px.density_heatmap()

    # if len(data) > 10 * MB:
    #     # larger than 10mb, going to be too big for the histograms
    #     print('Size of generated data is too big for generating histograms')
    #     # FIXME: Add an alert that pops up informing the user that the num encounters
    #     # is too large
    #     return px.density_heatmap(), px.density_heatmap(),  px.density_heatmap(), px.density_heatmap()
    # else:
    print('parsing all data @', 0, ' mins')
    gen_data = convert_and_combine_data(generated_data, ref_data)
    print('finished parsing all data @', (time.time()-start)/60, ' mins')

    # organize generated data by ac_id then enc_id
    df = pd.DataFrame(gen_data)
    df_group_by_ac = [pd.DataFrame(data) for i, data in df.groupby('ac_id', as_index=False)]
    print(len(df_group_by_ac))
    # df_to_interpolate = [pd.DataFrame(data) for data_df in df_group_by_ac for i, data in data_df.groupby('encounter_id')]
    
    num_processes = mp.cpu_count()
    # num_partitions = int(len(df_to_interpolate)/2)

    # pool = mp.Pool(num_processes)

    # ac_ids = [[1] for i in range(num_partitions)]
    # ac_ids += [[2] for i in range(num_partitions)]

    # print('\nbefore interpolating @', (time.time()-start)/60, ' mins')
    # results = pool.starmap(interpolate_df_time, zip(df_to_interpolate, ac_ids))
    # print('finished interpolating @', (time.time()-start)/60, ' mins')

    # pool.close()
    # pool.join()

    # df_ac_1_interp = pd.concat([result[0] for result in results[:num_partitions]])
    

    # df_ac_2_interp = pd.concat([result[0] for result in results[num_partitions:]])

    # print('\norganized: ', (time.time()-start)/60, ' mins')

    num_partitions = 4 # number of histograms
    #df_ac = [df_ac_1_interp, df_ac_1_interp, df_ac_2_interp, df_ac_2_interp]
    # df_acs = [pd.DataFrame(data) for data in df_group_by_ac]
    df_ac = [df_group_by_ac[0], df_group_by_ac[0], df_group_by_ac[1], df_group_by_ac[1]]
    x = ['xEast', 'time','xEast', 'time']
    y = ['yNorth', 'zUp', 'yNorth', 'zUp']

    pool = mp.Pool(num_processes)

    print('\nbefore creating histograms @', (time.time()-start)/60, ' mins')
    histograms = pool.starmap(create_histogram, zip(df_ac, x, y))
    print('finished building histograms @', (time.time()-start)/60,' mins\n')

    pool.close()
    pool.join()

    return histograms
    

def create_histogram(df_data, x, y):
    viridis = px.colors.sequential.gray #Blues
    colors = viridis
    # colors = [  [0, viridis[0]],
    #             [1./10000, viridis[3]],
    #             [1./1000, viridis[5]],
    #             [1./100, viridis[7]],
    #             [1./10, viridis[9]],
    #             [1., viridis[11]]   ]

    if x == 'xEast' and y == 'yNorth':
        return px.density_heatmap(df_data, x=x, y=y, nbinsx=100, nbinsy=100, 
                            labels={'xEast':'xEast (NM)', 'yNorth':'yNorth (NM)'}, color_continuous_scale=colors)

    if x == 'time' and y == 'zUp':
        return px.density_heatmap(df_data, x=x, y=y, nbinsx=100, nbinsy=100, 
                            labels={'time':'Time (s)', 'zUp':'zUp (ft)'}, color_continuous_scale=colors)



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
                [State('nominal-path-ac-ids', 'options'),
                State('save-dat-filename', 'value'),
                State('file-checklist', 'value'),
                State('dat-file-units', 'value'),
                State('memory-data', 'data'),
                State('session-id', 'data'),
               State('load-waypoints', 'contents'),
               State('load-waypoints', 'filename'),
               State('generated-data', 'data'),
               State('ref-data', 'data'),
               State('editable-table', 'data'),
               State('load-model', 'contents')],
                prevent_initial_call=True)
def on_click_save_dat_file(save_n_clicks, nom_ac_ids, dat_filename, files_to_save, dat_file_units, memory_data, session_id, waypoints_contents, loaded_filename, generated_data, ref_data, table_data, model_contents):
    
    if save_n_clicks > 0:
        if generated_data != {} and 'dat-item' in files_to_save:

            if dat_file_units == 'dat-units-geo':
                print("UNSUPPORTED OPTION")

            generated_data_filename = generated_data['filename']
            enc_indices = generated_data['encounter_indices']
            num_enc = generated_data['num_encounters']
            file_name = dat_filename if dat_filename else 'generated_waypoints.dat'

            with open(file_name, 'wb') as file_to_save, open(generated_data_filename, 'rb') as gen_file:
                encounters_data = gen_file.read()
                #encs_data_bytes = base64.b64decode(encounters_data)
                data_to_save = bytearray()
                data_to_save.extend(struct.pack('<II', num_enc-1, len(nom_ac_ids))) # remove nominal encounter
                data_to_save.extend(encounters_data[enc_indices[1]:])
                file_to_save.write(data_to_save)


            # FIXME: the dcc.download restricts the size of our data
            # maybe instead of the user getting it as a download, the user should specify a 
            # file path so we can just write to that destination on the user's computer...
            return dcc.send_file(file_name)
        else:
            print('Must generate an encounter set')

    return dash.no_update


@app.callback(Output('download-model', 'data'),
                Input('save-filename-button', 'n_clicks'),
                [State('generated-data', 'data'),
                State('cov-radio', 'value'),
                State('diag-sigma-input-hor', 'value'),
                State('diag-sigma-input-ver', 'value'),
                State('exp-kernel-input-a', 'value'),
                State('exp-kernel-input-b', 'value'),
                State('exp-kernel-input-c', 'value'),
                State('save-json-filename', 'value'),
                State('file-checklist', 'value'),
                State('ref-data', 'data')],
                prevent_initial_call=True)
def on_click_save_json_file(save_n_clicks, generated_data, cov_radio_val, sigma_hor, sigma_ver, a, b, c, json_filename, files_to_save, ref_data):

    if save_n_clicks > 0:
        if generated_data:
            if 'json-item' in files_to_save:
                model_json = {}
                
                enc_data = parse_enc_data(generated_data, [0], generated_data['ac_ids'], ref_data)
                df_enc = pd.DataFrame(enc_data)
                ac_ids = generated_data['ac_ids']
            
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

@app.callback(Output('ref-card-div', 'style'),
                Input('tabs', 'active_tab'),
                State('ref-card-div', 'style'))
def toggle_map_create_mode_div(active_tab, style):
    on = {'display': 'block'}
    off = {'display': 'none'}

    if active_tab == 'tab-1' or active_tab == 'tab-2':
        style['visibility'] = 'visible'
    elif active_tab == 'tab-4':
        style['visibility'] = 'hidden'

    return style


if __name__ == '__main__':
    app.run_server(debug=True, port=8333)
    
