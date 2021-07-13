import dash
from dash.dependencies import Input, Output, State, ALL
# from dash.exceptions import PreventUpdate

import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_leaflet as dl

import pandas as pd
import numpy as np
import collections

import json
import pymap3d as pm
import re

from read_file import *
import base64

print('\n\n############ Start of code ############')

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
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


map_iconUrl = "https://dash-leaflet.herokuapp.com/assets/icon_plane.png"
map_marker = dict(rotate=True, markerOptions=dict(icon=dict(iconUrl=map_iconUrl, iconAnchor=[16, 16])))
map_patterns = [dict(repeat='15', dash=dict(pixelSize=0, pathOptions=dict(color='#000000', weight=5, opacity=0.9))),
            dict(offset='100%', repeat='0%', marker=map_marker)]



app.layout = html.Div([
    # memory store reverts to the default on every page refresh
    dcc.Store(id='memory-data'),
    dcc.Store(id='session', data={'ref_lat': 40.63993,
                                  'ref_long': -73.77869,
                                  'ref_alt': 12.7}),
    
    # style
    html.Br(), 
    
    # buttons to load/save waypoints
    html.Div([
        html.Div([
            html.Label([
                dcc.Upload(id='load-waypoints', children = 
                           html.Button('Load Waypoints (.dat)', id='load-waypoints-button', n_clicks=0))
            ])
        ], style={"margin-bottom":"10px", 'display':'inline-block'}),

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
                 style={"margin-bottom":"10px", 'color': 'green', 'display':'none'}), 
        dcc.Input(id="encounter-index", type="number", placeholder="Enter encounter ID", debounce=False, min=1, 
                 style={"margin-left": "15px", "margin-bottom":"10px", 'display':'none'}),
        dcc.Input(id="ac-index", type="number", placeholder="Enter AC ID", debounce=False, min=1, 
                 style={"margin-left": "15px", "margin-bottom":"10px", 'display':'none'}),
        html.Button('Exit New Nominal Path', id='end-new-button', n_clicks=0,
                 style={"margin-left": "15px", "margin-bottom":"10px", 'color': 'green', 'display':'none'})
    ], className  = 'row'),

    
    # encounter/AC ID dropdown menu
    html.Div([
        html.Div([
            dcc.Dropdown(id='encounter-ids', placeholder="Select an encounter ID", multi=False)
        ], style={"margin-bottom":"10px"}, className='two columns'),
        html.Div([
            dcc.Dropdown(id='ac-ids', placeholder="Select AC ID(s)", multi=True)
        ], style={"margin-left": "15px", "margin-bottom":"10px"}, className='two columns'),
    ], className  = 'row'),


    # reference point input
    html.Div(id='reference-point-div', children = [
        dcc.Input(id='ref-point-input', type='text', 
                  placeholder='lat/lng/alt: 0.0/0.0/0.0',
                  debounce=True,
                  pattern=u"^(\-?\d+\.\d+?)\/(\-?\d+\.\d+?)\/(\d+\.\d+?)$",
                  style={'display':'inline-block'}),
        html.Button('Set Reference Point', id='set-ref-button', n_clicks=0,
                  style={"margin-left": "15px", 'display':'inline-block'}),
        html.Button('Clear', id='clear-ref-button', n_clicks=0,
                  style={"margin-left": "15px", 'display':'inline-block'}),
        html.Div(id='ref-point-output', children=[],
                  style={"margin-left": "5px"})
        ]
    ),

    html.Br(),
    
    
    # main tabs for navigating webpage
    html.Div([
        dcc.Tabs(id="tabs",
                 children=[
                     dcc.Tab(id='tab1', label='Graphs', value='tab-1'),
                     dcc.Tab(id='tab2', label='3d_Graph', value='tab-2'),
                     dcc.Tab(id='tab3', label='Map', value='tab-3')
                 ],
                 value='tab-1'),
        html.Div(id='tabs-content', children = None)
    ]),

    # initialize and display tab-1 graphs
    html.Div(id = "tab-1-graphs", 
             children=[
                 html.Div([
                     html.Div([dcc.Graph(id='editable-graph-xy', figure={})],
                               className='six columns', 
                               style={'display': 'inline-block'}),
                     html.Div([dcc.Graph(id='editable-graph-tz', figure={})],
                               className='six columns', 
                               style={'display': 'inline-block'})
                 ], className='row'),
                 html.Div([
                     html.Div([dcc.Graph(id='editable-graph-tspeed',figure={})], 
                               className='six columns', 
                               style={'display': 'none'}) #'inline-block'})
                 ], className='row')
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
#                         zoom=10, center=(40.63993, -73.77869), 
                        doubleClickZoom=False,
                        style={'width': '1500px', 'height': '750px', 'margin': "auto", 
                               'autosize': True, 'display': "block"})
             ], style={'display': "block"}),
    
    # style
    html.Br(), html.Br(),

    # waypoints data table
    html.Div([
        dash_table.DataTable(
            id = 'editable-table',
            editable = True,
            row_deletable = True),
        html.Button('Add Row', id='add-rows-button', n_clicks=0),
    ], className='row'),
    
    # style
    html.Br(), html.Br()
]) 


