#!/usr/bin/env python
"""
Export IFCB data into different format depending on application requested:
    + classification training: ideal for building a image dataset with metadata to train deep learning algorithm
    + real-time image classification: ideal for the classification of data in real-time with custom algorithm
    + export to EcoTaxa: prepare dataset to import it in EcoTaxa website (not yet implemented)
    + ecological studies: synthetize features (from ifcb-analysis), classification (from EcoTaxa), and metadata into one matlab table

MIT License

Copyright (c) 2021 Nils Haentjens
"""

import glob
import sys
import os
import re
import argparse
from warnings import warn

import pandas as pd
from pandas.api.types import union_categoricals
import numpy as np
import os, glob
from PIL import Image, ImageDraw, ImageFont
import matlab.engine
from tqdm import tqdm
import sys
import re


__version__ = '0.3.0'


ADC_COLUMN_NAMES = ['TriggerId', 'ADCTime', 'SSCIntegrated', 'FLIntegrated', 'PMTC', 'PMTD', 'SSCPeak', 'FLPeak',
                    'PeakC', 'PeakD',
                    'TimeOfFlight', 'GrabTimeStart', 'GrabTimeEnd', 'ImageX', 'ImageY', 'ImageWidth', 'ImageHeight',
                    'StartByte',
                    'ComparatorOut', 'StartPoint', 'SignalLength', 'Status', 'RunTime', 'InhibitTime']
ADC_COLUMN_SEL = ['SSCIntegrated', 'FLIntegrated', 'SSCPeak', 'FLPeak', 'TimeOfFlight',
                  'ImageX', 'ImageY', 'ImageWidth', 'ImageHeight', 'NumberImagesInTrigger']
HDR_COLUMN_NAMES = ['VolumeSampled', 'VolumeSampleRequested',
                    'TriggerSelection', 'SSCGain', 'FLGain', 'SSCThreshold', 'FLThreshold']
FTR_V2_COLUMN_NAMES = ['ImageId', 'Area', 'NumberBlobsInImage',
                       'EquivalentDiameter', 'FeretDiameter', 'MinorAxisLength', 'MajorAxisLength', 'Perimeter',
                       'Biovolume',
                       'TextureContrast', 'TextureGrayLevel', 'TextureEntropy', 'TextureSmoothness',
                       'TextureUniformity']
BLOB_FTR_V4_COLUMN_NAMES = ['ImageId', 'Area', 'NumberBlobsInImage']
SLIM_FTR_V4_COLUMN_NAMES = ['ImageId', 'Area', 'NumberBlobsInImage', 'EquivalentDiameter', 'MinFeretDiameter',
                            'MaxFeretDiameter',
                            'MinorAxisLength', 'MajorAxisLength', 'Perimeter', 'Biovolume', 'ConvexArea',
                            'ConvexPerimeter',
                            'SurfaceArea', 'Eccentricity', 'Extent', 'Orientation', 'RepresentativeWidth', 'Solidity']
ALL_FTR_V4_COLUMN_NAMES = ['ImageId', 'Area', 'NumberBlobsInImage',
                           'MajorAxisLength', 'MinorAxisLength', 'Eccentricity', 'Orientation', 'ConvexArea',
                           'EquivDiameter', 'Solidity', 'Extent', 'Perimeter', 'ConvexPerimeter',
                           'maxFeretDiameter', 'minFeretDiameter', 'BoundingBox_xwidth', 'BoundingBox_ywidth',
                           'texture_average_gray_level', 'texture_average_contrast', 'texture_smoothness',
                           'texture_third_moment', 'texture_uniformity', 'texture_entropy',
                           'moment_invariant1', 'moment_invariant2', 'moment_invariant3', 'moment_invariant4',
                           'moment_invariant5', 'moment_invariant6', 'moment_invariant7',
                           'shapehist_mean_normEqD', 'shapehist_median_normEqD', 'shapehist_skewness_normEqD',
                           'shapehist_kurtosis_normEqD', 'RWhalfpowerintegral', 'RWcenter2total_powerratio',
                           'Biovolume', 'SurfaceArea', 'RepresentativeWidth', 'summedArea', 'summedBiovolume',
                           'summedConvexArea', 'summedConvexPerimeter', 'summedMajorAxisLength',
                           'summedMinorAxisLength', 'summedPerimeter', 'summedSurfaceArea',
                           'H180', 'H90', 'Hflip', 'B180', 'B90', 'Bflip',
                           'RotatedBoundingBox_xwidth', 'RotatedBoundingBox_ywidth', 'rotated_BoundingBox_solidity',
                           'Wedge01', 'Wedge02', 'Wedge03', 'Wedge04', 'Wedge05', 'Wedge06', 'Wedge07', 'Wedge08',
                           'Wedge09', 'Wedge10', 'Wedge11', 'Wedge12', 'Wedge13', 'Wedge14', 'Wedge15', 'Wedge16',
                           'Wedge17', 'Wedge18', 'Wedge19', 'Wedge20', 'Wedge21', 'Wedge22', 'Wedge23', 'Wedge24',
                           'Wedge25', 'Wedge26', 'Wedge27', 'Wedge28', 'Wedge29', 'Wedge30', 'Wedge31', 'Wedge32',
                           'Wedge33', 'Wedge34', 'Wedge35', 'Wedge36', 'Wedge37', 'Wedge38', 'Wedge39', 'Wedge40',
                           'Wedge41', 'Wedge42', 'Wedge43', 'Wedge44', 'Wedge45', 'Wedge46', 'Wedge47', 'Wedge48',
                           'Ring01', 'Ring02', 'Ring03', 'Ring04', 'Ring05', 'Ring06', 'Ring07', 'Ring08', 'Ring09',
                           'Ring10', 'Ring11', 'Ring12', 'Ring13', 'Ring14', 'Ring15', 'Ring16', 'Ring17', 'Ring18',
                           'Ring19', 'Ring20', 'Ring21', 'Ring22', 'Ring23', 'Ring24', 'Ring25', 'Ring26', 'Ring27',
                           'Ring28', 'Ring29', 'Ring30', 'Ring31', 'Ring32', 'Ring33', 'Ring34', 'Ring35', 'Ring36',
                           'Ring37', 'Ring38', 'Ring39', 'Ring40', 'Ring41', 'Ring42', 'Ring43', 'Ring44', 'Ring45',
                           'Ring46', 'Ring47', 'Ring48', 'Ring49', 'Ring50',
                           'HOG01', 'HOG02', 'HOG03', 'HOG04', 'HOG05', 'HOG06', 'HOG07', 'HOG08', 'HOG09', 'HOG10',
                           'HOG11', 'HOG12', 'HOG13', 'HOG14', 'HOG15', 'HOG16', 'HOG17', 'HOG18', 'HOG19', 'HOG20',
                           'HOG21', 'HOG22', 'HOG23', 'HOG24', 'HOG25', 'HOG26', 'HOG27', 'HOG28', 'HOG29', 'HOG30',
                           'HOG31', 'HOG32', 'HOG33', 'HOG34', 'HOG35', 'HOG36', 'HOG37', 'HOG38', 'HOG39', 'HOG40',
                           'HOG41', 'HOG42', 'HOG43', 'HOG44', 'HOG45', 'HOG46', 'HOG47', 'HOG48', 'HOG49', 'HOG50',
                           'HOG51', 'HOG52', 'HOG53', 'HOG54', 'HOG55', 'HOG56', 'HOG57', 'HOG58', 'HOG59', 'HOG60',
                           'HOG61', 'HOG62', 'HOG63', 'HOG64', 'HOG65', 'HOG66', 'HOG67', 'HOG68', 'HOG69', 'HOG70',
                           'HOG71', 'HOG72', 'HOG73', 'HOG74', 'HOG75', 'HOG76', 'HOG77', 'HOG78', 'HOG79', 'HOG80',
                           'HOG81', 'Area_over_PerimeterSquared', 'Area_over_Perimeter', 'H90_over_Hflip',
                           'H90_over_H180', 'Hflip_over_H180', 'summedConvexPerimeter_over_Perimeter']
