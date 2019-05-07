# This script is intended to import data from EcoTaxa (ET) and export the images from the RAW data
# RAW data is required as the images on EcoTaxa have a size bar on them
#
# Output can be of three different forms:
#       + table with image_id and category
#       + folders with raw png for each category
#       + folders with formated png (resized) for each category (not available yet)
#       + binary file optimized for TensorFlow input            (not available yet)

import csv
import os, errno, argparse, sys, imageio
import numpy as np
from scipy import misc

# Packages for development
import time
import pandas as pd
import plotly.offline as py
import plotly.graph_objs as go


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


def checkValidDirects(raw, ecotaxa, out, tax):
    if not os.path.exists(raw):
        print("Error: Provided IFCB directory doesn't exist")
        sys.exit()
    if not os.path.exists(ecotaxa):
        print("Error: Provided ecotaxa tsv directory doesn't exist")
        sys.exit()
    if not os.path.exists(out):
        print("Error: Provided output directory doesn't exist")
        sys.exit()
    if not os.path.exists(tax):
        print("Error: Taxonomic grouping directory doesn't exist")
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

    args = parser.parse_args()

    #check provided directories exist & make img directory, save time if invalid
    if checkValidDirects(args.rawdirectory, args.ecotaxadirectory, args.outputdirectory, args.taxfile):
        translator = makeTrans(args.mode, args.taxfile)
        print("Parsing TSV file(s)")
        data = parseEcoTaxaDir(args.ecotaxadirectory, status=args.img_status)

        # Remove annotations from data with predicted status
        if args.img_status in ['predicted', 'dubious', 'unclassified']:
            for i in range(len(data['hierarchy'])):
                data['category'][i] = 'unclassified'
                data['hierarchy'][i] = 'unclassified'

        print('Number of images: ' + str(len(data['img_id'])))
        extractDeepLearn(data, args.rawdirectory, translator, args.outputdirectory)