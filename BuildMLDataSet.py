# This script is intended to import data from EcoTaxa (ET) and export the images from the RAW data
# RAW data is required as the images on EcoTaxa have a size bar on them
#
# Output can be of three different forms:
#       + table with image_id and category
#       + folders with raw png for each category
#       + folders with formated png (resized) for each category (not available yet)
#       + binary file optimized for TensorFlow input            (not available yet)

import os, errno, argparse, sys, imageio, random, csv
import numpy as np
from scipy import misc
from functools import lru_cache
from bisect import bisect_left
from multiprocessing import Pool

# Packages for development
import time
import pandas as pd
import plotly.offline as py
import plotly.graph_objs as go

B62LIST = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
THRESHOLD = 10
CNN_MIN_IMAGES = 1000
SUB_MAX_IMAGES = 10000
DEFAULT_ECOTAXA_FIELDNAME = {'img_id': 'object_id',
                             'person': 'object_annotation_person_name',
                             'category': 'object_annotation_category',
                             'hierarchy': 'object_annotation_hierarchy',
                             'status' : 'object_annotation_status'
                             }


def parseEcoTaxaFile(filename, check_status=True, status='validated', skip_2nd_line=False,
                     ecotaxa_fieldname=DEFAULT_ECOTAXA_FIELDNAME):
    with open(filename, 'r') as tsv:
        tsv = csv.reader(tsv, delimiter='\t')

        # Get header
        header = next(tsv)
        index = dict()
        index_status = header.index('object_annotation_status')
        for k,v in ecotaxa_fieldname.items(): index[k] = header.index(v)
        if skip_2nd_line: next(tsv)

        # Get data
        data = dict()
        for k in index.keys(): data[k] = list()
        for row in tsv:
            # Keep only validated data
            if not check_status or row[index_status] == status:
                for k in data.keys():
                    data[k].append(row[index[k]])

        return data


def parseEcoTaxaDir(dirname, recursive=True, ecotaxa_fieldname=DEFAULT_ECOTAXA_FIELDNAME, **kwargs):
    # Init data dict
    data = dict()
    for k in ecotaxa_fieldname.keys(): data[k] = list()

    # Loop through each file/dir name
    for f in os.listdir(dirname):
        df = os.path.join(dirname,f)
        if os.path.isdir(df):
            if recursive:
                foo = parseEcoTaxaDir(df, **kwargs)
                for k in data.keys():
                    data[k].extend(foo[k])
        elif df[-4:] == '.tsv':
            foo = parseEcoTaxaFile(df, **kwargs)
            for k in data.keys():
                data[k].extend(foo[k])

    return data


# Parse input with Panda (lot of text so slower)
# DEPRECATED as slower
def parseEcoTaxaFileWithPandas(filename):
    data = pd.read_csv(filename, sep='\t', header=0, skip_blank_lines=True)
    return data[['object_id', 'object_annotation_status', 'object_annotation_person_name', 'object_annotation_category', 'object_annotation_hierarchy']]


def parseEcoTaxaDirWithPandas(dirname, recusive=True):
    data= pd.DataFrame()
    for f in os.listdir(dirname):
        df = os.path.join(dirname,f)
        if os.path.isdir(df):
            if recusive:
                foo = parseEcoTaxaDirWithPandas(df)
                data.append(foo)
        elif df[-4:] == '.tsv':
            foo = parseEcoTaxaFileWithPandas(df)
            data.append(foo)
    return data


def writeUniqueHierarchy(data, filename):
    # Get unique sorted list of hierarchy
    hierarchy = sorted(set(data['hierarchy']))
    # Get suggested category name and counts
    category, counts = list(), list()
    for h in hierarchy:
        category.append(data['category'][data['hierarchy'].index(h)])
        counts.append(data['hierarchy'].count(h))
    # Output in csv
    writeCSV(filename, {'hierarchy':hierarchy, 'category': category, 'counts': counts},
            ['hierarchy', 'category', 'counts'])


