import struct
import time
import numpy as np
import multiprocessing as mp
from itertools import repeat
import pymap3d as pm
import base64
from collections import deque

INITIAL_DIM = 3
UPDATE_DIM = 4
NUM_UPDATE_BYTE_SIZE = 2
INFO_BYTE_SIZE = 4
WAYPOINT_BYTE_SIZE = 8

M_TO_NM = 0.000539957; NM_TO_M = 1/M_TO_NM
FT_TO_M = .3048; M_TO_FT = 1/FT_TO_M
FT_TO_NM = FT_TO_M*M_TO_NM
NM_TO_FT = 1/FT_TO_NM 

def exp_kernel_func(inputs, param_a, param_b, param_c): 
    inputs = np.array(inputs)
    N = inputs.shape[0]*inputs.shape[1]

    K_mean = inputs.reshape((N,))
    K_cov = np.zeros((N, N))  
    
    param_a, param_b, param_c = float(param_a), float(param_b), float(param_c)
    
    for i, inputs_i in enumerate(inputs):
        for j, inputs_j in enumerate(inputs):
            if i == j or i < j:           
                [x_i,y_i,z_i] = inputs_i
                [x_j,y_j,z_j] = inputs_j
                
                dist_xy = [[(x_i-x_j)**2, (x_i-y_j)**2], 
                           [(y_i-x_j)**2, (y_i-y_j)**2]]
                K_cov[3*i:3*i+2, 3*j:3*j+2] = np.exp(-(param_b * np.power(dist_xy, 2)) / (2 * param_a**2))
                
                dist_z = [(z_i-z_j)]
                K_cov[3*i+2, 3*j+2] = np.exp(-(param_c * np.power(dist_z, 2)) / (2 * param_a**2))

                if i != j:
                    K_cov[3*j:3*j+3, 3*i:3*i+3] = np.transpose(K_cov[3*i:3*i+3, 3*j:3*j+3])

    return K_mean, K_cov

def generation_error_found(memory_data_type, nom_ac_ids, num_encounters, cov_radio_value, 
                 sigma_hor, sigma_ver, exp_kernel_a, exp_kernel_b, exp_kernel_c) -> bool:
    error = False
    if memory_data_type == 'cleared': # or memory_data == []:
        print('Must create a nominal encounter or load a waypoint file')
        error = True
    if not nom_ac_ids:
        print("Must select at least one nominal path")
        error = True
    if not num_encounters:
        print('Must input number of encounters to generate')
        error = True    
    if cov_radio_value == 'cov-radio-diag':
        if not sigma_hor or not sigma_ver:
            print('Must input all sigma values.')
            error = True
    elif cov_radio_value == 'cov-radio-exp':
        if not exp_kernel_a or not exp_kernel_b or not exp_kernel_c:
            print('Must input all parameter values.')
            error = True
    
    return error

def generate_helper_diag(waypoints_list, gen_enc_data, ac, ac_time) -> dict:
    for i, waypoints in enumerate(waypoints_list):
        for enc_id, waypoint in enumerate(waypoints):
            if gen_enc_data[enc_id+1] == None:
                initial_ac_bytes = []
                update_ac_bytes = [[],[]]
            else:
                initial_ac_bytes = gen_enc_data[enc_id+1][0]
                update_ac_bytes = gen_enc_data[enc_id+1][1] 

            if ac_time[i] == 0:
                initial_ac_bytes.append(struct.pack('ddd', waypoint[0]*NM_TO_FT, waypoint[1]*NM_TO_FT, waypoint[2]))
            else:
                update_ac_bytes[ac-1].append(struct.pack('dddd', ac_time[i], waypoint[0]*NM_TO_FT, waypoint[1]*NM_TO_FT, waypoint[2]))
        
            gen_enc_data[enc_id+1] = [initial_ac_bytes, update_ac_bytes] 

    return gen_enc_data

def generate_helper_exp(waypoints_list, gen_enc_data, ac, ac_time, start) -> dict:
    for enc_id, waypoints in enumerate(waypoints_list):

        if enc_id % 10000 == 0: 
            print('\tenc_id: ', enc_id, ' @ ', time.time()-start)

        if len(gen_enc_data) > enc_id+1:
            enc_data = gen_enc_data.popleft()
            initial_ac_bytes = enc_data[0]
            update_ac_bytes = enc_data[1] 
        else:
            initial_ac_bytes = []
            update_ac_bytes = [[],[]]
        
        for i, waypoint in enumerate(waypoints):
            if ac_time[i] == 0:
                initial_ac_bytes.append(struct.pack('ddd', waypoint[0]*NM_TO_FT, waypoint[1]*NM_TO_FT, waypoint[2]))
            else:
                update_ac_bytes[ac-1].append(struct.pack('dddd', ac_time[i], waypoint[0]*NM_TO_FT, waypoint[1]*NM_TO_FT, waypoint[2]))

        enc_data = [initial_ac_bytes, update_ac_bytes] 
        gen_enc_data.append(enc_data)
        
    return gen_enc_data

