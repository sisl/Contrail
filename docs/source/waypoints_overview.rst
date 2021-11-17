.. _waypoints-overview:

Waypoints Overview
******************

.. _waypoint-description:

File Description
================

The waypoints file contains a set of encounters. Each encounter is
defined by a set of waypoints associated with a fixed number of
aircraft. The waypoints are positions in space according to a fixed,
global coordinate system. All distances are in feet. Time is specified
in seconds since the beginning of the encounter. 

.. _waypoint-structure:

File Structure
===============

The file is organized as follows::

    [Header]
    uint32 (number of encounters)
    uint32 (number of aircraft)
    [Encounter 1]
        [Initial positions]
            [Aircraft 1]
            double (north position in feet)
            double (east position in feet)
            double (altitude in feet)
            ...
            [Aircraft n]
            double (north position in feet)
            double (east position in feet)
            double (altitude in feet)
        [Updates]
            [Aircraft 1]
            uint16 (number of updates)
                [Update 1]
                double (time in seconds)
                double (north position in feet)
                double (east position in feet)
                double (altitude in feet)
                ...
                [Update m]
                double (time in seconds)
                double (north position in feet)
                double (east position in feet)
                double (altitude in feet)
            ...
            [Aircraft n]
                ...
    ...
    [Encounter k]