def writeClassifiedTable(filename, data, categories, sort_by='img_id'):
    # Write CSV table containing all image id and categories
    #
    # INPUT:
    #   data <dict<list>> containing fields to filter data on and hierarchy and img_id
    #   sort_by <str> img_id or category

    # Extract category
    img_id = data['img_id']
    hierarchy = data['hierarchy']
    category = list()
    for h in hierarchy:
        category.append(categories[h])

    # Sort data
    if sort_by == 'img_id':
        i = sorted(range(len(img_id)), key=lambda k: img_id[k])
    elif sort_by == 'category':
        i = sorted(range(len(img_id)), key=lambda k: category[k])
    elif sort_by == 'hierarchy':
        i = sorted(range(len(img_id)), key=lambda k: hierarchy[k])
    else:
        raise ValueError('sort_by not valid')

    writeCSV(filename, {'img_id': [img_id[j] for j in i], 'category': [category[j] for j in i]}, {'img_id', 'category'})


def histByCategory(data, filename_figure, sort_by='count'):
    # Count data
    # data = readCSV(filename_data)
    categories = sorted(set(data['category']))
    counts = [data['category'].count(c) for c in categories]

    # Sort data
    if sort_by == 'count':
        i = sorted(range(len(counts)), key=lambda k: counts[k])
    elif sort_by == 'category':
        i = sorted(range(len(counts)), key=lambda k: categories[k])
    else:
        raise ValueError('sort_by not valid')
    categories = [categories[j] for j in i]
    counts = [counts[j] for j in i]

    # Plot bar chart with plotly
    trace1 = go.Bar(x=categories,y=counts,name='Images')
    # trace2 = go.Scatter(x=categories, y=CNN_MIN_IMAGES * np.ones(len(categories)), name='Threshold')
    layout = go.Layout(
        title='Number of images by categories (n=' + str(sum(counts)) + ')',
        xaxis=dict(tickangle=-45),
        yaxis=dict(type='log', autorange=True)
    )
    # fig = go.Figure(data=[trace1, trace2], layout=layout)
    fig = go.Figure(data=[trace1], layout=layout)
    py.plot(fig, filename=filename_figure, config={'showLink': False})


def updateCategories(data, categories, size_fractionnated=False):
    # Update category value of data with the category of "categories" based on the key hierarchy
    categories_dict = {h: c for h, c in zip(categories['hierarchy'], categories['category'])}
    data['category'] = [categories_dict[d] for d in data['hierarchy']]
    if not size_fractionnated:
        # return {'img_id':data['img_id'], 'category': [categories[d] for d in data['hierarchy']]}
        return data
    else:
        # If data is size fractionnated:
        #   data must contain a key 'size'
        #   categories must contain a key 'size_faction'
        # Then create sub-categories for each size fraction

        # Get categories size fractionnated
        size_fraction = dict()
        for sf, c in zip(categories['size_fraction'], categories['category']):
            if sf:
                limits = [int(n) for n in sf.split(';')]
                size_fraction[c] = {'limits': limits,
                                    'lower_category': c + '_<' + str(limits[0]),
                                    'bounded_categories': [c + '_' + str(l) + 'to' + str(h) for l, h in zip(limits[0:-1], limits[1:])],
                                    'higher_category': c + '_>' + str(limits[-1])}

        for c in size_fraction.keys():
            for i in range(len(data['category'])):
                if data['category'][i] == c:
                    # Check if below lower boundary of size
                    if data['size'][i] < size_fraction[c]['limits'][0]:
                        data['category'][i] = size_fraction[c]['lower_category']
                    # Check if above higher boundary of size
                    elif data['size'][i] >= size_fraction[c]['limits'][-1]:
                        data['category'][i] = size_fraction[c]['higher_category']
                    # Check if within boundaries
                    else:
                        for l, h, nc in zip(size_fraction[c]['limits'][0:-1],
                                            size_fraction[c]['limits'][1:],
                                            size_fraction[c]['bounded_categories']):
                            if l <= data['size'][i] < h:
                                data['category'][i] = nc
                                continue

        return data


#############
## Toolbox ##
#############

def benchmark(function_name, filename):
    start_time = time.clock()
    data = function_name(filename)
    # if __debug__: print('Length(data[0]): ' + str(len(data[0])))
    print(function_name.__name__ + ': ' + str(time.clock() - start_time) + " seconds")


def writeCSV(filename, data, keys=None):
    # Take dictionary of list (data) and write it in csv file
    # the parameter keys can be used to order the column as dict are not ordered or to include only specific keys
    if keys is None: keys = data.keys()
    with open(filename, "w") as fid:
        writer = csv.writer(fid, delimiter=",")
        writer.writerow(keys)
        writer.writerows(zip(*[data[key] for key in keys]))


