.. _readme-contrail:

Contrail
******************
Interface for modeling, generating, visualizing and saving aircraft encounter data sets.

.. _contrail-overview:

Overview
===============

Aircraft encounter modeling allows users to represent aircraft behavior using statistical models. 

Contrail's intended purpose is for users to model, generate, visualize and save large 
encounter data sets in order to develop and verify aircraft collision avoidance software. 
For a more detailed explanation on the usage of this product, please refer to USAGE LINK. 

.. _contrail-intallation:

Installation
===============

``pip install git+https://github.com/sisl/Contrail``

.. _contrail-dependencies:

Dependencies
===============
Install requirements with pip

``pip install -r requirements.txt``
``pip install -e .``


..
    //A major 
    use case is leveraging models for how aircraft behave during close encounters to create a
    realistic set of flight dynamics where an aircraft collision avoidance system 
    would likely alert. These data sets can then be used to verify some collision avoidance software.