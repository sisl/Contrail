import json
import base64
import struct
import pandas as pd

from constants import *


'''
    Used when a new waypoints .dat file is loaded in. Takes the filename, opens the file,
    reads the contents and populates the encounter byte indices. Returns the 
    indices, num_ac and num_enc. 

    FIXME: Right now, the application assumes that the file is in the working directory
    (which in our case it is). However, this won't be the case for users on the
    client side. In fact, pretty sure dash does not allow you to access any files
    on the client's computer directly. All of the contents need to come through the 
    dcc.Upload contents component. This takes FOREVER for large files... So I didn't
    know exactly what to do here. 
'''
def parse_dat_file_and_set_indices(filepath):
    # filepath = DEFAULT_DATA_FILE_PATH + filename
    # print(filepath)
    with open(filepath, 'rb') as file:
        contents = file.read()

    if '.dat' in filepath:
        num_enc = int.from_bytes(contents[0:4], byteorder='little')
        num_ac = int.from_bytes(contents[4:8], byteorder='little')

        encounter_byte_indices = [None] * (num_enc+1)
        
        initial_bytes = num_ac * INITIAL_DIM * WAYPOINT_BYTE_SIZE
        cursor = 8
        for i in range(1, num_enc+1): 
            encounter_byte_indices[i] = cursor
            cursor += initial_bytes
            for j in range(num_ac):
                num_updates = int.from_bytes(contents[cursor:cursor+NUM_UPDATE_BYTE_SIZE], byteorder='little')
                update_bytes = num_updates * UPDATE_DIM * WAYPOINT_BYTE_SIZE
                cursor = cursor + NUM_UPDATE_BYTE_SIZE + update_bytes
            
        return encounter_byte_indices, num_ac, num_enc

    return False, 0, 0

'''
    Used when a user loads a model for generation. Takes in the json contents,
    parses through the contents and returns the encounters_data, encouter data indices
    num_ac and num_enc (which always = 1).
'''
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
    
'''
    Used when a user finishes in create mode. Steps through the data table, creates a 
    binary string representation of the data so that the structure of memory_data can
    remain constant. 
'''
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