def readCSV(filename):
    with open(filename, 'r') as fid:
        fid = csv.reader(fid, delimiter=',')
        # Get header line
        keys = next(fid)
        # Get content
        data = {k: [] for k in keys}
        for row in fid:
            for i, k in enumerate(keys):
                data[k].append(row[i])
        return data #, keys
    return None#, None

#Jason's functions

def makeTrans(mode, direct):
    # Make dictionary matching hierarchy to either prettified or grouped names
    df = pd.read_excel(direct)
    df['hierarchy'] = df['hierarchy'].replace(np.nan, 'unclassified', regex=True)
    if mode.lower() == 'species':
        translator = df.set_index('hierarchy')['category_prettified'].to_dict()
    elif mode.lower() == 'group':
        translator = df.set_index('hierarchy')['category_grouped'].to_dict()
    return translator


def changeCategory(translator, hierarchy):
    try:
        if hierarchy:
            result = translator[hierarchy]
        else:
            result = translator['unclassified']
    except KeyError:
        print("Error: hierarchy %s not found" % hierarchy)
        sys.exit()
    result = result.replace(' ', '-')
    result = result.replace('.', '')
    return result


def checkValidDirects(raw, ecotaxa, out, tax, meta):
    if not os.path.exists(raw):
        print("Error: Provided IFCB directory doesn't exist")
        sys.exit()
    if not os.path.exists(ecotaxa):
        print("Error: Provided ecotaxa tsv directory doesn't exist")
        sys.exit()
    if not os.path.exists(out):
        print("Provided output directory doesn't exist, creating...", end='')
        os.makedirs(out)
        print('Done!')
    if not os.path.exists(tax):
        print("Error: Taxonomic grouping directory doesn't exist")
        sys.exit()
    if not os.path.exists(meta):
        print("Error: Metadata directory does not exist")
        sys.exit()

    return True


# returns the str name of folder number in subdirectory
def getSubName(num):
    digits = len(str(num))
    return (('0'*(5-digits)) + str(num))


# identifies previous image extractions and resumes adding to last subdirectory
def resumeFromDir(path_png):
    filecount = len([f for f in os.listdir(path_png) if os.path.isdir(os.path.join(path_png, f))])
    # print("Folders in direct: "+ str(filecount))
    if filecount > 0:
        # Find greatest # folder
        max = 1;
        for x in os.listdir(path_png):
            if os.path.isdir(os.path.join(path_png, x)):
                if(int(x) > max):
                    max = int(x)

        # Find number of photos
        # print("Largest Folder Name: " + str(max))
        filecount = len([f for f in os.listdir(os.path.join(path_png,getSubName(max))) if f.endswith(".png")])
        # print("Last folder: "+ str(max)+ ", containing "+ str(filecount)+" images")
        return max, filecount
    else:
        return 1, 1


def extractDeepLearn(data, path_raw, translator, path_png):
    # Get each image by bin
    bin = [i[0:24] for i in data['img_id']]
    ubin = set(bin)
    fauind = 1

    # Init sub-directories
    activesub, imagenum = resumeFromDir(path_png)
    if activesub == 1:
        os.makedirs(os.path.join(path_png, getSubName(activesub)))

    #Needed, ensures path ends in trailing slash
    path_raw = os.path.join(path_raw, '')
    # Extract images
    for b in ubin:
        sys.stdout.write(F"\rExtracting bin {fauind} of {str(len(ubin))}")
        sys.stdout.flush()
        fauind += 1
        # Load ADC File
        # ADCFileFormat: trigger#, ADC_time, PMTA, PMTB, PMTC, PMTD, peakA, peakB, peakC, peakD, time of flight, grabtimestart, grabtimeend, ROIx, ROIy, ROIwidth, ROIheight,start_byte, comparator_out, STartPoint, SignalLength, status, runTime, inhibitTime
        adc = np.loadtxt(path_raw + b + '.adc', delimiter=',')
        width, height, start_byte = adc[:, 15].astype(int), adc[:, 16].astype(int), adc[:, 17].astype(int)
        end_byte = start_byte + width * height
        # end_byte = [start_byte[1:]].append(start_byte[-1] + width[-1] * height[-1])
        # Open ROI File
        roi = np.fromfile(path_raw + b + '.roi', 'uint8')
        # Get index of image, category, and status to extract
        roi_ids, roi_hier, roi_stat = list(), list(), list()
        for i, j, h, s in zip(data['img_id'], bin, data['hierarchy'], data['status']):
            if j == b:
                roi_ids.append(int(i[-5:]))
                roi_hier.append(h)
                roi_stat.append(s)

        # Extract images
        for i, h, s in zip(np.array(roi_ids) - 1, roi_hier, roi_stat):
            if start_byte[i] != end_byte[i]:
                imagenum+= 1
                if imagenum > SUB_MAX_IMAGES:
                    imagenum = 1
                    activesub += 1
                    os.mkdir(os.path.join(path_png,getSubName(activesub)))
                img = roi[start_byte[i]:end_byte[i]].reshape(height[i], width[i])
                category = changeCategory(translator, h)
                # Make image filename
                bsplit = b.split('_')
                imageio.imwrite(os.path.join(path_png, getSubName(activesub), '%s%sP%05d_%s.png' % (bsplit[1], bsplit[0], i + 1, category)), img)
            else:
                raise ValueError('Empty image was classified.')
    # Makes terminal cleaner
    print("")


