import os, sys, argparse, datetime
import configparser

# Provides path to cfg file, may be overwritten by user-input
CONFIG_PATH = os.path.join(os.getcwd(), "BuildScientificDataSet.cfg")


# parse value from section+key from config file, return as string
def loadConfig(section, key):
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    return config[section][key]


# modify value from section+key in config file, return as string
def modConfig(section, key, value):
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    config.set(section, key, value)
    with open(CONFIG_PATH, 'w') as configfile:
        config.write(configfile)


# modifies date_export to current date of form: yyyyymmdd
def updateExportDate():
    print("Updating date_export...")
    dt = datetime.datetime.now()
    modConfig('Ecotaxa', 'date_export', dt.strftime("%Y%m%d"))


# formats projects from cfg for EcotaxaExport
def projParse():
    rawprojects = loadConfig('EcoTaxa', 'projects_to_exports')
    spaceless = rawprojects.replace(' ', '')
    final = spaceless.replace(',', ' ')
    return final


# returns boolean values from config
def loadConfigBool(section, key):
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    return config.getboolean(section, key)


# Runs EcoTaxaExport Script with cfg parameters
def exportFromEcoTaxa():
    # Pull data from cfg
    spath = loadConfig('EcoTaxa', 'path_to_EcoTaxaExport')
    user = loadConfig('EcoTaxa', 'user')
    pw = loadConfig('EcoTaxa', 'password')
    exppath = loadConfig('EcoTaxa', 'path_to_ecotaxa_data')
    projects = projParse()

    os.system(f'python3 {spath} -u {user} -a {pw} -p {exppath} -i {projects}')

    # Updates export date pending cfg setting
    if loadConfigBool('EcoTaxa', 'change_date'):
        updateExportDate()


# Runs make_IFCB_table.m via commandline providing path to cfg
def generateTable():
    matlab_bin = loadConfig('Matlab', 'path_to_matlab')
    easyIFCB_scripts = loadConfig('Matlab', 'path_to_easyIFCB')
    exists = (os.path.isfile(os.path.join(easyIFCB_scripts, 'make_IFCB_table.m')) and
              os.path.isfile(matlab_bin))
    if exists:
        command = matlab_bin + ' -nodesktop -nosplash -r "CFG_FILENAME =' + \
                  "'" + CONFIG_PATH + "'" + '; ' + 'make_IFCB_table' + '; exit"'
        print(command)
        os.chdir(easyIFCB_scripts)
        os.system(command)
    else:
        raise ValueError("Invalid cfg parameter [Matlab]->path_to_easyIFCB or [Matlab]->path_to_matlab")


# Loads cfg info for EcoTaxaExport, then runs
if __name__ == "__main__":

    # provide option for cfg path
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-p', '--cfgpath',
        required=False,
        help='<optional> path to cfg file, ' + CONFIG_PATH + ' as default'
    )
    args = parser.parse_args()
    if (args.cfgpath is not None):
        if os.path.isfile(args.cfgpath):
            CONFIG_PATH = args.cfgpath
        else:
            print("Error: Provided cfg path does not exist!")
            sys.exit()

    exportFromEcoTaxa()
    generateTable()