##########################################################################################
##########################################################################################
@app.callback(Output('editable-graph-xy', 'figure'),
              Input('editable-table', 'data'))
def update_graph_xy(data):
    if data is None:
        return dash.no_update
    aggregation = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in data:
        if row.get('xEast') != '' and row.get('yNorth') != '':        
            a = aggregation[float(row.get('ac_id'))]
            a['name'], a['color'] = 'AC '+ str(row['ac_id']), row['ac_id']
            a['type'], a['mode'], a['marker'] = 'scatter', 'lines+markers', {'size': 5}
            
            a['x'].append(float(row.get('xEast')))
            a['y'].append(float(row.get('yNorth')))
    A = [x for x in aggregation.values()]
    
    return {'data': [x for x in aggregation.values()],
            'layout': {'title': 'xEast vs yNorth',
                       'xaxis': {'title': 'xEast (m)'},
                       'yaxis': {'title': 'yNorth (m)'}}
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
            a['name'], a['color'] = 'AC '+str(row['ac_id']), row['ac_id']
            a['type'], a['mode'], a['marker'] = 'scatter', 'lines+markers', {'size': 5}

            a['x'].append(float(row['time']))
            a['y'].append(float(row['zUp']))
    return {'data': [x for x in aggregation.values()],
            'layout': {'title': 'Time vs zUp',
                       'xaxis': {'title': 'Time (s)'},
                       'yaxis': {'title': 'zUp (m)'}}
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
            a['name'], a['color'] = 'AC '+str(row['ac_id']), row['ac_id']
            a['type'], a['mode'], a['marker'] = 'scatter', 'lines+markers', {'size': 5}

            a['x'].append(float(row['time']))
            a['y'].append(float(row['hor_speed']))
    return {'data': [x for x in aggregation.values()],
            'layout': {'title': 'Time vs Horizontal Speed',
                       'xaxis': {'title': 'Time (s)'},
                       'yaxis': {'title': 'Speed (m/s)'}}
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
            a['name'], a['color'] = 'AC '+str(row['ac_id']), row['ac_id']
            a['type'], a['mode'], a['marker'] = 'scatter3d', 'lines+markers', {'size': 5}

            a['x'].append(float(row['xEast']))
            a['y'].append(float(row['yNorth']))
            a['z'].append(float(row['zUp']))
    return {'data': [x for x in aggregation.values()],
            'layout': {'scene': {'xaxis': {'title': 'xEast'},
                                 'yaxis': {'title': 'yNorth'},
                                 'zaxis': {'title': 'zUp'}},
#                        'width': '1200px', 'height': '1200px',
                       'margin': {'l':0, 'r':0, 'b':0, 't':0}}
           }


@app.callback([Output('map', 'center'),
               Output('map', 'zoom')],
              Input('session', 'data'))
def center_map_around_ref_input(ref_data):
    if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
        # ref point was cleared - so reset to center of US and zoom out
        return (39,-98), 4
    return (ref_data['ref_lat'], ref_data['ref_long']), 10


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
                lat, lng, alt = pm.enu2geodetic(data_id['xEast'][i], data_id['yNorth'][i], data_id['zUp'][i], 
                                                ref_lat, ref_long, ref_alt, 
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
                 Input(dict(tag="marker", index=ALL), 'children')],
                [State('marker-layer', 'children'),
                 State('ac-index', 'value'),
                 State('session', 'data'),
                 State('load-waypoints-button', 'n_clicks'),
                 State('create-mode', 'n_clicks')])
def create_markers(dbl_click_lat_lng, start_new_n_clicks, encounter_options, ac_ids, current_marker_tools, current_markers, ac_value, ref_data, upload_n_clicks, create_n_clicks): 
    ctx = dash.callback_context

    if not ctx.triggered or not ctx.triggered[0]['value']:
        return dash.no_update

    ctx = ctx.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'map':
        # user double clicked the map
        if create_n_clicks > 0 and start_new_n_clicks > 0:
            if ac_value: #and encounter_value 
                if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
                    # reference point has not been reset, cannot create markers until it is
                    return dash.no_update

                xEast, yNorth, zUp = pm.geodetic2enu(dbl_click_lat_lng[0], dbl_click_lat_lng[1], ref_data['ref_alt'], 
                                                    ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt'],
                                                    ell=pm.Ellipsoid('wgs84'), deg=True)

                # markers have a position that is always in lat/long 
                # so that the map object can place then correctly
                # but the tooltips (blue pointer on the map) displays that position
                # in ENU coords to the user
                current_markers.append(dl.Marker(id=dict(tag="marker", index=len(current_markers)), 
                                        position=dbl_click_lat_lng,
                                        children=dl.Tooltip("({:.3f}, {:.3f})".format(*[xEast, yNorth])), 
                                        draggable=True))
            else:
                print('Enter an AC ID.')
        
    elif ctx == 'create-new-button':
        if create_n_clicks > 0 and len(current_markers) > 0:
            # clear past markers only when create-new-button is clicked again
            return []
    
    # elif ctx == 'create-new-button' and start_new_n_clicks > 0:
    #     return []

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
        # a marker has been dragged

        if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
            return dash.no_update

        # the input will be the dictionary id of the marker that was dragged
        # in the form {'tag':'marker','index':int}
        index = json.loads(ctx)['index']
        pos = new_positions[index]
        xEast, yNorth, zUp = pm.geodetic2enu(pos[0], pos[1], ref_data['ref_alt'], 
                                            ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt'],
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
               Input('load-waypoints', 'contents')],
              [State('load-waypoints', 'filename'),
               State('editable-table', 'data')])
def update_memory_data(upload_n_clicks, create_n_clicks, end_new_n_clicks, exit_create_n_clicks, contents, filename, data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    
    if ctx == 'create-mode' and create_n_clicks > 0:
        return [{}]
    elif ctx == 'end-new-button' and end_new_n_clicks > 0:
        return data
    
    if ctx == 'load-waypoints-button' and upload_n_clicks > 0:
        return [{}]
    elif ctx == 'load-waypoints':
        df = parse_contents(contents, filename) 
        return df.to_dict('records')
    elif contents is None:
        return [{}]
    elif not filename:
        return []
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
    
    if ctx == 'load-waypoints-button' and upload_n_clicks > 0:
        return [], []
        
    elif ctx == 'encounter-ids' and memory_data != [] and memory_data != [{}]: #and upload_n_clicks > 0 and exit_n_clicks == 0:
        # encounter ID has been updated or loaded in
        df = pd.DataFrame(memory_data)
        df_filtered = df.loc[df['encounter_id'] == encounter_id_selected]
        df_filtered = calculate_horizontal_speeds_df(df_filtered)
        return df_filtered.to_dict('records'), [{"name": i, "id": i} for i in df_filtered.columns]
    
    elif ctx == 'ac-ids':
        if encounter_id_selected is None or encounter_id_selected == []:
            print('Select an encounter ID.')
            return dash.no_update, dash.no_update
        else:
            # AC IDs have been updated or loaded in
            df = pd.DataFrame(memory_data)
            df_filtered = df.loc[(df['encounter_id'] == encounter_id_selected) & (df['ac_id'].isin(ac_ids_selected))]
            df_filtered = calculate_horizontal_speeds_df(df_filtered)
            return df_filtered.to_dict('records'), [{"name": i, "id": i} for i in df_filtered.columns]

    elif ctx == 'create-mode':
        if create_n_clicks > 0 and end_new_n_clicks == 0:
            # wipe all data
            return [], [{"name": 'encounter_id', "id": 'encounter_id'}, {"name": 'ac_id', "id": 'ac_id'}, {"name": 'time', "id": 'time'}, {"name": 'xEast', "id": 'xEast'}, {"name": 'yNorth', "id": 'yNorth'}, {"name": 'zUp', "id": 'zUp'}, {"name": 'hor_speed', "id": 'hor_speed'}]

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
                xEast, yNorth, zUp = pm.geodetic2enu(pos[0], pos[1], ref_data['ref_alt'], 
                                                     ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt'],
                                                     ell=pm.Ellipsoid('wgs84'), deg=True)
                marker_dict = {'encounter_id': 0, 'ac_id': ac_value, 'time': timestep, 
                               'xEast': xEast, 'yNorth': yNorth, 'zUp': zUp, 'hor_speed':0}  #'encounter_id': encounter_value
                data.append(marker_dict)
    
            else:
                # an already existing marker was dragged
                # and therefore its position in data table needs to get updated

                # FIXME: there must be a more efficient way to do this
                # because right now I touch all data points instead of the one that
                # is explicitly changed.
                for i, data_point in enumerate(data):
                    pos = current_markers[i]['props']['position']
                    xEast, yNorth, zUp = pm.geodetic2enu(pos[0], pos[1], ref_data['ref_alt'], 
                                                         ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt'],
                                                         ell=pm.Ellipsoid('wgs84'), deg=True)
                    data_point['xEast'] = xEast
                    data_point['yNorth'] = yNorth
                    data_point['zUp'] = zUp
            return data, columns
        
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
        if memory_data == [] or memory_data == [{}]:
            return []
        else:
            df = pd.DataFrame(memory_data)
            encounter_ids = df['encounter_id'].unique()
            options = [{'value': encounter_id, 'label': 'Encounter '+ str(int(encounter_id))} for encounter_id in encounter_ids]
            return options
    elif ctx == 'create-mode' and create_n_clicks > 0:
        if memory_data != [] and memory_data is not [{}]:
            return []
    
    elif ctx == 'end-new-button':
        if end_new_n_clicks > 0:
            encounter_value = 0

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
    
    elif ctx == 'create-mode' and create_n_clicks > 0: # and start_new_n_clicks == 0 and end_new_n_clicks == 0:
        return []  
    elif ctx == 'end-new-button' and end_new_n_clicks > 0:
        if ac_value is not None:
            new_option = {'value': ac_value, 'label': 'AC '+ str(ac_value)}
            if options is None or options == []:
                options= [new_option]
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
               Input('session', 'data')],
               [State('encounter-index', 'value'),
               State('ac-index', 'value')])