# Kaggle Functions
def num2base62(num):
    """Converts int to custom base62 string"""
    base62 = ''
    while num != 0:
        num, i = divmod(num, len(B62LIST))
        base62 = B62LIST[i] + base62

    return base62


def base62decode(b62):
    """Returns custom base62 string to int"""
    num = 0
    for i in range(len(b62)):
        num = (num * len(B62LIST)) + B62LIST.index(b62[i])
    return num


def getSubLists(startlist, subcount):
    """Breaks a given list of categories into 2 lists based on subcount"""
    testlist = random.sample(startlist, subcount)
    for i in testlist:
        startlist.remove(i)

    return startlist, testlist


def getSubsetSize(data, bad_list=None, limit=10, testfrac=0.05):
    """Returns a dictionary of lists with structure:
    dict['valid'] - valid classes being used in dataset
    dict['learnsize'] - # of images being added to learnset
    dict['testsize'] - # of images being added to testset
    dict['short'] - classes being excluded due to count < limit or user request"""
    sizedata = {}
    short = []
    learn = []
    test = []
    categories = sorted(set(data['category']))
    if bad_list is not None:
        for i in bad_list:
            if i in categories:
                short.append(i)
                categories.remove(i)
            else:
                print("Error: Invalid category '"+i+"' in exclusion list")
    counts = [data['category'].count(c) for c in categories]

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
    # print(short)
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
    print('')
    return indexDict


def translate(data, taxfiledirect, mode='species'):
    """Converts all categories according to taxo-spreadsheet + mode"""
    t = makeTrans(mode, taxfiledirect)
    for i in range(len(data['category'])):
        data['category'][i] = changeCategory(t, data['hierarchy'][i])
    return data


def generateMasterCSV(data, output_path, bad_list):
    """Create masterCSV for building dataset"""
    # Begin labeling data
    print("Generating new master CSV...")
    count = 250000
    data['img_num'] = []
    data['img_name'] = []
    data['subset'] = []
    for i in range(len(data['img_id'])):
        data['img_num'].append(count)
        data['img_name'].append(num2base62(count))
        # default label is excluded, all used data will be rewritten
        data['subset'].append('exclude')
        count += 1

    # Establish valid categories and number of images for testing subset
    print("Generating subset size...", end=" ")
    subdata = getSubsetSize(data, bad_list)
    print("Done!\nLabeling subset indices...")
    indicesdata = sortIndicesByCategory(data, subdata)

    # Split index lists into learning and testing sets, then label
    for i in indicesdata:
        print("Splitting and labeling class: "+ i + "...", end=' ')
        learn, test = getSubLists(indicesdata[i], subdata['testsize'][subdata['valid'].index(i)])
        for j in learn:
            data['subset'][j] = 'learn'
        for j in test:
            data['subset'][j] = 'test'
        print('Done!')
    print("Classes labeled, removing excess data & writing to CSV...", end=" ")
    # Strip Unnecessary Data and create mastercsv
    data.pop('person')
    data.pop('hierarchy')
    data.pop('status')
    writeCSV(os.path.join(output_path, 'master.csv'), data)
    print("Done!")
    return data


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
        elif mdata['subset'][i] == 'exclude':
            pass
        else:
            print("Invalid subset read(valid= 'learn', 'test', or 'exclude')")
            print(mdata['subset'][i])
            sys.exit()
    print("Done!")
    return testdata, learndata


