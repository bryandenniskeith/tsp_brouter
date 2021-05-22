#!/usr/bin/python3
import sys
import os
import datetime
import random
import pickle
import brouter_call
import ogr_helper
from osgeo import ogr
import osgeo.osr as osr

def Usage():
    print ('tsp_brouter -h help')
    print ('            -verify input_file -l layer -fname name_field -limit number')
    print ('            -createdm input_file -l layer -fse se_field -fname name_field')
    print ('                out_distance_matrix')
    print ('            -routes -rt -ow -bf in_distance_matrix out_gpx')
    return
def Help():
    Usage()
    print ('   tsp_brouter has three modes: -verify -createdm -routes')
    print ("   -verify   Verify that the PTs in input_file are valid.  Can be limited to")
    print ("             number.  PTs will be tested against the brouter server in random")
    print ("             pairs.")
    print ('       input_file   The input PT file to be read by ogr.  The first layer will')
    print ('                    be used unless it is specifically named with')
    print ('       -l layer   The name of the layer in input_file to use.')
    print ('       -fname name_field   A string field in input_file with names of the PTs.')
    print ('                           Used to facilitate finding problematic PTs.')
    print ("   -createdm   Create the distance matrix and store it in a pickled file called")
    print ('               out_distance_matrix.')
    print ('       input_file   The input PT file (to be read by ogr) for the distance')
    print ('                    matrix.  The first layer will be used unless it is')
    print ('                    specifically named with')
    print ('       -l layer   The name of the layer in input_file to use.')
    print ("       -fse se_field   The name of the field to find 'start' and 'end' PTs for")
    print ("                       the -ow algorithms.  If not specified, the first PT")
    print ("                       found will be the startPT and the final PT read will be")
    print ("                       the end PT.")
    print ('       -fname name_field   Optionally specify a name field to generate a list')
    print ('                           of PT names to write to the output pickle file.')
    print ('   -routes')
    print ('       -rt round trip')
    print ('       -ow one way   You must specify --rt or --ow or both')
    print ('       -bf brute force algorithm; be very careful using this with more than 12')
    print ('           points.  It is very slow.')
    print ('       in_distance_matrix   The distance matrix file to send to the algorithms.')
    print ('       out_gpx   The output gpx file with the LNs of the routes.')
    print ('   -h help   Print this help')
    return

#save the start time of the script
begin_time = datetime.datetime.now()

#parse command line arguments
bRoundTrip = False
bOneWay = False
bBruteForce = False
bVerify = False
bCreateDM = False
bRoutes = False
sInput = None
sSEField = None
sNameField = None
sDM = None
sOutput = None
ogrDriver = None
sLayer = None
iLimit = None
if (len(sys.argv) < 2):
    Usage()
    sys.exit()
#check the first argument
arg = sys.argv[1]
if (arg == '-h'):
    Help()
    sys.exit()
elif (arg == '-verify'):
    bVerify = True
elif (arg == '-createdm'):
    bCreateDM = True
elif (arg == '-routes'):
    bRoutes = True
if (not (bVerify or bCreateDM or bRoutes)):
    print (f'invalid mode: {arg}')
    Usage()
    sys.exit()
i = 2
if (bVerify):
    while (i < len(sys.argv)):
        arg = sys.argv[i]
        if (arg == '-fname'):
            i += 1
            arg = sys.argv[i]
            sNameField = arg
        elif (arg == '-l'):
            i += 1
            arg = sys.argv[i]
            sLayer = arg
        elif (arg == '-limit'):
            i += 1
            arg = sys.argv[i]
            iLimit = arg
        elif (arg == '-h'):
            Help()
            sys.exit()
        elif (arg[0] == '-'):
            print (f'invalid option {arg}')
            Usage()
            sys.exit()
        elif (sInput == None):
            sInput = arg
        i += 1
    if (sInput == None):
        print ('not enough arguments with -verify')
        Usage()
        sys.exit()
    if (iLimit != None):
        try:
            fLimit = float(iLimit)
        except:
            print ('-limit number must be a number.')
            Usage()
            sys.exit()
        iLimit = int(fLimit)
        if (iLimit != fLimit or iLimit < 4):
            print ('-limit number must an integer > 3.')
            Usage()
            sys.exit()
