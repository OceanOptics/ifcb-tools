IFCB to EcoTaxa
===============

The purpose of this set of code is to convert IFCB (Imaging Flow CytoBot)
raw data to input for EcoTaxa. This is based on Pierre-Luc Grandin matlab code
and require the IFCB_analysis toolbox from Heidi M. Sosik.

### General workflow
EcoTaxa takes in input a ".tsv" file containing a set of features caracterizing
the images of phytoplankton. The IFCB output is a set of ".roi", ".adc" and
".hdr" files containing the images of phytoplankton.

The goal is to separate the phytoplankton from the background of the picture,
this step is called blob extraction. The second step consist in characterizing
this region with a set of parameters, this is what is the feature extraction.

In order to visualize the image in EcoTaxa and not only have a set of features,
the images needs to be exported in png.

### Steps to follow
  - Clean the dataset first:
    - no empty files
    - no missing files: need all .roi, .adc and .hdr
    - GPS coordinates are in a .csv file with four columns:
        - time (yyyy/mm/dd HH:MM:SS)
        - lat (DD.DDDD North)
        - lon (DD.DDDD East)
        - depth (meters)
  - Configuration:
    - Set metadata and processing informations
    - Set the input, working and output directory in `default.cfg`
    - Set location of IFCB_analysis code
    - Enable/Disable parallel computing (default=false)
  - Export to EcoTaxa
    - Set the location of the configuration file in `main.m`
    - Run `main.m`, it will take few minutes to hours depending on the size of
    the dataset beeing processed, the following step are runned:
        - Blobs extraction
        - Features extraction
        - Images extraction
        - Export to EcoTaxa format

### Installation
IFCB_analysis toolbox from Heidi M. Sosik requires:
  - the file `/ifcb-analysis/feature_extraction/ModHausdorffDistMex.cpp`
  compiled for your operating system. If you are using operating system
  different than Windows 64-bits or OSX 64-bits, compile the original cpp file. Instructions are available [here](http://www.mathworks.com/matlabcentral/fileexchange/30108-mex-modified-hausdorff-distance-for-2d-point-sets)
  - the functions statxture, statmoments, invmoments, and bound2im from
  [DIPUM](http://www.imageprocessingplace.com/) in your path, the functions can
  be downloaded [here](http://fourier.eng.hmc.edu/e161/dipum/)

