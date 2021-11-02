'''
    EXPLANATION
'''

import pandas as pd
import numpy as np

from scipy.interpolate import PchipInterpolator

import pymap3d as pm

from constants import *


def interpolate_df_time(df, ac_ids_selected):
    df_interp = pd.DataFrame()
    min_values_list, max_values_list = [], []

    for ac_id in ac_ids_selected:
        df_ac = df.loc[df['ac_id'] == ac_id]
        df_ac = df_ac.apply(pd.to_numeric, errors='coerce').fillna(0).sort_values('time')
        # print('df_ac[time]', df_ac['time'])

        df_ac_interp = pd.DataFrame()
        df_ac_interp['time'] = np.arange(int(min(df_ac['time'])), int(max(df_ac['time'])+1))
        df_ac_interp['ac_id'] = [ac_id]*len(df_ac_interp['time'])
        df_ac_interp['xEast'] = PchipInterpolator(df_ac['time'], df_ac['xEast'])(df_ac_interp['time'])
        df_ac_interp['yNorth'] = PchipInterpolator(df_ac['time'], df_ac['yNorth'])(df_ac_interp['time'])
        df_ac_interp['zUp'] = PchipInterpolator(df_ac['time'], df_ac['zUp'])(df_ac_interp['time'])
        if 'horizontal_speed' in df_ac.columns:
            df_ac_interp['horizontal_speed'] = PchipInterpolator(df_ac['time'], df_ac['horizontal_speed'])(df_ac_interp['time'])
        if 'vertical_speed' in df_ac.columns:
            df_ac_interp['vertical_speed'] = PchipInterpolator(df_ac['time'], df_ac['vertical_speed'])(df_ac_interp['time'])

        df_interp = df_interp.append(df_ac_interp, ignore_index=True)   

        if 'horizontal_speed' in df_ac.columns:
            min_values_list.append([min(df_ac_interp['time']), min(df_ac_interp['xEast']), min(df_ac_interp['yNorth']), min(df_ac_interp['zUp']), \
                min(df_ac['horizontal_speed']), min(df_ac['vertical_speed'])])
            max_values_list.append([max(df_ac_interp['time']), max(df_ac_interp['xEast']), max(df_ac_interp['yNorth']), max(df_ac_interp['zUp']), \
                max(df_ac_interp['horizontal_speed']), max(df_ac_interp['vertical_speed'])])
        else:
            min_values_list.append([min(df_ac_interp['time']), min(df_ac_interp['xEast']), min(df_ac_interp['yNorth']), min(df_ac_interp['zUp'])])
            max_values_list.append([max(df_ac_interp['time']), max(df_ac_interp['xEast']), max(df_ac_interp['yNorth']), max(df_ac_interp['zUp'])])
            
    return df_interp, min_values_list, max_values_list


def calculate_horizontal_vertical_speeds_df(df):
    dataf = df.copy()
    hor_speeds = []
    ver_speeds = []
    for ac_id in set(df['ac_id']):
        ac_id_data = df.loc[df['ac_id'] == ac_id]
        move_over_time = (np.roll(ac_id_data, -1, axis=0) - ac_id_data)[:-1]
        hor_speed = np.sqrt(move_over_time.xEast ** 2 + move_over_time.yNorth ** 2) / move_over_time['time'] * 3600
        hor_speeds += (np.append(0.0, round(hor_speed, 4))).tolist()
        ver_speed = move_over_time.zUp / move_over_time['time'] * 60
        ver_speeds += (np.append(0.0, round(ver_speed, 4))).tolist()
    dataf.loc[:, 'horizontal_speed'] = hor_speeds
    dataf.loc[:, 'vertical_speed'] = ver_speeds
    return dataf


def populate_lat_lng_xEast_yNorth(data, ref_data):
    for data_point in data:
        if data_point['xEast'] and data_point['yNorth']:
            # calculate lat long
            data_point['lat'], data_point['long'],_ = pm.enu2geodetic(data_point['xEast']*NM_TO_M, data_point['yNorth']*NM_TO_M,
                                         data_point['yNorth']*FT_TO_M if data_point['yNorth'] else ref_data['ref_alt']*FT_TO_M, 
                                         ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M, 
                                         ell=pm.Ellipsoid('wgs84'), deg=True)
        
        elif data_point['lat'] and data_point['long']:
            x, y,_ =  pm.geodetic2enu(data_point['lat'], data_point['long'],
                                         data_point['yNorth']*FT_TO_M if data_point['yNorth'] else ref_data['ref_alt']*FT_TO_M, 
                                         ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M, 
                                         ell=pm.Ellipsoid('wgs84'), deg=True)
            data_point['xEast'], data_point['yNorth'] = x*M_TO_NM, y*M_TO_NM
    return data