elif (bCreateDM):
    while (i < len(sys.argv)):
        arg = sys.argv[i]
        if (arg == '-fname'):
            i += 1
            arg = sys.argv[i]
            sNameField = arg
        elif (arg == '-l'):
            i += 1
            arg = sys.argv[i]
            sLayer = arg
        elif (arg == '-fse'):
            i += 1
            arg = sys.argv[i]
            sSEField = arg
        elif (arg == '-h'):
            Help()
            sys.exit()
        elif (arg[0] == '-'):
            print (f'invalid option {arg}')
            Usage()
            sys.exit()
        elif (sInput == None):
            sInput = arg
        elif (sDM == None):
            sDM = arg
        i += 1
    if (sDM == None):
        print (f'not enough arguements with -createdm')
        Usage()
        sys.exit()
    #check to see if the distance matrix file already exists
    if (os.path.exists(sDM)):
        print (f'{sDM} exists.  Aborting.')
        sys.exit()
else: #run the algorithms
    while (i < len(sys.argv)):
        arg = sys.argv[i]
        if (arg == '-rt'):
            bRoundTrip = True
        elif (arg == '-ow'):
            bOneWay = True
        elif (arg == '-bf'):
            bBruteForce = True
        elif (arg == '-h'):
            Help()
            sys.exit()
        elif (arg[0] == '-'):
            print (f'invalid option {arg}')
            Usage()
            sys.exit()
        elif (sDM == None):
            sDM = arg
        elif (sOutput == None):
            sOutput = arg
        i += 1
    if (sOutput == None):
        print (f'not enough arguements with -routes')
        Usage()
        sys.exit()
    if (not (bRoundTrip or bOneWay)):
        print (f'You must specify one or both of: -rt -ow')
        Usage()
        sys.exit()
    #check to see if the distance matrix file exists
    if (not os.path.exists(sDM)):
        print (f'{sDM} does not exist.  Aborting.')
        sys.exit()
    
#open the input file, if needed
if (sInput != None):
    #check to see if the input file exists
    if (not os.path.exists(sInput)):
        print (f'{sInput} does not exist.  Aborting.')
        sys.exit()
    try:
        mDS = ogr.Open(sInput)
    except:
        print (f'{sInput} is not a valid ogr file.')
        sys.exit()
    if (sLayer == None):
        mLayer = mDS.GetLayer(0)
    else:
        mLayer = mDS.GetLayerByName(sLayer)

    #get the field indices, if given
    mFeature = mLayer.GetFeature(0)
    iSEFieldIndex = None
    if (sSEField != None):
        iSEFieldIndex = mFeature.GetFieldIndex(sSEField)
    iNameFieldIndex = None
    if (sNameField != None):
        iNameFieldIndex = mFeature.GetFieldIndex(sNameField)

    #make the output PT list
    mPTs = []
    mPTEnd = None
    lName = []

    #loop through the features
    for i in range(mLayer.GetFeatureCount()):
        mFeature = mLayer.GetFeature(i)
        mPT = mFeature.GetGeometryRef().Clone()
        mPTs += [mPT]
        if (iNameFieldIndex != None):
            lName += [mFeature.GetField(iNameFieldIndex)]
        else:
            lName += [f'{i}']
        if (iSEFieldIndex != None):
            sSE = mFeature.GetField(iSEFieldIndex)
            if (sSE == 'start'):
                #take the last items of the lists and make them first (start PT)
                mPTs.insert(0, mPTs.pop(-1))
                lName.insert(0, lName.pop(-1))
                            
            elif (sSE == 'end'):
                mPTEnd = mPTs.pop(-1)
                sNameEnd = lName.pop(-1)

    #add the end PT back in
    if (mPTEnd != None):
        mPTs += [mPTEnd]
        lName += [sNameEnd]

    iPTCount = len(mPTs)

