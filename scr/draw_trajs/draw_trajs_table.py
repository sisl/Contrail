import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_leaflet as dl

import pandas as pd
import numpy as np
import collections


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

columns = ['id', 'time', 'lat', 'long', 'alt']
df = pd.read_csv('data/traj_data_sample.csv', header=0)
traj_ids = set(df['id'])

def calculate_horizontal_speeds_df(df):
    hor_speeds = []
    for ac_id in traj_ids:
        ac_id_data = df.loc[df['id'] == ac_id]

        move_over_time = (np.roll(ac_id_data, -1, axis=0) - ac_id_data)[:-1]
        hor_speed = np.sqrt(move_over_time.lat ** 2 + move_over_time.long ** 2) / move_over_time['time']
        hor_speeds += (np.append(0.0, round(hor_speed, 4))).tolist()

    df['hor_speed'] = hor_speeds
    return df

df = calculate_horizontal_speeds_df(df)

map_iconUrl = "https://dash-leaflet.herokuapp.com/assets/icon_plane.png"
map_marker = dict(rotate=True, markerOptions=dict(icon=dict(iconUrl=map_iconUrl, iconAnchor=[16, 16])))
map_patterns = [dict(repeat='15', dash=dict(pixelSize=0, pathOptions=dict(color='#000000', weight=5, opacity=0.9))),
            dict(offset='100%', repeat='0%', marker=map_marker)]


