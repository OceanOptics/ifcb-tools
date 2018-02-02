#!/bin/zsh
# Script moving all tsv files in images bin and zipping them
# author: Nils Haentjens
# created: January 24, 2017

# Set directory of ecotaxa tsv files
DIR_TSV=(~/Documents/UMaine/Lab/data/NAAMES/02_ifcb/ecotaxa/tsv/*(.))
# Set directory of ecotaxa images
DIR_IMG=(~/Documents/UMaine/Lab/data/NAAMES/02_ifcb/images/)
# Set directory to compressed data ready for ecotaxa
DIR_OUT=(~/Documents/UMaine/Lab/data/NAAMES/02_ifcb/ecotaxa/import/)

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
