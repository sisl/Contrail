import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate

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

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

columns = ['id', 'time', 'lat', 'long', 'alt']
global df
df = pd.read_csv('data/traj_data_sample_ENU.csv', header=0)
traj_ids = set(df['id'])

def calculate_horizontal_speeds_df(dataf):
    hor_speeds = []
    for ac_id in traj_ids:
        ac_id_data = df.loc[df['id'] == ac_id]

        move_over_time = (np.roll(ac_id_data, -1, axis=0) - ac_id_data)[:-1]
        hor_speed = np.sqrt(move_over_time.lat ** 2 + move_over_time.long ** 2) / move_over_time['time']
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
    
    # trajectory ID dropdown menu
    html.Div([
        dcc.Markdown(("""Trajectory ID list""")),
        dcc.Dropdown(id='trajectory-ids', 
                     options=[{'value': traj_id, 'label': 'AC '+ str(traj_id)} for traj_id in traj_ids], 
                     multi=True, 
                     value=[1, 2])
    ]),
    
    # style
    html.Br(), 

    html.Div(id='buttons', children = [
        html.Button('Load Model', id='load-button', n_clicks=0),
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

    html.Div(id='reference-point-div', children = [
        dcc.Input(id='ref-point-input', type='text', placeholder='lat/lng/alt: 0.0/0.0/0.0',
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
                    zoom=5.25, 
                    center=(38, -73),
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
             [State('editable-table', 'data'),
             State('ac-index', 'value'),
             State('session', 'data')])
def update_data_table(traj_ids_selected, add_rows_n_clicks, create_n_clicks, current_markers, data, ac_index, ref_data):
    if data is None:
        raise PreventUpdate

    # allows us to identify which input triggered this callback
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'create-new-button' and create_n_clicks > 0:
        # wipe all data
        return []

    elif ctx == 'add-rows-button' and create_n_clicks == 0:
        if add_rows_n_clicks > 0:
            # add an empty row
            data.append({c: '' for c in df.columns})

    elif ctx == 'trajectory-ids':
        # trajectories have been updated or loaded in
        return filter_ids(traj_ids_selected)

    elif ctx == 'marker-layer' and create_n_clicks > 0:
        if not ac_index:
            return dash.no_update
        
        if len(data) != len(current_markers):
            # in creative mode and user has created another marker 
            # we add each marker to the data as it is created 
            # so we only have to grab last marker in the list
            pos = current_markers[-1]['props']['position']
            xEast, yNorth, zUp = pm.geodetic2enu(pos[0], pos[1], ref_data['ref_alt'], 
                                                ref_data['ref_lat'], 
                                                ref_data['ref_long'], 
                                                ref_data['ref_alt'],
                                                ell=pm.Ellipsoid('wgs84'), deg=True)
            marker_dict = {'id': ac_index, 'time': len(data)+1, 'lat': xEast, 'long': yNorth, 'alt': zUp, 'hor_speed':0}
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
                data_point['lat'] = xEast
                data_point['long'] = yNorth
                data_point['alt'] = zUp

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
            
            a['x'].append(float(row.get('lat')))
            a['y'].append(float(row.get('long')))
    return {'data': [x for x in aggregation.values()],
            'layout': {'title': 'latitude vs. longitude'}}

 
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
            a['y'].append(float(row['alt']))
    return {'data': [x for x in aggregation.values()],
            'layout': {'title': 'time vs. altitude'}}


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
            'layout': {'title': 'horizontal speed'}}


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

            a['x'].append(float(row['lat']))
            a['y'].append(float(row['long']))
            a['z'].append(float(row['alt']))
    return {'data': [x for x in aggregation.values()],
            'layout': {
                'scene': {'xaxis': {'title': 'lat'},
                         'yaxis': {'title': 'lon'},
                         'zaxis': {'title': 'alt'}},
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
        # data has changed - must update map polylines
        new_polylines = []
        
        if len(data) == 0:
            # if no data, save computation time
            return new_polylines

        aggregation = collections.defaultdict(lambda: collections.defaultdict(list))
        for row in data:
            if row.get('lat') != '' and row.get('long') != '':        
                a = aggregation[float(row.get('id'))]
                a['name'], a['color'] = 'AC '+ str(row['id']), row['id']

                a['lat'].append(float(row.get('lat')))
                a['long'].append(float(row.get('long')))
        data_group = [x for x in aggregation.values()]
            
        ref_lat = ref_data['ref_lat']
        ref_long = ref_data['ref_long']
        ref_alt = ref_data['ref_alt']

        for data_id in data_group:

            lat_lng_dict = []
            for i in range(len(data_id['lat'])):
                lat, lng, alt = pm.enu2geodetic(data_id['lat'][i], 
                                                data_id['long'][i], 
                                                ref_alt, ref_lat, 
                                                ref_long, ref_alt, 
                                                ell=pm.Ellipsoid('wgs84'), deg=True)
                lat_lng_dict.append([lat, lng])

            new_polylines.append(dl.PolylineDecorator(positions=lat_lng_dict, patterns=map_patterns))

        return new_polylines

    # I had some issues previously with returning the current_polylines... not sure why it is working now
    # so I am keeping this other return statement I wrote to recreate the existing lines
    #return [dl.PolylineDecorator(positions=info['props']['positions'], patterns=map_patterns) for info in current_polylines]

    return current_polylines


@app.callback(Output('marker-layer', 'children'),
                [Input("map", "dbl_click_lat_lng"),
                Input('create-new-button', 'n_clicks'),
                Input('exit-edit-button', 'n_clicks'),
                #Input('trajectory-ids', 'value'),
                Input(dict(tag="marker", index=ALL), 'position')],
                [State('marker-layer', 'children'),
                State('ac-index', 'value'),
                State('session', 'data')])
def create_markers(dbl_click_lat_lng, create_n_clicks, exit_n_clicks, new_positions, current_markers, ac_value, ref_data):
    ctx = dash.callback_context
    
    if not ctx.triggered or not ctx.triggered[0]['value']:
        return dash.no_update
    
    ctx = ctx.triggered[0]['prop_id'].split('.')[0]
    #print("CONTEXT: ", ctx)

    if ctx == 'map':
        if create_n_clicks > 0 and ac_value:
            xEast, yNorth, zUp = pm.geodetic2enu(dbl_click_lat_lng[0], dbl_click_lat_lng[1], ref_data['ref_alt'], 
                                                ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt'],
                                                ell=pm.Ellipsoid('wgs84'), deg=True)

            current_markers.append(dl.Marker(id=dict(tag="marker", index=len(current_markers)), 
                                    position=dbl_click_lat_lng,
                                    children=dl.Tooltip("({:.3f}, {:.3f})".format(*[xEast, yNorth])), 
                                    draggable=True))

    elif ctx == 'create-new-button':
        if create_n_clicks > 0 and len(current_markers) > 0:
        # clear past markers only when create-new-button is clicked again
            return []

    elif ctx == 'exit-edit-button':
        next
        # # clear markers when exit creative mode
        # if exit_n_clicks > 0:
        #     return []

    else:
        # a marker was dragged such that it's position changed
        index = json.loads(ctx)['index']
        current_markers[index]['props']['position'] = new_positions[index]

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
              State('session', 'data'))
def update_marker(new_positions, ref_data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if len(ctx) > 0:
        new_tools = []
        for pos in new_positions:
            xEast, yNorth, zUp = pm.geodetic2enu(pos[0], pos[1], ref_data['ref_alt'], 
                                                ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt'])
            new_tools.append([dl.Tooltip("({:.3f}, {:.3f})".format(*[xEast, yNorth]))])
        return new_tools
    
    return dash.no_update
    

@app.callback(Output('tabs', 'value'),
                Input('create-new-button', 'n_clicks'))
def creative_mode_switch_tabs(n_clicks):
    if n_clicks > 0:
        return 'tab-3'
    return 'tab-1'

@app.callback(Output('trajectory-ids', 'value'),
                [Input('create-new-button', 'n_clicks'),
                Input('exit-edit-button', 'n_clicks')],
                 State('ac-index', 'value'))
def creative_mode_clear_trajectory_ids(create_n_clicks, exit_n_clicks, ac_value):
    if create_n_clicks > 0:
        return []
    
    if exit_n_clicks > 0:
        if not ac_value:
            print("Need to give nominal path an index")
        else:
            return [ac_value]

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
        # create new dropdown menu option
        new_option = {'value': ac_value, 'label': 'AC '+ str(ac_value)}
        
        if new_option not in options:
            options.append({'value': ac_value, 'label': 'AC '+ str(ac_value)})
            add_data_to_df(data)
        else:
            print('AC Id already taken. Select a new one.')

    return options

@app.callback(Output('trajectory-ids', 'disabled'),
                [Input('create-new-button', 'n_clicks'),
                Input('exit-edit-button', 'n_clicks')])
def creative_mode_disable_trajectory_id_dropdown(create_n_clicks, exit_n_clicks):
    if create_n_clicks > 0:
        return True
    
    if exit_n_clicks > 0:
        return False

    return dash.no_update


@app.callback([Output('tab1','disabled'),
                Output('tab2', 'disabled')],
                [Input('create-new-button', 'n_clicks'),
                Input('exit-edit-button', 'n_clicks')])
def creative_mode_disable_tabs(create_n_clicks, exit_n_clicks):
    if create_n_clicks > 0:
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
        if ctx == 'create-new-button':
            reset_exit_clicks = 0 
            exit_style['display'] = 'inline-block'
            ac_style['display'] = 'inline-block'  
        
        if ctx == 'exit-edit-button' and exit_n_clicks > 0:
            exit_style['display'] = 'none'
            ac_style['display'] = 'none'
            reset_create_clicks = 0     
        
    return reset_create_clicks, reset_exit_clicks, exit_style, ac_style

@app.callback(Output('ac-index', 'value'),
                Input('exit-edit-button', 'n_clicks'),
                State('trajectory-ids', 'options'))
def exit_creative_mode_reset_ac_index(exit_n_clicks, options):
    if exit_n_clicks > 0:
        return None
    
    return dash.no_update


@app.callback(Output('ref-point-input', 'value'),
                [Input('set-ref-button', 'n_clicks'),
                Input('clear-ref-button', 'n_clicks')],
                State('ref-point-output', 'children'))
def reset_ref_point_value(set_n_clicks, clear_n_clicks, children):
    if clear_n_clicks > 0:
        return ''
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
        
        if set_n_clicks > 0 and len(ref_point_value) > 0:
            p = patt.match(ref_point_value)
            if p:
                ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt'] = p.groups()
                return 'reference point: ' + ref_point_value, ref_data
            else:
                return '!!invalid format!!', ref_data

    elif ctx == 'clear-ref-button':
        
        if clear_n_clicks > 0:
            return 'reference point: ', ref_data
    
    return 'reference point: ', ref_data



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
    app.run_server(debug=True, port=8538)
