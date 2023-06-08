from extractIFCBdata import BinExtractor, __version__
import os.path
from datetime import datetime


"""
Processing Parameters
"""

# Path to data
root = '/Users/alisonchase/Dropbox/UTOPIA'
path_to_raw_data = os.path.join(root, 'test/raw')
path_to_metadata = os.path.join(root, 'test/metadata.csv')
path_to_ecotaxa = os.path.join(root, 'to_ecotaxa')
path_to_taxonomic_grouping_csv = os.path.join(root, 'taxonomic_grouping_v5.csv')
# path_to_classification = None  # if classification from EcoTaxa not yet available
path_to_classification = None #os.path.join(root, 'from_ecotaxa/EcoTaxa_20211031')  # if classification from EcoTaxa is available
path_to_ml = os.path.join(root, 'test/ml')
path_to_science = os.path.join(root, 'sci')
path_to_seabass = os.path.join(root, 'SB_20211031')

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
                    'resolution_pixel_per_micron': info['IFCB_RESOLUTION']}
# Information about processing of images
process_info = {'id': f"ifcb-tools-alichase-{datetime.now().strftime('%Y%m%d')}",
                'software': 'ifcb-tools', 'software_version': __version__,
                'author': 'Ali Chase', 'date': datetime.now().strftime('%Y%m%d')}
# Public IFCB Dashboard URL
# dashboard_url = 'https://ifcb-data.whoi.edu/timeline?dataset=EXPORTS'
# List of bins to image
bin_list = []  # Process all bins present in metadata file
# bin_list = ['D20210503T092408_IFCB107', 'D20210506T001620_IFCB107']  # Process selected bins

"""
Parameters specific to SeaBASS export
"""
# seabass_metadata = {
#     'investigators': 'Lee_Karp-Boss,Emmanuel_Boss,Nils_Haentjens,Alison_Chase',
#     'affiliations': 'University_of_Maine,University_of_Maine,University_of_Maine,University_of_Maine',
#     'contact': 'nils.haentjens@maine.edu,lee.karp-boss@maine.edu',
#     'documents': f'{project_name}.IFCB.brief-protocol.pdf,{project_name}.IFCB.checklist.pdf',
#     'calibration_files': 'no_cal_files',
#     'associated_files': f'{project_name}.IFCB.raw.zip',
#     'associated_file_types': 'raw',
#     'instrument_model': 'Imaging_FlowCytobot_IFCB107',
#     'instrument_manufacturer': 'McLane_Research_Laboratories_Inc',
#     'pixel_per_um': info['IFCB_RESOLUTION'],
#     'data_status': 'update',
#     'experiment': 'NAAMES',
#     'cruise': 'NAAMES',
#     'filename_descriptor': 'IFCB_plankton&particles',
#     'revision': 'R1',
#     'dashboard_url': dashboard_url,
#     'ifcb_analysis_version': 'v4'
# }


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
ifcb.run_machine_learning(output_path=path_to_ml)
# Prepare IFCB data for Scientific Use
# ifcb.run_science(output_path=path_to_science, bin_list=bin_list, update_classification=True,
#                  make_matlab_table=True, matlab_table_info=info)
# EXPORT IFCB data to SeaBASS
# BinExtractor.run_seabass(path_to_science, path_to_seabass, seabass_metadata)
