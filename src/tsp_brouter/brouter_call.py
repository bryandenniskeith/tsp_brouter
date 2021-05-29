import urllib3
import sys
from osgeo import ogr
import osgeo.osr as osr
import itertools
import math
import numpy
import random
from tsp_brouter import ortools_tsp

#some tools for solutions to tsp problems (traveling salesman problem)
#where the "distances" are estimated times (or track_length or energy or cost)
#along a route returned by the brouter for the given profile

#available algorithms include:
#BF - a Brute Force algorithm that will find the best solution but can't be
#     used with more than about 12 PTs
#NN - a Nearest Neighbor algorithm that will start at a specified PT and always
#     continue to the next closest available PT
#SS - a Shortest Segment algorithm that will look at all segments and always
#     choose the shortest one of the remaining segments
#OR - the ORtools solution from google's ortools library

#all algorithsm are available in both
#OW - one way and
#RT - round trip versions

def GetShortestRoute(mPTs, aTime, lGeom, bRoundTrip, bOneWay, bIncludeBF = False):
    #this routine will call multiple TSP algorithms
    #mPTs is the list of PTs to consider; do not repeat the startPT at the
    #end PT; that will be added in where necessary; mPTs should be unique

    #set bRoundTrip to True to run the RT routines
    #set bOneway to True to run the OW routines
    #bRoundTrip or bOneway (or both) must be set to True
    #set bIncludeBF to include the brute force algorithm; be very cafeful
    #using this with more than 12 PTs

    #hold the output data here
    lOutput = []

    #print (f'len(mPTs): {len(mPTs)}')
    #print (f'aTimei GetShortestRoute\n{aTime}')

    #call the requested algorithms
    if (bRoundTrip):
        lOutput += [GetShortestRouteSS(mPTs, aTime, lGeom, True)]
        lOutput[-1] += ['RTSS']
        lOutput += [GetShortestRouteNNRT(mPTs, aTime, lGeom)]
        lOutput[-1] += ['RTNN'] 
        lOutput += [ortools_tsp.ReturnShortestRouteOR(mPTs, aTime, lGeom, True)]
        lOutput[-1] += ['RTOR'] 
        if (bIncludeBF):
            lOutput += [GetShortestRouteBF(mPTs, aTime, lGeom, True)]
            lOutput[-1] += ['RTBF'] 

    if (bOneWay):
        lOutput += [GetShortestRouteSS(mPTs, aTime, lGeom, False)]
        lOutput[-1] += ['OWSS'] 
        lOutput += [GetShortestRouteNN(mPTs, aTime, lGeom)]
        lOutput[-1] += ['OWNN'] 
        lOutput += [ortools_tsp.ReturnShortestRouteOR(mPTs, aTime, lGeom, False)]
        lOutput[-1] += ['OWOR'] 
        if (bIncludeBF):
            lOutput += [GetShortestRouteBF(mPTs, aTime, lGeom, False)]
            lOutput[-1] += ['OWBF'] 

    return lOutput

#progess bar
def progress(count, total, suffix=''):
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', suffix))
    sys.stdout.flush()  # As suggested by Rom Ruben