SB_HDR_STATIC_KEYS = ['investigators', 'affiliations', 'contact', 'documents', 'calibration_files',
                      'associated_files', 'associated_file_types', 'instrument_model', 'instrument_manufacturer',
                      'pixel_per_um', 'data_status', 'experiment']
PATH_TO_IFCB_ANALYSIS_V2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ifcb-analysis-master')
PATH_TO_IFCB_ANALYSIS_V3 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ifcb-analysis-features_v3')
PATH_TO_DIPUM = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'DIPUM')
PATH_TO_MATLAB_FUNCTIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'matlab_helpers')

IFCB_FLOW_RATE = 0.25


class IFCBTools(Exception):
    pass


class CorruptedBin(IFCBTools):
    pass


def upper_to_under(var):
    """
    Insert underscore before upper case letter followed by lower case letter and lower case all sentence.
    """
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', re.sub('(.)([A-Z][a-z]+)', r'\1_\2', var)).lower()


class BinExtractor:

    def __init__(self, path_to_bin, path_to_environmental_csv=None,
                 path_to_ecotaxa_tsv=None, path_to_taxonomic_grouping_csv=None,
                 matlab_engine=None, matlab_parallel_flag=False):
        self.path_to_bin = path_to_bin
        self.matlab_engine = matlab_engine
        self.matlab_parallel_flag = matlab_parallel_flag
        if path_to_environmental_csv:
            #   the environmental file must be in csv format and the first line must be the column names
            #   one of the column must be named "bin" and contain the bin id: D<yyyymmdd>T<HHMMSS>_IFCB<SN#>
            self.environmental_data = pd.read_csv(path_to_environmental_csv, header=0, engine='c',
                                                  parse_dates=['DateTime'])
            if 'bin' not in self.environmental_data:
                raise ValueError('Missing column bin in environmental data file.')
        else:
            self.environmental_data = None
        self.classification_data = None
        if path_to_ecotaxa_tsv and path_to_taxonomic_grouping_csv:
            self.init_ecotaxa_classification(path_to_ecotaxa_tsv, path_to_taxonomic_grouping_csv)

    def __del__(self):
        if self.matlab_engine is not None:
            self.matlab_engine.quit()

    def extract_images_and_cytometry(self, bin_name, write_images_to=None,
                                     with_scale_bar=False, scale_bar_resolution=3.4):
        if with_scale_bar:
            # Prepare Scale Bar
            sb_height = round(1.2 * scale_bar_resolution)  # pixel
            sb_width = round(10 * scale_bar_resolution)  # um
            sb_offset = 2 + sb_height / 2
            sb_font = ImageFont.truetype("Times New Roman", 10)  # font is required to anchor text

        # Parse ADC File
        adc = pd.read_csv(os.path.join(self.path_to_bin, bin_name + '.adc'), names=ADC_COLUMN_NAMES, engine='c',
                          na_values='-999.00000')
        adc.index = adc.index + 1  # increment index to match feature id
        adc['EndByte'] = adc['StartByte'] + adc['ImageWidth'] * adc['ImageHeight']
        # Get Number of ROI within one trigger
        adc['NumberImagesInTrigger'] = [sum(adc['TriggerId'] == x) for x in adc['TriggerId']]
        rows_to_remove = list()
        if write_images_to is not None and not adc.empty:
            # Set path
            if not os.path.exists(write_images_to):
                os.makedirs(write_images_to)
            path_to_png = os.path.join(write_images_to, bin_name)
            # Open ROI File
            roi = np.fromfile(os.path.join(self.path_to_bin, bin_name + '.roi'), 'uint8')
            if len(roi) != adc['EndByte'].iloc[-1]:
                raise CorruptedBin(f'CorruptedBin:{bin_name}: adc end byte is greater than roi size.')
            if not os.path.isdir(path_to_png):
                os.mkdir(path_to_png)
            for d in adc.itertuples():
                if d.StartByte != d.EndByte:
                    # Save Image
                    img = roi[d.StartByte:d.EndByte].reshape(d.ImageHeight, d.ImageWidth)
                    # Save with ImageIO (slower)
                    # imageio.imwrite(os.path.join(path_to_png, f'{bin_name}_{d.Index:05d}.png', img)
                    # Save with PILLOW
                    img = Image.fromarray(img)
                    if with_scale_bar:
                        draw = ImageDraw.Draw(img)
                        draw.line((2, d.ImageHeight - sb_offset, 2 + sb_width, d.ImageHeight - sb_offset), fill=0,
                                  width=sb_height)
                        draw.text((2 + sb_width / 2, d.ImageHeight - sb_offset), '10 µm', fill=0, anchor='md',
                                  font=sb_font)
                    img.save(os.path.join(path_to_png, f'{bin_name}_{d.Index:05d}.png'), 'PNG')
                    # deprecated image name:  f'{bin_name_parts[1]}{bin_name_parts[0]}P{d.Index:05d}.png'; bin_name_parts = bin_name.split('_')
                else:
                    # Remove line from adc
                    adc.drop(index=d.Index, inplace=True)
        else:
            for d in adc.itertuples():
                if d.StartByte == d.EndByte:
                    # Remove line from adc
                    adc.drop(index=d.Index, inplace=True)
        # Keep only columns of interest
        adc = adc[ADC_COLUMN_SEL].astype({'NumberImagesInTrigger': 'uint8'})
        adc.index = adc.index.astype('uint32')
        return adc

    def extract_header(self, bin_name):
        # Parse hdr file
        hdr = dict()
        with open(os.path.join(self.path_to_bin, bin_name + '.hdr')) as myfile:
            for line in myfile:
                name, var = line.partition(":")[::2]
                hdr[name.strip()] = var
        # Compute volume sampled
        look_time = float(hdr['runTime']) - float(hdr['inhibitTime'])  # seconds
        volume_sampled = IFCB_FLOW_RATE * look_time / 60
        # Format in Panda DataFrame
        hdr = pd.Series([volume_sampled, float(hdr['SyringeSampleVolume']),
                         int(hdr['PMTtriggerSelection_DAQ_MCConly']),
                         float(hdr['PMTAhighVoltage']), float(hdr['PMTBhighVoltage']),
                         float(hdr['PMTAtriggerThreshold_DAQ_MCConly']),
                         float(hdr['PMTBtriggerThreshold_DAQ_MCConly'])],
                        index=HDR_COLUMN_NAMES)
        return hdr

    def extract_features_v2(self, bin_name, minimal_feature_flag=False):
        """ Extract features using a custom function (fastFeatureExtration)
            based on the ifcb-analysis main branch (default) """
        if self.matlab_engine is None:
            # Start Matlab engine and add IFCB_analysis
            self.matlab_engine = matlab.engine.start_matlab()

        self.matlab_engine.addpath(os.path.join(PATH_TO_IFCB_ANALYSIS_V2, 'IFCB_tools'),
                                   os.path.join(PATH_TO_IFCB_ANALYSIS_V2, 'feature_extraction'),
                                   os.path.join(PATH_TO_IFCB_ANALYSIS_V2, 'feature_extraction', 'blob_extraction'),
                                   os.path.join(PATH_TO_IFCB_ANALYSIS_V2, 'feature_extraction', 'biovolume'),
                                   PATH_TO_MATLAB_FUNCTIONS,
                                   PATH_TO_DIPUM)
        features = self.matlab_engine.fastFeatureExtraction(self.path_to_bin, bin_name, minimal_feature_flag,
                                                            self.matlab_parallel_flag, nargout=1)
        features = pd.DataFrame(np.array(features._data).reshape(features.size[::-1]).T,
                                columns=FTR_V2_COLUMN_NAMES)
        features = features.astype({'ImageId': 'uint32', 'Area': 'uint64', 'NumberBlobsInImage': 'uint16'})
        features.set_index('ImageId', inplace=True)
        return features

    def extract_features_v4(self, bin_name, level=1):
        """
        Extract features based on code in Development/Heidi_explore/blobs_for_biovolume from branch features_v3 of ifcb-analysis
        The features are based on blob_v4

        level: 0: BLOB, 1: SLIM (recommended for ML or SCI), 2: ALL (recommended for EcoTaxa)
        """
        if self.matlab_engine is None:
            # Start Matlab engine and add IFCB_analysis
            self.matlab_engine = matlab.engine.start_matlab()

        self.matlab_engine.addpath(os.path.join(PATH_TO_IFCB_ANALYSIS_V3, 'IFCB_tools'),
                                   os.path.join(PATH_TO_IFCB_ANALYSIS_V3, 'feature_extraction'),
                                   os.path.join(PATH_TO_IFCB_ANALYSIS_V3, 'feature_extraction', 'blob_extraction'),
                                   os.path.join(PATH_TO_IFCB_ANALYSIS_V3, 'feature_extraction', 'biovolume'),
                                   os.path.join(PATH_TO_IFCB_ANALYSIS_V3, 'Development', 'Heidi_explore',
                                                'blobs_for_biovolume'),
                                   PATH_TO_MATLAB_FUNCTIONS,
                                   PATH_TO_DIPUM)
        self.matlab_engine.cd(
            os.path.join(PATH_TO_IFCB_ANALYSIS_V3, 'Development', 'Heidi_explore', 'blobs_for_biovolume'))
        features = self.matlab_engine.fastFeatureExtraction_v4(self.path_to_bin, bin_name, level,
                                                               self.matlab_parallel_flag, nargout=1)
        if level == 2:
            column_names = ALL_FTR_V4_COLUMN_NAMES
        elif level == 1:
            column_names = SLIM_FTR_V4_COLUMN_NAMES
        elif level == 0:
            column_names = BLOB_FTR_V4_COLUMN_NAMES
        features = pd.DataFrame(np.array(features._data).reshape(features.size[::-1]).T, columns=column_names)
        features = features.astype({'ImageId': 'uint32', 'Area': 'uint64', 'NumberBlobsInImage': 'uint16'})
        features.set_index('ImageId', inplace=True)
        return features

    def init_ecotaxa_classification(self, path_to_ecotaxa_tsv, path_to_taxonomic_grouping_csv):
        """ Build a table with id, taxon, group, and status for each image extracted from EcoTaxa """
        # Read EcoTaxa file(s)
        if os.path.isfile(path_to_ecotaxa_tsv):
            self.classification_data = pd.read_csv(path_to_ecotaxa_tsv, header=0, sep='\t', engine='c',
                                                   usecols=['object_id', 'object_annotation_status',
                                                            'object_annotation_hierarchy'],
                                                   dtype={'object_id': str, 'object_annotation_status': 'category',
                                                          'object_annotation_hierarchy': 'category'})
        elif os.path.isdir(path_to_ecotaxa_tsv):
            list_tsv = glob.glob(os.path.join(path_to_ecotaxa_tsv, '**', '*.tsv'))
            # Read each tsv file
            data = [None] * len(list_tsv)
            for i, f in enumerate(tqdm(list_tsv, desc='Reading Ecotaxa Files')):
                data[i] = pd.read_csv(f, header=0, sep='\t', engine='c',
                                      usecols=['object_id', 'object_annotation_status', 'object_annotation_hierarchy'],
                                      dtype={'object_id': str, 'object_annotation_status': 'category',
                                             'object_annotation_hierarchy': 'category'})
            # Union Categories
            us = union_categoricals([d.object_annotation_status for d in data])
            uh = union_categoricals([d.object_annotation_hierarchy for d in data])
            for i in range(len(data)):
                data[i].object_annotation_status = pd.Categorical(data[i].object_annotation_status,
                                                                  categories=us.categories)
                data[i].object_annotation_hierarchy = pd.Categorical(data[i].object_annotation_hierarchy,
                                                                     categories=uh.categories)
            # Merge all files
            self.classification_data = pd.concat(data, ignore_index=True, axis=0)
        else:
            raise ValueError('EcoTaxa TSV file not found.')
        # Read taxonomic grouping
        taxonomic_grouping = pd.read_csv(path_to_taxonomic_grouping_csv, header=0, engine='c')

        # Quick reformating of EcoTaxa table
        self.classification_data.rename(columns={'object_id': 'id', 'object_annotation_status': 'AnnotationStatus',
                                                 'object_annotation_hierarchy': 'Hierarchy'},
                                        inplace=True)
        # Rename/Group categories
        taxon = pd.Series(taxonomic_grouping.taxon.values, index=taxonomic_grouping.hierarchy).to_dict()
        group = pd.Series(taxonomic_grouping.group.values, index=taxonomic_grouping.hierarchy).to_dict()
        self.classification_data['Taxon'] = self.classification_data.Hierarchy\
            .apply(lambda x: taxon[x] if x in taxon.keys() else x).astype('category')
        self.classification_data['Group'] = self.classification_data.Hierarchy\
            .apply(lambda x: group[x] if x in group.keys() else x).astype('category')
        # self.classification_data['Taxon'] = self.classification_data.Hierarchy.cat.rename_categories(taxon)  # Non unique new categories so does not work
        # self.classification_data['Group'] = self.classification_data.Hierarchy.cat.rename_categories(group)
        # Drop hierarchy
        self.classification_data.drop(columns={'Hierarchy'}, inplace=True)
        # Remove Incorrect ids
        sel = self.classification_data['id'].str.len() != 30
        if np.any(sel):
            sel = np.where(sel)[0]
            print(f"Invalid id(s) in EcoTaxa file, dropping: {[self.classification_data['id'][i] for i in sel]}")
            self.classification_data.drop(index=sel, inplace=True)
        # Split EcoTaxa Id
        self.classification_data['bin'] = self.classification_data['id'].apply(lambda x: x[0:24]).astype('category')
        self.classification_data['ImageId'] = self.classification_data['id'].apply(lambda x: x[25:]).astype('uint32')

    def query_classification(self, bin_name, verbose=True):
        """ query classification data previously loaded with init_ecotaxa_classification"""
        foo = self.classification_data[self.classification_data['bin'] == bin_name]
        if foo.empty:
            if verbose:
                print("%s: No classification data." % bin_name)
            return pd.DataFrame(columns=['AnnotationStatus', 'Taxon', 'Group'])
        else:
            # Check if all ImageId are unique
            if not foo.ImageId.is_unique:
                print("%s: Non unique classification for each image." % bin_name)
                foo = foo.sort_values('AnnotationStatus', ascending=False).drop_duplicates('ImageId')
            return foo.drop(columns=['id', 'bin']).set_index('ImageId')

    def query_environmental_data(self, bin_name):
        foo = self.environmental_data[self.environmental_data['bin'].str.match(bin_name)]
        if foo.empty:
            raise ValueError('%s: No environmental data found.' % bin_name)
        elif len(foo.index) > 1:
            raise ValueError('%s: Non unique bin names in environmental data.' % bin_name)
        return foo.drop(columns={'bin'})

    def get_bin_data(self, bin_name, write_images_to=None, with_scale_bar=False, scale_bar_resolution=3.4,
                     include_classification=False, feature_level=1):
        # Extract cytometric data, features, clear environmental data, and classification for use in ecological studies
        cytometric_data = self.extract_images_and_cytometry(bin_name, write_images_to, with_scale_bar,
                                                            scale_bar_resolution)
        features = self.extract_features_v4(bin_name, level=feature_level)
        if len(features.index) != len(cytometric_data):
            raise ValueError('%s: Cytometric and features data frames have different sizes.' % bin_name)
        if include_classification:
            if self.classification_data is None:
                raise ValueError("Classification data must be loaded first.")
            classification_data = self.query_classification(bin_name, verbose=False)
            if len(classification_data.index) != len(cytometric_data):
                if classification_data.empty:
                    print('%s: No classification data.' % bin_name)
                else:
                    raise ValueError('Classification data incomplete: %d/%d' %
                                     (len(classification_data.index), len(cytometric_data)))
            data = pd.concat([features, cytometric_data, classification_data], axis=1)
        else:
            data = pd.concat([features, cytometric_data], axis=1)
        return data

    def run_ml_train(self):
        """ Extract png, cytometry, features, environmental data, and classification
         to prepare a dataset for machine learning training """
        print('Mode not implemented.')

    def run_machine_learning_single_bin(self, bin_name, output_path):
        """  Extract png, cytometry, features, and obfuscated environmental data
         to classify oceanic plankton images with machine learning algorithms """
        # Write png and get cytometry and features
        try:
            data = self.get_bin_data(bin_name, write_images_to=output_path)
        except CorruptedBin as e:
            print(e)
            return
        # Get environmental data
        environmental_data = self.query_environmental_data(bin_name)
        environmental_data = pd.DataFrame(np.repeat(environmental_data.values, len(data.index), axis=0),
                                          index=data.index, columns=environmental_data.columns)
        # Write data for machine learning
        data = pd.concat([data, environmental_data], axis=1)
        data.to_csv(os.path.join(output_path, bin_name, bin_name + '_ml.csv'),
                    index=False, na_rep='NaN', float_format='%.4f', date_format='%Y/%m/%d %H:%M:%S')

    def run_machine_learning(self, output_path):
        """ Run run_ml_classify_rt on list of bins loaded in environmental_data """
        for i in tqdm(range(len(self.environmental_data.index))):
            try:
                if not os.path.isfile(os.path.join(self.path_to_bin, self.environmental_data['bin'][i] + '.roi')):
                    print('%s: missing roi file.' % self.environmental_data['bin'][i])
                    continue
                if os.path.exists(os.path.join(output_path, self.environmental_data['bin'][i])):
                    print('%s: skipped' % self.environmental_data['bin'][i])
                    continue
                self.run_machine_learning_single_bin(self.environmental_data['bin'][i], output_path)
            except:
                print('%s: Caught Error' % self.environmental_data['bin'][i])

    def run_ecotaxa(self, output_path: str, bin_list: list = None,
                    acquisition: dict = {}, process: dict = {}, url: str = '',
                    force: bool = False, update: list = []):
        """
        Extract png with scale bar, cytometry, features, instrument configuration, environmental data
        for further validation with EcoTaxa.

        """
        if acquisition:
            for key in ['instrument', 'serial_number', 'resolution_pixel_per_micron']:
                if key not in acquisition.keys():
                    raise ValueError(f'acquisition is missing key: {key}')
        if process:
            for key in ['id', 'software']:
                if key not in process.keys():
                    raise ValueError(f'process is missing key: {key}')
        # Setup logic of parts to update
        from_raw = True if not update else False
        set_env = True if not update or 'environment' in update else False
        set_acq = True if not update or 'acquisition' in update else False
        set_proc = True if not update or 'process' in update else False
        # Files to process
        if not bin_list:
            bin_list = self.environmental_data['bin'].to_list()
        for bin_name in tqdm(bin_list):
            # Skip if already processed
            if os.path.exists(os.path.join(output_path, bin_name)) and not force:
                print(f'OutputExists:{bin_name}: Skipped')
                continue
            if from_raw:
                # Write images, read cytometry, and compute features
                try:
                    data = self.get_bin_data(bin_name, write_images_to=output_path, with_scale_bar=True,
                                             scale_bar_resolution=acquisition['resolution_pixel_per_micron'],
                                             feature_level=2)
                except CorruptedBin as e:
                    print(e)
                    continue
                if data.empty:
                    print(f'EmptyBin:{bin_name}: Skipped')
                    continue
                # Create DataFrame for EcoTaxa
                object_id = bin_name + '_' + data.index.astype('str').str.zfill(5)
                et = pd.DataFrame({'img_file_name': object_id + '.png', 'object_id': object_id}, index=data.index)
            else:
                if not os.path.exists(os.path.join(output_path, bin_name, 'ecotaxa_' + bin_name + '.tsv')):
                    print(f'MissingBin:{bin_name}: Skipped')
                    continue
                # Read already computed features and cytometry; skip image extraction
                et = pd.read_csv(os.path.join(output_path, bin_name, 'ecotaxa_' + bin_name + '.tsv'),
                                 header=[0, 1], delimiter='\t', dtype={'object_date': str, 'object_time': str})
            if set_env:
                # Get environmental data
                env = self.query_environmental_data(bin_name)
                # Object
                if url:
                    et['object_link'] = f'{url}&bin={bin_name}'
                et['object_lat'] = env.Latitude.values[0] if not env.Latitude.isna().any() else 44.9012018
                et['object_lon'] = env.Longitude.values[0] if not env.Latitude.isna().any() else -68.6704788
                et['object_date'] = env.DateTime.dt.strftime('%Y%m%d').values[0]
                et['object_time'] = env.DateTime.dt.strftime('%H%M%S').values[0]
                et['object_depth_min'] = env.Depth.values[0]
                et['object_depth_max'] = env.Depth.values[0]
            if from_raw:
                # Append all features and cytometry to Object
                # Done here to add columns in order
                cols = et.columns.to_list()
                et = pd.concat([et, data], axis=1)
                et.columns = cols + ['object_' + upper_to_under(k) for k in data.columns]
            # Sample
            if set_env:
                et['sample_id'] = bin_name
                for k in env.columns:
                    if k not in ['DateTime', 'Latitude', 'Longitude', 'Depth']:
                        et['sample_' + upper_to_under(k)] = env[k].astype(str).values[0]
            # Acquisition
            if set_acq:
                et['acq_id'] = acquisition['instrument'] + str(acquisition['serial_number']) + '.' + bin_name
                # User Input
                for k, v in acquisition.items():
                    et['acq_' + upper_to_under(k)] = str(v)
                # Bin Header (e.g. volume sampled, pmt settings)
                hdr = self.extract_header(bin_name)
                for k, v in hdr.items():
                    et['acq_' + upper_to_under(k)] = v
            # Process
            if set_proc:
                for k, v in process.items():
                    et['process_' + upper_to_under(k)] = str(v)
            # Write tsv (with line indicating type)
            if from_raw:
                cols = [(c, '[t]' if et[c].dtype == 'O' else '[f]') for c in et.columns]
            else:
                # Already multi-index, assign type only to unknown cols
                cols = []
                for c in et.columns:
                    if not c[1]:
                        cols.append((c[0], '[t]' if et[c[0]].dtype == 'O' else '[f]'))
                    else:
                        cols.append(c)
                # et[('object_time', '[t]')] = et[('object_time', '[t]')].apply(lambda r: f'{r:06d}')  # Patch object time
            et.columns = pd.MultiIndex.from_tuples(cols)
            et.to_csv(os.path.join(output_path, bin_name, 'ecotaxa_' + bin_name + '.tsv'),
                      index=False, na_rep='NaN', float_format='%.4f', sep='\t')

    def run_science(self, output_path, bin_list=None, update_all=False, update_classification=False,
                    make_matlab_table=False, matlab_table_info=None):
        """
        Generate a file per bin with cytometry, features, and classification data
        Generate a metadata file with all environmental data and bin header information
        """
        if make_matlab_table:
            if not isinstance(matlab_table_info, dict):
                raise ValueError('matlab_table_info is required and must be a dictionary')
            for k in ['PROJECT_NAME', 'ECOTAXA_EXPORT_DATE', 'IFCB_RESOLUTION',
                      'CALIBRATED', 'REMOVED_CONCENTRATED_SAMPLES']:
                if k not in matlab_table_info.keys():
                    raise ValueError(f'matlab_table_info must have field: {k}')
        # Load previous metadata or create new one
        metadata_filename = os.path.join(output_path, 'metadata.csv')
        if os.path.isfile(metadata_filename):
            new_metadata_file = False
            metadata = pd.read_csv(metadata_filename)
            metadata.rename(columns={'BinId': 'bin'}, inplace=True)
            if 'Validated' in metadata.columns:
                metadata.rename(columns={'Validated': 'AnnotationValidated'}, inplace=True)
        else:
            new_metadata_file = True
            metadata = self.environmental_data
            for c in HDR_COLUMN_NAMES:
                metadata[c] = np.nan
            metadata['TriggerSelection'] = -9999
            metadata['AnnotationValidated'] = np.nan
        # Set list to parse
        if not bin_list:
            bin_list = metadata['bin']
        for bin_name in tqdm(bin_list):
            i = metadata.index[metadata['bin'] == bin_name]
            try:
                if not os.path.isfile(os.path.join(self.path_to_bin, bin_name + '.roi')):
                    print('%s: missing roi file.' % bin_name)
                    metadata.drop(index=i, inplace=True)
                    continue
                bin_filename = os.path.join(output_path, bin_name + '_sci.csv')
                if new_metadata_file or update_all or not os.path.isfile(bin_filename):
                    # Get header information
                    metadata.loc[i, HDR_COLUMN_NAMES] = self.extract_header(bin_name).to_list()
                if not os.path.isfile(bin_filename) or update_all:
                    # Get cytometry, features, and classification and write to <bin_name>_sci.csv
                    try:
                        data = self.get_bin_data(bin_name, include_classification=True)
                    except CorruptedBin as e:
                        print(e)
                        continue
                    data.to_csv(bin_filename,
                                na_rep='NaN', float_format='%.4f', index_label='ImageId')
                    # Get percent validated
                    if not data.empty:
                        metadata.loc[i, 'AnnotationValidated'] = np.sum(data['AnnotationStatus'] == 'validated') / len(
                            data.index)
                elif update_classification:
                    # Get classification data to get validation percentage for metadata file
                    data = self.query_classification(bin_name, verbose=True)
                    if not data.empty:
                        foo = pd.read_csv(bin_filename, index_col='ImageId')
                        if foo.shape[0] != data.shape[0]:
                            print('%s: Unable to update classification, different sizes.' % bin_name)
                            continue
                        # Rename old column Status to AnnotationStatus (for old NAAMES files)
                        if 'Status' in foo.columns:
                            foo.rename(columns={'Status': 'AnnotationStatus'}, inplace=True)
                        # Replace old columns by new ones
                        foo.drop(columns=data.columns, axis=0, inplace=True)
                        data = pd.concat([foo, data], axis=1)
                        data.to_csv(bin_filename,
                                    na_rep='NaN', float_format='%.4f', index_label='ImageId')
                        # Update percent validated in metadata
                        metadata.loc[i, 'AnnotationValidated'] = np.sum(data['AnnotationStatus'] == 'validated') / len(
                            data.index)
                elif new_metadata_file:
                    # Get classification data to get validation percentage for metadata file
                    data = self.query_classification(bin_name, verbose=True)
                    if not data.empty:
                        # Get percent validated in metadata
                        metadata.loc[i, 'AnnotationValidated'] = np.sum(data['AnnotationStatus'] == 'validated') / len(
                            data.index)
                else:
                    # Bin already processed and does not need to be processed
                    # print('%s: skipped' % bin_name)
                    continue
            except Exception as e:
                # raise e
                print('%s: Caught Error: %s' % (bin_name, e))
        # Write metadata
        metadata['TriggerSelection'] = metadata['TriggerSelection'].astype('int32')
        metadata.rename(columns={'bin': 'BinId'}).to_csv(metadata_filename,
                                                         index=False, na_rep='NaN', float_format='%.4f',
                                                         date_format='%Y/%m/%d %H:%M:%S')
        # Make matlab table calling appropriate helper
        if make_matlab_table:
            if self.matlab_engine is None:
                # Start Matlab engine and add IFCB_analysis
                self.matlab_engine = matlab.engine.start_matlab()

            self.matlab_engine.addpath(PATH_TO_MATLAB_FUNCTIONS)
            cfg = dict(path_to_input_data=output_path, path_to_output_table=output_path)
            self.matlab_engine.make_ifcb_table(matlab_table_info, cfg, nargout=0)

    @staticmethod
    def run_seabass(path_to_sci: str, output_path: str, metadata: dict):
        """
        Format science data to SeaBASS format
        """

        def fmt(value):
            return '-9999' if pd.isna(value) else value

        def data_type_mapper(value):
            if value in ['inline', 'station']:
                return 'flow_thru'
            elif value in ['dock', 'niskin', 'micro-layer']:
                return 'bottle'
            elif value in ['towfish', 'zootow']:
                return 'net_tow'
            elif value in ['beads', 'culture', 'Experiment', 'PIC', 'ali6000', 'karen', 'test', 'incubation']:
                return 'experimental'
            else:
                warn(f"data type {value} not supported. default to experimental")
                return 'experimental'

        def fmt_trigger_mode(value):
            if value == 1:
                return 'side scattering (PMTA)'
            elif value == 2:
                return 'chlorophyll fluorescence (PMTB)'
            elif value == 3:
                return 'side scattering (PMTA) or chlorophyll fluorescence (PMTB)'
            else:
                raise ValueError(f'trigger mode {value} not supported.')

        # Prepare static header & check metadata
        static_hdr = "/begin_header\n"
        for k in SB_HDR_STATIC_KEYS:
            if k not in metadata.keys():
                raise KeyError(f'Missing key {k} in metadata')
            static_hdr += f"/{k}={metadata[k]}\n"
        for k in ['cruise', 'filename_descriptor', 'revision', 'dashboard_url', 'ifcb_analysis_version']:
            if k not in metadata.keys():
                raise KeyError(f'Missing key {k} in metadata')
        metadata['dashboard_url'] = metadata['dashboard_url'][:-1] if metadata['dashboard_url'][-1] == '/'\
            else metadata['dashboard_url']

        sci = pd.read_csv(os.path.join(path_to_sci, 'metadata.csv'), parse_dates=['DateTime'])
        for _, r in tqdm(sci.iterrows(), total=len(sci), desc='Exporting to SeaBASS'):
            sb_bin_id = r.BinId[1:9] + r.BinId[10:16]  # date & time of IFCB sample
            cruise = f"{metadata['cruise']}{r.Campaign}"
            filename = f"{metadata['experiment']}-{cruise}_{metadata['filename_descriptor']}_" \
                       f"{sb_bin_id}_{metadata['revision']}.sb"
            # Get Header
            hdr = static_hdr + \
                  f"/cruise={cruise}\n" + \
                  f"/station={fmt(r.Station)}\n" + \
                  f"/eventID={r.BinId}\n" + \
                  f"/data_file_name={filename}\n" + \
                  f"/associatedMedia_source={metadata['dashboard_url']}/{r.BinId}.html\n" + \
                  f"/data_type={data_type_mapper(r.Type)}\n" + \
                  f"/start_date={r.DateTime.strftime('%Y%m%d')}\n" + \
                  f"/end_date={r.DateTime.strftime('%Y%m%d')}\n" + \
                  f"/start_time={r.DateTime.strftime('%H:%M:%S')}[GMT]\n" + \
                  f"/end_time={r.DateTime.strftime('%H:%M:%S')}[GMT]\n" + \
                  f"/north_latitude={fmt(r.Latitude)}[DEG]\n" + \
                  f"/south_latitude={fmt(r.Latitude)}[DEG]\n" + \
                  f"/east_longitude={fmt(r.Longitude)}[DEG]\n" + \
                  f"/west_longitude={fmt(r.Longitude)}[DEG]\n" + \
                  f"/water_depth=NA\n" + \
                  f"/measurement_depth={r.Depth}\n" + \
                  f"/volume_sampled_ml={r.VolumeSampleRequested:.2f}\n" + \
                  f"/volume_imaged_ml={r.VolumeSampled:.4f}\n" + \
                  f"/length_representation_instrument_varname=maxFeretDiameter\n" + \
                  f"/width_representation_instrument_varname=minFeretDiameter\n" + \
                  f"/missing={fmt(float('nan'))}\n" + \
                  f"/delimiter=comma\n" + \
                  f"!\n" + \
                  f"! {cruise} cruise {metadata['filename_descriptor']}\n" + \
                  f"!\n" + \
                  f"! concentration: {r.Concentration}X\n" + \
                  f"!\n" + \
                  f"! IFCB trigger mode: {fmt_trigger_mode(r.TriggerSelection)}\n" + \
                  f"!\n" + \
                  f"! To access each image directly from the associatedMedia string: replace .html with .png\n" + \
                  f"!\n" + \
                  f"! {metadata['ifcb_analysis_version']} ifcb-analysis image products; " \
                  f"https://github.com/hsosik/ifcb-analysis\n" + \
                  f"!\n" + \
                  f"/fields=associatedMedia,biovolume,area_cross_section,length_representation,width_representation," \
                  f"equivalent_spherical_diameter,area_based_diameter," \
                  f"data_provider_category_automated,data_provider_category_manual\n" + \
                  f"/units=none,um^3,um^2,um,um,um,um,none,none\n" + \
                  f"/end_header\n"
            # Get content
            bin = pd.read_csv(os.path.join(path_to_sci, f'{r.BinId}_sci.csv'))
            lbl = 'AnnotationStatus' if 'AnnotationStatus' in bin.columns else 'Status'
            bin['TaxonAutomated'] = bin.apply(lambda x: x['Taxon'] if x[lbl] == 'predicted' else fmt(float('nan')),
                                              axis='columns')
            bin['TaxonManual'] = bin.apply(lambda x: x['Taxon'] if x[lbl] == 'validated' else fmt(float('nan')),
                                           axis='columns')
            bin['ESD'] = 2 * (3 / (4 * np.pi) * bin.Biovolume) ** (1/3)
            bin = bin.loc[:, ['ImageId', 'Biovolume', 'Area', 'MaxFeretDiameter', 'MinFeretDiameter',
                              'ESD', 'EquivalentDiameter', 'TaxonAutomated', 'TaxonManual']]
            bin['ImageId'] = [f"{metadata['dashboard_url']}/{r.BinId}_"] * len(bin) + \
                             bin['ImageId'].astype(str).astype('str').str.rjust(5, '0') + \
                             ['.html'] * len(bin)
            # Apply calibration
            bin['Biovolume'] /= metadata['pixel_per_um'] ** 3
            bin['Area'] /= metadata['pixel_per_um'] ** 2
            bin['MaxFeretDiameter'] /= metadata['pixel_per_um']
            bin['MinFeretDiameter'] /= metadata['pixel_per_um']
            bin['EquivalentDiameter'] /= metadata['pixel_per_um']
            bin['ESD'] /= metadata['pixel_per_um']
            # Write data
            with open(os.path.join(output_path, filename), 'w') as f:
                f.writelines(hdr)
                bin.to_csv(f, index=False, header=False, float_format='%.3f', na_rep=fmt(float('nan')))

    def check_machine_learning(self, path_to_data):
        flag = False
        # Get list of bins from 3 sources
        list_bins_env = list(self.environmental_data['bin'])
        list_bins_in = [b[0:-4] for b in os.listdir(self.path_to_bin) if b[-4:] == '.roi']
        list_bins_out = os.listdir(path_to_data)

        # Check no bins are missing
        if len(list_bins_env) != len(set(list_bins_env)):
            flag = True
            print('check_ml_classify_batch: Non unique list of bins in environmental data')

        missing_bins_from_env = np.setdiff1d(list_bins_env, list_bins_out)
        if missing_bins_from_env.size > 0:
            flag = True
            print('check_ml_classify_batch: Missing %d bins from environment file:' % missing_bins_from_env.size)
            for b in missing_bins_from_env:
                print('\t%s' % b)
            print()

        missing_bins_from_raw = np.setdiff1d(list_bins_in, list_bins_out)
        if missing_bins_from_raw.size > 0:
            flag = True
            print('check_ml_classify_batch: Missing %d bins from raw folder:' % missing_bins_from_raw.size)
            for b in missing_bins_from_raw:
                print('\t%s' % b)
            print()

        # Check that each bin is complete
        n = 0
        for b in tqdm(list_bins_out):
            path_to_metadata = os.path.join(path_to_data, b, b + '_ml.csv')
            if not os.path.exists(path_to_metadata):
                flag = True
                print('check_ml_classify_batch: %s no metadata file.' % b)
                continue
            meta = pd.read_csv(path_to_metadata, header=0, engine='c')
            bin_name_parts = b.split('_')
            list_images_from_meta = [f'{b}_{i:05d}.png' for i in meta['ImageId']]
            list_images_in_folder = [img for img in os.listdir(os.path.join(path_to_data, b)) if img[-4:] == '.png']

            missing_images_from_folder = np.setdiff1d(list_images_in_folder, list_images_from_meta)
            if missing_images_from_folder.size > 0:
                flag = True
                print('check_ml_classify_batch: Missing %d images in %s:' % (missing_images_from_folder.size, b))
                for i in missing_images_from_folder:
                    print('\t%s' % i)
                print()

            missing_images_from_meta = np.setdiff1d(list_images_from_meta, list_images_in_folder)
            if missing_images_from_meta.size > 0:
                flag = True
                print('check_ml_classify_batch: Missing %d metadata of %s:' % (missing_images_from_meta.size, b))
                for i in missing_images_from_meta:
                    print('\t%s' % i)
                print()

            n += len(list_images_in_folder)

        if not flag:
            print('check_ml_classify_batch: Pass')

        print('%d images checked in %d bins' % (n, len(list_bins_out)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', type=str, help="Set data extraction mode."
                                               " Options available are: ml-train, ml-classify-batch, ml-classify-rt, ecotaxa, ecology.")
    parser.add_argument('-r', '--raw', type=str, required=True,
                        help="Set path to raw IFCB directory (adc, hdr, and roi files).")
    parser.add_argument('-m', '--environmental', type=str, required=True,
                        help="Set path to environmental metadata file.")
    parser.add_argument('-t', '--taxonomy', type=str, required=False,
                        help="Set path to taxonomic grouping file. ")
    parser.add_argument('-e', '--ecotaxa', type=str, required=False,
                        help="Set path to EcoTaxa classification directory or file.")
    parser.add_argument('-o', '--output', type=str, required=True,
                        help="Set path to directory of formatted output data.")
    parser.add_argument('-p', '--parallel', action='store_true',
                        help="Enable Matlab parallel processing.")
    parser.add_argument('-s', '--sample', type=str,
                        help='Set sample to process in mode ml-classify-rt.')
    parser.add_argument('-f', '--force', action='store_true',
                        help="Force update of all data in mode ecology.")
    parser.add_argument('-u', '--update-classification', action='store_true',
                        help="Update classification data in mode ecology.")

    args = parser.parse_args()

    # Initialize extractor based on running mode
    extractor = BinExtractor(args.raw, args.environmental, matlab_parallel_flag=args.parallel)
    if 'ml' not in args.mode:
        if not args.ecotaxa:
            print('argument -e, --ecotaxa required')
            sys.exit(-1)
        if not args.taxonomy:
            print('argument -t, --taxonomy required')
            sys.exit(-1)
        extractor.init_ecotaxa_classification(args.ecotaxa, args.taxonomy)

    # Run extractor
    if args.mode == 'ml-train':
        extractor.run_ml_train(args.output)
    elif args.mode == 'ml-classify-batch':
        extractor.run_machine_learning(args.output)
        extractor.check_machine_learning(args.output)
    elif args.mode == 'ml-classify-rt':
        if not args.sample:
            print('argument -s, --sample required')
            sys.exit(-1)
        extractor.run_machine_learning_single_bin(args.sample, args.output)
    elif args.mode == 'ecotaxa':
        extractor.run_ecotaxa(args.output)
    elif args.mode == 'ecology':
        extractor.run_science(args.output, update_all=args.force, update_classification=args.update_classification)
    else:
        print('mode not supported.')
