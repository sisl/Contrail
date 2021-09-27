import struct
import pymap3d as pm
import base64

INITIAL_DIM = 3
UPDATE_DIM = 4
NUM_UPDATE_BYTE_SIZE = 2
INFO_BYTE_SIZE = 4
WAYPOINT_BYTE_SIZE = 8

STANDARD_NUM_PARTITIONS = 3

M_TO_NM = 0.000539957; NM_TO_M = 1/M_TO_NM
FT_TO_M = .3048; M_TO_FT = 1/FT_TO_M
FT_TO_NM = FT_TO_M*M_TO_NM
NM_TO_FT = 1/FT_TO_NM 

'''
    Used when a user selects an enc from the dropdown and memory_data['type']
    is either 'loaded' or 'generated'. The only difference between this function
    and parse_enc_data_from_encounters_data is how the data is read in. In this func,
    it is read in directly from the file.
'''
def parse_enc_data_from_filename(enc_ids_selected, enc_indices, encounters_filename, enc_ac_ids, ac_ids_selected, ref_data):
    enc_data_list = []

    initial_dim, update_dim = 3, 4
    num_update_byte_size, waypoint_byte_size = 2, 8

    for enc_id in enc_ids_selected:
        # print('** ENC_ID ', enc_id, '**')
        with open(encounters_filename, 'rb') as file:
            enc_start_ind = enc_indices[enc_id]
            file.seek(enc_start_ind)
            if enc_id+1 >= len(enc_indices):
                enc_data = file.read()
            else:
                enc_end_ind = enc_indices[enc_id+1]
                num_bytes = enc_end_ind - enc_start_ind
                enc_data = file.read(num_bytes)

        cursor = 0
        for ac in enc_ac_ids:
            [x,y,z] = struct.unpack('ddd', enc_data[cursor:cursor+(waypoint_byte_size*initial_dim)])
            
            if ac in ac_ids_selected:
                data_point = {'encounter_id': enc_id, 'ac_id':ac, 'time':0,\
                                'xEast':x*FT_TO_NM, 'yNorth':y*FT_TO_NM,\
                                'lat':None, 'long': None, 'zUp':z,\
                                'horizontal_speed':0, 'vertical_speed':0}

                data_point['lat'], data_point['long'], _ = pm.enu2geodetic(data_point['xEast']*NM_TO_M, data_point['yNorth']*NM_TO_M, data_point['zUp']*FT_TO_M, 
                                                                ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M, 
                                                                ell=pm.Ellipsoid('wgs84'), deg=True)
                enc_data_list += [data_point]

            cursor += (waypoint_byte_size*initial_dim)
        
        for ac in enc_ac_ids:
            num_updates = int.from_bytes(enc_data[cursor:cursor+num_update_byte_size], byteorder='little')
            # print('num_updates: ', num_updates)
            cursor += num_update_byte_size
            for i in range(num_updates): 
                [time,x,y,z] = struct.unpack('dddd', enc_data[cursor:cursor+(waypoint_byte_size*update_dim)])

                if ac in ac_ids_selected:
                    data_point = {'encounter_id': enc_id, 'ac_id':ac, 'time':time,\
                                    'xEast':x*FT_TO_NM, 'yNorth':y*FT_TO_NM,\
                                    'lat':None, 'long': None, 'zUp':z,\
                                    'horizontal_speed':0, 'vertical_speed':0}

                    data_point['lat'], data_point['long'], _ = pm.enu2geodetic(data_point['xEast']*NM_TO_M, data_point['yNorth']*NM_TO_M, data_point['zUp']*FT_TO_M, 
                                                                    ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M, 
                                                                    ell=pm.Ellipsoid('wgs84'), deg=True)
                    enc_data_list += [data_point]

                cursor += (waypoint_byte_size*update_dim)

    # print('this took  ', time.time() - start)
    return enc_data_list