def combine_data_set_cursor(gen_enc_data, num_encounters, nom_ac_ids, start):
    generated_data = bytearray(struct.pack('<II', int(num_encounters)+1, len(nom_ac_ids)))
    cursor = 2 * INFO_BYTE_SIZE

    enc_data_indices = [None] * (int(num_encounters)+1)
    
    enc_id = 0
    while gen_enc_data:
        enc = gen_enc_data.popleft()
        enc_data_indices[enc_id] = cursor
        enc_data_combined = bytes()
        
        initial_waypoints = enc[0]
        for i, waypoint in enumerate(initial_waypoints):
            enc_data_combined += waypoint

        cursor += len(initial_waypoints) * INITIAL_DIM * WAYPOINT_BYTE_SIZE

        updates = enc[1]
        for ac_id, update in enumerate(updates):
            num_updates = struct.pack('<H', len(update))
            cursor += NUM_UPDATE_BYTE_SIZE
            enc_data_combined += num_updates

            for i, waypoint in enumerate(update):
                enc_data_combined += waypoint

            cursor += len(update) * UPDATE_DIM * WAYPOINT_BYTE_SIZE

        generated_data.extend(enc_data_combined)

        del enc
        del enc_data_combined
        enc_id += 1
    
    return generated_data, enc_data_indices

def parse_enc_data(enc_ids_selected, enc_indices, encounters_filename, enc_ac_ids, ac_ids_selected, ref_data):
    # if encounters_data[0:2] == 'b\'':
    #     encounters_data = encounters_data[2:-1]
    #     difference = len(encounters_data) % 4
    #     padding = '=' * difference
    #     encounters_data += padding

    # decoded = base64.b64decode(encounters_data)

    enc_data_list = []

    initial_dim, update_dim = 3, 4
    num_update_byte_size, waypoint_byte_size = 2, 8

    for enc_id in enc_ids_selected:
        # enc_start_id = enc_indices[enc_id]
        # if enc_id+1 >= len(enc_indices):
        #     enc_data = decoded[enc_start_id:]
        # else:
        #     enc_end_id = enc_indices[enc_id+1]
        #     enc_data = decoded[enc_start_id:enc_end_id]

        with open(encounters_filename, 'rb') as file:
            enc_start_ind = enc_indices[enc_id]
            file.seek(enc_start_ind)
            if enc_id+1 >= len(enc_indices):
                enc_data = file.read()
            else:
                enc_end_ind = enc_indices[enc_id+1]
                num_bytes = enc_end_ind - enc_start_ind
                print('num_bytes: ', num_bytes)
                enc_data = file.read(num_bytes)
        print(type(enc_data))
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

def convert_and_combine_data(data, ref_data) -> list:
    num_encs = data['num_encounters']
    num_processes = mp.cpu_count()

    if num_encs > num_processes:
        num_enc_per_cpu = num_encs // num_processes
        num_enc_per_partition = num_enc_per_cpu // 3
    else:
        num_enc_per_partition = num_encs
    
    start, size, end = 0, num_enc_per_partition, num_enc_per_partition
    enc_ids = []
    
    total_partitions = num_encs // num_enc_per_partition
    if total_partitions > (3*num_processes): total_partitions = 3 * num_processes
    for i in range(total_partitions):
        if i == total_partitions - 1:
            end = num_encs
        encs = [enc for enc in range(start, end)]
        start = end
        end += size
        enc_ids.append(encs)

    

    enc_indices = repeat(data['encounter_indices'], total_partitions)
    encs_data = repeat(data['encounters_data'], total_partitions)
    ac_ids = repeat(data['ac_ids'], total_partitions)
    ac_ids_selected = repeat(data['ac_ids'], total_partitions)
    ref_data_repeats = repeat(ref_data, total_partitions)

    pool = mp.Pool(num_processes)

    start = time.time()
    print('\tbefore multiprocessing convert @ ', 0)
    results = pool.starmap(parse_enc_data, zip(enc_ids, enc_indices, encs_data, ac_ids, ac_ids_selected, ref_data_repeats))
    print('\tfinished multiprocessing convert @ ',time.time() - start)
    pool.close()
    pool.join()

    print('\tbefore combining @ ', time.time() - start)
    combined_data = []
    for i, result in enumerate(results):
        combined_data += result

    print('\tfinished combining @ ', time.time() - start)

    return combined_data