def update_dropdowns_value(encounter_id_selected, create_n_clicks, start_new_n_clicks, end_new_n_clicks, ref_data, encounter_value, ac_value):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'encounter-ids':
        return encounter_id_selected, []

    elif ctx == 'create-mode':
        if create_n_clicks > 0:
            # clear selected ac and enc indices when enter creative mode
            return "", []
    
    elif ctx == 'create-new-button':
        if start_new_n_clicks > 0:
            #print('encounter index value: ', encounter_value)
            return dash.no_update, []

    elif ctx == 'end-new-button':
        if end_new_n_clicks > 0:
            if not encounter_value or not ac_value:
                # if no ac_value was inputted, that means no markers were created
                # because the user cannot create markers until an ac_valye is chosen
                # so just clear the dropdown menu
                print("Enter encounter/AC ID to create new nominal path")
                return "", []
            else:
                print('encounter_value: ', encounter_value, ' ac_value: ', ac_value)
                # otherwise, return the encounter_value and ac_value chosen by user
                return encounter_value, [ac_value]

    elif ctx == 'session':
        if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
            # no trajectories should be selected if there isn't a ref point
            print('Enter a reference point.')
            return "", []


    # shouldn't do this because the dropdowns will be disabled anyway !
    # elif ctx == 'create-new-button' and create_n_clicks > 0:
    #     return [], []

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

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'create-mode': # or ctx == 'create-new-bu':
        if create_n_clicks > 0:
            return True, True

    elif ctx == 'exit-create-mode':
        if exit_create_n_clicks > 0:
            return False, False

    elif ctx == 'session':
        if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
            # no trajectories should be selected if there isn't a ref point
            return True, True
        else:
            return False, False

    return dash.no_update, dash.no_update



    # if create_n_clicks > 0:
    #     if ctx == 'create-mode' and start_new_n_clicks == 0:
    #         return True, True
    #     elif ctx == 'create-new-button' and start_new_n_clicks > 0:
    #         return True, True

    #     elif ctx == 'end-new-button' and end_new_n_clicks > 0:
    #         return False, False
    #     elif ctx == 'exit-create-mode' and exit_create_n_clicks > 0:
    #         return False, False

    # elif ctx == 'session':
    #     if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
    #         # no trajectories should be selected if there isn't a ref point
    #         return True, True
    #     else:
    #         return False, False

    # return dash.no_update, dash.no_update


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
    if create_n_clicks > 0:
        return True, True
    elif exit_create_n_clicks > 0:
        return False, False

    return dash.no_update, dash.no_update
    
    
    # if create_n_clicks > 0 and start_new_n_clicks > 0:
    #     return True, True
    # elif end_new_n_clicks > 0 or exit_create_n_clicks > 0:
    #     return False, False
    # return dash.no_update, dash.no_update