def DefineServersProfiles():
    #the key in this dictionary is the name of the server as used by me
    #the data is a dictionary with the following entries
    # sURLGET -- the URL to send with the GET request to return a geojson of the
    #      route and information about the route
    # sURLWeb -- the URL to see the route in a browser; I'm not dealing with the
    #      zoom level at this point; that would involve looking at the
    #      bounding box of the input PTs and knowing the appropriate zoom
    #      level to display said box; or, better, get the bounding box of the
    #      returned route and use that instead
    # sURLPOST -- the URL to send with the POST request to send a custom profile to the server
    # lProfile -- a list of the known profiles; surely there are more unknown
    #      profiles
    dbrouter = {
        'sURLGET' : "https://brouter.de/brouter?lonlats={fStartX:.6f},{fStartY:.6f}|{fEndX:.6f},{fEndY:.6f}&profile={sProfile}&alternativeidx=0&format=geojson", 
        'sURLWeb' : 'https://brouter.de/brouter-web/#map=10/{fMidY:.6f}/{fMidX:.6f}/standard&lonlats={fStartX:.6f},{fStartY:.6f};{fEndX:.6f},{fEndY:.6f}&profile={sProfile}',
        'sURLPOST' : 'https://brouter.de/brouter/profile/{sProfile}',
        'lProfile' :  
            ['trekking',
            'fastbike',
            'car-eco',
            'car-fast',
            'safety',
            'shortest',
            'trekking-ignore-cr',
            'trekking-steep',
            'trekking-noferries',
            'trekking-nosteps',
            'moped',
            'rail',
            'river',
            'vm-forum-liegerad-schnell',
            'vm-forum-velomobil-schnell',
            'fastbike-lowtraffic',
            'fastbike-asia-pacific',
            'hiking-beta']
        }
    dm11n = {
        'sURLGET' : "https://brouter.m11n.de/brouter-engine/brouter?lonlats={fStartX:.6f},{fStartY:.6f}|{fEndX:.6f},{fEndY:.6f}&profile={sProfile}&alternativeidx=0&format=geojson",
        'sURLWeb' : 'https://brouter.m11n.de/#map=11/{fMidY:.6f}/{fMidX:.6f}/standard&lonlats={fStartX:.6f},{fStartY:.6f};{fEndX:.6f},{fEndY:.6f}&profile={sProfile}',
        'sURLPOST' : 'https://brouter.m11n.de/brouter-engine/brouter/profile/{sProfile}',
        'lProfile' :  
            ['Fastbike-lowtraffic-tertiaries',
            'fastbike-lowtraffic',
            'fastbike',
            'm11n-gravel-pre',
            'm11n-gravel',
            'cxb-gravel',
            'Trekking-tracks',
            'mtb-zossebart',
            'mtb-zossebart-hard',
            'MTB',
            'MTB-light',
            'trekking',
            'fastbike-asia-pacific',
            'fastbike-verylowtraffic',
            'MTB-light-wet',
            'MTB-wet',
            'reroute-zossebart',
            'Trekking-dry',
            'Trekking-Fast-wet',
            'Trekking-Fast',
            'Trekking-FCR-dry',
            'Trekking-FCR-wet',
            'Trekking-hilly-paths',
            'Trekking-ICR-dry',
            'Trekking-ICR-wet',
            'trekking-ignore-cr',
            'Trekking-LCR-dry',
            'Trekking-LCR-wet',
            'Trekking-MTB-light-wet',
            'Trekking-MTB-light',
            'Trekking-MTB-medium-wet',
            'Trekking-MTB-medium',
            'Trekking-MTB-strong-wet',
            'Trekking-MTB-strong',
            'Trekking-No-Flat',
            'trekking-noferries',
            'trekking-nosteps',
            'Trekking-SmallRoads-wet',
            'Trekking-SmallRoads',
            'trekking-steep',
            'Trekking-Tertiaries',
            'Trekking-valley',
            'Trekking-wet',
            'vm-forum-liegerad-schnell',
            'vm-forum-velomobil-schnell',
            'car-eco',
            'car-fast',
            'car-vario',
            'dummy',
            'hiking-beta',
            'moped',
            'rail',
            'river',
            'safety',
            'shortest']
        }
    ddamsy = {
        'sURLGET' : "https://brouter.damsy.net/api/brouter?lonlats={fStartX:.6f},{fStartY:.6f}|{fEndX:.6f},{fEndY:.6f}&profile={sProfile}&alternativeidx=0&format=geojson",
        'sURLWeb' : 'https://brouter.damsy.net/latest/#map=11/{fMidY:.6f}/{fMidX:.6f}/standard&lonlats={fStartX:.6f},{fStartY:.6f};{fEndX:.6f},{fEndY:.6f}&profile={sProfile}',
        'sURLPOST' : 'https://brouter.damsy.net/api/brouter/profile/{sProfile}',
        'lProfile' :  
            ['trekking',
            'fastbike',
            'safety',
            'shortest',
            'trekking-ignore-cr',
            'trekking-steep',
            'trekking-noferries',
            'trekking-nosteps',
            'fastbike-lowtraffic',
            'rail',
            'river',
            'vm-forum-liegerad-schnell',
            'vm-forum-velomobil-schnell',
            'fastbike-asia-pacific',
            'moped',
            'car-test',
            'hiking-beta']
        }
    dServer = {
        'brouter' : dbrouter,
        'm11n' : dm11n,
        'damsy' : ddamsy
        }
    return dServer 

def POSTCustomProfile(sInputFN, sServer):
    #create a custom profile name and post the custom profile to the server

    #get the POST URL for the requested server
    dServer = DefineServersProfiles()
    dURL = dServer[sServer]
    sURLPOST = dURL['sURLPOST']

    #make a temporary file name for the server
    iRandomName = random.randint(10 ** 12, (10 ** 13) - 1)
    sProfile = f'custom_{iRandomName}'
    #add the new profile name to the POST URL
    sURLPOST = sURLPOST.format(sProfile = sProfile) 

    #send the POST request to get the custom profile (brf) to the server
    http = urllib3.PoolManager()
    with open(sInputFN, 'rb') as fp:
        binary_data = fp.read()
    try:
        r = http.request(
            'POST',
             sURLPOST,
            body=binary_data
        )
    except:
        print ('POSTing custom profile to server {sServer} failed.')
        print ('This URL failed:')
        print (sURLPOST)
        print ('Maybe try a different server?')
        sys.exit()
    print (f'custom profile {sInputFN} posted to {sServer} server as\n{sProfile}')

    return sProfile

