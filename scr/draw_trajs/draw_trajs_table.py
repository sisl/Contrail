import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate

import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_leaflet as dl

import pandas as pd
import numpy as np
import collections

import json
import pymap3d as pm
import re

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', dbc.themes.BOOTSTRAP]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

columns = ['id', 'time', 'xEast', 'yNorth', 'zUp']
global df
df = pd.read_csv('data/traj_data_sample_ENU.csv', header=0)
traj_ids = set(df['id'])

def calculate_horizontal_speeds_df(dataf):
    hor_speeds = []
    for ac_id in traj_ids:
        ac_id_data = df.loc[df['id'] == ac_id]

        move_over_time = (np.roll(ac_id_data, -1, axis=0) - ac_id_data)[:-1]
        hor_speed = np.sqrt(move_over_time.xEast ** 2 + move_over_time.yNorth ** 2) / move_over_time['time']
        hor_speeds += (np.append(0.0, round(hor_speed, 4))).tolist()

    dataf['hor_speed'] = hor_speeds
    return dataf

df = calculate_horizontal_speeds_df(df)

map_iconUrl = "https://dash-leaflet.herokuapp.com/assets/icon_plane.png"
map_marker = dict(rotate=True, markerOptions=dict(icon=dict(iconUrl=map_iconUrl, iconAnchor=[16, 16])))
map_patterns = [dict(repeat='15', dash=dict(pixelSize=0, pathOptions=dict(color='#000000', weight=5, opacity=0.9))),
            dict(offset='100%', repeat='0%', marker=map_marker)]

def add_data_to_df(data):
    global df
    df = df.append(data, ignore_index=True)


def filter_ids(traj_ids_selected):
    if not traj_ids_selected:
        return []
    
    # get data for the trajectory IDs that are currently selected
    df_filtered = df.query('id in @traj_ids_selected')
    return df_filtered.to_dict('records')


