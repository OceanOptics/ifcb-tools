IFCB Tools
==========
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8](https://img.shields.io/badge/Python-3.8-blue.svg)](https://www.python.org/downloads/)

_Set of tools to simplify interactions with IFCB data_

IFCB Tools provide tools to extract raw IFCB data to matlab files and incorporate classification from EcoTaxa (`extractIFCBdata.py`). In addition, an utility to download data from EcoTaxa is provided (`getEcoTaxa.py`).


## Installation
Install python dependencies

    pip install pandas numpy PIL beautifulsoup4 imageio
    
Download IFCB Analysis code required to extract features from the IFCB.
    
    cd ifcb-tools
    wget https://github.com/hsosik/ifcb-analysis/archive/master.zip
    unzip master.zip
    wget https://github.com/hsosik/ifcb-analysis/archive/features_v3.zip
    unzip features_v3

IFCB Analysis requirements:
  - the file `/ifcb-analysis-<branch>/feature_extraction/ModHausdorffDistMex.cpp`
  compiled for your operating system. If you are using operating system
  different than Windows 64-bits or OSX 64-bits, compile the original cpp file.
  Instructions are available [here](http://www.mathworks.com/matlabcentral/fileexchange/30108-mex-modified-hausdorff-distance-for-2d-point-sets)
  - the functions statxture, statmoments, invmoments, and bound2im from
  [DIPUM](http://www.imageprocessingplace.com/) must be present in the folder DIPUM.
  They can be downloaded [here](http://fourier.eng.hmc.edu/e161/dipum/)
  

## Usage
### getEcoTaxa.py
getEcoTaxa.py downloads projects classification from EcoTaxa. It requires the user to authentificate through his EcoTaxa account.

Usage: `getEcoTaxa.py [-h] -u USER [-p PATH] [-i IDS [IDS ...]] [-a AUTHORIZATION]`

Optional arguments:
  - `-h`, `--help`         show this help message and exit
  - `-u USER`, `--user USER`  (required) Set email of EcoTaxa account.
  - `-p PATH`, `--path PATH`  (optional) Set download directory. The download
                        directory is the directory where all files will be
                        saved.
  - `-i IDS [IDS ...], --ids IDS [IDS ...]`
                        (required) Set project identification numbers to be
                        downloaded. Multiple projects can be given (must be
                        separated by a space). If not provided all projects
                        from the EcoTaxa account are downloaded.
  - `-a AUTHORIZATION, --authorization AUTHORIZATION`
                        (optional) Provide EcoTaxa password through command
                        line. Not recommended.

Example:

    ./getEcoTaxa.py -u exampleuser@mail.edu -i 1234 4321 -p ~/Downloads/


### extractIFCBdata.py
`extractIFCBdata.py` extract raw IFCB data for machine learning training, machine learning classification, EcoTaxa, or Ecological studies.

Usage: `extractIFCBdata.py [-h] -r RAW -m ENVIRONMENTAL [-t TAXONOMY] [-e ECOTAXA] -o OUTPUT [-p] [-s SAMPLE] [-f] [-u] mode`

Positional arguments:
  - `mode`                  Set data extraction mode. Options available are: ml-
                        train, ml-classify-batch, ml-classify-rt, ecotaxa,
                        ecology.

Optional arguments:
  - `-h`, `--help`            show this help message and exit
  - `-r RAW`, `--raw RAW`     Set path to raw IFCB directory (adc, hdr, and roi
                        files).
  - `-m ENVIRONMENTAL`, `--environmental ENVIRONMENTAL`
                        Set path to environmental metadata file.
  - `-t TAXONOMY`, `--taxonomy TAXONOMY`
                        Set path to taxonomic grouping file.
  - `-e ECOTAXA`, `--ecotaxa ECOTAXA`
                        Set path to EcoTaxa classification directory or file.
  - `-o OUTPUT`, `--output OUTPUT`
                        Set path to directory of formatted output data.
  - `-p`, `--parallel`        Enable Matlab parallel processing.
  - `-s SAMPLE`, `--sample SAMPLE`
                        Set sample to process in mode ml-classify-rt.
  - `-f`, `--force`           Force update of all data in mode ecology.
  - `-u`, `--update-classification`
                        Update classification data in mode ecology.
