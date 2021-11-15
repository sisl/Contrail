.. _generation-model-overview:

Generation Model Overview
************************************

.. _model-description:

File Description
=================

The generation model file contains information about the nominal encounter and statistical
model previously used to generate an encounter data set. 

.. _model-structure:

File Structure
=================

The file is organized as follows:

{
    "mean" : {
        "num_ac" : n,
        "1" : {
            "num_waypoints" : m,
            "waypoints" : [
                {
                    "time": time_0,
                    "xEast": xEast_0,
                    "yNorth": yNorth_0,
                    "zUp": zUp_0
                },
                ...
                {
                    "time": time_m,
                    "xEast": xEast_m,
                    "yNorth": yNorth_m,
                    "zUp": zUp_m
                }
            ]
        },
        ...
        "n" : {
            "num_waypoints" : m,
            "waypoints" : [
                {
                    "time": time_0,
                    "xEast": xEast_0,
                    "yNorth": yNorth_0,
                    "zUp": zUp_0
                },
                ...
                {
                    "time": time_m,
                    "xEast": xEast_m,
                    "yNorth": yNorth_m,
                    "zUp": zUp_m
                }
            ]
        }
    },
    "covariance" : {
        *refer below for different covariance options*
    }
}

where time_0, xEast_0, yNorth_0 and zUp_0 refer to the initial waypoint values
and time_m, xEast_m, yNorth_m, and zUp_m refer to the mth (final) waypoint values for the specified aircraft.


.. _model-covariance_options:

Covariance Options
==================

"covariance" : {
    "type" : "diagonal",
    "sigma_hor": 0.05,
    "sigma_ver": 10
}

OR

"covariance": {
        "type": "exponential kernel",
        "a": 15,
        "b": 1,
        "c": 100
    }
