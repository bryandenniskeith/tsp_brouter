#!/usr/bin/python3
from osgeo import ogr

def ReturnMULTILINESTRINGFromPTTuples(mPTs):
    #mPTs is a list of tuples
    sOut = 'MULTILINESTRING (('
    for tPT in mPTs:
        sOut += f'{tPT[0]} {tPT[1]}'
        if (len(tPT) > 2):
            sOut += f' {tPT[2]}'
        sOut += ','
    sOut = f'{sOut[:-1]}))'
    return ogr.CreateGeometryFromWkt(sOut)

def CombineLNChain(lLNs):
    #this routine expects you have a number of LNs where the ending PT of each
    #LN is the starting PT of the next time
    #this routine combines those LNs into one while removing the end PT of
    #each LN (till the end)
    #lLNs is a list of LNs
    #a single LN is returned

    #loop through the LNs
    for m in range(len(lLNs)):
        #get the PTs in the current LN
        mPTsNew = lLNs[m].GetPoints()
        if (m == 0):
            mPTs = mPTsNew
        else:
            mPTsNew.pop(0)
            mPTs += mPTsNew

    return ReturnMULTILINESTRINGFromPTTuples(mPTs)
    
