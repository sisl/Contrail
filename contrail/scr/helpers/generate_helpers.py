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

            if i <= j:        
                [x_i,y_i,z_i] = inputs_i
                [x_j,y_j,z_j] = inputs_j
                
                dist_xy = [ [(x_i-x_j), (x_i-y_j)], 
                            [(y_i-x_j), (y_i-y_j)] ]

                K_cov[3*i:3*i+2, 3*j:3*j+2] = np.exp(-(param_b * np.power(dist_xy, 2)) / (2 * param_a**2))
                
                dist_z = [(z_i-z_j)]
                K_cov[3*i+2, 3*j+2] = np.exp(-(param_c * np.power(dist_z, 2)) / (2 * param_a**2))

                if i != j:
                    K_cov[3*j:3*j+3, 3*i:3*i+3] = np.transpose(K_cov[3*i:3*i+3, 3*j:3*j+3])

    return K_mean, K_cov
    

def stream_generated_data(generated_data, ac_times, filename, num_encounters):
    enc_data_indices = [None] * (num_encounters+1)
    ac_ids = len(generated_data)

    ac1_minmax_hist = []
    ac2_minmax_hist = []

    with open(filename, mode='wb') as file:
        file.write(struct.pack('<II', num_encounters+1, ac_ids))

        cursor = 2 * INFO_BYTE_SIZE
        
        for enc_id in range(num_encounters+1):
            enc_data_indices[enc_id] = cursor
            
            # stream initial waypoints
            for ac in range(ac_ids):
                waypoint = generated_data[ac][enc_id][0] 
                waypoint_data = struct.pack('ddd', waypoint[0]*NM_TO_FT, waypoint[1]*NM_TO_FT, waypoint[2])
                file.write(waypoint_data)

                time_waypoint = [*[0], *waypoint]
                if ac == 0:
                    ac1_minmax_hist.append(time_waypoint)
                elif ac == 1:
                    ac2_minmax_hist.append(time_waypoint)
                    
            cursor += ac_ids * INITIAL_DIM * WAYPOINT_BYTE_SIZE

            # stream update waypoints
            for ac in range(ac_ids):
                updates = generated_data[ac][enc_id][1:] 
                num_updates = struct.pack('<H', len(updates)) 
                file.write(num_updates)

                cursor += NUM_UPDATE_BYTE_SIZE

                ac_time = ac_times[ac][1:]
                for i, waypoint in enumerate(updates):
                    waypoint_data = struct.pack('dddd', ac_time[i], waypoint[0]*NM_TO_FT, waypoint[1]*NM_TO_FT, waypoint[2])
                    file.write(waypoint_data)

                    time_waypoint = [*[ac_time[i]], *waypoint]
                    if ac == 0:
                        ac1_minmax_hist.append(time_waypoint)
                    elif ac == 1:
                        ac2_minmax_hist.append(time_waypoint)

                cursor += len(updates) * UPDATE_DIM * WAYPOINT_BYTE_SIZE

    ac1_minmax_hist = np.array(ac1_minmax_hist)
    ac2_minmax_hist = np.array(ac2_minmax_hist)
    if ac1_minmax_hist.shape[0] == 0:
        ac1_minmax_hist = np.array([], dtype=np.int64).reshape(0,4)
    if ac2_minmax_hist.shape[0] == 0:
        ac2_minmax_hist = np.array([], dtype=np.int64).reshape(0,4)

    ac_minmax_hist = np.vstack((ac1_minmax_hist, ac2_minmax_hist))
    minmax_hist = [[ac_minmax_hist.min(axis=0), ac_minmax_hist.max(axis=0)],
                    [ac_minmax_hist.min(axis=0), ac_minmax_hist.max(axis=0)]]

    return enc_data_indices, minmax_hist