@lru_cache(maxsize=1)
def cachedRead(file):
    """Stores the last read to save time for multiple reads from the same file"""
    return readCSV(file)


def extractdate(id):
    """Pulls date in form YYYMMDD from id"""
    date = id[1:9]
    return int(date)


def makeSubsetCSV(subsetdata, metadirect, output_direct, file_name):
    """Adds metadata & strips IFCB nomenclature in preparation for distribution"""
    removefields = ['ESDV', 'PA', 'lat', 'long', 'img_num', 'subset', 'ConvexArea', 'ConvexPerimeter',
                    'Perimeter']
    fivedecfields = ['SSCIntegrated', 'SSCPeak', 'FLIntegrated', 'FLPeak']
    twodecfields = ['ESD', 'Biovolume', 'FeretDiameter', 'MajorAxisLength', 'MinorAxisLength']

    max = len(subsetdata['img_id'])
    count = 1
    for i in subsetdata['img_id']:
        if count % 10000 == 0:
            sys.stdout.write(F"\r Adding metadata {str(count)} of {max}")
            sys.stdout.flush()
        count += 1
        csvname = i[:-6] +'.csv'
        roi_id = str(int(i[-5:]))
        try:
            filedata = cachedRead(os.path.join(metadirect,csvname))
            index = filedata['ROIid'].index(roi_id)
        except FileNotFoundError:
            print(csvname)
            sys.exit()
        try:
            for key in filedata:
                if key != 'id' and key != 'ROIid':
                    subsetdata[key].append(filedata[key][index])
        except KeyError:
            for key in filedata:
                if key != 'id' and key != 'ROIid':
                    subsetdata[key] = []
                    subsetdata[key].append(filedata[key][index])

    # Clean up keys
    for x in removefields:
        subsetdata.pop(x)
    subsetdata['ImgName'] = subsetdata.pop('img_name')
    subsetdata['Category'] = subsetdata.pop('category')
    subsetdata['Date'] = subsetdata.pop('img_id')
    subsetdata['ESD'] = subsetdata.pop('ESDA')
    k = list(subsetdata.keys())
    for i in range(len(k)-4):
        subsetdata[k[0]] = subsetdata.pop(k[0])
        k = k[1:] + [k[0]]

    # Shorten specified categories into 2 & 5 decimal places, format date
    for i in range(len(subsetdata['ImgName'])):
        for j in fivedecfields:
            if subsetdata[j][i] != 'NaN':
                subsetdata[j][i] = '{0:.5f}'.format(float(subsetdata[j][i]))
        for j in twodecfields:
            if subsetdata[j][i] != 'NaN':
                subsetdata[j][i] = '{0:.2f}'.format(float(subsetdata[j][i]))
        subsetdata['Date'][i] = extractdate(subsetdata['Date'][i])

    print("\nMetadata linked, generating file...", end=' ')
    writeCSV(os.path.join(output_direct,file_name), subsetdata)
    print('Done!')


def getSortedDirect(subset, category, path_png, indexdict):
    """Taking a single element from imgdict generated in generateImages,
    this function returns the appropriate directory for that image"""
    directory = ''

    # Determine directory for image
    if subset == 'learn':
        directory = 'Learning'
    elif subset == 'test':
        directory = 'Testing'
    else:
        directory = 'Excluded'
    directory = directory + '/' + category + '/'

    # Determine subdirectory for image
    if directory in indexdict:
        key = directory
        directory = os.path.join(directory, getSubName(indexdict[key][0]))
        indexdict[key][1] += 1
        if indexdict[key][1] > SUB_MAX_IMAGES:
            indexdict[key][1] = 1
            indexdict[key][0] += 1
    else:
        indexdict[directory] = [1,1]
        key = directory
        directory = os.path.join(directory, getSubName(indexdict[directory][0]))
        indexdict[key][1] += 1

    # Merge with local directory for output location
    directory = os.path.join(path_png, directory)

    # If either sub or active directory d/n exist, make it
    if not os.path.isdir(directory):
        os.makedirs(directory)

    return directory, indexdict


