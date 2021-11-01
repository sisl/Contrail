.. _usage:

=====
Usage
=====

The EncounterGenerationGUI (EGGUI) is designed to allow users to leverage aircraft encounter modeling
to generate large aircraft encounter data sets and interact with the generated data. 

.. _visualization:

Visualization
=====

First, let's discuss how to visualize already generated data sets using the interface. To do so,
the user will click the "Load Waypoints" button in the upper left-hand corner; this will prompt
the user to upload a waypoint file (.dat). Reference THIS DOC to understand exactly what
a waypoint file is and the required structure for the file type (.dat). 

After uploading a waypoint file, the Encounter ID dropdown menu options will update accordingly. 
The user can use the Encounter ID dropdown menu to select an encounter to visualize, which
will populate the 2d-graphs, 3d-graph, map and data table. 

There are six 2d-graphs: xEast vs yNorth, Time vs zUp, Time vs Horizontal Distance, Time vs
Vertical Distance, Time vs Horizontal Speed, and Time vs Vertical Speed. Use the scroll 
funcitonality to adjust which of the 2d-graphs you can see. There is one 3d-graph:
xEast vs yNorth vs zUp. There is a slider bar beneath these plots that enables users to step through
the waypoints in the visualized trajectories. Drag the slider to see the waypoints at a specific
time step in the encounter. 

After selecting an encounter to visualize, the user can use the Aircraft (AC) ID dropdown menu to 
select which AC IDs they would like to visualize. Default setting is to visualize both aircrafts
in the selected encounter. 

After selecting an encounter and AC IDs to visualize, the user can look at the map on the right
to see the trajectories with respect to a set reference point. Hovering the mouse over the map 
enables the user to drag the mouse to adjust the center of the map and scroll to zoom in and zoom out. 
The value for the current reference point is displayed in the grey section above the map. The reference
point is represented by latitude (°) / longitute (°) / altitude (ft) coordinates. To change the
reference point, click the "Set Reference Point" button. This will generate a popup window that
gives the user the ability to clear and set a new reference point. If cleared and never reset,
the reference point will be invalid and the user won't be able to visualize any encounters until
the reference point has a valid value. After typing in a valid value (in the form of x.x/x.x/x.x) 
for the reference point, click the "Save" button. You should see the updated reference point value in the grey section and should now be able to visualize your data again. 

The user can refer to the data table displayed below the map to see every waypoint for the visualized
aircraft trajetories. This data table is editable; for example, if you would like to change the altitude for the waypoint at time 0, click the altitude box in that row and begin typing your
desired value. Hit enter to confirm your update. After changing any value in the data table, you
must click "Update Data Table" to see your changes propogated correctly. 

.. _generation:

Generation
=====


In order to 
generate new encounters, the user must either upload a waypoint file with a preliminary set of 
aircraft encounters (.dat) or use EGGUI to create a nominal encounter with at least two aircrafts. 
The user will then select one encounter to represent the nominal encounter for the generation 
process. 

..
    goal here is to embed a video for a user to generate from a loaded in waypoints file
    and a video showing how a user could generate from a created nominal encounter

.. video:: videos/EGGUI_nominal_encounter
   :scale: 50 %
   :alt: Using EncounterGenerationGUI interface to upload/create encounters.
   :align: center