@app.callback([Output('create-mode', 'n_clicks'),
               Output('exit-create-mode', 'n_clicks'),
               Output('create-new-button', 'n_clicks'),
               Output('end-new-button', 'n_clicks'),
               Output('exit-create-mode', 'style'),
               Output('create-new-button', 'style'),
               Output('end-new-button', 'style'),
               Output('encounter-index', 'style'),
               Output('ac-index', 'style')],
              [Input('create-mode', 'n_clicks'), 
               Input('exit-create-mode', 'n_clicks'),
               Input('create-new-button', 'n_clicks'),
               Input('end-new-button', 'n_clicks')],
              [State('exit-create-mode', 'style'),
               State('create-new-button', 'style'),
               State('end-new-button', 'style'),
               State('encounter-index', 'style'),
               State('ac-index', 'style')])
def toggle_create_mode(create_n_clicks, exit_create_n_clicks, start_new_n_clicks, end_new_n_clicks, exit_create_style, start_new_style, end_new_style, encounter_style, ac_style):
    reset_create_clicks, reset_exit_create_clicks = create_n_clicks, exit_create_n_clicks
    reset_start_new_clicks, reset_end_new_clicks = start_new_n_clicks, end_new_n_clicks

    on = 'inline-block'
    off = 'none'

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if create_n_clicks > 0:
        if ctx == 'create-mode':
            reset_exit_create_clicks = 0 
            exit_create_style['display'], start_new_style['display'] = on, on

        if ctx == 'create-new-button' and start_new_n_clicks > 0:
            reset_end_new_clicks = 0
            encounter_style['display'], ac_style['display'], end_new_style['display'] = on, on, on
            
        if ctx == 'end-new-button' and end_new_n_clicks > 0:
            reset_start_new_clicks = 0
            encounter_style['display'], ac_style['display'], end_new_style['display'] = off, off, off
            
        if ctx == 'exit-create-mode' and exit_create_n_clicks > 0:
            reset_create_clicks = 0
            reset_start_new_clicks, reset_end_new_clicks = 0, 0
            exit_create_style['display'], start_new_style['display'], end_new_style['display'] = off, off, off
            encounter_style['display'], ac_style['display'] = off, off
    return reset_create_clicks, reset_exit_create_clicks, reset_start_new_clicks, reset_end_new_clicks, exit_create_style, start_new_style, end_new_style, encounter_style, ac_style


@app.callback([Output('encounter-index', 'value'),
                Output('ac-index', 'value')],
                Input('exit-create-mode', 'n_clicks'))
def exit_create_mode_reset_enc_and_ac_index(exit_n_clicks):
    if exit_n_clicks > 0:
        return None, None
    
    return dash.no_update, dash.no_update


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
    ref = 'reference point: ', ref_data['ref_lat'], "/", ref_data['ref_long'], '/', ref_data['ref_alt']

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
def disable_ref_input(create_n_clicks, exit_create_n_clicks):
    if create_n_clicks > 0:
        return True
    if exit_create_n_clicks > 0:
        return False
    return dash.no_update


##########################################################################################
##########################################################################################
@app.callback([Output('tab-1-graphs', 'style'), 
              Output('tab-2-graphs', 'style'), 
              Output('tab-3-graphs', 'style')],            
              Input('tabs', 'value'))
def render_content(active_tab):
    # easy on-off toggle for rendering content
    on = {'display': 'block'}
    off = {'display': 'none'}
    
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
    app.run_server(debug=True, port=8330)
    

