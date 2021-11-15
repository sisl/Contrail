import struct
import time
import numpy as np
import multiprocessing as mp
from itertools import repeat

from helpers.parse_encounter_helpers import *
from helpers.constants import *

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

def exp_kernel_func(inputs, param_a, param_b, param_c): 
    inputs = np.array(inputs)
    N = inputs.shape[0]*inputs.shape[1]

    K_mean = inputs.reshape((N,))
    K_cov = np.zeros((N, N))  
    
    for i, inputs_i in enumerate(inputs):
        for j, inputs_j in enumerate(inputs):
            #if i == j or i < j:   
            if i <= j:        
                [x_i,y_i,z_i] = inputs_i
                [x_j,y_j,z_j] = inputs_j
                
                dist_xy = [ [(x_i-x_j)**2, (x_i-y_j)**2], 
                            [(y_i-x_j)**2, (y_i-y_j)**2] ]

                K_cov[3*i:3*i+2, 3*j:3*j+2] = np.exp(-(param_b * np.power(dist_xy, 2)) / (2 * param_a**2))
                
                dist_z = [(z_i-z_j)]
                K_cov[3*i+2, 3*j+2] = np.exp(-(param_c * np.power(dist_z, 2)) / (2 * param_a**2))

                if i != j:
                    K_cov[3*j:3*j+3, 3*i:3*i+3] = np.transpose(K_cov[3*i:3*i+3, 3*j:3*j+3])

    return K_mean, K_cov


def stream_generated_data(generated_data, ac_times, filename, num_encounters):
    enc_data_indices = [None] * (num_encounters+1)
    ac_ids = len(generated_data)

    with open(DEFAULT_DATA_FILE_PATH + filename, mode='wb') as file:
        
        file.write(struct.pack('<II', num_encounters+1, ac_ids))
        
        cursor = 2 * INFO_BYTE_SIZE

        for enc_id in range(num_encounters+1):
            enc_data_indices[enc_id] = cursor
            
            # stream initial waypoints
            for ac in range(ac_ids):
                waypoint = generated_data[ac][enc_id][0] #initial waypoint
                
                waypoint_data = struct.pack('ddd', waypoint[0]*NM_TO_FT, waypoint[1]*NM_TO_FT, waypoint[2])
                file.write(waypoint_data)

            cursor += ac_ids * INITIAL_DIM * WAYPOINT_BYTE_SIZE

            # stream update waypoints
            for ac in range(ac_ids):
                updates = generated_data[ac][enc_id][1:] # ignore initial waypoint

                num_updates = struct.pack('<H', len(updates)) 
                file.write(num_updates)
                cursor += NUM_UPDATE_BYTE_SIZE

                ac_time = ac_times[ac][1:] # ignore initial waypoint
                for i, waypoint in enumerate(updates):
                    waypoint_data = struct.pack('dddd', ac_time[i], waypoint[0]*NM_TO_FT, waypoint[1]*NM_TO_FT, waypoint[2])
                    file.write(waypoint_data)

                cursor += len(updates) * UPDATE_DIM * WAYPOINT_BYTE_SIZE
        
    return enc_data_indices
    
    
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

    mem_data = repeat(data, total_partitions)
    ac_ids_selected = repeat(data['ac_ids'], total_partitions)
    ref_data_repeats = repeat(ref_data, total_partitions)

    pool = mp.Pool(num_processes)

    start = time.time()
    print('\tbefore converting w/ multiprocessing @ ', (time.time() - start)/60, ' mins')
    results = pool.starmap(parse_enc_data, zip(mem_data, enc_ids, ac_ids_selected, ref_data_repeats))
    print('\tfinished converting w/ multiprocessing @ ', (time.time() - start)/60, ' mins')

    pool.close()
    pool.join()

    print('\tbefore combining @ ', (time.time() - start)/60, ' mins')
    combined_data = []
    for i, result in enumerate(results):
        combined_data += result

    print('\tfinished combining @ ', (time.time() - start)/60, ' mins')

    return combined_data