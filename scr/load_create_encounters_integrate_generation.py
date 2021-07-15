import dash
from dash.dependencies import Input, Output, State, ALL

import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_leaflet as dl

import plotly.express as px
import plotly.graph_objects as go

import pandas as pd
import numpy as np
import collections

import json
import pymap3d as pm
import re

from read_file import *
import base64


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', dbc.themes.BOOTSTRAP]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)


def calculate_horizontal_speeds_df(df):
    dataf = df.copy()
    hor_speeds = []
    for ac_id in set(df['ac_id']):
        ac_id_data = df.loc[df['ac_id'] == ac_id]
        move_over_time = (np.roll(ac_id_data, -1, axis=0) - ac_id_data)[:-1]
        hor_speed = np.sqrt(move_over_time.xEast ** 2 + move_over_time.yNorth ** 2) / move_over_time['time']
        hor_speeds += (np.append(0.0, round(hor_speed, 4))).tolist()
    dataf.loc[:, 'hor_speed'] = hor_speeds
    return dataf


M_TO_NM = 0.000539957; NM_TO_M = 1/M_TO_NM
FT_TO_M = .3048; M_TO_FT = 1/FT_TO_M
FT_TO_NM = FT_TO_M*M_TO_NM


map_iconUrl = "https://dash-leaflet.herokuapp.com/assets/icon_plane.png"
map_marker = dict(rotate=True, markerOptions=dict(icon=dict(iconUrl=map_iconUrl, iconAnchor=[16, 16])))
map_patterns = [dict(repeat='15', dash=dict(pixelSize=0, pathOptions=dict(color='#000000', weight=5, opacity=0.9))),
            dict(offset='100%', repeat='0%', marker=map_marker)]


