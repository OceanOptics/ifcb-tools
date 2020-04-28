#!/bin/zsh
# Script undoing export2ecotaxa.sh
# Move selected data (DIR_SEL/SELECTION_NAME)
#      from ecotaxa-ready zipped files (DIR_ZIP)
#      to a given directory (DIR_OUT)
# Use unzipBin2ecotaxa.sh after
# author: Nils Haentjens
# created: February 8, 2017

# Selection name
# SELECTION_NAME='niskin_AT34042'
# SELECTION_NAME='incubation_AT34041'
# SELECTION_NAME='station_inline_5'
SELECTION_NAME='inline_without_stations'
# Set directory of selection files
DIR_SEL=(~/Documents/UMaine/Lab/data/NAAMES/02_ifcb/selections/)
# Set directory of compressed data (ready for ecotaxa)
DIR_ZIP=(~/Documents/UMaine/Lab/data/NAAMES/02_ifcb/ecotaxa/import/)
# Set directory to copy bins of selection
DIR_OUT=(~/Documents/UMaine/Lab/data/NAAMES/02_ifcb/ecotaxa/inline_without_stations/)

mkdir -p $DIR_OUT$SELECTION_NAME
cd $DIR_IMG
# Loop through all tsv files
while read bin; do
  # Display bin processed
  echo $bin;
  # Move zip file
  cp $DIR_ZIP$bin'.zip' $DIR_OUT$SELECTION_NAME'/'
done < $DIR_SEL$SELECTION_NAME'.csv'
