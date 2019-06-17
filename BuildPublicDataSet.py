import BuildMLDataSet
import random
import os
import imageio
import sys
import numpy as np
from functools import lru_cache

b62list = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

rawdirect = "/Users/jasonmorrill/Desktop/Quickdirect/IFCB107"
tsvdirect = "/Users/jasonmorrill/Desktop/Quickdirect/EcoTaxa_20190613_111226"
outputdirect = "/Users/jasonmorrill/Desktop/KaggleFiles"
taxfiledirect = "/Users/jasonmorrill/Desktop/Quickdirect/taxonomic_grouping_v4.xlsx"
testfolder = 'TestSet'
learnfolder = 'LearnSet'
THRESHOLD = 10

def num2base62(num):
    """Converts int to custom base62 string"""
    base62 = ''
    while num != 0:
        num, i = divmod(num, len(b62list))
        base62 = b62list[i] + base62

    return base62

@lru_cache(maxsize=1)
def cachedRead(file):
    """Stores the last read to save time for multiple reads from the same file"""
    return BuildMLDataSet.readCSV(file)

def base62decode(b62):
    """Returns custom base62 string to int"""
    num = 0
    for i in range(len(b62)):
        num = (num * len(b62list)) + b62list.index(b62[i])
    return num


def getSubLists(startlist, subcount):
    """Breaks a given list of categories into 2 lists based on subcount"""
    testlist = random.sample(startlist, subcount)
    for i in testlist:
        startlist.remove(i)

    return startlist, testlist


def getSubsetSize(data, limit=10, testfrac=0.05):
    """Returns a dictionary of lists with structure:
    dict['valid'] - valid classes being used in dataset
    dict['learnsize'] - # of images being added to learnset
    dict['testsize'] - # of images being added to testset
    dict['short'] - classes being excluded due to count < limit"""
    sizedata = {}
    categories = sorted(set(data['category']))
    counts = [data['category'].count(c) for c in categories]

    short = []
    learn = []
    test = []
    # Add file to short if < limit
    for i in range(len(categories)):
        if counts[i] < limit:
            short.append(categories[i])
        # Otherwise split count into subset by fraction
        else:
            tvalue = int(round(testfrac * counts[i]))
            if tvalue == 0:
                tvalue = 1
            lvalue = counts[i] - tvalue
            test.append(tvalue)
            learn.append(lvalue)

    # Add to dictionary and return
    valid = [c for c in categories if c not in short]
    sizedata['valid'] = valid
    sizedata['learnsize'] = learn
    sizedata['testsize'] = test
    sizedata['short'] = short
    print(short)
    return sizedata


def sortIndicesByCategory(data, subdata):
    """Returns dictionary with valid classes as keys and lists of indices of data belonging
    to said class"""
    indexDict = {}
    for i in subdata['valid']:
        indexDict[i] = []

    for i in range(len(data['img_id'])):
        if (i + 1) % 1000 == 0:
            sys.stdout.write(F"\r {str(i+1)}  indexes categorized")
            sys.stdout.flush()
            # print(str(i + 1) + " indexes categorized")
        if data['category'][i] not in subdata['short']:
            indexDict[data['category'][i]].append(i)
    return indexDict


def translate(data, mode='species'):
    """Converts all categories according to taxo-spreadsheet + mode"""
    t = BuildMLDataSet.makeTrans(mode, taxfiledirect)
    for i in range(len(data['category'])):
        data['category'][i] = BuildMLDataSet.changeCategory(t, data['hierarchy'][i])
    return data


