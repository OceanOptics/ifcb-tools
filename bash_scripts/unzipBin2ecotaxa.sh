#!/bin/zsh
# Unzip each bin in a directory
# separating images and tsv files from zip
# author: Nils Haentjens
# created: February 8, 2017

# Set directory of files to unzip
# /**/*(.) -> process all files recursively
# DIR_IN=(~/Documents/UMaine/Lab/data/NAAMES/02_ifcb/ecotaxa/inline_without_stations/**/*(.))
DIR_IN=(~/Documents/UMaine/Lab/data/NAAMES/01_ifcb/ecotaxa/import/*(.))

# Loop through all stations
for file in $DIR_IN; do
  # Display bin processed
  echo ${file:(-28):24};
  # Go to good directory
  cd ${file:0:-28};
  # UnCompress input
  unzip -q $file
  # Remove zip file
  rm $file
done
