# tsp_brouter
A Python CLI script to run travelling salesman problem (**tsp**) algorithms using **brouter** routing times.

In addition to the CLI script the **tsp_brouter** library includes functions to call the algorithms from within Python, of course.

[brouter](https://brouter.de/brouter-web/) provides routing services with profiles that can be particularly interesting for touring bicyclists.  It is highly configurable.  **tsp_brouter_cli.py** is a Python3 script that calls the brouter server and returns (in **-createdm** mode) a "distance matrix" and route segments for all the points that the user provided (via a point file that is read by the gdal/ogr library).  

In the **-routes** mode **tsp_brouter** calls up to four algorithms to get traveling salesman problem solutions.  Three of them I wrote myself (as an exercise, I suppose):

1. a **Brute Force** algorithm to get an exact solution at such a high cost in processing time that it can't be run for more than about 12 points.
2. a **Nearest Neighbor** algorithm that starts at one point and continues along the route to the end point always going to the next closest available point to a defined end point.
3. a **Shortest Segment** algorithm that looks at all available route segments and always includes the shortest one until there are no available segments left.
4. a much more clever and fast algorithm than the ones I wrote, using the **ortools** library from Google.

The algorithms are available in both **one way** (the user indicates the start and end points) and **round trip** versions.

The user selects which parameter from the brouter results to minimize (distance, travel time, energy, or cost (as defined by the profile)).  By supplying your own custom profile for brouter you can get time estimates and preferred routes that are tailored to your own riding and prefernces.  One custom profile is included in the **brouter_profiles** folder.  It's one that works well for me in mountainous regions of Turkey.  The [m11n server](https://brouter.m11n.de) has many interesting profiles.

The output is a **gpx** file of the route (to put in one's phone and follow on a bicycle tour, perhaps!).

### installation

There is no installation package.  I'm working on it.

Required Python3 libraries that may not be installed by default include:

- [gdal/ogr](https://pypi.org/project/GDAL/)
- [numpy](https://pypi.org/project/numpy/)
- [urllib3](https://pypi.org/project/urllib3/)
- [ortools](https://developers.google.com/optimization/install/python)

In my testing I was unable to get **GDAL** and **numpy** included in the tsp_brouter installation package.  Install them separately if you don't already have them.  

Numpy should easy:

`pip install numpy`

GDAL can perhaps be installed like this:

`pip install GDAL`

Let me know if that doesn't work.  There seem to be lots of ways to install **GDAL**.

### usage

TO DO...

### to do
- check behaviour when bad points are sent to -createdm
- allow user to specify which algorithms to run (currently the only optional one is the brute force algorithm because it is slow)
- cache data from server to avoid needing to call it again for the same from point-to point-server-profile combination
- allow user to override check that their non-local profile already exists (in case the profile exist on the server but not in the tsp_brouter dictionary)
- return dictionaries instead of lists (GetShortestRoute, ReturnTimeGeometryFromGeoJSON, GetTravelTimes, VerifyPTs) (I think this is better coding practice; I'm sure there's a lot I can do toward better coding practice)
- how should I structure the code?  It's all just functions (procedural?) now.  I suppose I should have a class that runs the algorithms as requested since they pretty much all take the same inputs?
