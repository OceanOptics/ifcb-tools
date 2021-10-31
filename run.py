from extractIFCBdata import BinExtractor, __version__
import os.path
from datetime import datetime


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

"""
Parameters specific to Scientific Export
"""
info = {'PROJECT_NAME': 'EXPORTS-NA',
        'ECOTAXA_EXPORT_DATE': '20211031',
        'IFCB_RESOLUTION': 2.7488,  # pixels/µm
        'CALIBRATED': True,  # if True, apply calibration from pixel to µm using the IFCB_RESOLUTION
        'REMOVED_CONCENTRATED_SAMPLES': False}

"""
Parameters specific to EcoTaxa export
"""
# Image acquisition system informations
acquisition_info = {'instrument': 'IFCB',
                    'serial_number': '107',
                    'resolution_pixel_per_micron': 2.7488}
# Information about processing of images
process_info = {'id': f"ifcb-tools-nils-{datetime.now().strftime('%Y%m%d')}",
                'software': 'ifcb-tools', 'software_version': __version__,
                'author': 'Nils Haentjens', 'date': datetime.now().strftime('%Y%m%d')}
# Public IFCB Dashboard URL
dashboard_url = 'https://ifcb-data.whoi.edu/timeline?dataset=EXPORTS'
# List of bins to image
bin_list = []  # Process all bins present in metadata file
# bin_list = ['D20210503T092408_IFCB107', 'D20210506T001620_IFCB107']  # Process selected bins


"""
Run Processing
"""
# matlab_engine = matlab.engine.start_matlab()
# matlab_engine.parpool()
ifcb = BinExtractor(path_to_raw_data, path_to_metadata, path_to_classification, path_to_taxonomic_grouping_csv,
                    matlab_parallel_flag=True)#, matlab_engine=matlab_engine)

# Prepare IFCB data for EcoTaxa
# ifcb.run_ecotaxa(output_path=path_to_ecotaxa, bin_list=bin_list,
#                  acquisition=acquisition_info, process=process_info, url=dashboard_url,
#                  force=True, update=['process'])
# Prepare IFCB data for Training or Classification with Machine Learning Methods
# ifcb.run_machine_learning(output_path=path_to_ml)
# Prepare IFCB data for Scientific Use
ifcb.run_science(output_path=path_to_science, bin_list=bin_list, update_classification=True,
                 make_matlab_table=True, matlab_table_info=info)
# to make IFCB matlab table run matlab_helpers/make_IFCB_table_v2.m in matlab