def GetTravelTime(mPTStart, mPTEnd, sServer, sProfile):
    #given two xy pairs (ogr PTs) in wgs84 this will attempt to return the
    #travel time between them on a trekking bicycle based on the brouter
    #trekking bike algorithm at brouter

    #both the server (brouter) and the brouter script (bicycle touring) are
    #hard-coded here

    #this routine returns a list with 4 items:
    # 0 -- a boolean, True if the routine was successful; False is for error
    #      trapping, but I haven't done anything with it yet; failure happens
    #      if you're too far from the osm route network and likely other ways
    #      that I haven't discovered yet
    # 1 -- travel time in seconds between the PTs
    # 2 -- an ogr line of the suggested route
    # 3 -- the geojson data

    fStartX = mPTStart.GetX()
    fStartY = mPTStart.GetY()
    fEndX = mPTEnd.GetX()
    fEndY = mPTEnd.GetY()

    fMidX = (fStartX + fEndX) / 2
    fMidY = (fStartY + fEndY) / 2

    #get the router server dictionary
    dRouter = DefineServersProfiles()
    dURL = dRouter[sServer]
    sURL = dURL['sURLGET'].format(fStartX = fStartX, fStartY = fStartY, fEndX = fEndX, fEndY = fEndY, sProfile = sProfile)
    sURLBrowser = dURL['sURLWeb'].format(fStartX = fStartX, fStartY = fStartY, fEndX = fEndX, fEndY = fEndY, fMidX = fMidX, fMidY = fMidY, sProfile = sProfile)


    #example URL for a browser
    #10 is the zoom level and the hard-coded PT is the center of the map
    #I don't believe they affect the returned route in any way
    #sURLBrowser = f'https://brouter.de/brouter-web/#map=10/36.6045/30.2117/standard&lonlats={fStartX:.6f},{fStartY:.6f};{fEndX:.6f},{fEndY:.6f}'
    #print (sURLBrowser)

    #we'll send a GET request to the website and see if it returns us data
    #example URL for a GET reques
    #sURL = "https://brouter.de/brouter?lonlats=30.326007,36.374856|29.842805,36.648589&profile=trekking&alternativeidx=0&format=geojson"
    #sURL = f"https://brouter.de/brouter?lonlats={fStartX:.6f},{fStartY:.6f}|{fEndX:.6f},{fEndY:.6f}&profile=trekking&alternativeidx=0&format=geojson"

    #here's the url for a profile that is more gravel friendly
    #sURL = f"https://brouter.m11n.de/brouter-engine/brouter?lonlats={fStartX:.6f},{fStartY:.6f}|{fEndX:.6f},{fEndY:.6f}&profile=m11n-gravel&alternativeidx=0&format=geojson"

    #with this:
    #POST https://brouter.m11n.de/brouter-engine/brouter/profile/custom_1621854674832
    #I'm able to post a custom profile to the server (the POST asks for the 
    #data which I end with crtl-d
    #I can see that the profile is there by looking in the browser like this:
    #https://brouter.m11n.de/#map=13/37.2158/31.1761/standard&lonlats=31.17907,37.237313;31.127443,37.228862&profile=custom_1621854674832

    http = urllib3.PoolManager()
    r = http.request('GET', sURL)

    #r.data is geojson data!

    JSONdriver = ogr.GetDriverByName('GeoJSON')
    mGeoData = JSONdriver.Open(r.data, 0)
    #there appears to be only one layer
    try:
        mLayer = mGeoData.GetLayerByIndex(0)
    except:
        #for now just return the browser url of the problem point
        return [False, r, sURLBrowser]
    #and there appears to be only one feature
    mFeature = mLayer.GetFeature(0)
    
    #field 5 (0-based) is the time in seconds as a string
    iTime = int(mFeature.GetField(5))
    mGeom = mFeature.GetGeometryRef()
    #you can get the length of this feature, but it's in decimal degrees
    #if you really need the length, it makes sense to convert it to UTM first
    return [True, iTime, mGeom.Clone(), r.data]

