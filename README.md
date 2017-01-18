easyIFCB
========

The purpose of this set of code is to process Imaging Flow CytoBot (IFCB)
raw data in order to upload it on EcoTaxa.

EcoTaxa takes in input a `.tsv` file containing a set of features caracterizing
the images of phytoplankton captured by the IFCB. The IFCB output is a set of
`.roi`, `.adc` and `.hdr` files containing the images of phytoplankton
and some metadata.

The first step is to separate the phytoplankton from the background of the picture,
this step is called blob extraction. The second step consist in characterizing
this region with a set of parameters, this is known as the feature extraction
and requires the blobs. In order to visualize the features in EcoTaxa,
images needs to be extracted from the .roi files (with the help of the .adc)
and converted to png.

This is exactly what the software is developped for with the help of the
udge matlab library from Heidi M. Sosik: IFCB_analysis.

### Quick start protocol
  - First clean the dataset:
    - no empty files
    - no missing files: need all trio of .roi, .adc and .hdr
    - all the raw/ifcb data in one folder (no subfolder)
    - one clean metadata.csv file (see section metadata)
  - Set configuration file based on default.cfg:
    - Copy and rename default.cfg file
    - Edit that new file with your favorite text editor (Sublime Text, Matlab...)
    - Follow comments in the file and feel all the fields
    - To export data to EcoTaxa the following parameters need to be true:
      - `process.blobs=true`
      - `process.features=true`
      - `process.images=true`
      - `process.ecotaxa=true`
      - `process.classification` can be either `true` or `false`;
          it is not needed by EcoTaxa
  - Process the IFCB data in Matlab:
      - in `main.m` set the name of the configuration file prepared ealier line 17:
          cfg.filename = 'my_new_configuration_file.cfg'
      - run the script `main.m` (cmd+alt+R), this step can take few
        minutes to days depending on the amount of data to process, the
        number of core available on the computer used, and the speed of
        the harddrive/SSD. The software will also generate a lot of data
        (especially, the computation of features and the generation of images).
      - At the end you should have one "big" tsv file and a folder of images
        both located as specified in the configuration file.
  - Export to EcoTaxa
    - Set the location of the configuration file in `main.m`
    - Run `main.m`, it will take few minutes to hours depending on the size of
    the dataset beeing processed, the following step are runned:
        - Blobs extraction
        - Features extraction
        - Images extraction
        - Export to EcoTaxa format

### Installation
easyIFCB was developped and tested on Matlab 2016 a and b, earlier version
of Matlab should work but some unexpected behaviour might be observed.
If you can make sure that you run the proper Matlab version.

easyIFCB is built on top of the IFCB_analysis toolbox available on github.
To download IFCB_analysis toolbox, in your terminal go to an appropriate directory and download
the latest version of the repository (make sure that [git is installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
on your computer, if you do not know how to use this version control tool,
please check the chapter 1 and 2 of this [book](https://git-scm.com/book/en/v2)).

    cd  ~/Documents/MATLAB/
    git clone https://github.com/hsosik/ifcb-analysis.git

IFCB_analysis evolves very quickly thereafter if the latest version of the
code does not run please download the version `e9e37998a8bb8caf587b19418202b650ba0b99f2` of the toolbox:

    git clone https://github.com/hsosik/ifcb-analysis.git <my_repository>
    cd <my_repository>
    git reset --hard e9e37998a8bb8caf587b19418202b650ba0b99f2

IFCB_analysis toolbox requires:
  - the file `/ifcb-analysis/feature_extraction/ModHausdorffDistMex.cpp`
  compiled for your operating system. If you are using operating system
  different than Windows 64-bits or OSX 64-bits, compile the original cpp file.
  Instructions are available [here](http://www.mathworks.com/matlabcentral/fileexchange/30108-mex-modified-hausdorff-distance-for-2d-point-sets)
  - the functions statxture, statmoments, invmoments, and bound2im from
  [DIPUM](http://www.imageprocessingplace.com/) in your path, the functions can
  be downloaded [here](http://fourier.eng.hmc.edu/e161/dipum/)

To download easyIFCB:

    cd ~/Documents/MATLAB/
    git clone git@github.com:OceanOptics/easyIFCB.git


### Selections
An option is available to process only selected bins listed in a file.
This file should be located in the directory indicated at
cfg.path.selection and the name of the file is specified in
cfg.process.selection. By default `cfg.process.selection='all'` which
means that all the bin present in the directory are processed. This file
should contain a list of bin names, one per line. The bin name should be
formated as follow: D<YYYYMMDD>T<hhmmss>_IFCB<###>

This feature allow to process only a subset of data at a time possibly correspoding to a station or an experiment.


### Metadata
A metadata file should be joined to the IFCB data to export it to EcoTaxa.
The location of the metadata file is indicated in the configuration in the
section path under the attribute meta. The metadata file is a csv
(comma separated value) file composed of the columns listed below.
The four first elements are mandatory (bin_id, lat, lon, and depth).

  - bin identification number <D<YYYYMMDD>T<hhmmss>_IFCB<###>>
  - latitude <float or NaN> (decimal degree)
  - longitude <float or NaN> (decimal degree)
  - depth <float or NaN> (meters)
  - concentration factor <float or NaN> (no units)
  - flag <int or NaN> (1:good, 2:partial sample (not valid for quantification), 4:bad sample)
  - sample type <string or empty> (inline, niskin, or incubation)
  - sample id <string or empty> (CTD cast identification number)
  - comments <string or empty>:
    - it can be any kind of text in lower case without special caracters
    - it can be any supplementary field separated by ;
       - stn_id=##; cast_id=##; niskin_id=##
       - T0/Tf=##; dillution=###; bottle_id=###

Example of file content:

    D20160524T084849_IFCB107, 47.6530, -39.1180,   5, 1.0, 1, inline, ,
    D20160524T120438_IFCB107, 47.6320, -39.0540,  10, 1.0, 1, niskin, AT34023, stn_id=4; cast_id=1; niskin_id=21
    D20160524T124359_IFCB107, 47.6320, -39.0540,   6, 1.0, 1, niskin, AT34023, stn_id=4; cast_id=1; niskin_id=22
    D20160524T134109_IFCB107, 47.6320, -39.0540,   5, 1.0, 1, inline, ,
    D20160524T140437_IFCB107, 47.6310, -39.0530, NaN, NaN, 1, incubation, AT34020, T0/Tf=Tf; dillution=100; bottle_id=5
    D20160524T143158_IFCB107, 47.6290, -39.0530, NaN, NaN, 1, incubation, AT34020, T0/Tf=Tf; dillution=20; bottle_id=5

