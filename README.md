# EcotaxaScripts
Scripts for the export, import, and management of project data from Ecotaxa Servers

**Non-Native Packages:**

* argparse - used to add easy-to-read command arguments to scripts
* beautifulsoup4 - used for parsing html files for EcotaxaExport
* imageio - used in generating images for BuildMLDataSet
* requests - used for web-scraping with EcotaxaExport
* numpy - used for graphing in BuildMLDataSet
* pandas - used for easy reading of excel & csv files in BuildMLDataSet

# EcotaxaExport
**Summary:**
Using provided user information, connects to Ecotaxa server and pulls specific projects 
in basic .tsv format

**Arguments:**

* -u / --user           (required) email of Ecotaxa account
* -i / --ids            (required) ids of projects to be downloaded, separated by a space
    - 0 to export all projects
* -p / --path           (optional) path script will export to
    - default: cwd
* -a / --authorization  (optional) provide password for Ecotaxa via command-line
    - default: Manuel entry of password
```
example:
python3 EcotaxaExport -u exampleuser@website.net -i 1234 4321 0101 -p /path/of/export -a password
```

# BuildScientificDataSet
**Summary:**
Generates a matlab table struct using binary metadata from options stored in cfg file

**Arguments:**
* -p / --cfgpath (optional) defines path to cfg file
    - default: cwd
    - NOTE: WILL NOT RUN WITOUT CFG

```
example:
python3 BuildScientificDataSet.py -p /path/to/cfg
```

# BuildMLDataSet
**Summary:**
Converts exported tsv from local metadata into images titled by project ids

**Arguments:**
* -e / --ecotaxadirectory (required) path to exported ecotaxa tsv files
* -r / --rawdirectory (required) directory of IFCB folder containing raw binary metadata
* -o / --outputdirectory (optional) directory of desired output
    - default: ./Dataset in cwd
* -m / --mode (optional) specifies image titling options from taxonomy spreadsheet
    - choices: 'species' or 'group'
    - default: 'species'
* -t / --taxfile (optional) directory of taxonomic translation spreadsheet
    - default: cwd
    
```
example:
python3 BuildMLDataSet.py -e /Ecotaxa/TSV/Directory -r /IFCB/Binary/Data/ -o /Image/Output/Directory -m group -t /Taxonomy/Excel/File
```