def GetTravelTimes(mPTs, bRoundTrip, sServer, sProfile):
    #this routine gets all the travel times and routes connecting all the PTs
    #in mPTs

    #if bRoundTrip is False, then segments going to the start PT and from the
    #end PT (the first and last PTs in mPTs, respectively) will be excluded
    #all this does is mean that there are fewer calls to the server

    #it returns a list with two items:
    #0 - a 2d numpy array where a[i, j] is the time in seconds from PT i to PT j
    #    empty records will be numpy.inf
    #1 - a 2d list where l[i][j] is the route (ogr line) from PT i to PT j

    #set the number of PTs I'm dealing with
    iPTCount = len(mPTs)

    #initialize my arrays to hold times and geometries
    #missing values in the numpy array will be numpy.inf which comes in
    #handy with the SS algorithms that continuously look for the shortest
    #remaining segment (almost everything is less than infinity)
    aTime = numpy.matrix(numpy.ones((iPTCount, iPTCount)) * numpy.inf)
    #create a 2d list to hold the geometries
    lGeom = [[None for i in range(iPTCount)] for j in range(iPTCount)]

    #it makes more sense to just send the geoJSON data to pickle
    lGeoJSON = [[None for i in range(iPTCount)] for j in range(iPTCount)]

    #when you unpickle geometries, an error:
    #ERROR 1: Empty geometries cannot be constructed
    #is printed to the console.  I tried the following (and a couple other
    #things) but couldn't get it to go away.  Can I just ignore that error?
    #lGeom = [[ogr.CreateGeometryFromWkt('LINESTRING (0 0, 0 0)') for i in range(iPTCount)] for j in range(iPTCount)]

    #for testing
    #initialize my arrays to hold times and geometries
    #aTime = numpy.matrix(numpy.ones((iPTCount + 1, iPTCount + 1)) * numpy.inf)
    #create a 2d list to hold the geometries
    #lGeom = [[None for i in range(iPTCount + 1)] for j in range(iPTCount + 1)]

    #for status bar
    iSTTotal = iPTCount * iPTCount

    #fill the arrays with the times and geometries
    for i in range(iPTCount):
        #if it's a oneway trip, skip the last PT as from PT
        if (not bRoundTrip and i == iPTCount - 1):
            continue
        for j in range(iPTCount):
            #skip if the to and from PTs are the same
            if (i == j):
                continue
            #if it's a oneway trip, skip the first PT as a to PT
            if (not bRoundTrip and j == 0):
                continue
            #if it's a oneway trip, don't go from start PT to end PT directly
            if (not bRoundTrip and i == 0 and (j == iPTCount - 1)):
                continue
            #get the times and the geometries
            lTT = GetTravelTime(mPTs[i], mPTs[j], sServer, sProfile)
            #error trapping for failed http request
            if (not lTT[0]):
                r = lTT[1]
                sURLBrowser = lTT[2]
                print (f'Call to server {sServer} failed.  Did you verify your points first?') 
                print (f'Does the following URL work for you?\n{sURLBrowser}')
                print ('Aborting')
                sys.exit()
            aTime[i, j] = lTT[1]
            lGeom[i][j] = lTT[2]
            lGeoJSON[i][j] = lTT[3]

            #progress bar
            progress ((i * iPTCount) + j, iPTCount ** 2)
    
    #finish the progress bar
    progress (iPTCount, iPTCount)
    sys.stdout.write('\n')

    return [aTime, lGeom, lGeoJSON]

def ReturnTimeGeometryFromGeoJSON(lGeoJSON, iField):
    #this routime will return the distance matrix (aTime) and geometry (LN)
    #matrix from a GeoJSON matrix
    #iField will be the index of the field for the data to use in the
    #distance matrix where:
    # 2 -- track_length
    # 5 -- time
    # 6 -- energy
    # 7 -- cost

    #set the number of PTs I'm dealing with
    iPTCount = len(lGeoJSON)

    #initialize my arrays to hold times and geometries
    #missing values in the numpy array will be numpy.inf which comes in
    #handy with the SS algorithms that continuously look for the shortest
    #remaining segment (almost everything is less than infinity)
    aTime = numpy.matrix(numpy.ones((iPTCount, iPTCount)) * numpy.inf)
    #create a 2d list to hold the geometries
    lGeom = [[None for i in range(iPTCount)] for j in range(iPTCount)]
    JSONdriver = ogr.GetDriverByName('GeoJSON')

    #loop through the GeoJSON data
    for i in range(len(lGeoJSON)):
        for j in range(len(lGeoJSON)):
            mGeoJSON = lGeoJSON[i][j]
            if (mGeoJSON != None):
                mGeoData = JSONdriver.Open(mGeoJSON, 0)
                #there appears to be only one layer
                mLayer = mGeoData.GetLayerByIndex(0)
                #and there appears to be only one feature
                mFeature = mLayer.GetFeature(0)
                
                #field 5 (0-based) is the time in seconds as a string
                iTime = int(mFeature.GetField(iField))
                mGeom = mFeature.GetGeometryRef()
                
                aTime[i, j] = iTime
                lGeom[i][j] = mGeom.Clone()

    return [aTime, lGeom]

