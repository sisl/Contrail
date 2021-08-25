import json
import base64
import struct
import pandas as pd

INITIAL_DIM = 3
UPDATE_DIM = 4
NUM_UPDATE_BYTE_SIZE = 2
INFO_BYTE_SIZE = 4
WAYPOINT_BYTE_SIZE = 8

M_TO_NM = 0.000539957; NM_TO_M = 1/M_TO_NM
FT_TO_M = .3048; M_TO_FT = 1/FT_TO_M
FT_TO_NM = FT_TO_M*M_TO_NM
NM_TO_FT = 1/FT_TO_NM 


def parse_dat_file_and_set_indices(contents, filename):
    content_type, content_string = contents.split(',')
    
    if '.dat' in filename:
        decoded = base64.b64decode(content_string)
        num_enc = int.from_bytes(decoded[0:4], byteorder='little')
        print(num_enc)

        encounter_byte_indices = [None] * (num_enc+1)
    
        num_ac = int.from_bytes(decoded[4:8], byteorder='little')
        print(num_ac)
        cursor = 8
        initial_bytes = num_ac * INITIAL_DIM * WAYPOINT_BYTE_SIZE

        for i in range(1, num_enc+1): 
            encounter_byte_indices[i] = cursor
            cursor += initial_bytes
            for j in range(num_ac):
                num_updates = int.from_bytes(decoded[cursor:cursor+NUM_UPDATE_BYTE_SIZE], byteorder='little')
                update_bytes = num_updates * UPDATE_DIM * WAYPOINT_BYTE_SIZE
                cursor = cursor + NUM_UPDATE_BYTE_SIZE + update_bytes
            
        return content_string, encounter_byte_indices, num_ac, num_enc

    return False, False, 0, 0

def convert_json_file(contents):
    content_type, content_string = contents.split(',')
        
    if 'json' in content_type:
        model = json.loads(base64.b64decode(content_string))
        mean = model['mean']

        encounters_data = struct.pack('<II', 1, mean['num_ac']) 
        cursor = 2 * INFO_BYTE_SIZE
        enc_data_indices = [cursor]
        initial_ac_bytes = []
        update_ac_bytes = [[],[]]
            
        for ac in range(1, mean['num_ac']+1):
            ac_traj = mean[str(ac)]['waypoints']
            for waypoint in ac_traj:
                if waypoint['time'] == 0:
                    initial_ac_bytes.append(struct.pack('ddd', waypoint['xEast']*NM_TO_FT, waypoint['yNorth']*NM_TO_FT, waypoint['zUp']))
                else:
                    update_ac_bytes[ac-1].append(struct.pack('dddd', waypoint['time'], waypoint['xEast']*NM_TO_FT, waypoint['yNorth']*NM_TO_FT, waypoint['zUp']))
                
        for waypoint in initial_ac_bytes:
            encounters_data += waypoint

        for ac_id, update in enumerate(update_ac_bytes):
            encounters_data += struct.pack('<H', len(update))
            for waypoint in update:
                encounters_data += waypoint

        return base64.b64encode(encounters_data), enc_data_indices, mean['num_ac'], 1
    

def convert_created_data(table_data):
    df = pd.DataFrame(table_data)
    ac_ids = set(df['ac_id'])

    encounters_data = struct.pack('<II', 1, len(ac_ids)) # only one encounter when in create mode
    cursor = 2 * INFO_BYTE_SIZE

    initial_ac_bytes = []
    update_ac_bytes = [[],[]]
    for ac in ac_ids:
        ac_df = df.loc[df['ac_id'] == ac]

        for i, waypoint in ac_df.iterrows():
            if waypoint['time'] == 0:
                initial_ac_bytes.append(struct.pack('ddd', waypoint['xEast']*NM_TO_FT, waypoint['yNorth']*NM_TO_FT, waypoint['zUp']))
            else:
                update_ac_bytes[ac-1].append(struct.pack('dddd', waypoint['time'], waypoint['xEast']*NM_TO_FT, waypoint['yNorth']*NM_TO_FT, waypoint['zUp']))

    enc_data_indices = [cursor]
    for waypoint in initial_ac_bytes:
        encounters_data += waypoint

    for ac_id, update in enumerate(update_ac_bytes):
        encounters_data += struct.pack('<H', len(update))
        for waypoint in update:
            encounters_data += waypoint
    
    return base64.b64encode(encounters_data), enc_data_indices, len(ac_ids), 1