def generateImages(masterdata, path_raw, path_png):
    """Create Images and move to appropriate directory"""
    # Make dictionary for naming images of format imgdict[img_id] = (img_name, subset)
    print("Creating naming dictionary...", end=' ')
    imgdict = {}
    for i in range(len(masterdata['img_id'])):
        imgdict[masterdata['img_id'][i]] = (
        masterdata['img_name'][i], masterdata['category'][i], masterdata['subset'][i])
        indexdict = {}
    print("Done!")

    # Get each image by bin
    bin = [i[0:24] for i in masterdata['img_id']]
    ubin = set(bin)
    fauind = 1

    # Needed, ensures path ends in trailing slash
    path_raw = os.path.join(path_raw, '')

    # Extract images
    for b in ubin:
        sys.stdout.write(F"\rExtracting bin {fauind} of {str(len(ubin))}")
        sys.stdout.flush()
        fauind += 1
        # Load ADC File
        # ADCFileFormat: trigger#, ADC_time, PMTA, PMTB, PMTC, PMTD, peakA, peakB, peakC, peakD, time of flight, grabtimestart, grabtimeend, ROIx, ROIy, ROIwidth, ROIheight,start_byte, comparator_out, STartPoint, SignalLength, status, runTime, inhibitTime
        adc = np.loadtxt(path_raw + b + '.adc', delimiter=',')
        width, height, start_byte = adc[:, 15].astype(int), adc[:, 16].astype(int), adc[:, 17].astype(int)
        end_byte = start_byte + width * height
        # end_byte = [start_byte[1:]].append(start_byte[-1] + width[-1] * height[-1])
        # Open ROI File
        roi = np.fromfile(path_raw + b + '.roi', 'uint8')
        # Get index of image, category, and status to extract
        ids = list()
        for i, j in zip(masterdata['img_id'], bin):
            if j == b:
                ids.append(int(i[-5:]))

        # Extract images
        for i in np.array(ids) - 1:
            if start_byte[i] != end_byte[i]:
                img = roi[start_byte[i]:end_byte[i]].reshape(height[i], width[i])
                # Make image filename
                name = '%s_%05d' % (b, i + 1)
                sorteddirect, indexdict = getSortedDirect(imgdict[name][2], imgdict[name][1], path_png, indexdict)
                imageio.imwrite(os.path.join(path_png, sorteddirect, (imgdict[name][0] + '.png')), img)
            else:
                raise ValueError('Empty image was classified.')
    # Makes terminal cleaner
    print("")


def newDataSet(ecotaxa_path, taxo_path, raw_path, meta_path, output_path, bad_list):
    """Generates a new dataset consisting of organized images and csv metadata for public
    learning and testing subsets, as well as a master csv file for identifying results.
    NOTE: The master CSV file SHOULD NOT be distributed"""

    # Confirm valid directories & generate output folder before starting
    checkValidDirects(raw_path, ecotaxa_path, output_path, taxo_path, meta_path)

    # Load data and translate it's categories
    print("Building masterdata...", end='')
    data = parseEcoTaxaDir(ecotaxa_path, status='validated')
    data = translate(data, taxo_path)
    print('Done!')

    # Write master data to CSV, then reload (Acts as save/stop point)
    data = generateMasterCSV(data, output_path, bad_list)
    #data = readCSV(os.path.join(output_path, 'master.csv'))

    # Generate images sorted into subsets
    generateImages(data, raw_path, output_path)

    # Split & write data into learning and testing CSVs
    testdata, learndata = splitMasterData(data)
    learn_direct = os.path.join(output_path, 'Learning')
    test_direct = os.path.join(output_path, 'Testing')

    makeSubsetCSV(testdata, meta_path, test_direct, 'testmeta.csv')
    makeSubsetCSV(learndata, meta_path, learn_direct, 'learnmeta.csv')

    # Produce csv of images excluded from subsets & label as excluded
    excludedata = {}
    for key in data:
        excludedata[key] = []

    for i in range(len(data['img_id'])):
        if data['subset'][i] == 'exclude':
            for key in data:
                excludedata[key].append(data[key][i])
    writeCSV(os.path.join(output_path, 'exclude.csv'), excludedata)


def binary_search(a, x, lo=0, hi=None):
    """Used to more rapidly search through large sorted data"""
    hi = hi if hi is not None else len(a)
    pos = bisect_left(a,x,lo,hi)
    return (pos if pos != hi and a[pos] == x else -1)


