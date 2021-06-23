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
                     options=[{'value': traj_id, 'label': 'AC '+str(traj_id)} for traj_id in traj_ids], 
                     multi=True, 
                     value=[1, 2])
    ]),
    
    # style
    html.Br(), html.Br(),

    # main tabs for navigating webpage
    html.Div([
        dcc.Tabs(id="tabs",
                 children=[
                     dcc.Tab(label='Graphs', value='tab-1'),
                     dcc.Tab(label='3d_Graph', value='tab-2'),
                     dcc.Tab(label='Map', value='tab-3')
                 ]),
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
        style={'display': 'block'}),
    
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
            dl.Map(children=[dl.TileLayer(), dl.LayerGroup(id='layer-container', children=[])],
                    id='map',
                    zoom=5.25, 
                    center=(38, -73),
                    style={'width': '1500px', 'height': '750px', 'margin': "auto", "display": "block"}
                    )],
            style={"display": "block"}),
    
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
        html.Button('Add Row', id='editing-rows-button', n_clicks=0),
    ], className='row'),
    
    # style
    html.Br(), html.Br()
])    


############################################################
############################################################
@app.callback(Output('memory-output', 'data'),
              Output('editable-table', 'data'),
              Input('trajectory-ids', 'value'))
def filter_ids(traj_ids_selected):
    if not traj_ids_selected:

        # FIXME: shouldn't this return nothing? I think our
        #        graphs should be empty if nothing is selected
        # return df.to_dict('records')
        return [], []
    
    # get data for the trajectory IDs that are currently selected
    df_filtered = df.query('id in @traj_ids_selected')

    # update memory and table
    return df_filtered.to_dict('records'), df_filtered.to_dict('records')


# @app.callback(
#     Output('editable-table', 'data'),
#     [Input('editing-rows-button', 'n_clicks')],
#     State('editable-table', 'data'))
# def add_row(n_clicks, data):
#     if data is None:
#         raise PreventUpdate
#     if n_clicks > 0:
#         # add an empty row
#         data.append({c: '' for c in df.columns})
#     return data


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
def on_data_set_graph_tz(data):
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

@app.callback(Output('layer-container', 'children'),
              Input('editable-table', 'data'))         
def on_data_set_map(data):
    if data is None:
        raise PreventUpdate
    
    aggregation = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in data:
        if row.get('lat') != '' and row.get('long') != '':        
            a = aggregation[float(row.get('id'))]
            a['name'], a['color'] = 'AC '+ str(row['id']), row['id']

            a['lat'].append(float(row.get('lat')))
            a['long'].append(float(row.get('long')))
    data_group = [x for x in aggregation.values()]
        
    markers_list = []
    for data_id in data_group:
        lat_lng_dict = [[data_id['lat'][i], data_id['long'][i]] for i in range(len(data_id['lat']))]
        markers_list.append(dl.PolylineDecorator(positions=lat_lng_dict, patterns=map_patterns))
    
    return markers_list

    



############################################################
############################################################
# @app.callback(Output('tabs-content', 'children'),            
#               Input('tabs', 'value'),
#               Input('editable-table', 'data'))
@app.callback([Output('tab-1-graphs', 'style'), Output('tab-2-graphs', 'style'), Output('tab-3-graphs', 'style')],            
              Input('tabs', 'value'),
              Input('editable-table', 'data'))
def render_content(active_tab, data):

    # FIXME: Right now, if a tab has not been open, the graph
    # objects on the closed tabs do not exist. So, if new info
    # is added to the table, the webpage cannot update all of
    # the graphs (throws an error).
    
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
    app.run_server(debug=True, port=8511)
