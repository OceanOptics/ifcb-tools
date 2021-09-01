from extractIFCBdata import BinExtractor, __version__
import os.path


"""
Processing Parameters
"""

# Path to data
root = '/Users/nils/Data/test-ifcb-tools/'
path_to_raw_data = os.path.join(root, 'raw')
path_to_metadata = os.path.join(root, 'metadata.csv')
path_to_ecotaxa = os.path.join(root, 'to_ecotaxa')
path_to_taxonomic_grouping_csv = os.path.join(root, 'taxonomic_grouping_v5.csv')
path_to_classification = None  # if classification from EcoTaxa not yet available
# path_to_classification = os.path.join(root, 'from_ecotaxa/EcoTaxa_20191115_091240')  # if classification from EcoTaxa is available
path_to_ml = os.path.join(root, 'ml')
path_to_science = os.path.join(root, 'sci')


# Image acquisition system informations
acquisition_info = {'id': 'IFCB107',
                    'instrument': 'IFCB',
                    'serial_number': '107',
                    'resolution_pixel_per_micron': 2.75}
# Information about processing of images
process_info = {'id': 'ifcb-tools-nils-20210830', 'software': 'ifcb-tools', 'software_version': __version__,
                'author': 'Nils Haentjens', 'date':'20210901'}
# Public IFCB Dashboard URL
dashboard_url = 'https://ifcb-data.whoi.edu/timeline?dataset=EXPORTS'
# List of bins to image
bin_list = []  # Process all bins present in metadata file
# bin_list = ['D20210505T193419_IFCB107', 'D20210505T205329_IFCB107']  # Process selected bins


"""
Run Processing
"""
# matlab_engine = matlab.engine.start_matlab()
# matlab_engine.parpool()
ifcb = BinExtractor(path_to_raw_data, path_to_metadata, path_to_classification, path_to_taxonomic_grouping_csv,
                    matlab_parallel_flag=True)#, matlab_engine=matlab_engine)

# Prepare IFCB data for EcoTaxa
ifcb.run_ecotaxa(output_path=path_to_ecotaxa, bin_list=bin_list, acquisition=acquisition_info, process=process_info, url=dashboard_url)
# Prepare IFCB data for Training or Classification with Machine Learning Methods
# ifcb.run_ml_classify_batch(output_path=path_to_ml)
# Prepare IFCB data for Scientific Use
# ifcb.run_ecology(output_path=path_to_science, update_classification=True)
# to make IFCB matlab table run matlab_helpers/make_IFCB_table_v2.m in matlab
