.. _tutorial:

Tutorial
**********

.. _tutorial-introduction:

*This tutorial is up-to-date for version `0.0.0`*

Introduction
======================

This tutorial is intended for readers to learn how to use the Contrail tool on their own device. 
Familiarity with the underlying aircraft encounter modeling theory is recommended, 
but is not strictly necessary for use. Please install the repository before proceeding. 
For help with installation, please refer to the `README <https://github.com/sisl/Contrail/blob/main/README.rst>`_.


There are 6 parts to this tutorial. Familiarize yourself with all portions before using the tool:

#. `Preliminary Steps`_
#. `Style Guide`_
#. `Visualization`_
#. `Create Mode`_
#. `Generation`_
#. `Saving`_


.. _tutorial-preliminary-steps:

Preliminary Steps
======================

If you are having issues running the package locally, follow these steps to troubleshoot:

#. Confirm you have downloaded the latest version of the Contrail repository to your local computer.
#. Using any Terminal instance, step into the contrail/scr folder within the directory of your local repository.
#. Enter 'python -Wignore run.py' into the command line.

   * Running Contrail with the -Wignore flag will block any warnings related to deprecated dash component versions
  
#. Command click on the http address displayed to open the interface in your preferred browser.

After following these steps, you should have Contrail open in the browser of your choice. As long
as the terminal instance in which you performed step 3 stays active, you will be able to use the tool. To
restart the tool, hit ctrl-c in the running terminal instance and rerun step 3 or just refresh the browser.

.. _tutorial-style-guide:

Style Guide
======================
* The names of clickable items (e.g. buttons and dropdown menus) will be *italicized* for readability

.. _tutorial-visualization:

Visualization
======================

Now, let's discuss how to visualize already generated data sets using the interface. 

Steps to Set Up Visualization:
-------------------------------

#. Click *Load Waypoints*, which will prompt you to upload a waypoint file.
#. Upload the provided test_waypoint.dat file or any generated (.dat) file located in the scr/data folder of your repository.
#. Click the *Encounter ID* menu to select an encounter to visualize. This will populate the 2d-graphs, 3d-graph, map and data table.
#. Use the *Aircraft ID* menu to select the AC IDs you would like to visualize. The default setting is to visualize both 
   aircrafts in the selected encounter.
#. Explore the components of the home page!

Understanding the Components of the Home Page:
--------------------------------------------------------------

* **2D-GRAPHS**: xEast vs. yNorth, Time vs. zUp, Time vs. Horizontal Distance, Time vs. Vertical Distance, Time vs. Horizontal Speed, and 
  Time vs. Vertical Speed. 

  * Use the scroll bar to the right of the graphs to adjust which of the 2d-graphs you can see. 
  * Drag the slider bar above these plots to step through the waypoints in the visualized trajectories. 

* **3D-GRAPH**: xEast vs. yNorth vs. zUp. 
  
  * Use the tabs to switch back and forth between visualizing the 2d- and 3d-graphs. 
  
* **MAP**: displays the selected trajectories with respect to a set reference point.

  * Hovering the mouse over the map enables the click-and-drag functionality to adjust the center of the map and scroll to zoom 
    in and zoom out. 
  
* **REFERENCE POINT**: represented by latitude (??N) / longitude (??E) / altitude (ft) coordinates.
   
  * To change it, click *Set Reference Point*. This will generate a popup window that gives you the ability to clear and set 
    a new reference point. If cleared and never reset, the reference point will be invalid and you won't be able to visualize 
    any encounters.
  * You must type in a valid reference point value in the form x.x/x.x/x.x and click *Save* in order to begin visualizing again.
  * View the current reference point value in the grey section above the map.

* **DATA TABLE**: displays every waypoint for the visualized aircraft trajectories.

  * This data table is editable.
  
    * To change the altitude for the waypoint at time 0, click the altitude box in that row, begin typing your desired value, and hit enter 
      to confirm your update.

      * Click *Update Data Table* to see your changes propagated correctly.
  
    * To add a waypoint to any existng AC trajectory, click *Add Row* to create an empty row in which you can input the AC ID 
      and fill in the rest of the columns with your desired values.

      * Click *Update Speeds* after adding any new waypoints to see your changes propagated correctly.