def GetShortestRouteBF(mPTsOriginal, aTime, lGeom, bRoundTrip = False):
    #this routine returns a list of geometries (lines) of the shortest (by
    #definition previously explained) route; brute force algorithm

    #use bRouteTrip = True if you want a round trip; do not repeat the first
    #PT as the last PT

    #for a round trip just repeat the first PT as the last PT
    if (bRoundTrip == True):
        #I should not change the original PT list
        mPTs = []
        for i in range(len(mPTsOriginal)):
            mPTs += [mPTsOriginal[i].Clone()]
            
        mPTs += [mPTsOriginal[0].Clone()]
    else:
        mPTs = mPTsOriginal

    #let's loop through all possible routes
    #brute force stuff happens here
    #calculate the number of intermediate PTs; we don't need permutations
    #on the first and last PTs because we know they are the first and last PTs
    iIntermediatePC = len(mPTs) - 2

    #make a set to send to itertools
    #this is an ordered set starting with 1 (0 is for the start point which
    #is always the same and known ahead of time) up to the number of
    #intermediate PTs
    mSet = set([1 + x for x in range(iIntermediatePC)])

    #make an iterator with all the possible routes
    #warning: combinatorial! (see below, factorial!)
    mIterator = itertools.permutations(mSet)
    #calculate the number of permutations
    iAllToursCount = math.factorial(iIntermediatePC)

    #make an empty list to store the total time of each tour
    #we'll use this later to find the shortest tour time (it will be the
    #lowest value in this list)
    #this is a big list; is there a better way to store this?
    lTourTime = [None] * iAllToursCount

    #make a dictionary to store the tour segment time and route
    #we need to look at very few segments compared to the number of route
    #possibilities
    dTT = {}
    #i is used for the progress bar
    i = 0
    #loop through all the possible tours
    for tTour in mIterator:
        #loop through a single tour
        iTime = 0
        # + 1 here because tTour is only the intermediate PTs; we need to
        #start at the start PT
        for j in range(len(tTour) + 1):
            #get the index of the start and end points of this segment,
            #returned as a tuple used as the index for the dictionary
            tSegmentIndex = GetSegmentIndex(j, tTour, bRoundTrip)

            #add to the tour time the time of this segment
            iTime += aTime[tSegmentIndex[0],tSegmentIndex[1]]

        #store all the tour times here; we'll want to know the shortest time
        #later
        lTourTime[i] = iTime
        #update the progress bar
        progress (i, iAllToursCount)
        i += 1

    #finish the progress bar
    progress (iAllToursCount, iAllToursCount)
    sys.stdout.write('\n')

    #get the index of the shortest tour
    #this will throw an error if None is present
    iTimeOutput = min(lTourTime)
    iMinIndex = lTourTime.index(iTimeOutput)
    #I need to iterate again, and I guess I need to regenerate the iterator
    #it will always return the same order because mSet is ordered; see:
    #https://docs.python.org/3/library/itertools.html

    #get the shortest tour from the iterator
    mIterator = itertools.permutations(mSet)
    tShortTour = nth(mIterator, iMinIndex)
        
    #get the geometries for this tour
    lGeomOutput = []
    for j in range(len(tShortTour) + 1):
        tSegmentIndex = GetSegmentIndex(j, tShortTour, bRoundTrip)
        lGeomOutput += [lGeom[tSegmentIndex[0]][tSegmentIndex[1]]]

    return [lGeomOutput, iTimeOutput]

def GetSegmentIndex(j, tTour, bRoundTrip):
    #a helper function for the brute force algorithm

    #our iterator ignores the start and end points since they're fixed (as I
    #defined the problem) when we're looping through a potential route;
    #this routine will get us indices of the segments, returned as a tuple
    #which is the key for the dictionary to store the time and geometry

    #get the index of the start and end points
    if (j == 0):
        iStartIndex = 0
    else:
        iStartIndex = tTour[j - 1]
    if (j == len(tTour)):
        if (bRoundTrip):
            #go to the first column (row?) to get the data
            iEndIndex = 0
        else:
            iEndIndex = j + 1
    else:
        iEndIndex = tTour[j]
    tSegmentIndex = (iStartIndex, iEndIndex)
    return tSegmentIndex

def nth(iterable, n, default=None):
    #a helper function for the brute force algorithm
    #this routine returns the nth value of an iterator; some people are very
    #clever
    "Returns the nth item or a default value"
    return next(itertools.islice(iterable, n, None), default)
#see:
#https://docs.python.org/3/library/itertools.html

def GetShortestRouteNN(mPTsOriginal, aTime = None, lGeom = None,
        iStartPTIndex = 0):
    #this function calls both the
    #GetShortestRouteNNForward and
    #GetShortestRouteNNReverse routines and returns the shorter route

    #iStartPTIndex is only used to output the times for every PT
    #if the arrays have been rolled (see GetShortestRouteNNRT)), then the
    #startPT may be something other than the startPT in the used-provided list

    lGeomF, iTimeF = GetShortestRouteNNForward(mPTsOriginal, aTime, lGeom)
    lGeomR, iTimeR = GetShortestRouteNNReverse(mPTsOriginal, aTime, lGeom)
   
    #intermediate results are now available here; for now just print them to
    #the screen
    for iTime, sD in [[iTimeF, 'F'], [iTimeR, 'R']]:
        print (f'NN{sD}: {iTime} startPT: {iStartPTIndex} PTCount: {len(mPTsOriginal)}')
 
    if (iTimeF > iTimeR):
        lGeomOutput = lGeomR
        iTime = iTimeR
    else:
        lGeomOutput = lGeomF
        iTime = iTimeF
    return [lGeomOutput, iTime]

