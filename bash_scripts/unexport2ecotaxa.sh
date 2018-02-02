#!/bin/zsh
# Script undoing export2ecotaxa.sh
# separating images and tsv files from zip
# author: Nils Haentjens
# created: February 8, 2017

# Set directory of ecotaxa tsv files (OUTPUT)
DIR_TSV=(~/Documents/UMaine/Lab/data/NAAMES/02_ifcb/ecotaxa/tsv_old/)
# Set directory of ecotaxa images (OUTPUT)
DIR_IMG=(~/Documents/UMaine/Lab/data/NAAMES/02_ifcb/images/)
# Set directory of compressed bin (INPUT)
DIR_IN=(~/Documents/UMaine/Lab/data/NAAMES/02_ifcb/ecotaxa/import/*(.))

mkdir -p $DIR_TSV
mkdir -p $DIR_IMG
cd $DIR_IMG
# Loop through all tsv files
for file in $DIR_IN; do
  # Display bin processed
  echo ${file:(-28):24};
  # UnCompress input
  unzip -q $file
  # Move TSV file
  mv $DIR_IMG${file:(-28):24}'/ecotaxa_'${file:(-28):24}'.tsv' $DIR_TSV
done
