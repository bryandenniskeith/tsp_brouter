# tsp_brouter
A Python CLI script to run travelling salesman problem (tsp) algorithms using brouter routing times.
brouter provides routing services with profiles that can be particularly interesting for touring bicyclists.  It is highly configurable.  tsp_brouter.py is a Python3 script that calls the brouter server and returns (in -createdm mode) a "distance matrix" (they are actually travel times) for all the points that the user provided (via a point file that is read by the gdal/ogr library).  
In the -routes mode tsp_brouter calls up to four algorithms to get traveling salesman problem solutions.  Three of them I wrote myself (as an exercise, I suppose):
1 -- a Brute Force algorithm to get an exact solution at such a high cost in processing time that it can't be run for more than about 12 points.
2 -- a Nearest Neighbor algorithm that starts at one point and continues along the route to the end point always going to the next closest available point to a defined end
3 -- a Shortest Segment algorithm that looks at all avilable route segments and always includes the shortest one until there are no available segments left
4 -- a much more clever and fast algorithm than the ones I wrote, using the ortools library from Google

The algorithms are available in both one way (the user indicates the start and end points) and round trip versions.

The output is a gpx file of the route.

The brouter server and profile are (for now) hard-coded.

There is no installation package.  Required Python3 libraries include:
gdal/ogr
numpy
pickle
urllib3
itertools
ortools