app.layout = html.Div([
    #   memory store reverts to the default on every page refresh
    dcc.Store(id='memory-data', data=[{}]),
    dcc.Store(id='session', data={'ref_lat': 40.63993,
                                  'ref_long': -73.77869,
                                  'ref_alt': 12.7}),

    dcc.Store(id='generated-encounters', data={}),
    
    # style
    html.Br(), 
    
    # buttons to load/save waypoints
    html.Div([
        html.Div([
            html.Label([
                dcc.Upload(id='load-waypoints', children = 
                           html.Button('Load Waypoints (.dat)', id='load-waypoints-button', n_clicks=0,
                           style={"margin-left": "15px"}))
            ])
        ], style={"margin-left": "15px", "margin-bottom":"10px", 'display':'inline-block'}),

        html.Div([
            html.Label([
                dcc.Upload(id='load-model', children = 
                           html.Button('Load Model (.json)', id='load-model-button', n_clicks=0))
            ])
        ], style={"margin-left": "15px", "margin-bottom":"10px", 'display':'inline-block'}),

        html.Div([
            html.Button('Save Waypoints (.dat)', id='save-button', n_clicks=0)
        ], style={"margin-left": "15px", "margin-bottom":"10px", 'display':'inline'}),
        
        html.Button('Create Mode', id='create-mode', n_clicks=0,
                 style={"margin-left": "15px", "margin-bottom":"10px"}),
        
        html.Button('Exit Create Mode', id='exit-create-mode', n_clicks=0,
                 style={"margin-left": "15px", "margin-bottom":"10px", 'display':'none'})
    ],  className  = 'row'),
    
    
    # buttons to create new path
    html.Div([
        html.Button('Start New Nominal Path', id='create-new-button', n_clicks=0,
                 style={"margin-left": "15px", "margin-bottom":"10px", 'color': 'green', 'display':'none'}), 
        dcc.Input(id="encounter-index", type="number", placeholder="Enter encounter ID", debounce=False, min=1, 
                 style={"margin-left": "15px", "margin-bottom":"10px", 'display':'none'}),
        dcc.Input(id="ac-index", type="number", placeholder="Enter AC ID", debounce=False, min=1, 
                 style={"margin-left": "15px", "margin-bottom":"10px", 'display':'none'}),
        html.Button('Exit New Nominal Path', id='end-new-button', n_clicks=0,
                 style={"margin-left": "15px", "margin-bottom":"10px", 'color': 'green', 'display':'none'})
    ], style={"margin-left": "1px"}, className  = 'row'),

    
    # encounter/AC ID dropdown menu
    html.Div([
        html.Div([
            dcc.Dropdown(id='encounter-ids', placeholder="Select an encounter ID", multi=False,
            style={"margin-left": "15px"})
        ], style={"margin-bottom":"10px"}, className='two columns'),
        html.Div([
            dcc.Dropdown(id='ac-ids', placeholder="Select AC ID(s)", multi=True, style={"margin-left": "10px"})
        ], style={"margin-left": "15px", "margin-bottom":"10px"}, className='two columns'),
    ], className  = 'row'),


    # reference point input
    html.Div(id='reference-point-div', children = [
        dcc.Input(id='ref-point-input', type='text', 
                  placeholder='lat/lng/alt: 0.0/0.0/0.0',
                  debounce=True,
                  pattern=u"^(\-?\d+\.\d+?)\/(\-?\d+\.\d+?)\/(\d+\.\d+?)$",
                  style={"margin-left": "15px", 'display':'inline-block'}),
        html.Button('Set Reference Point', id='set-ref-button', n_clicks=0,
                  style={"margin-left": "15px", 'display':'inline-block'}),
        html.Button('Clear', id='clear-ref-button', n_clicks=0,
                  style={"margin-left": "15px", 'display':'inline-block'}),
        html.Div(id='ref-point-output', children=[],
                  style={"margin-left": "15px", "margin-top": "10px"})
        ]
    ),

    html.Br(),

    html.Div(id='generation', children=[
        html.Button('Generate Encounter Set', id='gen-encounters-button', n_clicks=0,
                style={'display':'inline-block', "margin-left": "15px"})
    ]),

    html.Br(),


    html.Div(id='gen-modal-div', children=[
        dbc.Modal([
                dbc.ModalHeader("Generate an Encounter Set"),
                dbc.ModalBody("First Stage: Multivariate Normal"),
                dcc.Markdown(("""Select at least one Nominal Path"""), style={"margin-left": "20px"}),
                dcc.Dropdown(id='nominal-path-ac-ids', 
                    options=[], 
                    multi=True, 
                    value=[],
                    style={"margin-left": "10px", "width": "71%"}),
                html.Br(),
                dcc.Markdown(("""Input Sigma Value"""), style={"margin-left": "20px"}),
                dcc.Input(id='sigma-input', type='text', placeholder='default sigma = 1',
                    debounce=True,
                    pattern=u"^(\d+)$",
                    value=1,
                    style={"margin-left": "20px", "width": "50%"}),
                html.Br(),
                dcc.Markdown(("""Number of Encounters to Generate"""), style={"margin-left": "20px"}),
                dcc.Input(id='num-encounters-input', type='text', placeholder='',
                    debounce=True,
                    pattern=u"^(\d+)$",
                    style={"margin-left": "20px", "width": "50%"}),
                html.Br(),
                dbc.ModalFooter(children= [
                    dbc.Button("CLOSE", id="close-button"),
                    dbc.Button("GENERATE", id="generate-button", className="ml-auto")
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
    
    
    # main tabs for navigating webpage
    html.Div([
        dcc.Tabs(id="tabs",
                 children=[
#                      dcc.Tab(id='tab1', label='Graphs', value='tab-1'), 
                     dcc.Tab(id='tab1', label='2d_Graphs', value='tab-1'),
                     dcc.Tab(id='tab2', label='3d_Graph', value='tab-2'),
                     dcc.Tab(id='tab3', label='Map', value='tab-3'),
                    #  dcc.Tab(id='tab4', label='Log Histogram', value='tab-4',
                    #  style={'display':'none'})
                 ],
                 value='tab-1'),
        html.Div(id='tabs-content', children = None)
    ]),


    # initialize and display tab-1 graphs
    html.Div(id = "tab-1-graphs", 
             children=[
                 html.Div([
                     html.Div([dcc.Graph(id='editable-graph-xy', figure={})],
                               className='four columns', 
                               style={'display': 'none'}), #style={'display': 'inline-block'}),
                     html.Div([dcc.Graph(id='editable-graph-tz', figure={})],
                               className='four columns', 
                               style={'display': 'none'}), #style={'display': 'inline-block'}), 
                     html.Div([dcc.Graph(id='editable-graph-tspeed',figure={})], 
                               className='four columns', 
                               style={'display': 'none'}), #style={'display': 'block'})
                 ], className='row'),
                 html.Div([
                     html.Div([dcc.Graph(id='editable-graph-xy-slider', 
                               figure={'layout': {'title': 'xEast vs yNorth'}})],
                               className='four columns', 
                               style={'display': 'inline-block'}), #'width': '500px', 'height': '550px', 
                     html.Div([dcc.Graph(id='editable-graph-tz-slider', 
                               figure={'layout': {'title': 'Time vs zUp'}})],
                               className='four columns', 
                               style={'display': 'inline-block'}), #'width': '500px', 'height': '550px', 
                     html.Div([dcc.Graph(id='editable-graph-tspeed-slider',
                               figure={'layout': {'title': 'Time vs Horizontal Speed'}})], 
                               className='four columns', 
                               style={'display': 'block'}) #'width': '500px', 'height': '550px', 
                 ], className='row'),
                 html.Div([
                     html.Div(id='slider-drag-output', children='Time: ',
                              style={'margin-left':'35px', 'margin-right': '15px', 'font-size': 15}),
                     html.Div([dcc.Slider(id='slider', #min=?, max=?, marks=?
                                          value=0, step=1, updatemode='drag')
                              ], style={'width': '800px'})
                 ], style={'margin-bottom':'10px'}, className='row'), #style={'justifyContent':'center'}, 
             ], style={'display': 'block'}),    

    # initialize tab-2 graphs
    html.Div(id = 'tab-2-graphs', 
             children = [dcc.Graph(id='editable-graph-xyz', figure={})],
             style={'width': '1500px', 'height': '750px',
                    'margin': {'l':0, 'r':0, 'b':0, 't':0, 'pad':0}, 
                    'autosize': False, 'display': "block"}),
    
    # initialize tab-3 graphs
    html.Div(id = 'tab-3-graphs', 
             children = [
                 dl.Map(id='map',
                        children=[
                            dl.TileLayer(), 
                            dl.LayerGroup(id='polyline-layer', children=[]),
                            dl.LayerGroup(id='marker-layer', children=[], attribution='off')],
#                         zoom=11.5, center=(40.63993, -73.77869), 
                        doubleClickZoom=False,
                        style={'width': '1500px', 'height': '750px', 'margin': "auto", 
                               'autosize': True, 'display': "block"})
             ], style={'display': "block"}),
    
    # # initialize tab-4 graphs
    # html.Div(id = 'tab-4-graphs', 
    #          children = [
    #              dcc.Graph(id='density-heatmap', figure={},
    #                         style={'width': '1500px', 'height': '750px', 'margin': "auto", 
    #                                 'autosize': False,'display':'block'})
    #          ], style={'display': "none"}),
    
    # style
    html.Br(), html.Br(),
    
    
    # waypoints data table
    html.Div([
        dash_table.DataTable(
            id = 'editable-table',
            editable = True,
            row_deletable = True,
            style_table={'width': '1200px', 'margin-left': "15px", 'display': "block"}), #'height': '750px',  
        html.Button('Add Row', id='add-rows-button', n_clicks=0,
                    style={'margin-left':'15px'}),
    ], className='row'),

    
    # style
    html.Br(), html.Br()
]) 

print('\n*****START OF CODE*****\n')


##########################################################################################
##########################################################################################
COLOR_LIST = ['blue', 'orange', 'green', 'red', 'black', 'purple']

@app.callback(Output('editable-graph-xy', 'figure'),
              Input('editable-table', 'data'))
def update_graph_xy(data):
    if data is None:
        return dash.no_update
    aggregation = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in data:
        if row.get('xEast') != '' and row.get('yNorth') != '':        
            a = aggregation[float(row.get('ac_id'))]
            a['name'] = 'AC '+ str(row['ac_id'])
            a['type'], a['mode'], a['marker'] = 'scatter', 'lines+markers', {'color': COLOR_LIST[int(row['ac_id'])], 'size': 5}
            a['x'].append(float(row.get('xEast')))
            a['y'].append(float(row.get('yNorth')))    
    return {'data': [x for x in aggregation.values()],
            'layout': {'title': 'xEast vs yNorth',
                       'xaxis': {'title': 'xEast (NM)'},
                       'yaxis': {'title': 'yNorth (NM)'}}
           }

 
@app.callback(Output('editable-graph-tz', 'figure'),
              Input('editable-table', 'data'))
def update_graph_tz(data):
    if data is None:
        return dash.no_update
    aggregation = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in data:
        if row.get('time') != '' and row.get('zUp') != '':        
            a = aggregation[float(row.get('ac_id'))]
            a['name'] = 'AC '+str(row['ac_id'])
            a['type'], a['mode'], a['marker'] = 'scatter', 'lines+markers', {'color': COLOR_LIST[int(row['ac_id'])], 'size': 5}
            a['x'].append(float(row['time']))
            a['y'].append(float(row['zUp']))
    return {'data': [x for x in aggregation.values()],
            'layout': {'title': 'Time vs zUp',
                       'xaxis': {'title': 'Time (s)'},
                       'yaxis': {'title': 'zUp (ft)'}}
           }


@app.callback(Output('editable-graph-tspeed', 'figure'),
              Input('editable-table', 'data'))
def update_graph_tspeed(data):
    if data is None:
        return dash.no_update
    aggregation = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in data:
        if row.get('time') != '' and row.get('hor_speed') != '':        
            a = aggregation[float(row.get('ac_id'))]
            a['name'] = 'AC '+str(row['ac_id'])
            a['type'], a['mode'], a['marker'] = 'scatter', 'lines+markers', {'color': COLOR_LIST[int(row['ac_id'])], 'size': 5}
            a['x'].append(float(row['time']))
            a['y'].append(float(row['hor_speed']))
    return {'data': [x for x in aggregation.values()],
            'layout': {'title': 'Time vs Horizontal Speed',
                       'xaxis': {'title': 'Time (s)'},
                       'yaxis': {'title': 'Speed (NM/s)'}}
           }


@app.callback(Output('editable-graph-xyz', 'figure'),
              Input('editable-table', 'data'))
def update_graph_xyz(data):
    if data is None:
        return dash.no_update
    aggregation = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in data:
        if row.get('time') != '' and row.get('zUp') != '':        
            a = aggregation[float(row.get('ac_id'))]
            a['name'] = 'AC '+str(row['ac_id'])
            a['type'], a['mode'], a['marker'] = 'scatter3d', 'lines+markers', {'color': COLOR_LIST[int(row['ac_id'])], 'size': 5}
            a['x'].append(float(row['xEast']))
            a['y'].append(float(row['yNorth']))
            a['z'].append(float(row['zUp']))
    return {'data': [x for x in aggregation.values()],
            'layout': {'scene': {'xaxis': {'title': 'xEast (NM)'},
                                 'yaxis': {'title': 'yNorth (NM)'},
                                 'zaxis': {'title': 'zUp (ft)'}},
#                        'width': '1200px', 'height': '1200px',
                       'margin': {'l':0, 'r':0, 'b':0, 't':0}}
           }



from scipy.interpolate import PchipInterpolator

@app.callback(Output('slider-drag-output', 'children'),
              Output('editable-graph-xy-slider', 'figure'),
              Output('editable-graph-tz-slider', 'figure'),
              Output('editable-graph-tspeed-slider', 'figure'),
#               Output('editable-graph-xyz-slider', 'figure'),
              Output('slider', 'min'),
              Output('slider', 'max'),
              Input('slider', 'value'),
              Input('editable-graph-xy', 'figure'),
              Input('editable-graph-tz', 'figure'),
              Input('editable-graph-tspeed', 'figure'),
              State('editable-table', 'data'),
              State('encounter-ids', 'value'),
              State('ac-ids', 'value')
             )
def update_graph_slider(t_value, fig_xy, fig_tz, fig_tspeed, data, encounter_id_selected, ac_ids_selected):
    if data is None or encounter_id_selected is None or encounter_id_selected == []:
        return dash.no_update
        
    for x in fig_xy['data']:
        x['mode'] = 'lines'  
    for x in fig_tz['data']:
        x['mode'] = 'lines'
    for x in fig_tspeed['data']:
        x['mode'] = 'lines'   
        
    df = pd.DataFrame(data)
    data_fig_xy, data_fig_tz, data_fig_tspeed = [], [], []
    
#     time_range, xEast_range, yNorth_range = [], [], []
    min_values_list, max_values_list = [], []
    
    for ac_id in ac_ids_selected:
        df_ac_id = df.loc[df['ac_id'] == ac_id].sort_values('time')
        
        time_interp = np.arange(int(min(df_ac_id['time'])), int(max(df_ac_id['time'])+1))        
        xEast_interp = PchipInterpolator(df_ac_id['time'], df_ac_id['xEast'])(time_interp)
        yNorth_interp = PchipInterpolator(df_ac_id['time'], df_ac_id['yNorth'])(time_interp)
        zUp_interp = PchipInterpolator(df_ac_id['time'], df_ac_id['zUp'])(time_interp)
        hor_speed_interp = PchipInterpolator(df_ac_id['time'], df_ac_id['hor_speed'])(time_interp)

        for i in range(len(time_interp)):
            if time_interp[i] == t_value:
                data_fig_xy += [{'name': 'AC '+ str(ac_id), 
                                 'type': 'scatter', 'mode': 'markers', 
                                 'marker': {'color': COLOR_LIST[ac_id], 'size': 10},
                                 'x': [float(xEast_interp[i])], 'y': [float(yNorth_interp[i])]}]
                data_fig_tz += [{'name': 'AC '+ str(ac_id), 
                                 'type': 'scatter', 'mode': 'markers', 
                                 'marker': {'color': COLOR_LIST[ac_id], 'size': 10},
                                 'x': [float(time_interp[i])], 'y': [float(zUp_interp[i])]}]
                data_fig_tspeed += [{'name': 'AC '+ str(ac_id), 
                                 'type': 'scatter', 'mode': 'markers', 
                                 'marker': {'color': COLOR_LIST[ac_id], 'size': 10},
                                 'x': [float(time_interp[i])], 'y': [float(hor_speed_interp[i])]}]        
        min_values_list.append([min(time_interp), min(xEast_interp), min(yNorth_interp), min(zUp_interp), min(hor_speed_interp)])
        max_values_list.append([max(time_interp), max(xEast_interp), max(yNorth_interp), max(zUp_interp), max(hor_speed_interp)])
        
    if min_values_list == [] and max_values_list == []:
        return 'Time: ', {}, {}, {}, 0, 100

    min_values = np.min(np.array(min_values_list), axis=0)
    max_values = np.max(np.array(max_values_list), axis=0)
    return 'Time: {} (s)'.format(t_value), {
            'data': fig_xy['data'] + data_fig_xy,
            'layout': {'title': 'xEast vs yNorth',
                       'xaxis': {'title': 'xEast (NM)', 'range':[min(min_values[1],min_values[2])-0.2, 
                                                                  max(max_values[1], max_values[2])+0.2]},
                       'yaxis': {'title': 'yNorth (NM)', 'range':[min(min_values[1],min_values[2]-0.2), 
                                                                   max(max_values[1], max_values[2])+0.2]}}
#                       'uirevision': True}
           }, {
            'data': fig_tz['data'] + data_fig_tz,
            'layout': {'title': 'Time vs zUp',
                       'xaxis': {'title': 'Time (s)', 'range':[min_values[0]-2, max_values[0]+2]},
                       'yaxis': {'title': 'zUp (ft)', 'range':[min_values[3]-50, max_values[3]+50]}}
           }, {
            'data': fig_tspeed['data'] + data_fig_tspeed,
            'layout': {'title': 'Time vs Horizontal Speed',
                       'xaxis': {'title': 'Time (s)', 'range':[min_values[0]-2, max_values[0]+2]},
                       'yaxis': {'title': 'Speed (NM/s)', 'range':[min_values[4]-0.005, max_values[4]+0.005]}}
           }, min_values[0], max_values[0]


##########################################################################################
##########################################################################################
@app.callback([Output('map', 'center'),
               Output('map', 'zoom')],
              Input('session', 'data'))
def center_map_around_ref_input(ref_data):
    if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
        # ref point was cleared - so reset to center of US and zoom out
        return (39,-98), 4
    return (ref_data['ref_lat'], ref_data['ref_long']), 11.5


@app.callback(Output('polyline-layer', 'children'),
              Input('editable-table', 'data'),
              [State('polyline-layer', 'children'),
               State('session', 'data')])         
def update_map(data, current_polylines, ref_data):
    if data is None:
        return dash.no_update

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'editable-table' or ctx == 'session':
        # data has changed - must update map polylines
        new_polylines = []
        
        if len(data) == 0:
            # no data, save computation time
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
            
        ref_lat = ref_data['ref_lat']
        ref_long = ref_data['ref_long']
        ref_alt = ref_data['ref_alt']

        for data_id in data_group:
            lat_lng_dict = []
            for i in range(len(data_id['xEast'])):
                lat, lng, alt = pm.enu2geodetic(data_id['xEast'][i]*NM_TO_M, data_id['yNorth'][i]*NM_TO_M, data_id['zUp'][i]*FT_TO_M, 
                                                ref_lat, ref_long, ref_alt*FT_TO_M, 
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
            if ac_value: #and encounter_value 
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



##########################################################################################
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
               Input('create-mode', 'n_clicks'),
               Input('end-new-button', 'n_clicks'),
               Input('exit-create-mode', 'n_clicks'),
               Input('load-waypoints', 'contents'),
               Input('generated-encounters', 'data')],
              [State('load-waypoints', 'filename'),
               State('editable-table', 'data')])
def update_memory_data(upload_n_clicks, create_n_clicks, end_new_n_clicks, exit_create_n_clicks, contents, generated_data, filename, data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'create-mode' and create_n_clicks > 0:
        return [{}]
    elif ctx == 'end-new-button' and end_new_n_clicks > 0:  ## NEED TO FIX (ctx == 'exit-create-mode' ?)
        return data  ## NEED TO FIX
    
    elif ctx == 'load-waypoints-button' and upload_n_clicks > 0:
        return [{}]
    elif ctx == 'load-waypoints':
        if contents is None or not filename:
            return [{}]

        df = parse_contents(contents, filename) 
        df['xEast'] = df['xEast'] * FT_TO_NM  #np.around(df['xEast'] * FT_TO_NM, decimals=4)
        df['yNorth'] = df['yNorth'] * FT_TO_NM  #np.around(df['yNorth'] * FT_TO_NM, decimals=4)
        return df.to_dict('records')

    elif ctx == 'generated-encounters':
        if data is not None:
            return generated_data
    return dash.no_update


@app.callback([Output('editable-table', 'data'),
               Output('editable-table', 'columns')],
              [Input('load-waypoints-button', 'n_clicks'),
               Input('encounter-ids', 'value'),
               Input('ac-ids', 'value'),
               Input('add-rows-button', 'n_clicks'),
               Input('create-mode', 'n_clicks'),
               Input('create-new-button', 'n_clicks'),
               Input('end-new-button', 'n_clicks'),
               Input('marker-layer', 'children')],
              [State('editable-table', 'data'),
               State('editable-table', 'columns'),
               State('ac-index', 'value'),
               State('memory-data', 'data'),
               State('session', 'data')])
def update_data_table(upload_n_clicks, encounter_id_selected, ac_ids_selected, add_rows_n_clicks, create_n_clicks, start_new_n_clicks, end_new_n_clicks, current_markers, data, columns, ac_value, memory_data, ref_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    columns = [{"name": 'encounter_id', "id": 'encounter_id'}, {"name": 'ac_id', "id": 'ac_id'},\
                {"name": 'time', "id": 'time'}, {"name": 'xEast', "id": 'xEast'}, {"name": 'yNorth', "id": 'yNorth'},\
                {"name": 'zUp', "id": 'zUp'}, {"name": 'hor_speed', "id": 'hor_speed'}]

    if ctx == 'load-waypoints-button' and upload_n_clicks > 0:
        return [], []
        
    if ctx == 'encounter-ids':
        if encounter_id_selected is None or encounter_id_selected == []:
            return [], columns
        
        df = pd.DataFrame(memory_data)
        df_filtered = df.loc[df['encounter_id'] == encounter_id_selected]
        df_filtered = calculate_horizontal_speeds_df(df_filtered)
        return df_filtered.to_dict('records'), [{"name": i, "id": i} for i in df_filtered.columns]
    
    if ctx == 'ac-ids':
        if encounter_id_selected is None or encounter_id_selected == []:
            print('Select an encounter ID.')
            return dash.no_update, dash.no_update
        else:
            # AC IDs have been updated or loaded in
            df = pd.DataFrame(memory_data)
            df_filtered = df.loc[(df['encounter_id'] == encounter_id_selected) & (df['ac_id'].isin(ac_ids_selected))]
            df_filtered = calculate_horizontal_speeds_df(df_filtered)
            return df_filtered.to_dict('records'), [{"name": i, "id": i} for i in df_filtered.columns]

    elif ctx == 'create-mode' and create_n_clicks > 0 and end_new_n_clicks == 0:
        # wipe all data
        return [], columns

    elif ctx == 'add-rows-button' and create_n_clicks == 0:
        if add_rows_n_clicks > 0:
            # add an empty row
            data.append({col["id"]: '' for col in columns})
        return data, columns

    else:
        if ctx == 'create-new-button' and start_new_n_clicks > 0:
            global timestep
            timestep = 0
            
        elif ctx == 'marker-layer' and create_n_clicks > 0 and start_new_n_clicks > 0:
            if not ac_value or not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_alt']: #not encounter_value
                return dash.no_update, dash.no_update
            
            timestep += 1
            if len(data) != len(current_markers):
                # in creative mode and user has created another marker 
                # we add each marker to the data as it is created 
                # so we only have to grab last marker in the list
                pos = current_markers[-1]['props']['position']
                xEast, yNorth, zUp = pm.geodetic2enu(pos[0], pos[1], ref_data['ref_alt']*FT_TO_M, 
                                                     ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M,
                                                     ell=pm.Ellipsoid('wgs84'), deg=True)
                marker_dict = {'encounter_id': 0, 'ac_id': ac_value, 'time': timestep, 
                               'xEast': xEast*M_TO_NM, 'yNorth': yNorth*M_TO_NM, 'zUp': zUp*M_TO_FT, 'hor_speed':0}  #'encounter_id': encounter_value
                data.append(marker_dict)
    
            else:
                # an already existing marker was dragged
                # and therefore its position in data table needs to get updated

                # FIXME: there must be a more efficient way to do this
                # because right now I touch all data points instead of the one that
                # is explicitly changed.
                for i, data_point in enumerate(data):
                    pos = current_markers[i]['props']['position']
                    xEast, yNorth, zUp = pm.geodetic2enu(pos[0], pos[1], ref_data['ref_alt']*FT_TO_M, 
                                                         ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M,
                                                         ell=pm.Ellipsoid('wgs84'), deg=True)
                    data_point['xEast'] = xEast*M_TO_NM
                    data_point['yNorth'] = yNorth*M_TO_NM
                    data_point['zUp'] = zUp*M_TO_FT
            return data, columns
        
        elif ctx == 'end-new-button' and end_new_n_clicks > 0: 
            df = pd.DataFrame(data)
            df = calculate_horizontal_speeds_df(df)
            return df.to_dict('records'), [{"name": i, "id": i} for i in df.columns]
            
        return dash.no_update, dash.no_update


##########################################################################################
##########################################################################################
@app.callback(Output('encounter-ids', 'options'),
              [Input('memory-data', 'data'),
               Input('create-mode', 'n_clicks'),
               Input('end-new-button', 'n_clicks')],
              [State('encounter-ids', 'options')])
def update_encounter_dropdown(memory_data, create_n_clicks, end_new_n_clicks, options):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    
    if ctx == 'memory-data':
        if memory_data == [{}]: #or memory_data == []
            return []
        else:
            df = pd.DataFrame(memory_data)
            encounter_ids = df['encounter_id'].unique()
            options = [{'value': encounter_id, 'label': 'Encounter '+ str(int(encounter_id))} for encounter_id in encounter_ids]
            return options
    elif ctx == 'create-mode' and create_n_clicks > 0:
        if memory_data is not [{}]: #and memory_data != []
            return []
    
    elif ctx == 'end-new-button' and end_new_n_clicks > 0:
        encounter_value = 0
#         if encounter_value is not None:
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
               State('editable-table', 'data'),
               State('memory-data', 'data')])
def update_ac_dropdown(upload_n_clicks, create_n_clicks, encounter_id_selected, end_new_n_clicks, ac_value, options, start_new_n_clicks, data, memory_data):
    if not encounter_id_selected and not ac_value:
        return dash.no_update
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    
    if ctx == 'load-waypoints-button' and upload_n_clicks > 0:
        return []    
    elif ctx == 'encounter-ids' and upload_n_clicks > 0 and end_new_n_clicks == 0:
        df = pd.DataFrame(memory_data)
        df_filtered = df.loc[df['encounter_id'] == encounter_id_selected]
        ac_ids = df_filtered['ac_id'].unique()
        dropdown_options = [{'value': ac_id, 'label': 'AC '+ str(ac_id)} for ac_id in ac_ids]
        return dropdown_options
    
    elif ctx == 'create-mode' and create_n_clicks > 0 and start_new_n_clicks == 0 and end_new_n_clicks == 0:
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
              Input('create-mode', 'n_clicks'),
               Input('create-new-button', 'n_clicks'),
               Input('end-new-button', 'n_clicks'),
               Input('generate-button', 'n_clicks'),
               Input('session', 'data')],
               [State('ac-index', 'value'),
               State('ac-ids', 'value'),
               State('memory-data', 'data')])
def update_dropdowns_value(encounter_id_selected, create_n_clicks, start_new_n_clicks, end_new_n_clicks, generate_n_clicks, ref_data, ac_value, ac_selected, memory_data): #encounter_value, 
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'encounter-ids':
        if encounter_id_selected is None or encounter_id_selected == []:
            return [], []
        else:
            df = pd.DataFrame(memory_data)
            df_filtered = df.loc[df['encounter_id'] == encounter_id_selected]
            ac_ids = df_filtered['ac_id'].unique()
            return encounter_id_selected, [ac_id for ac_id in ac_ids]

    elif ctx == 'create-mode' and create_n_clicks > 0:
        return [], []

    elif ctx == 'create-new-button' and start_new_n_clicks > 0:
        return [], ac_selected

    elif ctx == 'end-new-button' and end_new_n_clicks > 0:
        if not ac_value: #not encounter_value 
            print("Enter an AC ID to create new nominal path")
        else:
            ac_selected.append(ac_value)
            return [0], ac_selected #[encounter_value], 

    elif ctx == 'generate-button':
        # entered generation mode - clear dropdown values
        if generate_n_clicks > 0:
            return [], []

    elif ctx == 'session':
        if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
            # no trajectories should be selected if there isn't a ref point
            print('Enter a reference point.')
            return [], []

    return dash.no_update, dash.no_update



@app.callback([Output('encounter-ids', 'disabled'),
               Output('ac-ids', 'disabled')],
              [Input('create-mode', 'n_clicks'),
               Input('exit-create-mode', 'n_clicks'),
               Input('create-new-button', 'n_clicks'),
               Input('end-new-button', 'n_clicks'),
               Input('session', 'data')])
def creative_mode_disable_dropdowns(create_n_clicks, exit_create_n_clicks, start_new_n_clicks, end_new_n_clicks, ref_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if create_n_clicks > 0:
        if ctx == 'create-mode' and start_new_n_clicks == 0:
            return True, True
        elif ctx == 'create-new-button' and start_new_n_clicks > 0:
            return True, True

        elif ctx == 'end-new-button' and end_new_n_clicks > 0:
            return False, False
        elif ctx == 'exit-create-mode' and exit_create_n_clicks > 0:
            return False, False

    elif ctx == 'session':
        if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
            # no trajectories should be selected if there isn't a ref point
            return True, True
        else:
            return False, False

    return dash.no_update, dash.no_update


##########################################################################################
##########################################################################################
@app.callback(Output('tabs', 'value'),
              Input('create-new-button', 'n_clicks'))
def creative_mode_switch_tabs(n_clicks):
    if n_clicks > 0:
        return 'tab-3'
    return 'tab-1'
    
    
@app.callback([Output('tab1','disabled'),
               Output('tab2', 'disabled')],
              [Input('create-mode', 'n_clicks'),
               Input('create-new-button', 'n_clicks'),
               Input('end-new-button', 'n_clicks'),
               Input('exit-create-mode', 'n_clicks')])
def creative_mode_disable_tabs(create_n_clicks, start_new_n_clicks, end_new_n_clicks, exit_create_n_clicks):
    if create_n_clicks > 0 and start_new_n_clicks > 0:
        return True, True
    elif end_new_n_clicks > 0 or exit_create_n_clicks > 0:
        return False, False
    return dash.no_update, dash.no_update


@app.callback([Output('create-mode', 'n_clicks'),
               Output('exit-create-mode', 'n_clicks'),
               Output('create-new-button', 'n_clicks'),
               Output('end-new-button', 'n_clicks'),
               Output('exit-create-mode', 'style'),
               Output('create-new-button', 'style'),
               Output('end-new-button', 'style'),
               Output('ac-index', 'style')],
              [Input('create-mode', 'n_clicks'), 
               Input('exit-create-mode', 'n_clicks'),
               Input('create-new-button', 'n_clicks'),
               Input('end-new-button', 'n_clicks')],
              [State('exit-create-mode', 'style'),
               State('create-new-button', 'style'),
               State('end-new-button', 'style'),
               State('ac-index', 'style')])
def toggle_create_mode(create_n_clicks, exit_create_n_clicks, start_new_n_clicks, end_new_n_clicks, exit_create_style, start_new_style, end_new_style, ac_style):
    reset_create_clicks, reset_exit_create_clicks = create_n_clicks, exit_create_n_clicks
    reset_start_new_clicks, reset_end_new_clicks = start_new_n_clicks, end_new_n_clicks

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if create_n_clicks > 0:
        if ctx == 'create-mode':
            reset_exit_create_clicks = 0 
            exit_create_style['display'], start_new_style['display'] = 'inline-block', 'inline-block'

        if ctx == 'create-new-button' and start_new_n_clicks > 0:
            reset_end_new_clicks = 0
            ac_style['display'], end_new_style['display'] = 'inline-block', 'inline-block'
            
        if ctx == 'end-new-button' and end_new_n_clicks > 0:
            reset_start_new_clicks = 0
            ac_style['display'], end_new_style['display'] = 'none', 'none'
            
        if ctx == 'exit-create-mode' and exit_create_n_clicks > 0:
            reset_create_clicks = 0
            reset_start_new_clicks, reset_end_new_clicks = 0, 0
            exit_create_style['display'], start_new_style['display'], end_new_style['display'] ='none', 'none', 'none'
            ac_style['display'] = 'none'     
    return reset_create_clicks, reset_exit_create_clicks, reset_start_new_clicks, reset_end_new_clicks, exit_create_style, start_new_style, end_new_style, ac_style


@app.callback(Output('ac-index', 'value'),
                Input('exit-create-mode', 'n_clicks'),
                State('ac-ids', 'options'))
def exit_creative_mode_reset_ac_index(exit_n_clicks, options):
    if exit_n_clicks > 0:
        return None
    return dash.no_update


##########################################################################################
##########################################################################################
@app.callback([Output('ref-point-output', 'children'),
                Output('session', 'data')],
                [Input('set-ref-button', 'n_clicks'),
                Input('clear-ref-button', 'n_clicks')],
                [State('ref-point-input', 'value'),
                State('ref-point-input', 'pattern'),
                State('session', 'data')])
def set_ref_point_data(set_n_clicks, clear_n_clicks, ref_point_value, pattern, ref_data):
    patt = re.compile(pattern)
    ref = 'reference point: ', ref_data['ref_lat'], chr(176), "/ ", ref_data['ref_long'], chr(176), '/ ', ref_data['ref_alt'], 'ft'

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if ctx == 'set-ref-button':
        if set_n_clicks > 0 and ref_point_value:
            p = patt.match(ref_point_value)
            if p:
                vals = p.groups()
                ref_data['ref_lat'] = float(vals[0])
                ref_data['ref_long'] = float(vals[1])
                ref_data['ref_alt'] = float(vals[2])

                return 'reference point: ' + ref_point_value, ref_data
            else:
                return '!!invalid format!!', ref_data

    elif ctx == 'clear-ref-button':
        if clear_n_clicks > 0:
            ref_data['ref_lat'] = None
            ref_data['ref_long'] = None
            ref_data['ref_alt'] = None
            return 'reference point: ', ref_data
    
    return ref, ref_data


@app.callback(Output('ref-point-input', 'value'),
                [Input('set-ref-button', 'n_clicks'),
                Input('clear-ref-button', 'n_clicks')],
                State('ref-point-output', 'children'))
def reset_ref_point_value(set_n_clicks, clear_n_clicks, children):
    if clear_n_clicks > 0:
        return ''
    return dash.no_update


@app.callback(Output('ref-point-input', 'disabled'),
                [Input('create-mode', 'n_clicks'),
                Input('exit-create-mode', 'n_clicks')])
def disable_ref_input(create_n_clicks, exit_create_n_clicks):
    if create_n_clicks > 0:
        return True
    if exit_create_n_clicks > 0:
        return False
    return dash.no_update


@app.callback(Output('clear-ref-button', 'disabled'),
                [Input('create-mode', 'n_clicks'),
                Input('exit-create-mode', 'n_clicks')])
def disable_clear_ref_button(create_n_clicks, exit_create_n_clicks):
    if create_n_clicks > 0:
        return True
    if exit_create_n_clicks > 0:
        return False
    return dash.no_update

@app.callback(Output('set-ref-button', 'disabled'),
                [Input('create-mode', 'n_clicks'),
                Input('exit-create-mode', 'n_clicks')])
def disable_set_ref_button(create_n_clicks, exit_create_n_clicks):
    if create_n_clicks > 0:
        return True
    if exit_create_n_clicks > 0:
        return False
    return dash.no_update

##########################################################################################
##########################################################################################
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

@app.callback(Output('nominal-path-ac-ids', 'options'),
                Input('ac-ids', 'options'))
def set_nominal_enc_id_options(ac_options):
    if ac_options is not None:
        return ac_options
    
    return dash.no_update


@app.callback(Output('generated-encounters', 'data'),
                Input('generate-button', 'n_clicks'),
                [State('nominal-path-ac-ids', 'value'),
                State('sigma-input', 'value'),
                State('num-encounters-input', 'value'),
                State('memory-data', 'data')])
def generate_encounters(gen_n_clicks, nom_ac_ids, sigma, num_encounters, memory_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'generate-button':
        if gen_n_clicks > 0:

            # error checking
            error = False
            if memory_data == [{}]: # or memory_data == []:
                print('Must create a nominal encounter')
                error = True
            if not nom_ac_ids:
                print("Must select at least one nominal path")
                error = True
            if not sigma:
                print('Must input a sigma value')
                error = True
            if not num_encounters:
                print('Must input number of encounters to generate')
                error = True
            if error:
                return {}

            cov = [ [sigma, 0, 0], 
                    [0, sigma, 0], 
                    [0, 0, sigma] ]

            df = pd.DataFrame(memory_data)  
            ac_params = {}
            for ac in range(1, len(nom_ac_ids)+1):
                ac_data = (df.loc[df['ac_id'] == ac]).to_dict('records')
                ac_params[ac] = [[waypoint['xEast'], waypoint['yNorth'], waypoint['zUp']] for waypoint in ac_data]
            
            generated_data = []
            for ac in range(1, len(nom_ac_ids)+1):
                # this should typically only happen twice
                params = ac_params[ac]
                waypoints_list = [np.random.multivariate_normal(mean,cov,int(num_encounters)) for mean in params]
                generated_data += [{'encounter_id': enc_id, 'ac_id': ac, 'time': i, 'xEast': waypoint[0], 'yNorth': waypoint[1], 'zUp': waypoint[2]} for i,waypoints in enumerate(waypoints_list) for enc_id, waypoint in enumerate(waypoints)]
            
            # if we need them to be sorted...
            # generated_data = sorted(generated_data, key=lambda k: k['encounter_id'])

            return generated_data


    return dash.no_update

##########################################################################################
##########################################################################################
# @app.callback(Output('density-heatmap', 'figure'),
#                 Input('generated-encounters', 'data'))
# def on_generation_update_density_heatmap(generated_data):
#     df = pd.DataFrame(generated_data)
#     df_ac_1= df.loc[df['ac_id'] == 1]
#     # bottom_x = df_ac_1['xEast'].min()
#     # top_x = df_ac_1['xEast'].max()
#     # bottom_y = df_ac_1['yNorth'].min()
#     # top_y = df_ac_1['yNorth'].max()

#     # print('\n--xEast Values--')
#     # print(df_ac_1['xEast'])

#     # print('\n--yNorth Values--')
#     # print(df_ac_1['yNorth'])

#     x_y_counts = df_ac_1[['xEast','yNorth']].value_counts(sort=False).reset_index()
#     #print(x_y_counts['xEast'])
#     # print(bottom_x)
#     # print()
#     # print(top_x)
#     #print(df_ac_1)
#     #df_ac_2 = df.loc[df['ac_id'] == 2]
#     #df_filtered = df.loc[df['encounter_id'] == encounter_id_selected]
#     fig = go.Figure(data=go.Heatmap(x=x_y_counts['xEast'],
#                         y=x_y_counts['yNorth'],
#                         z=x_y_counts[0],
#                         colorscale=[[0, "#FFFFFF"], [1, "#19410a"]]),
#                     layout=go.Layout(title='HeatMap')
#     )
#     return fig


    # fig = px.density_heatmap(df_ac_1, x='xEast', y='yNorth', nbinsx=100, nbinsy=100, title='Aircraft 1', color_continuous_scale='Viridis')
    # return fig



##########################################################################################
##########################################################################################
@app.callback([Output('tab-1-graphs', 'style'), 
              Output('tab-2-graphs', 'style'), 
              Output('tab-3-graphs', 'style'),
#               Output('tab-4-graphs','style')
              ],            
              Input('tabs', 'value'))
def render_content(active_tab):
    # easy on-off toggle for rendering content
    on = {'display': 'block'}
    off = {'display': 'none'}
    
#     if active_tab == 'tab-1':
#         return on, off, off #, off
#     elif active_tab == 'tab-2':
#         return off, on, off #, off
#     elif active_tab == 'tab-3':
#         return off, off, on #, off
#     # elif active_tab == 'tab-4':
#     #     return off, off, off, on

    if active_tab == 'tab-1':
        return on, off, off
    elif active_tab == 'tab-2':
        return off, on, off
    elif active_tab == 'tab-3':
        return off, off, on
    
    if not active_tab:
        return "No tab actively selected"
    else:
        return "invalid tab"


if __name__ == '__main__':
    app.run_server(debug=True, port=8332)
    
