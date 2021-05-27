#!/usr/bin/python3
import sys
from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2
import numpy
import pickle

def GatherGeometriesFromSolution(manager, routing, solution, lGeom):
    #store the output geometries here
    lGeomOutput = []
    #get the start index of the route
    index = routing.Start(0)
    route_distance = 0
    #this code is mostly taken from the ortools examples on the web
    #see:
    #https://developers.google.com/optimization/examples
    while not routing.IsEnd(index):
        #the multiple indices here are confusing
        #geomFromIndex and geomToIndex are the original PT list indices to get
        #the geometries that were returned from the brouter algorithm
        geomFromIndex = manager.IndexToNode(index)
        #these are the indices used to retrieve the results from the ortools
        #tsp solution
        previous_index = index
        index = solution.Value(routing.NextVar(index))
        geomToIndex = manager.IndexToNode(index)

        route_distance += routing.GetArcCostForVehicle(previous_index, index, 0)
        iToIndex = index
        if (geomToIndex == len(lGeom)):
            geomToIndex = 0
        lGeomOutput += [lGeom[geomFromIndex][geomToIndex]]

    return [lGeomOutput, route_distance]

def NumpyArrayToList(aArray):
    #my distance matrix is stored as a numpy array (which is useful for my
    #ShortestSegment algorithm)
    #ortools wants a list of integers so I convert it here
    #there's got to be a better way to do this
    tShape = aArray.shape
    iCount = tShape[0]
    jCount = tShape[1]
    lOut = [[0 for i in range(iCount)] for j in range(jCount)]
    for i in range(iCount):
        for j in range(jCount):
            if (i != j):
                lOut[i][j] = int(aArray[i, j])
    return lOut

def ReturnShortestRouteOR(mPTS, aTime, lGeom, bRoundTrip = False):
    #mPTs is here for compatability, and, I suppose, for debugging

    #note that the distance_callback function must be within the function
    #that calls the ortools routing solution
    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]

    #make a list of integers from our numpy array
    lTime = NumpyArrayToList(aTime)

    #set the parameters for the problem
    data = {}
    data['distance_matrix'] = lTime
    data['num_vehicles'] = 1

    if (not bRoundTrip):
        #a one way problem wants start and end PTs
        data['starts'] = [0]
        data['ends'] = [len(lGeom) - 1]
        manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                        data['num_vehicles'], data['starts'], data['ends'])
    else:
        #I'm not sure if a round trip problem really needs a depot, but it
        #doesn't make a difference
        data['depot'] = 0
        manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                        data['num_vehicles'], data['depot'])

    #see
    #https://developers.google.com/optimization/routing/tsp
    #ortools magic starts here
    routing = pywrapcp.RoutingModel(manager)

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    solution = routing.SolveWithParameters(search_parameters)
    if not solution:
        #I need more error handling here
        print ('ortools_tsp.ReturnShortestRouteORRT routing failed')
        sys.exit()

    #def GatherGeometriesFromSolution(manager, routing, solution, lGeom):
    return GatherGeometriesFromSolution(manager, routing, solution, lGeom)

