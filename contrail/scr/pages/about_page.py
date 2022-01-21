import warnings
warnings.filterwarnings("ignore")

import dash
import dash_bootstrap_components as dbc

from dash import dcc
from dash import html



import dash_leaflet as dl

# Import Dash Instance #
from app import app

MIT_license = 'MIT License\n\n\
                Copyright (c) 2021 Stanford Intelligent Systems Laboratory \n\
                Permission is hereby granted, free of charge, to any person obtaining a copy\
                of this software and associated documentation files (the "Software"), to deal\
                in the Software without restriction, including without limitation the rights\
                to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\
                copies of the Software, and to permit persons to whom the Software is\
                furnished to do so, subject to the following conditions:\n\
                The above copyright notice and this permission notice shall be included in all\
                copies or substantial portions of the Software.\n\
                THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\
                IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\
                FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\
                AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\
                LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\
                OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\
                SOFTWARE.'

layout = html.Div([
    dbc.Row([
        dbc.Card(className='card-about-page ml-4', children=[
            dbc.CardBody([
                dbc.Row([
                        dcc.Link("Link to Contrail Documentation and Tutorial", href='https://github.com/sisl/Contrail', target='_blank', className="github-link m-25")
                ],
                justify='center',
                align='center',
                no_gutters=True)
            ])
        ])
    ]),
    dbc.Row([
        dbc.Card(className='card-about-page-license ml-4 mt-2', children=[
            dbc.CardBody([
                    html.H5(id='mit-license-1', children=["MIT License"], className="card-body-white p-1 ml-1"),
                    html.H6(id='mit-license-2', children=["Copyright (c) 2021 Stanford Intelligent Systems Laboratory"], className="card-body-white p-1 ml-1"),
                    html.H6(id='mit-license-3', children=["Permission is hereby granted, free of charge, to any person obtaining a copyof this software\
                                                        and associated documentation files (the \"Software\"), to deal in the Software without\
                                                        restriction, including without limitation the rights to use, copy, modify, merge, publish,\
                                                        distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom\
                                                        the Software is furnished to do so, subject to the following conditions:"], className="card-body-white p-1 ml-1"),
                    html.H6(id='mit-license-4', children=["The above copyright notice and this permission notice shall be included in all\
                                                        copies or substantial portions of the Software"], className="card-body-white p-1 ml-1"),
                    html.H6(id='mit-license-5', children=["THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\
                                                        IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\
                                                        FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\
                                                        AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\
                                                        LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\
                                                        OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\
                                                        SOFTWARE."], className="card-body-white p-1 ml-1"),
            ])
        ])
    ])
        
])