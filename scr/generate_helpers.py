import struct
import time
import numpy as np
import multiprocessing as mp
from itertools import repeat
from parse_encounter_helpers import *

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
            if len(gen_enc_data) > enc_id+1:
                enc_data = gen_enc_data.popleft()
                initial_ac_bytes = enc_data[0]
                update_ac_bytes = enc_data[1] 
            else:
                initial_ac_bytes = []
                update_ac_bytes = [[],[]]

            if ac_time[i] == 0:
                initial_ac_bytes.append(struct.pack('ddd', waypoint[0]*NM_TO_FT, waypoint[1]*NM_TO_FT, waypoint[2]))
            else:
                update_ac_bytes[ac-1].append(struct.pack('dddd', ac_time[i], waypoint[0]*NM_TO_FT, waypoint[1]*NM_TO_FT, waypoint[2]))
        
            enc_data = [initial_ac_bytes, update_ac_bytes] 
            gen_enc_data.append(enc_data)

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

    
    
'''
    Used when building the histograms. Steps through the encounters_data and 
    parses each enc into it's dictionary form. Then returns a list of dictionaries of
    individual waypoints.

    FIXME: I implemented multiprocessing, but it doesn't help enough. As soon as the
    encounter set gets larger than a few thousand encounters, this function takes many minutes to 
    run. Not sure how we could speed this up more...
'''
def convert_and_combine_data(data, ref_data) -> list:
    num_encs = data['num_encounters']
    num_processes = mp.cpu_count()

    # the most efficient way to divide the encounters up for multiprocessing
    # It distributes them over num_processes evenly, which increases the
    # speed of the multiprocessing 
    if num_encs > num_processes:
        num_enc_per_cpu = num_encs // num_processes
        if num_enc_per_cpu > STANDARD_NUM_PARTITIONS:
            num_enc_per_partition = num_enc_per_cpu // STANDARD_NUM_PARTITIONS
        else:
            num_enc_per_partition = STANDARD_NUM_PARTITIONS
    else:
        num_enc_per_partition = num_encs
    
    start, size, end = 0, num_enc_per_partition, num_enc_per_partition
    enc_ids = []
    
    # if it wants to create too many partitions, reduce the total number of partitions
    # to the standard number (3 per process)
    total_partitions = num_encs // num_enc_per_partition
    if total_partitions > (STANDARD_NUM_PARTITIONS * num_processes): 
        total_partitions = STANDARD_NUM_PARTITIONS * num_processes
    
    for i in range(total_partitions):
        if i == total_partitions - 1:
            end = num_encs
        encs = [enc for enc in range(start, end)]
        start = end
        end += size
        enc_ids.append(encs)

    # enc_indices = repeat(data['encounter_indices'], total_partitions)
    # encs_data = repeat(data['encounters_data'], total_partitions)
    # ac_ids = repeat(data['ac_ids'], total_partitions)
    # ac_ids_selected = repeat(data['ac_ids'], total_partitions)
    # ref_data_repeats = repeat(ref_data, total_partitions)

    mem_data = repeat(data, total_partitions)
    ac_ids_selected = repeat(data['ac_ids'], total_partitions)
    ref_data_repeats = repeat(ref_data, total_partitions)

    pool = mp.Pool(num_processes)

    start = time.time()
    print('\tbefore multiprocessing convert @ ', 0)
    #results = pool.starmap(parse_enc_data, zip(enc_ids, enc_indices, encs_data, ac_ids, ac_ids_selected, ref_data_repeats))
    results = pool.starmap(parse_enc_data, zip(mem_data, enc_ids, ac_ids_selected, ref_data_repeats))
    print('\tfinished multiprocessing convert @ ',time.time() - start)
    pool.close()
    pool.join()

    print('\tbefore combining @ ', time.time() - start)
    combined_data = []
    for i, result in enumerate(results):
        combined_data += result

    print('\tfinished combining @ ', time.time() - start)

    return combined_data