############################################################
############################################################
app.layout = html.Div([
    # memory store reverts to the default on every page refresh
    dcc.Store(id='memory-output'),

    dcc.Store(id='session', data={'ref_lat': 40.63993,
                                  'ref_long': -73.77869,
                                  'ref_alt': 12.7}),

    dcc.Store(id='generated-encounters', data={}),
    
    # trajectory ID dropdown menu
    html.Div([
        dcc.Markdown(("""Trajectory ID list""")),
        dcc.Dropdown(id='trajectory-ids', 
                     options=[{'value': traj_id, 'label': 'AC '+ str(traj_id)} for traj_id in traj_ids], 
                     multi=True, 
                     value=[1, 2]),
        ],
        style={"margin-left": "15px"}
    ),
    
    # style
    html.Br(), 

    html.Div(id='buttons', children = [
        html.Button('Load Model', id='load-button', n_clicks=0,
                    style={"margin-left": "15px"}),
        html.Button('Save Model', id='save-button', n_clicks=0, 
                    style={"margin-left": "15px"}),
        
        html.Button('Create New Nominal Path', id='create-new-button', n_clicks=0,
                style={"margin-left": "15px"}),
                 
        html.Button('Exit Nominal Path Creative Mode', id='exit-edit-button', n_clicks=0,
                style={"margin-left": "15px", 'display':'none'}),

        dcc.Input(id="ac-index", type="number", placeholder="AC Index", 
                debounce=False, min=0,
                style={"margin-left": "15px", 'display':'none'})

        
        ]
    ),
    
    html.Br(), html.Br(),

    # reference point input, set and clear buttons
    html.Div(id='reference-point-div', children = [
        dcc.Input(id='ref-point-input', type='text', placeholder='lat/lng/alt: 0.0/0.0/0.0',
                debounce=True,
                pattern=u"^(\-?\d+\.\d+?)\/(\-?\d+\.\d+?)\/(\d+\.\d+?)$",
                style={'display':'inline-block', "margin-left": "15px"}),
        html.Button('Set Reference Point', id='set-ref-button', n_clicks=0,
                style={"margin-left": "15px", 'display':'inline-block'}),
        html.Button('Clear', id='clear-ref-button', n_clicks=0,
                style={"margin-left": "15px", 'display':'inline-block'}),
        html.Div(id='ref-point-output', children=[],
                style={"margin-left": "20px"})
        ]
    ),

    html.Br(),

    html.Div(id='generation', children=[
        html.Button('Generate Encounter Set', id='gen-encounters-button', n_clicks=0,
                style={'display':'inline-block', "margin-left": "15px"}),
        # html.Dialog(id='gen-dialog-box', children=[
        #     html.Button('BUTTON', id='button', n_clicks=0,
        #         style={'display':'inline-block'})
        #     ],
        #     hidden=False,
        #     title='Generate an Encounter Set',
        #     style={'display':'block',
        #             'size': (1000,1000)},
        #             )
        
    ]),

    html.Div(id='gen-modal-div', children=[
        dbc.Modal([
                dbc.ModalHeader("Generate an Encounter Set"),

                dbc.ModalBody("*****"),

                dcc.Markdown(("""Select a Nominal Path"""), style={"margin-left": "20px"}),

                dcc.Dropdown(id='nominal-path-id', 
                    options=[{'value': traj_id, 'label': 'AC '+ str(traj_id)} for traj_id in traj_ids], 
                    multi=True, 
                    value=[],
                    style={"margin-left": "10px", "width": "71%"}),

                
                html.Br(),

                dcc.Markdown(("""Input Sigma Value"""), style={"margin-left": "20px"}),

                dcc.Input(id='sigma-input', type='text', placeholder='default sigma = 1',
                    debounce=True,
                    pattern=u"^(\d+)$",
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
            id='gen-modal',
            is_open=False,
            size="lg",
            backdrop=True,  # Modal to not be closed by clicking on backdrop
            centered=True,  # Vertically center modal 
            keyboard=True,  # Close modal when escape is pressed
            fade=True,
            style={"max-width": "none", "width": "50%"}
            
        )
    ]),

    html.Br(), html.Br(),

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
    html.Div(id = "tab-1-graphs", children=[
            html.Div([
                html.Div([
                    dcc.Graph(id='editable-graph-xy',
                              figure={}
                             )], 
                    className='six columns', 
                    style={'display': 'inline-block'}
                ),
                html.Div([
                    dcc.Graph(id='editable-graph-tz',
                              figure={}
                             )],
                    className='six columns', 
                    style={'display': 'inline-block'}
                )
            ], className='row'),
            
            html.Div([
                html.Div([
                    dcc.Graph(id='editable-graph-tspeed',
                             figure={}
                             )], 
                    className='six columns', 
                    style={'display': 'inline-block'}
                )
            ], className='row')
        ],
        style={'display': 'block'}
    ),
    
    # initialize tab-2 graphs
    html.Div(id = 'tab-2-graphs', children = [
            dcc.Graph(id='editable-graph-xyz',
                      figure={}
                     )],
            style={'width': '1500px', 'height': '750px',
                   'margin': {'l':0, 'r':0, 'b':0, 't':0, 'pad':0}, 
                   'autosize': False, 'display': "block"}
        ),
    
    # initialize tab-3 graphs
    html.Div(id = 'tab-3-graphs', children = [
            dl.Map(children=[dl.TileLayer(), 
                             dl.LayerGroup(id='polyline-layer', children=[]),
                             dl.LayerGroup(id='marker-layer', children=[], attribution='off')],
                    id='map',
                    zoom=5.8, 
                    center=(40, -74),
                    doubleClickZoom=False,
                    style={'width': '1500px', 'height': '750px', 'margin': "auto", "display": "block"}
                    )],
            style={"display": "block"}
        ),
    
    # style
    html.Br(), html.Br(),

    # trajectory data table
    html.Div([
        dash_table.DataTable(
            id = 'editable-table',
            columns = [{'name': c, 'id': c} for c in df.columns],
            data = df.to_dict('records'),
            editable = True,
            row_deletable = True
        ),
        html.Button('Add Row', id='add-rows-button', n_clicks=0),
    ], className='row'),
    
    # style
    html.Br(), html.Br()
]) 



############################################################
############################################################
@app.callback(Output('memory-output', 'data'),
              Input('trajectory-ids', 'value'))
def update_memory(traj_ids_selected):
    return filter_ids(traj_ids_selected)



@app.callback(Output('editable-table', 'data'),
             [Input('trajectory-ids', 'value'),
             Input('add-rows-button', 'n_clicks'),
             Input('create-new-button', 'n_clicks'),
             Input('marker-layer', 'children')],
             #Input(WHATEVER)],
             [State('editable-table', 'data'),
             State('ac-index', 'value'),
             State('session', 'data')])
def update_data_table(traj_ids_selected, add_rows_n_clicks, create_n_clicks, current_markers, data, ac_index, ref_data):
    if data is None:
        raise PreventUpdate

    # allows us to identify which input triggered this callback
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'create-new-button':
        if create_n_clicks > 0:
            # wipe all data, start fresh
            return []

    elif ctx == 'add-rows-button' and create_n_clicks == 0:
        if add_rows_n_clicks > 0:
            # add an empty row
            data.append({c: '' for c in df.columns})

    elif ctx == 'trajectory-ids':
        # user has selected a new trajectory id or
        # deselected a trajectory id
        return filter_ids(traj_ids_selected)

    elif ctx == 'marker-layer' and create_n_clicks > 0:

        if not ac_index or not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
            # the ac_index has not been chosen
            # and the reference point has not been reset
            return dash.no_update
        
        if len(data) != len(current_markers):
            # in creative mode and user has created another marker 
            # we add each marker to the data as it is created 
            # so we only have to grab last marker in the list
            pos = current_markers[-1]['props']['position']
            xEast, yNorth, zUp = pm.geodetic2enu(pos[0], pos[1], ref_data['ref_alt'], 
                                                ref_data['ref_lat'], 
                                                ref_data['ref_long'], 
                                                ref_data['ref_long'],
                                                ell=pm.Ellipsoid('wgs84'), deg=True)
            marker_dict = {'id': ac_index, 'time': len(data)+1, 'xEast': xEast, 'yNorth': yNorth, 'zUp': zUp, 'hor_speed':0}
            data.append(marker_dict)
        else:
            # an already existing marker was dragged
            # and therefore its position in data table needs to get updated

            # FIXME: Should be able to isolate which position changed
            # in order to make this more efficient
            for i, data_point in enumerate(data):

                pos = current_markers[i]['props']['position']

                # data_point does not have altitutde value yet
                # so use ref_alt as default
                xEast, yNorth, zUp = pm.geodetic2enu(pos[0], pos[1], ref_data['ref_alt'], 
                                                ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt'],
                                                ell=pm.Ellipsoid('wgs84'), deg=True)
                data_point['xEast'] = xEast
                data_point['yNorth'] = yNorth
                data_point['zUp'] = zUp

    #elif ctx == 'WHATEVER':
        #do what you need to do here

    return data


@app.callback(Output('editable-graph-xy', 'figure'),
              Input('editable-table', 'data'))
def on_data_set_graph_xy(data):
    if data is None:
        raise PreventUpdate
    aggregation = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in data:
        if row.get('lat') != '' and row.get('long') != '':        
            a = aggregation[float(row.get('id'))]
            a['name'], a['color'] = 'AC '+ str(row['id']), row['id']
            a['type'], a['mode'], a['marker'] = 'scatter', 'lines+markers', {'size': 5}
            
            a['x'].append(float(row.get('xEast')))
            a['y'].append(float(row.get('yNorth')))
    return {'data': [x for x in aggregation.values()],
            'layout': {
                    'title': 'xEast vs yNorth',
                    'xaxis':{'title':'xEast (m)'},
                    'yaxis':{'title':'yNorth (m)'}
                    }
            }

 
@app.callback(Output('editable-graph-tz', 'figure'),
              Input('editable-table', 'data'))
def on_data_set_graph_tz(data):
    if data is None:
        raise PreventUpdate
    aggregation = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in data:
        if row.get('time') != '' and row.get('alt') != '':        
            a = aggregation[float(row.get('id'))]
            a['name'], a['color'] = 'AC '+str(row['id']), row['id']
            a['type'], a['mode'], a['marker'] = 'scatter', 'lines+markers', {'size': 5}

            a['x'].append(float(row['time']))
            a['y'].append(float(row['zUp']))
    return {'data': [x for x in aggregation.values()],
            'layout': {
                    'title': 'Time vs zUp',
                    'xaxis':{'title':'Time (????)'},
                    'yaxis':{'title':'zUp (m)'}
                    }
            }


@app.callback(Output('editable-graph-tspeed', 'figure'),
              Input('editable-table', 'data'))
def on_data_set_graph_tspeed(data):
    if data is None:
        raise PreventUpdate
    aggregation = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in data:
        if row.get('time') != '' and row.get('hor_speed') != '':        
            a = aggregation[float(row.get('id'))]
            a['name'], a['color'] = 'AC '+str(row['id']), row['id']
            a['type'], a['mode'], a['marker'] = 'scatter', 'lines+markers', {'size': 5}

            a['x'].append(float(row['time']))
            a['y'].append(float(row['hor_speed']))
    return {'data': [x for x in aggregation.values()],
            'layout': {
                    'title': 'Time vs Horizontal Speed',
                    'xaxis':{'title':'Time (???)'},
                    'yaxis':{'title':'Speed (m/s)'}
                    }
            }


@app.callback(Output('editable-graph-xyz', 'figure'),
              Input('editable-table', 'data'))
def on_data_set_graph_xyz(data):
    if data is None:
        raise PreventUpdate
    aggregation = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in data:
        if row.get('time') != '' and row.get('alt') != '':        
            a = aggregation[float(row.get('id'))]
            a['name'], a['color'] = 'AC '+str(row['id']), row['id']
            a['type'], a['mode'], a['marker'] = 'scatter3d', 'lines+markers', {'size': 5}

            a['x'].append(float(row['xEast']))
            a['y'].append(float(row['yNorth']))
            a['z'].append(float(row['zUp']))
    return {'data': [x for x in aggregation.values()],
            'layout': {
                'scene': {'xaxis': {'title': 'xEast (m)'},
                         'yaxis': {'title': 'yNorth (m)'},
                         'zaxis': {'title': 'zUp (m)'}},
                'width': '1200px', 'height': '1200px',
                'margin': {'l':0, 'r':0, 'b':0, 't':0}
            }}


@app.callback(Output('polyline-layer', 'children'),
              Input('editable-table', 'data'),
              [State('polyline-layer', 'children'),
              State('session', 'data')])         
def update_map(data, current_polylines, ref_data):
    if data is None:
        raise PreventUpdate

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'editable-table':
        # data table has changed - must update map polylines
        new_polylines = []
        
        if len(data) == 0:
            # if no data, save computation time
            return new_polylines

        aggregation = collections.defaultdict(lambda: collections.defaultdict(list))
        for row in data:
            if row.get('lat') != '' and row.get('long') != '':        
                a = aggregation[float(row.get('id'))]
                a['name'], a['color'] = 'AC '+ str(row['id']), row['id']

                a['lat'].append(float(row.get('xEast')))
                a['long'].append(float(row.get('yNorth')))
                a['alt'].append(float(row.get('zUp')))
        data_group = [x for x in aggregation.values()]
            
        # pulling out the reference point data from the
        # dcc.Store('session', 'data') object
        ref_lat = ref_data['ref_lat']
        ref_long = ref_data['ref_long']
        ref_alt = ref_data['ref_alt']

        for data_id in data_group:

            lat_lng_dict = []
            for i in range(len(data_id['lat'])):
                # now the data point has an altitude value
                # use it instead of ref_alt
                lat, lng, alt = pm.enu2geodetic(data_id['lat'][i], 
                                                data_id['long'][i], 
                                                data_id['alt'][i], 
                                                ref_lat, ref_long, ref_alt, 
                                                ell=pm.Ellipsoid('wgs84'), deg=True)
                lat_lng_dict.append([lat, lng])

            new_polylines.append(dl.PolylineDecorator(positions=lat_lng_dict, patterns=map_patterns))

        return new_polylines

    return current_polylines


@app.callback([Output('map', 'center'),
                Output('map', 'zoom')],
                Input('session', 'data'))
def center_map_around_ref_input(ref_data):

    if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
        # ref point was cleared - so reset to center of map to the center of the US and zoom out
        return (39,-98), 4
    
    # otherwise center the map on the reference point
    return (ref_data['ref_lat'], ref_data['ref_long']), 5.8


@app.callback(Output('marker-layer', 'children'),
                [Input("map", "dbl_click_lat_lng"),
                Input('create-new-button', 'n_clicks'),
                Input('trajectory-ids', 'value'),
                Input(dict(tag="marker", index=ALL), 'children')],
                [State('marker-layer', 'children'),
                State('ac-index', 'value'),
                State('session', 'data')])
def create_markers(dbl_click_lat_lng, create_n_clicks, traj_ids, current_marker_tools, current_markers, ac_value, ref_data):
    ctx = dash.callback_context
       
    if not ctx.triggered or not ctx.triggered[0]['value']:
        return dash.no_update
    
    ctx = ctx.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'map':
        # user double clicked the map
        if create_n_clicks > 0 and ac_value:
            # in creative mode and an ac_value has been set

            if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
                # reference point has not been reset, cannot create markers until it is
                return dash.no_update

            xEast, yNorth, zUp = pm.geodetic2enu(dbl_click_lat_lng[0], 
                                                dbl_click_lat_lng[1], 
                                                ref_data['ref_alt'], 
                                                ref_data['ref_lat'], 
                                                ref_data['ref_long'], 
                                                ref_data['ref_alt'],
                                                ell=pm.Ellipsoid('wgs84'), deg=True)

            # markers have a position that is always in lat/long 
            # so that the map object can place then correctly
            # but the tooltips (blue pointer on the map) displays that position
            # in ENU coords to the user
            current_markers.append(dl.Marker(id=dict(tag="marker", index=len(current_markers)), 
                                    position=dbl_click_lat_lng,
                                    children=dl.Tooltip("({:.3f}, {:.3f})".format(*[xEast, yNorth])), 
                                    draggable=True))

    elif ctx == 'create-new-button':
        if create_n_clicks > 0 and len(current_markers) > 0:
            # clear past markers only when create-new-button is clicked again
            return []

    elif ctx == 'trajectory-ids':
        # clear markers if more than one trajectory is active
        if len(traj_ids) > 1:
            return []

    return current_markers


@app.callback(Output(dict(tag="marker", index=ALL), 'draggable'),
              Input('create-new-button', 'n_clicks'),
              [State(dict(tag="marker", index=ALL), 'draggable')])
def toggle_marker_draggable(create_n_clicks, draggable):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'create-new-button' and create_n_clicks > 0:
        # in creative mode, the markers should be draggable
        return [True] * len(draggable)
    elif ctx == 'create-new-button' and create_n_clicks == 0:
        # after exiting creative mode, the markers are no longer draggable

        # FIXME: This is functionality choice that we could change
        # if we wanted to. AKA always keep the markers draggable?
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
            # reference point has not been reset, cannot update markers until it is
            return dash.no_update

        # the input will be the dictionary id of the marker that was dragged
        # in the form {'tag':'marker','index':int}
        index = json.loads(ctx)['index']
        pos = new_positions[index]

        xEast, yNorth, zUp = pm.geodetic2enu(pos[0], pos[1], 
                                            ref_data['ref_alt'], 
                                            ref_data['ref_lat'], 
                                            ref_data['ref_long'], 
                                            ref_data['ref_alt'],
                                            ell=pm.Ellipsoid('wgs84'), deg=True)

        # this is what gives the tooltips the ability to display and update the marker
        # position after being dragged
        current_marker_tools[index] = dl.Tooltip("({:.3f}, {:.3f})".format(*[xEast, yNorth]))
    
    return current_marker_tools


@app.callback(Output('tabs', 'value'),
                Input('create-new-button', 'n_clicks'))
def creative_mode_switch_tabs(n_clicks):
    # when click create new nominal path - takes user to tab-3
    if n_clicks > 0:
        return 'tab-3'
    return 'tab-1'
    

@app.callback(Output('trajectory-ids', 'value'),
                [Input('create-new-button', 'n_clicks'),
                Input('exit-edit-button', 'n_clicks'),
                Input('session', 'data')],
                 State('ac-index', 'value'))
def creative_mode_clear_trajectory_ids(create_n_clicks, exit_n_clicks, ref_data, ac_value):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'create-new-button':
        if create_n_clicks > 0:
            # clear selected ids when user clickes create new nominal path
            return []
    
    elif ctx == 'exit-edit-button':
        if exit_n_clicks > 0:
            if not ac_value:
                # if no ac_value was inputted, that means no markers were created
                # because the user cannot create markers until an ac_valye is chosen
                # so just clear the dropdown menu
                return []
            else:
                # otherwise, return the ac_value chosen by user
                return [ac_value]
    
    elif ctx == 'session':
        if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
            # no trajectories should be selected if there isn't a ref point
            # test this by clicking the clear button
            return []

    return dash.no_update


@app.callback(Output('trajectory-ids', 'options'),
                Input('exit-edit-button', 'n_clicks'),
                [State('ac-index', 'value'),
                State('trajectory-ids', 'options'),
                State('editable-table', 'data')])
def creative_mode_add_trajectory(n_clicks, ac_value, options, data):
    if not ac_value:
        return dash.no_update

    elif n_clicks > 0:
        # create new dropdown menu option for new nominal path
        new_option = {'value': ac_value, 'label': 'AC '+ str(ac_value)}
        
        if new_option not in options:
            options.append({'value': ac_value, 'label': 'AC '+ str(ac_value)})

            # FIXME: THIS IS WHERE I APPEND THE DATA TO THE GLOBAL DF
            # Instead, this data should be added to memory-output data
            # and we should leave the global df behind
            add_data_to_df(data)
        else:
            # user choice an AC ID that already exists
            # not a valid ID choice
            print('AC Id already taken. Select a new one.')

    return options


@app.callback(Output('trajectory-ids', 'disabled'),
                [Input('create-new-button', 'n_clicks'),
                Input('exit-edit-button', 'n_clicks'),
                Input('session', 'data')])
def creative_mode_disable_trajectory_id_dropdown(create_n_clicks, exit_n_clicks, ref_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'create-new-button':
        if create_n_clicks > 0:
            # if in creative mode, should not be able to select trajectory ids from the menu
            return True
    
    elif ctx == 'exit-edit-button':
        if exit_n_clicks > 0:
            # if leave creative mode, should be able to select trajectory ids from menu
            return False

    elif ctx == 'session':
        if not ref_data['ref_lat'] or not ref_data['ref_long'] or not ref_data['ref_long']:
            # no trajectories should be selected if there isn't a ref point
            return True
        else:
            return False


    return dash.no_update


@app.callback([Output('tab1','disabled'),
                Output('tab2', 'disabled')],
                [Input('create-new-button', 'n_clicks'),
                Input('exit-edit-button', 'n_clicks')])
def creative_mode_disable_tabs(create_n_clicks, exit_n_clicks):
    if create_n_clicks > 0:
        # in creative mode, cannot switch to tab1 or tab2
        # until finished making the nominal path waypoints
        return True, True
    elif exit_n_clicks > 0:
        return False, False

    return dash.no_update


@app.callback([Output('create-new-button', 'n_clicks'),
                Output('exit-edit-button', 'n_clicks'),
                Output('exit-edit-button', 'style'),
                Output('ac-index', 'style')],
                [Input('create-new-button', 'n_clicks'), 
                Input('exit-edit-button', 'n_clicks')],
                [State('exit-edit-button', 'style'),
                State('ac-index', 'style')])
def toggle_creative_mode(create_n_clicks, exit_n_clicks, exit_style, ac_style):
    reset_create_clicks = create_n_clicks
    reset_exit_clicks = exit_n_clicks

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if create_n_clicks > 0:
        # in creative mode
        if ctx == 'create-new-button':
            # display the exit button and ac input
            reset_exit_clicks = 0 
            exit_style['display'] = 'inline-block'
            ac_style['display'] = 'inline-block'  
        
        if ctx == 'exit-edit-button' and exit_n_clicks > 0:
            # exiting creative mode, so do not display exit button or ac input anymore
            exit_style['display'] = 'none'
            ac_style['display'] = 'none'
            reset_create_clicks = 0     
        
    return reset_create_clicks, reset_exit_clicks, exit_style, ac_style


@app.callback(Output('ac-index', 'value'),
                Input('exit-edit-button', 'n_clicks'),
                State('trajectory-ids', 'options'))
def exit_creative_mode_reset_ac_index(exit_n_clicks, options):
    if exit_n_clicks > 0:
        # clear ac_value when user exits creative mode
        return None
    
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

    ref = 'reference point: ', ref_data['ref_lat'], "/", ref_data['ref_long'], '/', ref_data['ref_alt']

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'set-ref-button':
        
        if set_n_clicks > 0 and ref_point_value:
            # user clicked set reference point button after inputting a new ref point val

            # the ac input has a Regex that makes sure the user inputs ref point in 
            # the proper format: 0.0/0.0/0.0
            # the values all must be floats
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
            # reset the reference point
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
        # reset value displayed in ref point input
        return ''
    return dash.no_update


@app.callback(Output('ref-point-input', 'disabled'),
                [Input('create-new-button', 'n_clicks'),
                Input('exit-edit-button', 'n_clicks')])
def disable_ref_input(create_n_clicks, exit_n_clicks):
    if create_n_clicks > 0:
        # must set the reference point before the user enters creative mode
        # so the input is disabled in creative mode
        return True
    
    if exit_n_clicks > 0:
        return False

    return dash.no_update


@app.callback(Output('clear-ref-button', 'disabled'),
                [Input('create-new-button', 'n_clicks'),
                Input('exit-edit-button', 'n_clicks')])
def disable_clear_ref_button(create_n_clicks, exit_n_clicks):
    if create_n_clicks > 0:
        # user should not be able to clear the reference point while in creative mode
        return True
    
    if exit_n_clicks > 0:
        return False

    return dash.no_update


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


@app.callback(Output('generated-encounters', 'data'),
                Input('generate-button', 'n_clicks'),
                [State('nominal-path-id', 'value'),
                State('sigma-input', 'value'),
                State('num-encounters-input', 'value'),
                State('memory-output', 'data')])
def generate_encounters(gen_n_clicks, nom_path_id, sigma, num_encounters, data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'generate-button':
        if gen_n_clicks > 0:
            print("THIS IS WHERE WE DO THE GENERATING :)")

            # error checking
            error = False
            if not nom_path_id:
                print("Must select a nominal path")
                error = True
            if not sigma:
                print('Must input a sigma value')
                error = True
            if not num_encounters:
                print('Must input number of encounters to generate')
                error = True
            if error:
                return {}

            nom_path_data = filter_ids(nom_path_id)
            params = [[waypoint['xEast'], waypoint['yNorth'], waypoint['zUp']] for waypoint in nom_path_data]
            
            cov = [ [sigma, 0, 0], 
                    [0, sigma, 0], 
                    [0, 0, sigma] ]

            # for enc in num_encounters:
            #     trajectory = []
            #     for mean in params:
            #         #print(type(np.random.multivariate_normal(mean, cov, 1)))
            #         trajectory.append(np.random.multivariate_normal(mean, cov, 1)[0])
            #     print("ENCOUNTER ", enc)
            #     print(trajectory, '\n')

    return dash.no_update


############################################################
############################################################
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

    app.run_server(debug=True, port=8375)
