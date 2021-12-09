.. _readme-contrail:

.. image:: docs/images/contrail_logo_background.png
   :width: 250
******************

Interface for modeling, generating, visualizing and saving aircraft encounter data sets.

.. _contrail-overview:

Overview
===============

Aircraft encounter modeling allows users to represent aircraft behavior using statistical models. 

Contrail's intended purpose is for users to model, generate, visualize and save large 
encounter data sets in order to develop and verify aircraft collision avoidance software. 
For a more detailed explanation on the usage of this product, please refer to
`usage.rst <https://github.com/sisl/Contrail/blob/main/docs/source/usage.rst>`_. 

After installation, refer to `tutorial.rst <https://github.com/sisl/Contrail/blob/main/docs/source/tutorial.rst>`_ for a
detailed explanation on how to run and use the tool.

.. _contrail-intallation:

Installation
===============

``pip install git+https://github.com/sisl/Contrail``

to install Contrail as a package.

Additionally, you can clone the Contrail repository to your local computer and open/run it in an IDE. The
`tutorial.rst <https://github.com/sisl/Contrail/blob/main/docs/source/tutorial.rst>`_ assumes that you have
done this step.

.. _contrail-dependencies:

Dependencies
===============
If you clone the repository (do not install it as a package), install the environment requirements with pip

``pip install -r requirements.txt``

Best practice is to install the requirements in a Python virtual environment and run Contrail in that venv to avoid any version issues.