def GetShortestRouteNNRT(mPTsOriginal, aTime, lGeom):
    #this routine will try starting at every single point in both directions
    #and return the shortest route using the Nearest Neighbor algorithm

    #if you just want one Nearest Neighbor RT, you can send your mPTs to one
    #of the other NN algorithms and just repeat the start PT at the end

    #I need to clone all these PTs because I don't want to change the
    #original PT list
    mPTs = []
    for i in range(len(mPTsOriginal)):
        mPTs += [mPTsOriginal[i].Clone()]
        
    #add the first PT to the end of the list because this is a round trip
    #problem
    mPTs += [mPTsOriginal[0].Clone()]

    #keep track of lowest time
    iTimeOutput = None

    #print (f'aTime GetShortestRouteNNRT\n{aTime}')

    # -1 here because the startPT and endPT are the same; I don't need to try
    # starting at both the startPT and endPT if they're the same
    for n in range(len(mPTs) - 1):
        #send to NN algorithm
        lGeomTemp, iTimeTemp = GetShortestRouteNN(mPTs, aTime , lGeom,
            n)
        
        #save only the shortest route
        if (iTimeOutput == None or iTimeTemp < iTimeOutput):
            iTimeOutput = iTimeTemp
            lGeomOutput = lGeomTemp
        #I need to shuffle the lists and the numpy array
        #the idea is to move the first PT in the list to the last
        #remove the first item of the PT list
        mPTs.pop(0)
        #add the new first PT to the end
        mPTs += [mPTs[0]]
        #move the values in the first row of the array to the bottom
        #just like we did with the PTs
        aTime = numpy.roll(aTime, -1, axis = 0) 
        #move the values in each row one to the left (because when you
        #switch the start PT to what used to be the second PT and
        #everything else switches up, well, you need to move the array
        #along both axes
        aTime = numpy.roll(aTime, -1, axis = 1)
        #take the top geometry row and put it on the bottom
        lGeom.append(lGeom.pop(0))
        #now move along the second axis
        for i in range(len(lGeom)):
            lGeom[i].append(lGeom[i].pop(0))

    #print (f'aTime GetShortestRouteNNRT\n{aTime}')
    return [lGeomOutput, iTimeOutput]

def GetShortestRouteNNForward(mPTsOriginal, aTime = None, lGeom = None,
        sServer = None, sProfile = None):
    #this routine takes a list of ogr PTs and returns the "shortest" route
    #using a nearest neighor algorithm (shortest being minimizing whatever
    #data is in aTime)
    #it is expected that the first PT in the list is the start point and
    #the last PT in the last is the end point

    #you can optionally send the segment data and geometry arrays
    #(GetTravelTimes formats)
    #if not, it's no big deal 'cause this routine run once makes minimum
    #server calls; in that instance (not supplying aTime and lGeom) you must
    #specify the server (sServer) and profile (sProfile)

    #make an empty list to store the output geometries
    lGeomOutput = []

    #make a copy of the list of PTs; we need it later to find the indices if
    #times and geometries are provided
    mPTs = None
    if (lGeom != None):
        mPTs = mPTsOriginal.copy()

    #the first PT in the list is expected to be the start PT for this
    #segment; take it and remove it (pop)
    mStartPT = mPTs.pop(0)

    #store the total time here
    iTotalTime = 0

    while (len(mPTs) > 0):
        #make an empty lists to store the segment times and geometries
        lTime = []
        lSegmentGeom = []

        #get the number of PTs left
        iPTCount = len(mPTs)
        #loop through the PTs in the list and find the segments' travel time
        #and geometry
        for j in range(iPTCount):
            #I don't want this to run for the final PT unless it's the only
            #one left
            #why not? because it is the explicitly stated end PT of the route
            #at the end we just have to take it no matter what it's value
            #(travel time) is
            if (j == (iPTCount - 1) and iPTCount > 1):
                break

            #use the times and geometries provided, if provided
            #if not, call GetTravelTime
            if (lGeom == None):
                lTT = GetTravelTime(mStartPT, mPTs[j], sServer, sProfile)
            else:
                lTT = ReturnTTFromPTs(mStartPT, mPTs[j], mPTsOriginal, aTime,
                    lGeom)

            lTime += [lTT[1]]
            lSegmentGeom += [lTT[2]]

        #find the index of the shortest segment
        iTime = min(lTime)
        #if (bDebug):
        #    print (f'iTime: {iTime}')
        iMinIndex = lTime.index(iTime)
        iTotalTime += iTime

        #add the geometry of the shortest segment to our output
        lGeomOutput += [lSegmentGeom[iMinIndex]]

        #get the next startPT
        mStartPT = mPTs.pop(iMinIndex)

    return [lGeomOutput, iTotalTime]