############################################################
############################################################
app.layout = html.Div([
    # memory store reverts to the default on every page refresh
    dcc.Store(id='memory-output'),
    
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
        
        html.Button('Create New Model', id='create-new-button', n_clicks=0, 
                style={"margin-left": "15px"}),
                 
        html.Button('Exit Edit Mode', id='exit-edit-button', n_clicks=0, 
                style={"margin-left": "15px", 'display':'none'})
        ]
    ),
    
    
    html.Br(),
    html.Br(),

    # main tabs for navigating webpage
    html.Div([
        dcc.Tabs(id="tabs",
                 children=[
                     dcc.Tab(label='Graphs', value='tab-1'),
                     dcc.Tab(label='3d_Graph', value='tab-2'),
                     dcc.Tab(label='Map', value='tab-3')
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

def filter_ids(traj_ids_selected):
    if not traj_ids_selected:
        return []
    
    # get data for the trajectory IDs that are currently selected
    df_filtered = df.query('id in @traj_ids_selected')
    return df_filtered.to_dict('records')

############################################################
############################################################
@app.callback(Output('memory-output', 'data'),
              Input('trajectory-ids', 'value'))
def update_memory(traj_ids_selected):
    return filter_ids(traj_ids_selected)


@app.callback(Output('editable-table', 'data'),
             [Input('trajectory-ids', 'value'),
             Input('add-rows-button', 'n_clicks'),
             Input('exit-edit-button', 'n_clicks')],
             [State('editable-table', 'data'),
             State('marker-layer', 'children')])
def update_data_table(traj_ids_selected, add_rows_n_clicks, exit_n_clicks, data, current_markers):

    # allows us to identify which input triggered this callback
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'add-rows-button':
        if data is None:
            raise PreventUpdate
        if add_rows_n_clicks > 0:
            # add an empty row
            data.append({c: '' for c in df.columns})
        return data

    elif ctx == 'trajectory-ids':
        # trajectories have been updated or loaded in
        return filter_ids(traj_ids_selected)

    elif ctx == 'exit-edit-button' and exit_n_clicks > 0:
        if current_markers is []:
            return []

        time = 1
        alt = 700
        hor_speed = 0
        new_data = []
        for marker in current_markers:
            marker_dict = {'id': 1, 'time': time, 'lat': 0, 'long': 0, 'alt':700, 'hor_speed':0}
            
            pos = marker['props']['position']
            marker_dict['lat'] = pos[0]
            marker_dict['long'] = pos[1]

            new_data.append(marker_dict)
            time += 1
        
        return new_data

    
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
            #   Input("map", "click_lat_lng")],
              [State('polyline-layer', 'children'),
              State('create-new-button', 'n_clicks')])         
def update_map(data, current_markers, n_clicks):
    if data is None and click_lat_lng is None:
        raise PreventUpdate

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'editable-table' and n_clicks == 0:
        markers_list = []

        if data == []:
            # if no data, save computation time
            return markers_list

        aggregation = collections.defaultdict(lambda: collections.defaultdict(list))
        for row in data:
            if row.get('lat') != '' and row.get('long') != '':        
                a = aggregation[float(row.get('id'))]
                a['name'], a['color'] = 'AC '+ str(row['id']), row['id']

                a['lat'].append(float(row.get('lat')))
                a['long'].append(float(row.get('long')))
        data_group = [x for x in aggregation.values()]
            
        for data_id in data_group:
            lat_lng_dict = [[data_id['lat'][i], data_id['long'][i]] for i in range(len(data_id['lat']))]
            markers_list.append(dl.PolylineDecorator(positions=lat_lng_dict, patterns=map_patterns))

        return markers_list

    elif n_clicks > 0: 
        # in creative mode
        # wipe all previous data
        return []
    
    # elif ctx == 'map' and n_clicks > 0:
    #     # THIS IS WHERE WE ADD LAT/LNG MARKERS!
    #     current_markers.append(dl.Marker(position=click_lat_lng, children=dl.Tooltip("({:.3f}, {:.3f})".format(*click_lat_lng)), draggable=True))
    #     return current_markers

    # FIXME: This does not seem like the most efficient way to do this
    # check back in on this decision later!
    
    return [dl.PolylineDecorator(positions=info['props']['positions'], patterns=map_patterns) for info in current_markers]


@app.callback(Output('marker-layer', 'children'),
                [Input("map", "click_lat_lng"),
                Input('exit-edit-button','n_clicks')],
                [State('create-new-button', 'n_clicks'),
                    State('marker-layer', 'children'),
                    State('editable-table', 'data')])
def create_markers(click_lat_lng, exit_n_clicks, create_n_clicks, current_markers, data):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'map' and create_n_clicks > 0:
        current_markers.append(dl.Marker(position=click_lat_lng, children=dl.Tooltip("({:.3f}, {:.3f})".format(*click_lat_lng)), draggable=True))
    # elif data != []:
    #     print('data here')
    #     return []

    return current_markers


@app.callback([Output('tabs', 'value'), 
                Output('trajectory-ids', 'value')],
                Input('create-new-button', 'n_clicks'),
                State('trajectory-ids', 'value'))
def create_new_model(n_clicks, traj_ids):
    print(n_clicks)
    if n_clicks > 0:
        return 'tab-3', []

    # FIXME: I want to add a popup screen that explains the steps
    # for how the user can create the nominal path.
    # 1. click map for lat/long points along a trajectory
    # 2. click 'finish' button
    # 3. takes user back to tab1 to edit default alt and speed info in data table
    
    return 'tab-1', traj_ids

@app.callback([Output('exit-edit-button', 'style'), 
                Output('create-new-button', 'n_clicks'),
                Output('exit-edit-button', 'n_clicks')],
                [Input('create-new-button', 'n_clicks'), Input('exit-edit-button', 'n_clicks')],
                State('exit-edit-button', 'style'))
def toggle_exit_edit_button(create_n_clicks, exit_n_clicks, style):
    reset_create_clicks = create_n_clicks
    reset_exit_clicks = exit_n_clicks

    if create_n_clicks > 0:
        if exit_n_clicks == 0:
            style['display'] = 'inline-block'
            #reset_create_clicks = 0
        else:
            style['display'] = 'none'
            reset_create_clicks = 0
            

    return style, reset_create_clicks, reset_exit_clicks

# @app.callback(Output('marker-layer', 'attribution'),
#                 [Input('create-new-button', 'n_clicks'), 
#                 Input('exit-edit-button', 'n_clicks')])
# def set_marker_attribution(create_n_clicks, exit_n_clicks):
#     ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
#     if ctx == 'create-new-button' and create_n_clicks > 0:
#         return 'on'
#     elif ctx == 'exit-edit-button' and exit_n_clicks > 0:
#         return 'off'

#     return 'off'



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
    app.run_server(debug=True, port=8517)
