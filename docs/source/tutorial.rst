.. _tutorial:

Tutorial
******************

.. _tutorial-introduction:

*This tutorial is up-to-date for version `0`*

Introduction
======================

This tutorial is intended for readers to learn how to use the Contrail tool on their own device. 
Familiarity with the underlying aircraft encounter modeling theory is recommended, 
but is not strictly necessary for use. Please download/install the package before proceeding. 
For help with installation, please refer to the README:ref:'readme-aem'.

.. _tutorial-visualization:

Preliminary Steps
======================

If you are having issues running the package locally, follow these steps to troubleshoot:

#. Confirm you have downloaded the lastest version of the Contrail repository to your local computer
#. Using any Terminal instance, step into the /scr folder within the directory of your local repository
#. Enter 'python run.py' into the command line
#. Command click on the http address displayed to open the interface in your preferred browser

After following these steps, you should have Contrail open in the browser of your choosing. As long
as the terminal instance in which you performed step 3 stays active, you will be able to use the tool. To
restart the tool, ctrl-c in the running terminal instance and rerun step 3.

Style Guide
======================
* The names of clickable items (aka buttons and dropdown menus) will be *italicized* for readability
* 

Visualization
======================

Now, let's discuss how to visualize already generated data sets using the interface. 

Steps to Set Up Visualization:
-------------------------------

#. Click *Load Waypoints* which will prompt you to upload a waypoint file
#. Upload the provided test_waypoint.dat file or any generated (.dat) file located in the /data folder of your repository
#. Click *Encounter ID* menu to select an encounter to visualize. This will populate the 2d-graphs, 3-graph, map and data table.
#. Use the *Aircraft ID* menu to select the AC IDs you would like to visualize. Default setting is to visualize both 
   aircrafts in the selected encounter.
#. Explore the components of the home page!

Understanding the Components of the Home Page:
--------------------------------------------------------------

* **2D-GRAPHS**: xEast vs yNorth, Time vs zUp, Time vs Horizontal Distance, Time vs Vertical Distance, Time vs Horizontal Speed, and 
  Time vs Vertical Speed. 

  * Use the scroll funcitonality to the right of the graphs to adjust which of the 2d-graphs you can see. 
  * Drag the slider bar beneath these plots to step through the waypoints in the visualized trajectories. 

* **3D-GRAPH**: xEast vs yNorth vs zUp. 
  
  * Use the tabs to switch back and forth between visualizing the 2d and 3d graphs. 
  
* **MAP**: displays the selected trajecotries with respect to a set reference point.

  * Hovering the mouse over the map enables the click-and-drag functionality to adjust the center of the map and scroll to zoom 
    in and zoom out. 
  
* **REFERENCE POINT**: represented by latitude (°) / longitute (°) / altitude (ft) coordinates.
   
  * To change it, click *Set Reference Point*. This will generate a popup window that gives you the ability to clear and set 
    a new reference point. If cleared and never reset, the reference point will be invalid and you won't be able to visualize 
    any encounters.
  * Must type in a valid reference point value in the form x.x/x.x/x.x and click *Save* in order to begin visualizing again.
  * See the current reference point value in the grey section above the map.

* **DATA TABLE**: displays every waypoint for the visualized aircraft trajectories.

  * This data table is editable.
  
    * To change the altitude for the waypoint at time 0, click the altitude box in that row and begin typing your desired value and hit enter to confirm your update.

      * Must click *Update Data Table* to see your changes propogated correctly.
  
    * To add a waypoint to any exisitng AC trajectory, click *Add Row* to create an empty row in which you can input the AC ID 
      and fill in the rest of the columns with your desired values.

      * Must click *Update Speeds* after adding any new waypoints to see your changes propogated correctly.

.. _tutorial_create_mode:

Create Mode
======================

Contrail provides users with a Create Mode that allows them to forgo uploading a waypoint 
file and instead directly create a nominal encounter. 

To enter Create Mode, click *Enter Create Mode* below the map. 

Steps for Nominal Path Creation:
-------------------------------------

#. Click *Start New Nominal Path*.

   #. Input the AC ID for which you are creating a trajectory. This AC ID must be unique with respect to the other AC IDs in your nominal encounter, and all AC IDs must be in sequential, increasing order starting at 1.
   #. Input the desired time interval between waypoints (this can either be constant for your entire trajectory or you can change it from waypoint to waypoint).
   #. Input the zUp value for your first waypoint.
  
#. After setting those three values, you can begin creating a trajectory for your nominal encounter:

   #. Double click on the map; this will create a blue tool tip representing the location of your new waypoint. You can click-and-drag the tool tip to adjust its exact location. Refer to the data table below to confirm that your new waypoint is in the correct position. 
   #. Repeat this process until you have created all of the waypoints that you want for the current trajectory. 
   #. Click *Save Nominal Path* when you are satisfied with the nominal path created.
  
#. Repeat this process until you have created two nominal paths inside of one nominal encounter.
    
Click *Exit Create Mode* to leave create mode. You can visualize your nominal encounter in the same way 
described in the Visualization section above. 

You CANNOT edit the data table directly when in create mode - please do so
after exiting create mode. 

.. _tutorial_generation:

Generation
======================

In order to generate new encounters, you must have either uploaded a waypoint file or used Create Mode
to create a nominal encounter with at least two aircrafts. 

Steps to Generate an Encounter Set:
-------------------------------------

#. Click the *Generate Encounter Set*. This will trigger a popup window. 
#. Either load in a predefined model or input the necessary values for a new generation model. 


How to Create a New Generation Model:
-------------------------------------

#. Select a nominal encounter.
#. Select which AC IDs you would like to generate from
   
   * If you only select one AC ID, then the generated data will not be of encounters but rather single aircraft trajectories. 

#. Select which generation protocol you would like to use. 
   
   * Currently, the tool defines diagonal covariance and exponential kernal covariance models. The waypoints of the trajectories in this selected nominal encounter will serve as the mean values for these multivariate probability distributions during generation.

#. Indicate how many encounters you would like to generate using the model you just defined.
#. Click *Generate*. 

You will be redirected back to the home page where you will see a spinner in the center of the screen; the 
spinner will continue to spin until the generation process has completed. Once the spinner disappears,
you can click on the *Encounter ID* dropdown menu to confirm the generation process worked correctly. If you see 
a Nominal Encounter and the correct number of encounters avaliable in the dropdown menu, then the process was successful. 

Visualize your newly generated data using the same technique described in the Visualization section above. 

Statistics
-------------------------------------

Click over to the statistics tab for information on your newly generated encounter set.

As of version 0.0.0, the statistics tab only displays 2d-histograms for xEast vs yNorth and Time vs zUp 
for both AC IDs in the generated data. 


.. _tutorial_saving:

Saving
======================

Contrail allows users to save both generated data sets (generated_waypoints.dat) and previously used 
generation models (generated_model.json).

Refer to :ref:`Waypoints Overview <t2waypoints:waypoints-overview>` for the structure of a waypoint file. 

Refer to :ref:`Generation Model Overview <t2generation-model:generation-model-overview>` for the structure of a generation model file.

Steps to Save Waypoints and Models:
-------------------------------------

#. Click *Save Waypoints (.dat) or Model (.json)*
   * This will trigger a popup window where you can select whether you'd like to save the generated waypoints, the generation model, or both. 
#. Fill in the names for the desired files and then click *Save.* 
   * This will automatically save the waypoint files to the scr/data folder and the generation models to the scr/models folder within the local repository. 
   *  If the files are not too large, the browser will also present the files as a download. 

You can only save after generating a data set, not after uploading a waypoints file or creating a nominal encounter.