.. _tutorial_create_mode:

Create Mode
======================

Contrail provides users with a Create Mode that allows them to forgo uploading a waypoint 
file and directly create a nominal encounter instead. 

To enter Create Mode, click *Enter Create Mode* below the map. 

Steps for Nominal Path Creation:
-------------------------------------

#. Click *Start New Nominal Path*.

   #. Input the AC ID for which you are creating a trajectory. This AC ID must be unique with respect to the other AC IDs in your nominal 
      encounter, and all AC IDs must be in sequential, increasing order starting at 1.
   #. Input the desired time interval between waypoints (this can either be constant for your entire trajectory or you can change it from 
      waypoint to waypoint).
   #. Input the zUp value for your first waypoint.
  
#. After setting those three values, you can begin creating a trajectory for your nominal encounter:

   #. Double click on the map; this will create a blue tool tip representing the location of your new waypoint. You can click-and-drag 
      the tool tip to adjust its exact location. Refer to the data table below to confirm that your new waypoint is in the correct position. 
   #. Repeat this process until you have created all of the waypoints that you want for the current trajectory. 
   #. Click *Save Nominal Path* when you are satisfied with the nominal path created.
  
#. Repeat this process until you have created two nominal paths inside of one nominal encounter.
    
Click *Exit Create Mode* to leave create mode. You can visualize your nominal encounter in the same way 
described in the `Visualization`_ section above. 

You CANNOT edit the data table directly when in create mode, but can do so
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
#. Select the AC IDs you would like to generate from.
   
   * If you only select one AC ID, then the generated data will not include encounters but rather single aircraft trajectories. 

#. Select which statistical model you would like to use. 
   
   * Currently, the tool defines a multivariate Gaussian distribution with either a diagonal covariance or exponential kernel covariance matrix. 
     Enter the parameters for whichever model you choose. 
     The waypoints of the trajectories in this selected nominal encounter will serve as the mean values for the multivariate probability 
     distribution during generation.

#. Indicate how many encounters you would like to generate using the model you just defined. Recommend generating at least 1000 encounters.
#. Click *Generate*. 

You will be redirected back to the home page where you will see a spinner in the navbar; the 
spinner will continue to spin until the generation process has completed. Once the spinner disappears,
you can click on the *Encounter ID* dropdown menu to confirm the generation process worked correctly. If you see 
a Nominal Encounter and the correct number of encounters available in the dropdown menu, then the process was successful. 

Visualize your newly generated data using the same technique described in the `Visualization`_ section above. 

Statistics
-------------------------------------

Click over to the statistics tab using the toggle on the top right corner of the app for information on your newly generated encounter set.

As of version 0.0.0, the statistics tab only displays 2d-histograms for xEast vs. yNorth and Time vs. zUp 
for both AC IDs in the generated data. 


.. _tutorial_saving:

Saving
======================

Contrail allows users to save both generated data sets (generated_waypoints.dat) and previously used 
generation models (generated_model.json).

Refer to `waypoints_overview.rst <https://github.com/sisl/Contrail/blob/main/docs/source/waypoints_overview.rst>`_ for the 
structure of a waypoint file. 

Refer to `generation_model_overview.rst <https://github.com/sisl/Contrail/blob/main/docs/source/generation_model_overview.rst>`_ 
for the structure of a generation model file.

Steps to Save Waypoints and Models:
-------------------------------------

#. Click *Save Waypoints (.dat) or Model (.json)*
   
   * This will trigger a popup window where you can select whether you'd like to save the generated waypoints, the generation model, or both. 

#. Fill in the names for the desired files.
#. Click *Save*.
   
   * This will automatically save the waypoint files to the contrail/scr/data folder and the generation models to the contrail/scr/models folder within the local repository. 
   * If the files are not too large, the browser will also present the files as a download. 

You can only save after generating a data set, not after uploading a waypoints file or creating a nominal encounter.
