


import dash
import dash_bootstrap_components as dbc

from dash import dash_table
from dash import dcc
from dash import html

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
from helpers.generate_helpers import *
from helpers.parse_encounter_helpers import *
from helpers.memory_data_helpers import *
from helpers.constants import *

import time
import struct
import uuid


# Import Dash Instance #
from app import app

layout = html.Div([
    html.P("Filepath for loading waypoint (.dat) files"),
    dbc.InputGroup(
        [
            #dbc.InputGroupAddon("@", addon_type="prepend"),
            dbc.Input(placeholder=DEFAULT_DATA_FILE_PATH),
            dbc.Input(id="file-path-input", type="text", placeholder="FILEPATH", debounce=False, value=DEFAULT_DATA_FILE_PATH, style={'display':'none'}),
        ],
        className="mb-3"
    )
    # ),
    # dbc.InputGroup(
    #     [
    #         dbc.Input(placeholder="Recipient's username"),
    #         dbc.InputGroupAddon("@example.com", addon_type="append"),
    #     ],
    #     className="mb-3",
    # ),
    # dbc.InputGroup(
    #     [
    #         dbc.InputGroupAddon("$", addon_type="prepend"),
    #         dbc.Input(placeholder="Amount", type="number"),
    #         dbc.InputGroupAddon(".00", addon_type="append"),
    #     ],
    #     className="mb-3",
    # ),
    # dbc.InputGroup(
    #     [
    #         dbc.InputGroupAddon("With textarea", addon_type="prepend"),
    #         dbc.Textarea(),
    #     ],
    #     className="mb-3",
    # ),
    # dbc.InputGroup(
    #     [
    #         dbc.Select(
    #             options=[
    #                 {"label": "Option 1", "value": 1},
    #                 {"label": "Option 2", "value": 2},
    #             ]
    #         ),
    #         dbc.InputGroupAddon("With select", addon_type="append"),
    #     ]
    # ),
])