def GetShortestRouteNNReverse(mPTsOriginal, aTime = None, lGeom = None, sServer = None, sProfile = None):
    #similar to the GetShortestRouteNNForward algorithm except this one starts
    #at the end point and works backwards; this is different from just starting
    #at the end and working forwards because the times (the proxy used for
    #distance) are direction dependent

    #this routine takes a list of ogr PTs and returns the "shortest"
    #(shortest being whatever data is in aTime) route
    #using a nearest neighbor algorithm 
    #it is expected that the first PT in the list is the start point and
    #the last PT in the last is the end point

    #make an empty list to store the output geometries
    lGeomOutput = []

    #copy the list of PTs; I'll need it later for the indices if times and
    #geometries are provided
    mPTs = None
    if (lGeom != None):
        mPTs = mPTsOriginal.copy()
    
    #the last PT in the list is expected to be the end PT for this
    #segment; take it and remove it (pop)
    mEndPT = mPTs.pop(-1)

    #store the total time here
    iTotalTime = 0

    while (len(mPTs) > 0):
        #make an empty lists to store the segment times and geometries
        lTime = []
        lSegmentGeom = []

        #get the number of PTs left
        iPTCount = len(mPTs)
        #add 1 to iMinIndex while we're skipping the start PT
        iMIA = 0
        #loop through the PTs in the list and find the segments' travel time
        #and geometry
        for i in range(iPTCount):
            #I don't want this to run for the start PT unless it's the only
            #one left
            if (i == 0 and iPTCount > 1):
                iMIA = 1
                continue

            #use the time and geometries provided, if provided
            #if not, call GetTravelTime
            if (lGeom == None):
                lTT = GetTravelTime(mPTs[i], mEndPT, sServer, sProfile)
            else:
                lTT = ReturnTTFromPTs(mPTs[i], mEndPT, mPTsOriginal, aTime,
                    lGeom)

            lTime += [lTT[1]]
            lSegmentGeom += [lTT[2]]

        #find the index of the shortest segment
        iTime = min(lTime)
        iMinIndex = lTime.index(iTime)
        iTotalTime += iTime

        #add the geometry of the shortest segment to the beginning of our
        #output since we're working backwards
        lGeomOutput.insert(0, lSegmentGeom[iMinIndex])
        
        #increment iMinIndex when we're working with the original lists
        iMinIndex += iMIA

        #get the next startPT
        mEndPT = mPTs.pop(iMinIndex)

    return [lGeomOutput, iTotalTime]

def ReturnTTFromPTs(mStartPT, mEndPT, mPTsOriginal, aTime, lGeom,
        bDebug = False):
    #a helper function for the nearest neighbor routines
    #used when segment times are pre-provided to find the indices for the
    #current segment and return the time and geometry in the same format
    #as GetTravelTime
    i = None
    j = None
    for n in range(len(mPTsOriginal)):
        mPT = mPTsOriginal[n]
        if (mPT.Equals(mStartPT)):
            i = n
        elif (mPT.Equals(mEndPT)):
            j = n
        if (i != None and j != None):
            break
    
    #print (f'from(i): {i} to(j): {j}')

    #format lTT to match what GetTravelTime returns
    lTT = [0]
    lTT += [aTime[i, j]]
    lTT += [lGeom[i][j]]

    return lTT

def GetShortestRouteSS(mPTs, aTimeOriginal, lGeom, bRoundTrip = False):
    #this tsp routine returns the shortest route using a shortest segment
    #algorithm
    #all segments will be calculated, and the route will always choose the
    #shortest one of the ones that are still available

    #first I need to get the distance between all the segments except the
    #start and end segments

    #make a deep copy of the time array (aTime) because I am going to
    #change it
    aTime = aTimeOriginal.copy()

    #for a OW trip ensure that distances to the start PT and from the end
    #PT are removed from the array
    if (not bRoundTrip):
        aTime[-1,:] = numpy.inf
        aTime[:,0] = numpy.inf
        aTime[0,-1] = numpy.inf

    #keep track of the total time
    iTime = 0

    #keep track of the number of segments found; this will be used in the one
    #way case to avoid abandoned PTs or segments or chain
    iSegmentCount = 0

    #hold the edge indices here:
    #these will be all the segments used in the output
    lIndex = []
    #make a dictionary to store the segments
    #this will be used to combine segments which will be used for removing
    #segments to avoid closed loops
    #the index of dSegment is the start PT index
    dSegment = {}
    #keep going until all the segments are used
    while (not numpy.all(aTime == numpy.inf)):

        #print (f'aTime GetShortestRouteSS\n{aTime}')
        
        #find the index of the lowest number in the array
        tIndex = numpy.unravel_index(aTime.argmin(), aTime.shape)
        #get i and j from the tuple; these are the indices of the shortest
        #segment
        i = tIndex[0]
        j = tIndex[1]

        #print (f'i: {i} j:{j}')

        #the shortest segment may need to be rejected if using it causes
        #orphaned PTs or segments or chains
        if (RejectSegment(mPTs, i, j, dSegment, iSegmentCount, bRoundTrip)):
            aTime[i, j] = numpy.inf
            continue

        #print (f'aTime GetShortestRouteSS after RejectSegment\n{aTime}')

        iTime += aTime[i, j]
        #keep this edge to use later
        lIndex += [tIndex]

        #now I need to remove all segments starting with the start PT that I
        #just found
        aTime[i, :] = numpy.inf
        #and remove segments ending with the end PT I just found
        aTime[:, j] = numpy.inf
        #and remove the same segment that I found but in the opposite direction
        aTime[j, i] = numpy.inf
        #print (f'aTime GetShortestRouteSS after aTime[j, i] = numpy.inf\n{aTime}')
        #remove any segments that would make a closed loop
        lNewSegment = [i, j]
        #check to see if a previous segment starts with our endpoint
        #easy to do because dSegment is indexed by startPT index
        if (j in dSegment):
            #get the old segment, remove it from the dictionary (not truely
            #necessary, I believe) and adjust the new segment (I'm really just
            #combining two segments here)
            lOldSegment = dSegment.pop(j)
            lNewSegment[1] = lOldSegment[1]
            #remove the potential closed loop
            #if this is the last segment, we might need the time
            iTimeLastSegment = aTime[lNewSegment[1], lNewSegment[0]]
            aTime[lNewSegment[1], lNewSegment[0]] = numpy.inf

        #that was easy.  how do I check to see if a previous segment ends with
        #our startpoint?
        #loop through the dictionary, I guess
        for n in dSegment:
            #check to see if the current dictionary item's last PT is the same
            #as our startPT
            if (lNewSegment[0] == dSegment[n][1]):
                #the logic is the same as above
                lOldSegment = dSegment.pop(n)
                lNewSegment[0] = lOldSegment[0]
                #if this is the last segment, we might need the time
                iTimeLastSegment = aTime[lNewSegment[1], lNewSegment[0]]
                aTime[lNewSegment[1], lNewSegment[0]] = numpy.inf
                #there can only be one record to deal with so we're done here
                break

        #add the new segment (modified or otherwise) to our dictionary of
        #segments
        dSegment[lNewSegment[0]] = lNewSegment
        iSegmentCount += 1
        #print (f'aTime GetShortestRouteSS\n{aTime}')

    #if it's a round trip, I need to add back in the segment that I just
    #removed from aTime
    if (bRoundTrip):
        lIndex += [(lNewSegment[1], lNewSegment[0])]
        iTime += iTimeLastSegment

    #print (f'lIndex: {lIndex}')

    #now I have a list of tuples of the edges I want
    #I need to do this in order
    lGeomOutput = OrderTuplesCollectGeometries(lIndex, lGeom)
    return [lGeomOutput, iTime]

