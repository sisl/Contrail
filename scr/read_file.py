
# According to file format specified in Matlab script
# written by Mykel Kochenderfer, mykel@stanford.edu

# This script loads a "waypoints" file of the following format, and 
# returns a structure holding the waypoints for different encounter sets.

#     WAYPOINTS FILE:
#     The waypoints file contains a set of encounters. Each encounter is
#     defined by a set of waypoints associated with a fixed number of
#     aircraft. The waypoints are positions in space according to a fixed,
#     global coordinate system. All distances are in feet. Time is specified
#     in seconds since the beginning of the encounter. The file is organized
#     as follows:

#     [Header]
#     uint32 (number of encounters)
#     uint32 (number of aircraft)
#       [Encounter 1]
#           [Initial positions]
#               [Aircraft 1]
#               double (north position in feet)
#               double (east position in feet)
#               double (altitude in feet)
#               ...
#               [Aircraft n]
#               double (north position in feet)
#               double (east position in feet)
#               double (altitude in feet)
#           [Updates]
#               [Aircraft 1]
#               uint16 (number of updates)
#                   [Update 1]
#                   double (time in seconds)
#                   double (north position in feet)
#                   double (east position in feet)
#                   double (altitude in feet)
#                   ...
#                   [Update m]
#                   double (time in seconds)
#                   double (north position in feet)
#                   double (east position in feet)
#                   double (altitude in feet)
#               ...
#               [Aircraft n]
#                   ...
#       ...
#       [Encounter k]

#     WAYPOINTS STRUCTURE:
#     The waypoints structure is an m x n structure matrix, where m is the
#     number of aircraft and n is the number of encounters. This structure
#     matrix has two fields: initial and update. The initial field is a 3
#     element array specifying the north, east, and altitude. The update
#     field is a 4 x n matrix, where n is the number of updates. The rows
#     correspond to the time, north, east, and altitude position of the
#     waypoints.

import numpy as np
import pandas as pd

def load_encounters(filename, initial_dim, update_dim, num_update_type):
    file = open(filename, 'rb')
    num_encounters = np.fromfile(file, dtype=np.uint32, count=1)[0]  #int.from_bytes(file.read(4), byteorder='little', signed=False)
    num_ac = np.fromfile(file, dtype=np.uint32, count=1)[0]

    encounters = dict()
    for i in range(num_encounters):
        for j in range(num_ac):
            encounters[j, i] = dict() #Dict{String, Array{Float64, 2}}()
            encounters[j, i]["initial"] = np.fromfile(file, dtype=np.float64, count=initial_dim)

        for j in range(num_ac):
            num_update = np.fromfile(file, dtype=num_update_type, count=1)[0]
            encounters[j, i]["update"] = np.fromfile(file, dtype=np.float64, count=update_dim*num_update).reshape(num_update, update_dim)

    return [encounters, num_ac, num_encounters]


def load_waypoints(filename):
    initial_dim = 3
    update_dim = 4
    num_update_type = np.uint16
    
    return load_encounters(filename, initial_dim, update_dim, num_update_type)


def waypoints_to_df(encounters, num_encounters, num_ac):
    encounters_array = np.array([])
    for i in range(num_encounters):
        for j in range(num_ac):
            initial_pos = np.concatenate((np.array([i, j, 0]), encounters[j, i]["initial"]))
            if encounters_array.shape[0] == 0:
                encounters_array = np.append(encounters_array, initial_pos)
            else:
                encounters_array = np.vstack((encounters_array, initial_pos))
            update_pos = np.column_stack((np.repeat([[i, j]], repeats=len(encounters[j, i]["update"]), axis=0), \
                                          encounters[j, i]["update"]))
            encounters_array = np.vstack((encounters_array, update_pos))
            
    columns = ['encounter_id', 'traj_id', 'time', 'xEast', 'yNorth', 'zUp']
    encounters_df = pd.DataFrame(encounters_array, columns = columns)
    return encounters_df


if __name__ == "__main__":
    filename = "data/test_waypoint_encounters.dat"
    [encounters, num_ac, num_encounters] = load_waypoints(filename)
    
    print('Number of encounters:', num_encounters)
    print('Number of aircraft in each encounter:', num_ac)