'''
    Used when a user selects an enc from the dropdown and memory_data['type']
    is either 'created' or 'json'. The only difference between this function
    and parse_enc_data_from_filename is how the data is read in. In this func,
    it is read in directly from the the stored memory_data['encounters_data']
    which is a base64 encoded string.
'''
def parse_enc_data_from_encounters_data(enc_ids_selected, enc_indices, encounters_data, enc_ac_ids, ac_ids_selected, ref_data):
    if encounters_data[0:2] == 'b\'':
        encounters_data = encounters_data[2:-1]
        difference = len(encounters_data) % 4
        padding = '=' * difference
        encounters_data += padding

    decoded = base64.b64decode(encounters_data)

    enc_data_list = []

    initial_dim, update_dim = 3, 4
    num_update_byte_size, waypoint_byte_size = 2, 8

    for enc_id in enc_ids_selected:
        enc_start_id = enc_indices[enc_id]
        if enc_id+1 >= len(enc_indices):
            enc_data = decoded[enc_start_id:]
        else:
            enc_end_id = enc_indices[enc_id+1]
            enc_data = decoded[enc_start_id:enc_end_id]

        cursor = 0
        for ac in enc_ac_ids:
            [x,y,z] = struct.unpack('ddd', enc_data[cursor:cursor+(waypoint_byte_size*initial_dim)])
            
            if ac in ac_ids_selected:
                data_point = {'encounter_id': enc_id, 'ac_id':ac, 'time':0,\
                                'xEast':x*FT_TO_NM, 'yNorth':y*FT_TO_NM,\
                                'lat':None, 'long': None, 'zUp':z,\
                                'horizontal_speed':0, 'vertical_speed':0}

                data_point['lat'], data_point['long'], _ = pm.enu2geodetic(data_point['xEast']*NM_TO_M, data_point['yNorth']*NM_TO_M, data_point['zUp']*FT_TO_M, 
                                                                ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M, 
                                                                ell=pm.Ellipsoid('wgs84'), deg=True)
                enc_data_list += [data_point]

            cursor += (waypoint_byte_size*initial_dim)
        
        for ac in enc_ac_ids:
            num_updates = int.from_bytes(enc_data[cursor:cursor+num_update_byte_size], byteorder='little')
            cursor += num_update_byte_size
            for i in range(num_updates): 
                [time,x,y,z] = struct.unpack('dddd', enc_data[cursor:cursor+(waypoint_byte_size*update_dim)])

                if ac in ac_ids_selected:
                    data_point = {'encounter_id': enc_id, 'ac_id':ac, 'time':time,\
                                    'xEast':x*FT_TO_NM, 'yNorth':y*FT_TO_NM,\
                                    'lat':None, 'long': None, 'zUp':z,\
                                    'horizontal_speed':0, 'vertical_speed':0}

                    data_point['lat'], data_point['long'], _ = pm.enu2geodetic(data_point['xEast']*NM_TO_M, data_point['yNorth']*NM_TO_M, data_point['zUp']*FT_TO_M, 
                                                                    ref_data['ref_lat'], ref_data['ref_long'], ref_data['ref_alt']*FT_TO_M, 
                                                                    ell=pm.Ellipsoid('wgs84'), deg=True)
                    enc_data_list += [data_point]

                cursor += (waypoint_byte_size*update_dim)

    return enc_data_list


def parse_enc_data(memory_data, enc_ids_selected, ac_ids_selected, ref_data):
    if memory_data['type'] == 'created' or memory_data['type'] == 'json':
        return parse_enc_data_from_encounters_data(enc_ids_selected, memory_data['encounter_indices'], memory_data['encounters_data'], memory_data['ac_ids'], ac_ids_selected, ref_data)
    else:
        return parse_enc_data_from_filename(enc_ids_selected, memory_data['encounter_indices'], memory_data['filename'], memory_data['ac_ids'], ac_ids_selected, ref_data)