def validateDataSet(output_path):
    """Confirms images exist in expected directories & on meta CSV files"""
    subsetname = {
        'test': 'Testing',
        'learn' : 'Learning',
        ' ' : 'Excluded',
        'exclude' : 'Excluded'
    }

    # Use containing folder to get sub_directories
    master_path = os.path.join(output_path, 'master.csv')
    learn_path = os.path.join(output_path, 'Learning', 'learnmeta.csv')
    test_path = os.path.join(output_path, 'Testing', 'testmeta.csv')
    exclude_path = os.path.join(output_path, 'exclude.csv')

    # Read data into memory
    print("Loading data files: ")
    masterdata = readCSV(master_path)
    print('master.csv loaded!')
    learndata = readCSV(learn_path)
    learndata = sorted(learndata['img_name'])
    print('learnmeta.csv loaded & sorted')
    testdata = readCSV(test_path)
    testdata = sorted(testdata['img_name'])
    print('testmeta.csv loaded & sorted')
    excludedata = readCSV(exclude_path)
    excludedata = sorted(excludedata['img_name'])
    print('learnmeta.csv loaded & sorted')

    bad_imgs = []
    bad_metas = []

    masterlen = len(masterdata['img_name'])
    count = 1;
    for i in range(masterlen):
        if count % 10000 == 0:
            sys.stdout.write(F"\r Searching for img {str(count)} of {masterlen}")
            sys.stdout.flush()

        # Look for image
        imgname = masterdata['img_name'][i] + '.png'
        imgsub = subsetname[masterdata['subset'][i]]
        searchdirect = os.path.join(output_path, imgsub, masterdata['category'][i])
        found = False
        for i in os.listdir(searchdirect):
            if os.path.isfile(os.path.join(searchdirect, i, imgname)):
                found = True
                break
        if not found:
            bad_imgs.append(imgname)
        found = True

        # Look for metadata
        if imgsub == 'Learning':
            pos = binary_search(learndata,imgname)
            if pos != -1 or learndata[pos] != imgname:
                found = False
        elif imgsub == 'Testing':
            pos = binary_search(testdata, imgname)
            if pos != -1 or testdata[pos] != imgname:
                found = False
        else:
            pos = binary_search(excludedata, imgname)
            if pos != -1 or excludedata[pos] != imgname:
                found = False
        if not found:
            bad_metas.append(imgname)
        count += 1

    if (len(bad_imgs) and len(bad_metas)) == 0:
        print('\nAll data is accounted for!')
    else:
        print('\nMissing Images:')
        print(bad_imgs)
        print('Missing Metadata: ')
        print(bad_metas)


if __name__ == "__main__":
    # Command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-e', '--ecotaxadirectory',
        required=True,
        help='<required> directory of ecotaxa folder containing TSVs'
    )
    parser.add_argument(
        '-r', '--rawdirectory',
        required=True,
        help='<required> directory of IFCB folder containing raw photos'
    )
    parser.add_argument(
        '-meta', '--metadatadirectory',
        required=True,
        help='<required> location of metadata to be paired with images'
    )
    parser.add_argument(
        '-o', '--outputdirectory',
        required=False,
        help='<optional> directory of desired output, places PNGs into ./Dataset in cwd otherwise',
        default='dataset'
    )
    parser.add_argument(
        '-m', '--mode',
        required=False,
        choices=['species', 'group'],
        help='<optional> species = prettified(default), group = grouped',
        default='species'
    )
    parser.add_argument(
        '-t', '--taxfile',
        required=False,
        help='<optional> directory of taxonomic translation spreadsheet',
        default='taxonomic_grouping.xlsx'
    )
    parser.add_argument(
        '-s', '--img_status',
        required=False,
        help='<optional> status of image to export (validated by default)',
        default='validated'
    )
    parser.add_argument(
        '-c', '--classes',
        required=False,
        nargs='+',
        type=str,
        help="<optional> classes to be excluded from the final dataset, separated by spaces"
    )

    args = parser.parse_args()
    newDataSet(args.ecotaxadirectory, args.taxfile,args.rawdirectory, args.metadatadirectory, args.outputdirectory, args.classes)
    #validateDataSet(args.outputdirectory)