if (bVerify):
    #shuffle the PT list and reduce it to -limit if requested
    lRandom = list(range(mLayer.GetFeatureCount()))
    random.shuffle(lRandom)

    mPTsOriginal = mPTs
    mPTs = []
    lNameOriginal = lName
    lName = []

    for i in range(len(lRandom)):
        mPTs += [mPTsOriginal[lRandom[i]]]
        lName += [lNameOriginal[lRandom[i]]]
        if (iLimit != None and iLimit - 1 <= i):
            break

    iPTCount = len(mPTs)

    bFailure = False
    lOutput = brouter_call.VerifyPTs(mPTs)

    for i in range(len(lOutput)):
        lTT = lOutput[i]
        if (not lTT[0]):
            bFailure = True
            r = lTT[1]
            if (r._body == b'from-position not mapped in existing datafile\n'):
                mPT = mPTs[i - 1]
                #from PTs are -1 from the list; while to PTs are i (the index)
                #print (f'point {lName[i - 1]} ({i}) ({mPT.GetX()} {mPT.GetY()}) is not close enough to the osm route network for brouter to process')
                #for debugging let's report like this
                print (f'problem (from) from {lName[i - 1]} to {lName[i]}') 
            elif (r._body == b'to-position not mapped in existing datafile\n'):
                #ignore this error because it should be taken care of with the
                #from PT
                print (f'problem (to) from {lName[i - 1]} to {lName[i]}') 
                continue
            else:
                print (f'point {lName[i]} unexpected error: {r._body}')

    if (not bFailure):

        print (f'Verified!  Your {len(mPTs)} points seem to work.  Try them for real!')
elif(bCreateDM):
    #get the times and geometries of our segments
    aTime, lGeom = brouter_call.GetTravelTimes(mPTs, True)
    #our distance matrix file will store a list with:
    # 0 -- the distance matrix as a 2d numpy array
    # 1 -- the geometry matrix as a 2d list 
    # 2 -- a list of the names of the PTs
    # 3 -- the list of PTs
    #the two dimensions of the matrices will have dimensions of the number
    #of PT in the list
    with open(sDM, 'wb') as filehandler:
        pickle.dump([aTime, lGeom, lName, mPTs], filehandler)
    print (f'{sDM} written')
    #sys.exit()
else:
    #run the algorithms here
    #get the time and geometry arrays from the distance matrix file
    with open(sDM, 'rb') as filehandler:
        #this will generate some errors; can they be safely ignored?
        lPickle = pickle.load(filehandler)
        
    aTime = lPickle[0]
    lGeom = lPickle[1]
    lName = lPickle[2]
    mPTs = lPickle[3]
    
    #iPTCount is simply to report at the end how many PTs were used; it's not
    #actually used for anything
    iPTCount = len(mPTs)

    #prepare the output file
    #only gpx is currently supported
    #we want to do this before starting the alorithms in case there's a
    #problem
    GPXdriver = ogr.GetDriverByName('GPX')
    mDS = GPXdriver.CreateDataSource(sOutput)
    # create the spatial reference, WGS84
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    # create the layer
    mLayer = mDS.CreateLayer("tracks", srs, ogr.wkbMultiLineString)

    #def GetShortestRoute(mPTs, aTime, lGeom, bRoundTrip, bOneWay, bIncludeBF = False):
    lOutput = brouter_call.GetShortestRoute(mPTs, aTime, lGeom, bRoundTrip, bOneWay, bBruteForce)
    #loop through the results from each algorithm
    for n in lOutput:
        #TO DO: add comments here; what's going on?  what is LTT?
        lTT = n[0]   #a list of the LNs making up the route
        iTime = n[1] #the time (in seconds) of the route
        sName = n[2] #the name of the algorithm used to get the route

        mLN = ogr_helper.CombineLNChain(lTT)

        mFeature = ogr.Feature(mLayer.GetLayerDefn())
        # Set the feature geometry using the point
        #any cloning required here?
        mFeature.SetGeometry(mLN)
        # 10 -- the first numeric field in the gpx output; an integer called
        #       "number"  used to store the route time
        mFeature.SetField2(10, iTime)
        #  0 -- the "name" field in the gpx output; used to store the
        #       source algorithm name of this route
        mFeature.SetField2(0, sName)

        # Create the feature in the layer
        mLayer.CreateFeature(mFeature)
        # Dereference the feature
        mFeature = None

    #save the gpx file (flush to disk)
    mDS = None

print (f'number of points: {iPTCount}')
print (f'script execution time:  {datetime.datetime.now() - begin_time}')
