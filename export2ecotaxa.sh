#!/bin/zsh
# Script moving all tsv files in images bin and zipping them
# author: Nils Haentjens
# created: January 24, 2017

# Set directory of ecotaxa tsv files
DIR_TSV=(~/Documents/MATLAB/IFCB/training_test_data/ecotaxa/tsv/*(.))
# Set directory of ecotaxa images
DIR_IMG=(~/Documents/MATLAB/IFCB/training_test_data/images/)
# Set directory to compressed data ready for ecotaxa
DIR_OUT=(~/Documents/MATLAB/IFCB/training_test_data/import/)

mkdir -p $DIR_OUT
cd $DIR_IMG
# Loop through all tsv files
for file in $DIR_TSV; do
  # Display bin processed
  echo ${file:(-28):24};
  # Move TSV file
  mv $file $DIR_IMG${file:(-28):24}
  # Compress output
  # zip $DIR_OUT${file:(-28):24}'.zip' ${file:(-28):24}/*
  find ${file:(-28):24}/ -print | zip -q $DIR_OUT${file:(-28):24}'.zip' -@
  # Remove images
  rm -r $DIR_IMG${file:(-28):24}
done
