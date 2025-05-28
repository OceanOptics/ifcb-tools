from extractIFCBdata import BinExtractor, __version__
import os.path
import warnings
from datetime import datetime

import pandas as pd

from extractIFCBdata import BinExtractor, __version__, flag_str_to_int


"""
Processing Parameters
"""

# Path to data
root = '/Users/nils/Data/EXPORTS/IFCB107'
path_to_raw_data = os.path.join(root, 'raw')
path_to_metadata = os.path.join(root, 'metadata.csv')
path_to_ecotaxa = os.path.join(root, 'to_ecotaxa')
path_to_taxonomic_grouping_csv = os.path.join(root, 'taxonomic_grouping_v5.csv')
# path_to_classification = None  # if classification from EcoTaxa not yet available
path_to_classification = os.path.join(root, 'from_ecotaxa/EcoTaxa_20211031')  # if classification from EcoTaxa is available
path_to_ml = os.path.join(root, 'ml')
path_to_science = os.path.join(root, 'sci')
path_to_seabass = os.path.join(root, 'SB_20211031')

"""
Parameters specific to Scientific Export
"""
info = {'PROJECT_NAME': experiment,
        'ECOTAXA_EXPORT_DATE': '20230507',
        # 'IFCB_RESOLUTION': 2.7488,  # pixels/µm  (IFCB107)
        'IFCB_RESOLUTION': 3.4,  # pixels/µm  (DEFAULT)
        'CALIBRATED': True,  # if True, apply calibration from pixel to µm using the IFCB_RESOLUTION
        'REMOVED_CONCENTRATED_SAMPLES': False}

"""
Parameters specific to EcoTaxa export
"""
# Image acquisition system informations
acquisition_info = {'instrument': 'IFCB',
                    'serial_number': instr.split('B')[-1],
                    'resolution_pixel_per_micron': info['IFCB_RESOLUTION']}
# Information about processing of images
process_info = {'id': f"ifcb-tools-nils-{datetime.now().strftime('%Y%m%d')}",
                'software': 'ifcb-tools', 'software_version': __version__,
                'author': 'Nils Haentjens', 'date': datetime.now().strftime('%Y%m%d')}
# Public IFCB Dashboard URL
dashboard_url = f'http://misclab.umeoce.maine.edu:8081/timeline?dataset={experiment}'
# List of bins to image
bin_list = []  # Process all bins present in metadata file
# bin_list = ['D20210503T092408_IFCB107', 'D20210506T001620_IFCB107']  # Process selected bins
# Custom bin list based on metadata
meta = pd.read_csv(path_to_metadata, index_col='bin')
# ['LEG01_Lorient-Amsterdam', 'LEG02_Amsterdam-Aarhus', 'LEG03_Aarhus-Sopot', 'LEG05_Tallin-Kristineberg', 'LEG06_Kristineberg-Galway', 'LEG07_Galway-Bilbao', 'LEG08_Bilbao-Cadiz',
#  nan, 'LEG09_Malaga-Barcelona', 'LEG10_Barcelona-Marseille', 'LEG11_Marseille-Napoli', 'LEG13_Ancona-Kotor', 'LEG_HyperBoost']
leg_name = 'LEG_HyperBoost'
meta['flag_int'] = meta.Flag.apply(flag_str_to_int).astype(int)
bin_list = meta.index[(meta.Leg == leg_name) &
                      ~((meta.flag_int & 2**10) | (meta.flag_int & 2**2) | (meta.flag_int & 2**1) | (meta.flag_int & 2**5))].tolist()
path_to_ecotaxa = os.path.join(path_to_ecotaxa, leg_name)
if not os.path.exists(path_to_ecotaxa):
    os.makedirs(path_to_ecotaxa)
path_to_raw_data = os.path.join(root, '2024')


"""
Parameters specific to SeaBASS export
"""
seabass_metadata = {
    'investigators': 'Nils_Haentjens,Alison_Chase',
    'affiliations': 'University_of_Maine,University_of_Maine',
    'contact': 'nils.haentjens@maine.edu,lee.karp-boss@maine.edu',
    'documents': f'{experiment}.IFCB.brief-protocol.pdf,{experiment}.IFCB.checklist.pdf',
    'calibration_files': 'no_cal_files',
    'associated_files': f'{experiment}.IFCB.raw.zip',
    'associated_file_types': 'raw',
    'instrument_model': f'Imaging_FlowCytobot_IFCB{acquisition_info["serial_number"]}',
    'instrument_manufacturer': 'McLane_Research_Laboratories_Inc',
    'pixel_per_um': info['IFCB_RESOLUTION'],
    'data_status': 'update',
    'experiment': 'NAAMES',
    'cruise': 'NAAMES',
    'experiment': experiment,
    'cruise': cruise,
    'filename_descriptor': 'IFCB_plankton&particles',
    'revision': 'R0',
    'dashboard_url': dashboard_url,
    'ifcb_analysis_version': 'v4'
}


"""
Run Processing
"""
# matlab_engine = matlab.engine.start_matlab()
# matlab_engine.parpool()
ifcb = BinExtractor(path_to_raw_data, path_to_metadata, path_to_classification, path_to_taxonomic_grouping_csv,
                    matlab_parallel_flag=True)#, matlab_engine=matlab_engine)

# Prepare IFCB data for EcoTaxa
warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)
ifcb.run_ecotaxa(output_path=path_to_ecotaxa, bin_list=bin_list,
                 acquisition=acquisition_info, process=process_info, url=dashboard_url)
                 # force=True, update=['process'])
# Prepare IFCB data for Training or Classification with Machine Learning Methods
# ifcb.run_machine_learning(output_path=path_to_ml)
# Prepare IFCB data for Scientific Use
ifcb.run_science(output_path=path_to_science, bin_list=bin_list, update_classification=True,
                 make_matlab_table=True, matlab_table_info=info)
# EXPORT IFCB data to SeaBASS
BinExtractor.run_seabass(path_to_science, path_to_seabass, seabass_metadata)
