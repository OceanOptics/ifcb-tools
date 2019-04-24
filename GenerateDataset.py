import os, sys, argparse, datetime
import configparser

# Provides path to cfg file, may be overwritten by user-input
CONFIGPATH = "/Users/jasonmorrill/Desktop/Work/Generation_Config.cfg"


# parse value from section+key from config file, return as string
def loadConfig(section, key):
    config = configparser.ConfigParser()
    config.read(CONFIGPATH)
    return config[section][key]


# modify value from section+key in config file, return as string
def modConfig(section, key, value):
    config = configparser.ConfigParser()
    config.read(CONFIGPATH)
    config.set(section, key, value)
    with open(CONFIGPATH, 'w') as configfile:
        config.write(configfile)


# modifies date_export to current date of form: yymmdd
def updateExportDate():
    print("Updating date_export...")
    dt = datetime.datetime.now()
    modConfig('Ecotaxa', 'DateExport', dt.strftime("%y%m%d"))


# formats projects from cfg for EcotaxaExport
def projParse():
    rawprojects = loadConfig('Ecotaxa', 'projects')
    spaceless = rawprojects.replace(' ', '')
    final = spaceless.replace(',', ' ')
    return final


# returns boolean values from config
def loadConfigBool(section, key):
    config = configparser.ConfigParser()
    config.read(CONFIGPATH)
    return config.getboolean(section, key)


# Runs EcotaxaExport Script with cfg parameters
def exportFromEcotaxa():
    # Pull data from cfg
    spath = loadConfig('Ecotaxa', 'scriptpath')
    user = loadConfig('Ecotaxa', 'user')
    pw = loadConfig('Ecotaxa', 'password')
    exppath = loadConfig('Ecotaxa', 'exportpath')
    projects = projParse()

    os.system(f'python3 {spath} -u {user} -a {pw} -p {exppath} -i {projects}')

    # Updates export date pending cfg setting
    if loadConfigBool('Ecotaxa', 'changedate'):
        updateExportDate()


# Runs make_IFCB_table.m via commandline providing path to cfg
def generateTable():
    exists = os.path.isfile(loadConfig('Matlab', 'scriptpath')+'make_IFCB_table.m')
    if exists:
        command = '/Applications/MATLAB_R2019a.app/bin/matlab -nodesktop -nosplash -r "CFG_FILENAME =' + \
               "'" + CONFIGPATH + "'" + '; ' + 'make_IFCB_table' + ';exit"'
        print(command)
        os.chdir(loadConfig('Matlab', 'scriptpath'))
        os.system(command)
    else:
        print("Error: Invalid cfg parameter [Matlab]->ScriptPath")
        sys.exit()


# Loads cfg info for EcotaxaExport, then runs
if __name__ == "__main__":

    # provide option for cfg path
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-p', '--cfgpath',
        required=False,
        help='<optional> path to cfg file, ' +CONFIGPATH+ ' as default'
    )
    args = parser.parse_args()
    if (args.cfgpath is not None):
        if os.path.isfile(args.cfgpath):
            CONFIGPATH = args.cfgpath
        else:
            print("Error: Provided cfg path does not exist!")
            sys.exit()

    exportFromEcotaxa()
    generateTable()




