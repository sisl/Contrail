.. _tutorial-tutorial:

Tutorial
******************
.. _tutorial-introduction:

*This tutorial is up-to-date for version `0`*

1 Introduction
===============

This tutorial is intended for readers to learn how to use this package on their own device. Familiarity with the underlying theory is recommended, but is not strictly necessary for use. Please install the package before proceeding.

.. _tutorial-about-ast:

1.1 About Aircraft Encounter Modeling
-----------------

SOME THINGS HERE

A few things will be needed:

* note 
* note
* note
* note

.. _tutorial-visualization:

2 Visualization
======================

First, let's discuss how to visualize already generated data sets using the interface. To do so,
click the "Load Waypoints" button in the upper left-hand corner; this will prompt
you to upload a waypoint file (.dat). Reference THIS DOC to understand exactly what
a waypoint file is and the required structure for the file type (.dat). 

After uploading a waypoint file, the Encounter (ENC) ID dropdown menu options will update accordingly. 
You can use the ENC ID dropdown menu to select an encounter to visualize, which
will populate the 2d-graphs, 3d-graph, map and data table. 

There are six 2d-graphs: xEast vs yNorth, Time vs zUp, Time vs Horizontal Distance, Time vs
Vertical Distance, Time vs Horizontal Speed, and Time vs Vertical Speed. Use the scroll 
funcitonality to adjust which of the 2d-graphs you can see. There is one 3d-graph:
xEast vs yNorth vs zUp. Use the tabs to switch back and forth between the 2d and 2d graphs.
There is a slider bar beneath these plots that enables users to step through
the waypoints in the visualized trajectories. Drag the slider to see the waypoints at a specific
time step in the encounter. 

After selecting an encounter to visualize, you can use the Aircraft (AC) ID dropdown menu to 
select which AC IDs they would like to visualize. Default setting is to visualize both aircrafts
in the selected encounter. 

After selecting an ENC ID and AC IDs to visualize, you can look at the map on the right
to see the trajectories with respect to a set reference point. The value for the current reference 
point is displayed in the grey section above the map. The reference point is represented by 
latitude (°) / longitute (°) / altitude (ft) coordinates. To change the
reference point, click the "Set Reference Point" button. This will generate a popup window that
gives you the ability to clear and set a new reference point. If cleared and never reset,
the reference point will be invalid and you won't be able to visualize any encounters. 
You must type in a valid reference point value in the form x.x/x.x/x.x and click the "Save" button 
in order to begin visualizing again. You should see the updated reference point value in the grey section
above the map. Lastly, hovering the mouse over the map enables you to click-and-drag the mouse to adjust 
the center of the map and scroll to zoom in and zoom out. 

You can refer to the data table displayed below the map to see every waypoint for the visualized
aircraft trajetories. This data table is editable; for example, if you would like to change the 
altitude for the waypoint at time 0, click the altitude box in that row and begin typing your
desired value. Hit enter to confirm your update. After changing any value in the data table, you
must click "Update Data Table" below the table to see your changes propogated correctly. You can
also add a waypoint to any existing AC trajectory. Click the "Add Row" button below the table to create
an empty row. Input the AC ID for the AC trajectory you would like to add to and fill in the
rest of the columns with your desired values. You must click "Update Speeds" after adding any new
waypoints to see your changes propogated correctly.

.. _tutorial_create_mode:

2 Create Mode
======================

EGGUI provides users with a create mode functionality that allows them to forgo uploading a waypoint 
file and instead directly create a nominal encounter. 

To enter create mode, click the "Enter Create Mode" button below the map on the right side. 

Nominal Path Creation:

- To create a new nominal path (trajectory), click "Start New Nominal Path." First, indicate the 
  also AC ID for which you are creating a trajectory. This AC ID must be unique with respect to the other
  AC IDs in your nominal encounter, and all AC IDs must be in sequential, increasing order starting at 1. Next, 
  indicate your desired time interval between waypoints (this can either be consistent for your entire trajectory 
  or you can change it from waypoint to waypoint). Lastly, input the zUp value for your first waypoint.

- After setting those three values, you can begin creating a trajectory for your nominal encounter. Use your mouse
  to double click on the map; this will create a blue tool tip representing the location of your waypoint. You can 
  click-and-drag the tool tip to adjust its exact location. Refer to the data table below to confirm that your new
  waypoint is in the correct position. Repeat this process until you have created all of the waypoints that you
  want for the current trajectory. Click "Save Nominal Path" when you are satisfied with the nominal path created.

- Repeat this process until you have created two nominal paths.
    
Click the "Exit Create Mode" button to leave create mode. You can visualize your nominal encounter in the same way 
described in the Visualization section of this doc. 

You CANNOT edit the data table directly when in create mode - please do so
after exiting create mode. 

.. _tutorial_generation:

2 Generation
======================

In order to generate new encounters, the user must have either uploaded a waypoint file or used EGGUI 
to create a nominal encounter with at least two aircrafts. 

To generate an encounter set, click the "Generate Encounter Set" button located in the top-left corner.
This will trigger a popup window. You will get the option of either loading in a predefined model or 
inputting values for a new generation model. Let's consider the latter option first.

To create a new generation model, you must first select a nominal encounter. The waypoints of the
trajectories in this encounter will serve as the mean waypoints during generation. Next, select
which AC IDs you would like to generate from (if you only select one AC ID, then the generated data
will not be of encounters but rather single aircraft trajectories). 

Next, you will select which generation protocol you would like to use. HERE IS A DIAGONAL COVARIENCE 
EXPLANATION. HERE IS A KERNEL COVARIENCE EXPLANATION. 

Lastly, indicate how many encounters you would like to generate using the model you just defined, and
click "Generate." You will be redirected back to the home page where you will see a spinner - the 
spinner will continue to spin until the generation process has been completed. Once the spinner disappears,
you can click on the ENC ID dropdown menu to confirm the generation process worked correctly. If you see 
that the number of encounters avaliable in the dropdown menu equals the number of encounters you hoped to
generate, then the process was successful. 

.. _tutorial_saving:

2 Saving
======================


The EGGUI allows users to save both generated data sets (.dat) and previously used generation models (.json).
You can refer to THIS DOC for what a generation model is and how it is structured. 

You can only save after generating a data set. 

To save, click the "Save Waypoints (.dat) or Model (.json)" button on the top-left corner. This will trigger
a popup window where you can select whether you'd like to save the generated waypoints, the generation model,
or both. Fill in the names for those files and then click "Save." This will automatically save the waypoint files 
to the scr/data folder and the generation models to the scr/models folder within the local repository. If the
files are not too large, the browser will also present the files as a download. 

LEAD USERS TO THE PAGE DESCRIBING HOW THE SETTINGS PAGE WORKS.

..
    goal here is to embed a video for a user to generate from a loaded in waypoints file
    and a video showing how a user could generate from a created nominal encounter

  .. video:: videos/EGGUI_nominal_encounter
     :scale: 50 %
     :alt: Using EncounterGenerationGUI interface to upload/create encounters.
     :align: center