def stream_count_histograms(filename, enc_indices, minmax_hist, num_encounters, ac_ids):    

    ac_1_xy_bin_counts = np.zeros((NUM_BINS_HISTOGRAM+1, NUM_BINS_HISTOGRAM+1))
    ac_1_tz_bin_counts = np.zeros((NUM_BINS_HISTOGRAM+1, NUM_BINS_HISTOGRAM+1))
    ac_2_xy_bin_counts = np.zeros((NUM_BINS_HISTOGRAM+1, NUM_BINS_HISTOGRAM+1))
    ac_2_tz_bin_counts = np.zeros((NUM_BINS_HISTOGRAM+1, NUM_BINS_HISTOGRAM+1))

    [ac1_minmax_hist, ac2_minmax_hist] = minmax_hist
    ac1_minmax_hist = np.array(ac1_minmax_hist)
    ac2_minmax_hist = np.array(ac2_minmax_hist)
    
    ac1_t_minmax, ac1_x_minmax, ac1_y_minmax, ac1_z_minmax = ac1_minmax_hist.T[0], ac1_minmax_hist.T[1], ac1_minmax_hist.T[2], ac1_minmax_hist.T[3]
    ac1_t_bin_width = (ac1_t_minmax[1]-ac1_t_minmax[0]) / NUM_BINS_HISTOGRAM
    ac1_x_bin_width = (ac1_x_minmax[1]-ac1_x_minmax[0]) / NUM_BINS_HISTOGRAM
    ac1_y_bin_width = (ac1_y_minmax[1]-ac1_y_minmax[0]) / NUM_BINS_HISTOGRAM
    ac1_z_bin_width = (ac1_z_minmax[1]-ac1_z_minmax[0]) / NUM_BINS_HISTOGRAM

    ac1_t_edges = np.linspace(ac1_t_minmax[0], ac1_t_minmax[1], num=NUM_BINS_HISTOGRAM+1, endpoint=True)    
    ac1_x_edges = np.linspace(ac1_x_minmax[0], ac1_x_minmax[1], num=NUM_BINS_HISTOGRAM+1, endpoint=True)
    ac1_y_edges = np.linspace(ac1_y_minmax[0], ac1_y_minmax[1], num=NUM_BINS_HISTOGRAM+1, endpoint=True)
    ac1_z_edges = np.linspace(ac1_z_minmax[0], ac1_z_minmax[1], num=NUM_BINS_HISTOGRAM+1, endpoint=True)

    ac2_t_minmax, ac2_x_minmax, ac2_y_minmax, ac2_z_minmax = ac2_minmax_hist.T[0], ac2_minmax_hist.T[1], ac2_minmax_hist.T[2], ac2_minmax_hist.T[3]
    ac2_t_bin_width = (ac2_t_minmax[1]-ac2_t_minmax[0]) / NUM_BINS_HISTOGRAM
    ac2_x_bin_width = (ac2_x_minmax[1]-ac2_x_minmax[0]) / NUM_BINS_HISTOGRAM
    ac2_y_bin_width = (ac2_y_minmax[1]-ac2_y_minmax[0]) / NUM_BINS_HISTOGRAM
    ac2_z_bin_width = (ac2_z_minmax[1]-ac2_z_minmax[0]) / NUM_BINS_HISTOGRAM

    ac2_t_edges = np.linspace(ac2_t_minmax[0], ac2_t_minmax[1], num=NUM_BINS_HISTOGRAM+1, endpoint=True)    
    ac2_x_edges = np.linspace(ac2_x_minmax[0], ac2_x_minmax[1], num=NUM_BINS_HISTOGRAM+1, endpoint=True)
    ac2_y_edges = np.linspace(ac2_y_minmax[0], ac2_y_minmax[1], num=NUM_BINS_HISTOGRAM+1, endpoint=True)
    ac2_z_edges = np.linspace(ac2_z_minmax[0], ac2_z_minmax[1], num=NUM_BINS_HISTOGRAM+1, endpoint=True)

    with open(filename, 'rb') as file:
        enc_data = file.read(2*INFO_BYTE_SIZE)
        [num_enc_ids,num_ac_ids] = struct.unpack('<II', enc_data[0:2*INFO_BYTE_SIZE])

    for enc_id in range(num_encounters):
        enc_start_ind = enc_indices[enc_id]
        cursor = 0

        with open(filename, 'rb') as file:
            file.seek(enc_start_ind)
            if enc_id+1 >= len(enc_indices):
                enc_data = file.read()

            else:
                enc_end_ind = enc_indices[enc_id+1]
                num_bytes = enc_end_ind - enc_start_ind
                enc_data = file.read(num_bytes)
        
        # count initial waypoints
        for ac in ac_ids:
            [x,y,z] = struct.unpack('ddd', enc_data[cursor:cursor+(WAYPOINT_BYTE_SIZE*INITIAL_DIM)])
            x, y = x*FT_TO_NM, y*FT_TO_NM

            if ac == 1 :
                ac1_x_ind = (x - ac1_x_minmax[0]) // ac1_x_bin_width
                ac1_y_ind = (y - ac1_y_minmax[0]) // ac1_y_bin_width
                ac1_t_ind = (0 - ac1_t_minmax[0]) // ac1_t_bin_width
                ac1_z_ind = (z - ac1_z_minmax[0]) // ac1_z_bin_width 

                ac_1_xy_bin_counts[int(ac1_y_ind), int(ac1_x_ind)] += 1
                ac_1_tz_bin_counts[int(ac1_z_ind), int(ac1_t_ind)] += 1

            elif ac == 2:
                ac2_x_ind = (x - ac2_x_minmax[0]) // ac2_x_bin_width
                ac2_y_ind = (y - ac2_y_minmax[0]) // ac2_y_bin_width 
                ac2_t_ind = (0 - ac2_t_minmax[0]) // ac2_t_bin_width
                ac2_z_ind = (z - ac2_z_minmax[0]) // ac2_z_bin_width 

                ac_2_xy_bin_counts[int(ac2_y_ind), int(ac2_x_ind)] += 1
                ac_2_tz_bin_counts[int(ac2_z_ind), int(ac2_t_ind)] += 1

            cursor += INITIAL_DIM * WAYPOINT_BYTE_SIZE

        # count update waypoints
        for ac in ac_ids:
            num_updates = int.from_bytes(enc_data[cursor:cursor+NUM_UPDATE_BYTE_SIZE], byteorder='little')
            cursor += NUM_UPDATE_BYTE_SIZE

            for i in range(num_updates): 
                [time,x,y,z] = struct.unpack('dddd', enc_data[cursor:cursor+(WAYPOINT_BYTE_SIZE*UPDATE_DIM)])
                x, y = x*FT_TO_NM, y*FT_TO_NM

                if ac == 1:
                    ac1_x_ind = (x - ac1_x_minmax[0]) // ac1_x_bin_width
                    ac1_y_ind = (y - ac1_y_minmax[0]) // ac1_y_bin_width 
                    ac1_t_ind = (time - ac1_t_minmax[0]) // ac1_t_bin_width
                    ac1_z_ind = (z - ac1_z_minmax[0]) // ac1_z_bin_width 
                    
                    ac_1_xy_bin_counts[int(ac1_y_ind), int(ac1_x_ind)] += 1
                    ac_1_tz_bin_counts[int(ac1_z_ind), int(ac1_t_ind)] += 1

                elif ac == 2:   
                    ac2_x_ind = (x - ac2_x_minmax[0]) // ac2_x_bin_width   
                    ac2_y_ind = (y - ac2_y_minmax[0]) // ac2_y_bin_width 
                    ac2_t_ind = (time - ac2_t_minmax[0]) // ac2_t_bin_width
                    ac2_z_ind = (z - ac2_z_minmax[0]) // ac2_z_bin_width 

                    ac_2_xy_bin_counts[int(ac2_y_ind), int(ac2_x_ind)] += 1
                    ac_2_tz_bin_counts[int(ac2_z_ind), int(ac2_t_ind)] += 1

                cursor += UPDATE_DIM * WAYPOINT_BYTE_SIZE
    
    return ac_1_xy_bin_counts, ac_1_tz_bin_counts, ac_2_xy_bin_counts, ac_2_tz_bin_counts,\
        ac1_t_edges, ac1_x_edges, ac1_y_edges, ac1_z_edges,\
        ac2_t_edges, ac2_x_edges, ac2_y_edges, ac2_z_edges
        
