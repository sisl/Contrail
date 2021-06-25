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
             Input('create-new-button', 'n_clicks'),
             Input('marker-layer', 'children')],
             State('editable-table', 'data'))
def update_data_table(traj_ids_selected, add_rows_n_clicks, create_n_clicks, current_markers, data):#, current_markers):
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
        print("UPDATING MARKER-LAYER CHILDREN YUP")
        # in creative mode and user has created another marker 
        # we add each marker to the data as it is created 
        # so we only have to grab last marker in the list
        pos = current_markers[-1]['props']['position']
        marker_dict = {'id': 1, 'time': len(data)+1, 'lat': pos[0], 'long': pos[1], 'alt':700, 'hor_speed':0}
        data.append(marker_dict)
    
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
              State('polyline-layer', 'children'))         
def update_map(data, current_polylines):
    if data is None:
        raise PreventUpdate

    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'editable-table':
        # data has changed - must update map polylines
        markers_list = []
        
        if len(data) == 0:
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

    # I had some issues previously with returning the current_polylines... not sure why it is working now
    # so I am keeping this other return statement I wrote to recreate the existing lines
    #return [dl.PolylineDecorator(positions=info['props']['positions'], patterns=map_patterns) for info in current_polylines]

    return current_polylines


@app.callback(Output('marker-layer', 'children'),
                #Output(dict(tag="marker", index=ALL), 'children')],
                [Input("map", "click_lat_lng"),
                Input('create-new-button', 'n_clicks')],
                #Input(dict(tag="marker", index=ALL), 'position')],
                State('marker-layer', 'children'))
def create_markers(click_lat_lng, create_n_clicks, current_markers):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    if ctx == 'map' and create_n_clicks > 0:
        current_markers.append(dl.Marker(id=dict(tag="marker", index=len(current_markers)), position=click_lat_lng,\
                                 children=dl.Tooltip("({:.3f}, {:.3f})".format(*click_lat_lng)), 
                                 draggable=True))
    elif ctx == 'create-new-button' and create_n_clicks > 0 and len(current_markers) > 0:
        # clear past markers only when create-new-button is clicked again
        return []

    # elif len(ctx) > 0:
    #     print('marker_',json.loads(ctx)['index'], ' was moved')
 
    #     new_tools = []
    #     for pos in new_positions:
    #         #new_tools.append(dl.Tooltip("({:.3f}, {:.3f})".format([pos])))
    #         new_tools.append([dl.Tooltip("({lat}, {long})".format(lat=pos[0], long=pos[1]))])
    #     return new_tools
    # else:
    #     raise PreventUpdate

    return current_markers


@app.callback(Output(dict(tag="marker", index=ALL), 'children'),
              [Input(dict(tag="marker", index=ALL), 'position')])
def update_marker(new_positions):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if len(ctx) > 0:
        print('marker_',json.loads(ctx)['index'], ' was moved')
 
        new_tools = []
        for pos in new_positions:
            #new_tools.append(dl.Tooltip("({:.3f}, {:.3f})".format([pos])))
            new_tools.append([dl.Tooltip("({lat}, {long})".format(lat=pos[0], long=pos[1]))])
        return new_tools
    else:
        raise PreventUpdate
    

@app.callback([Output('tabs', 'value'), 
                Output('trajectory-ids', 'value'),
                Output('trajectory-ids', 'disabled')],
                Input('create-new-button', 'n_clicks'),
                State('trajectory-ids', 'value'))
def create_new_model(n_clicks, traj_ids):
    if n_clicks > 0:
        return 'tab-3', [], True

    return 'tab-1', traj_ids, False

@app.callback([Output('exit-edit-button', 'style'), 
                Output('create-new-button', 'n_clicks'),
                Output('exit-edit-button', 'n_clicks')],
                [Input('create-new-button', 'n_clicks'), 
                Input('exit-edit-button', 'n_clicks')],
                State('exit-edit-button', 'style'))
def toggle_exit_edit_button(create_n_clicks, exit_n_clicks, style):
    reset_create_clicks = create_n_clicks
    reset_exit_clicks = exit_n_clicks

    if create_n_clicks > 0:
        if exit_n_clicks > 0:
            style['display'] = 'none'
            reset_create_clicks = 0
            reset_exit_clicks = 0
        else:
            style['display'] = 'inline-block'

    return style, reset_create_clicks, reset_exit_clicks


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
    app.run_server(debug=True, port=8509)