def OrderTuplesCollectGeometries(lIndex, lGeom):
    #a helper function for GetShortestRouteSS
    #lIndex is the list of tuples to be ordered
    #lGeom is the full 2d array of geometries

    #the desired geometries are returned in order

    #let's start at the first PT
    iIndex = 0
    #store the output geometries
    lGeomOutput = []

    while (len(lIndex) > 0):
        #I think this can be done faster, but it's no big deal here
        for i in range(len(lIndex)):
            #get the current segment
            tIndex = lIndex[i]
            if (tIndex[0] == iIndex):
                iIndex = tIndex[1]
                #gather the geometries here
                lGeomOutput += [lGeom[tIndex[0]][tIndex[1]]]   
                lIndex.pop(i)
                break

    return lGeomOutput

def RejectSegment(mPTs, i, j, dSegment, iSegmentCount, bRoundTrip):
    #TO DO: run some tests of this routine (I just made big changes (20210521))

    #a helper function for GetShortestRouteSS

    #the problem is making a closed loop between your route start and
    #end PTs while leaving orphaned PTs, segments, or chains
    #if this happens, we need to reject the segment

    #this is only possible in the one way case and only possible if we're
    #not at the final segment

    #combine our new segment with segments previously in the dictionary
    #if the new segment goes from the start PT to end PT, then reject it

    bReject = False
    #I think this can't happen in the RT case
    if (not bRoundTrip):
        #print ('one way')
        #here we'll attempt to combine segments
        #if, while combining, we end up with from startPT to endPT and
        #we haven't used all our PTs, then we have a problem

        #keep track of the number of segments found (we
        #know how many there are supposed to be by the end); combine
        #this segment with the stored chains; if it's a start to end
        #chain after combination and the total number of segments found
        #isn't enough, well, remove the segment we just found from the
        #array and continue

        #if this is the last possible segment, then we don't have a
        #problem
        # -2 here because we don't want to reject the final segment
        if (iSegmentCount < len(mPTs) - 2):
            #print ('too few segments')

            #if a previous segment starts with our end PT, get the new end PT
            if (j in dSegment):
                #print ('found a previous segment that starts with our end PT')
                #print (f'dSegment[j]: {dSegment[j]}')
                #print (f'len(mPTs): {len(mPTs)}')
                #we have a new end PT
                j = dSegment[j][1]

            #check if a previous segment ends with our start PT
            #loop through the stored segments
            for n in dSegment:
                if (i == dSegment[n][1]):
                    #we have a new start PT
                    i = dSegment[n][0]
                    break

            #do we go from the start to the end?
            if (i == 0 and j == len(mPTs) - 1):
                bReject = True
                
    return bReject

def VerifyPTs(mPTs, sServer, sProfile):
    #this routine will test the list of PTs against the brouter server and
    #tell the user which ones are problematic
    lOutput = []

    #progess bar
    iPTCount = len(mPTs)

    for n in range(iPTCount):

        mPTStart = mPTs[n - 1]
        mPTEnd = mPTs[n]
        #the following should never fail, right?  I should remove the
        #try-except?
        try:
            lOutput += [GetTravelTime(mPTStart, mPTEnd, sServer, sProfile)]
        except:
            continue
        #progress bar
        progress (n, iPTCount)
    
    #finish the progress bar
    progress (iPTCount, iPTCount)
    sys.stdout.write('\n')
    
    return lOutput

