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

def calculate_speeds_df(df):
    time = 'time'
    move_over_time = (np.roll(df, -1, axis=0) - df)[:-1]
    hor_speed = np.sqrt(move_over_time.lat ** 2 + 
                        move_over_time.long ** 2) / move_over_time[time]
    df['hor_speed'] = np.append(0.0, round(hor_speed, 4))
    return df
df = calculate_speeds_df(df)


############################################################
############################################################
app.layout = html.Div([
    dcc.Store(id='memory-output'),
    
    dcc.Markdown(("""Trajectory ID list""")),
    html.Div([
        dcc.Dropdown(id='memory-ids', 
                     options=[{'value': traj_id, 'label': 'AC '+str(traj_id)} for traj_id in traj_ids], 
                     multi=True, value=[1, 2])
    ]),
    
    html.Br(), html.Br(),
    html.Div([
        dcc.Tabs(id="tabs",
                 children=[
                     dcc.Tab(label='Graphs', value='tab-1'),
                     dcc.Tab(label='3d_Graph', value='tab-2'),
                     dcc.Tab(label='Map', value='tab-3')
                 ]),
        html.Div(id='tabs-content')
    ]),
    
    html.Br(), html.Br(),
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
    
    html.Br(), html.Br()
])    


############################################################
############################################################
@app.callback(Output('memory-output', 'data'),
              Output('editable-table', 'data'),
              Input('memory-ids', 'value'))
def filter_ids(traj_ids_selected):
    if not traj_ids_selected:
        return df.to_dict('records')
    df_filtered = df.query('id in @traj_ids_selected')
    return df_filtered.to_dict('records'), df_filtered.to_dict('records')


@app.callback(
    Output('editable-table', 'data'),
    [Input('editing-rows-button', 'n_clicks')],
    State('editable-table', 'data'))
def add_row(n_clicks, data):
    if data is None:
        raise PreventUpdate
    if n_clicks > 0:
        data.append({c: '' for c in df.columns})
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
            a['name'], a['color'] = 'AC '+str(row['id']), row['id']
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


############################################################
############################################################
@app.callback(Output('tabs-content', 'children'),
              Input('tabs', 'value'),
              Input('editable-table', 'data'))
def render_content(tab, data):
    if tab == 'tab-1':
        return html.Div(children=[
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
        ])

    elif tab == 'tab-2':
        return html.Div([
            dcc.Graph(id='editable-graph-xyz',
                      figure={}
                     )],
            style={'width': '1500px', 'height': '750px',
                   'margin': {'l':0, 'r':0, 'b':0, 't':0, 'pad':0}, 
                   'autosize': False, 'display': "block"}
        )
    
    elif tab == 'tab-3':
        iconUrl = "https://dash-leaflet.herokuapp.com/assets/icon_plane.png"
        marker = dict(rotate=True, markerOptions=dict(icon=dict(iconUrl=iconUrl, iconAnchor=[16, 16])))
        patterns = [dict(repeat='15', dash=dict(pixelSize=0, pathOptions=dict(color='#000000', weight=5, opacity=0.9))),
                    dict(offset='100%', repeat='0%', marker=marker)]
        
        aggregation = collections.defaultdict(lambda: collections.defaultdict(list))
        for row in data:
            if row.get('lat') != '' and row.get('long') != '':        
                a = aggregation[float(row.get('id'))]
                a['name'], a['color'] = 'AC '+str(row['id']), row['id']

                a['lat'].append(float(row.get('lat')))
                a['long'].append(float(row.get('long')))
        data_group = [x for x in aggregation.values()]
            
        markers_list = []
        for data_id in data_group:
            lat_lng_dict = [[data_id['lat'][i], data_id['long'][i]] for i in range(len(data_id['lat']))]
            markers_list.append(dl.PolylineDecorator(positions=lat_lng_dict, 
                                                        patterns=patterns))

        return html.Div(dl.Map([dl.TileLayer(), 
                               dl.LayerGroup(markers_list)
                               ], 
                               id="map", zoom=5.25, center=(38, -73),
                               style={'width': '1500px', 'height': '750px', 'margin': "auto", "display": "block"}
                              )
                       )
    

@app.callback(Output('editable-table', 'data'),
              Output("layer", "children"),
              [Input("map", "click_lat_lng")],
              State('editable-table', 'data'))
def map_click(click_lat_lng, data):
    if click_lat_lng is None:
        raise PreventUpdate
    data.append({'id': 2, 
                 'lat': np.round(click_lat_lng,2)[0], 'long': np.round(click_lat_lng,2)[1], 
                 'alt': '', 'hor_speed': ''})
    return data, [dl.Marker(position=click_lat_lng, 
                     children=dl.Tooltip("({:.2f}, {:.2f})".format(*click_lat_lng)))]


if __name__ == '__main__':
    app.run_server(debug=True, port=8511)