def generateMasterCSV(data):
    """Create masterCSV for building dataset"""
    # Begin labeling data
    print("Generating new master CSV")
    count = 2000000
    data['img_num'] = []
    data['img_name'] = []
    data['subset'] = []
    for i in range(len(data['img_id'])):
        data['img_num'].append(count)
        data['img_name'].append(num2base62(count))
        data['subset'].append(' ')
        count += 1

    # Establish valid categories and number of images for testing subset
    print("Generating subdata...", end=" ")
    subdata = getSubsetSize(data)
    print("Done!\nGenerating indices data...", end=" ")
    indicesdata = sortIndicesByCategory(data, subdata)
    print("Done!")

    # Split index lists into learning and testing sets, then label
    for i in indicesdata:
        print("Splitting and labeling class: "+ i)
        learn, test = getSubLists(indicesdata[i], subdata['testsize'][subdata['valid'].index(i)])
        for j in learn:
            data['subset'][j] = 'learn'
        for j in test:
            data['subset'][j] = 'test'
    print("Classes labeled, removing excess data...")
    # Strip Unnecessary Data and create mastercsv
    data.pop('person')
    data.pop('hierarchy')
    data.pop('status')
    print("Writing CSV...", end=" ")
    BuildMLDataSet.writeCSV('master.csv', data)
    print("Done!")
    return data


def loadMasterCSV(file):
    """Loads master CSV, and returns data as learn and test data"""
    # Load data from master file
    print("Loading data from master CSV...", end=" ")
    masterdata = BuildMLDataSet.readCSV(file)
    print("Done!")
    return masterdata


def splitMasterData(mdata):
    """ Splits master csv data and returns as test + learn subsets,
    ignoring subsets labeled as blank (short)"""
    # Create empty dictionaries with keys
    print("Splitting master data into subsets...", end = ' ')
    learndata = {}
    testdata = {}
    for i in mdata.keys():
        learndata[i] = []
        testdata[i] = []

    for i in range(len(mdata['subset'])):
        if mdata['subset'][i] == 'learn':
            for x in mdata:
                learndata[x].append(mdata[x][i])
        elif mdata['subset'][i] == 'test':
            for x in mdata:
                testdata[x].append(mdata[x][i])
        elif mdata['subset'][i] == ' ':
            pass
        else:
            print("Invalid subset read(valid= 'learn', 'test', or ' ')")
            sys.exit()
    print("Done!")
    return testdata, learndata


def makeSubsetCSV(subsetdata, metadirect):
    """Adds metadata & strips IFCB nomenclature in preparation for distribution"""
    max = len(subsetdata['img_id'])
    count = 1
    for i in subsetdata['img_id']:
        sys.stdout.write(F"\r Adding metadata {str(count)} of {max}")
        sys.stdout.flush()
        count += 1
        filename = i[:-6] +'.csv'
        roi_id = str(int(i[-5:]))
        try:
            filedata = cachedRead(os.path.join(metadirect,filename))
            index = filedata['ROIid'].index(roi_id)
        except FileNotFoundError:
            continue

        try:
            for key in filedata:
                if key != 'id' and key != 'ROIid':
                    subsetdata[key].append(filedata[key][index])
        except KeyError:
            for key in filedata:
                if key != 'id' and key != 'ROIid':
                    subsetdata[key] = []
                    subsetdata[key].append(filedata[key][index])
    subsetdata.pop('img_id')
    subsetdata.pop('img_num')
    subsetdata.pop('subset')
    subsetdata['category'] = subsetdata.pop('category')
    print("\nMetadata linked, generating file...", end=' ')
    BuildMLDataSet.writeCSV('learnfile.csv', subsetdata)
    print('Done!')


# TO DO
# Add any newly validated/added to dataset
# Generate Photos(Done in BuildMLDataSet)
# Move & relabel photos: /Testing, /Learning (/ClassFolders/)

raw_path = '/Users/jasonmorrill/Desktop/Quickdirect/IFCB107'
png_path = '/Users/jasonmorrill/Desktop/temp'
master_path = '/Users/jasonmorrill/Desktop/MasterCSV_example/master.csv'
meta_path = '/Users/jasonmorrill/Desktop/UnModded_IFCB_CSVs'
# data = BuildMLDataSet.parseEcoTaxaDir(tsvdirect, status='validated')
# data = translate(data)
# generateMasterCSV(data)
mdata = loadMasterCSV(master_path)
testdat, learndat = splitMasterData(mdata)
makeSubsetCSV(learndat, meta_path)


# s = getSubsetSize(data)


