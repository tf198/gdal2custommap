GDAL to CustomMap Tools
=======================
Some python scripts to generate Garmin CustomMap compatible KMZ from
geo-referenced images.

Garmin CustomMap has some restrictions on the KMZ it can display

1. No tile larger than 1024x1024 (or equivalent total pixels)
2. No more than 100 tiles on the device (e.g. 4 KMZ files with 25 tiles each)

``gdal2tiles`` (the GDAL default tiler) uses 256x256 tiles so requires 4 times
as many tiles as necessary.  ``gdal2kml`` tries to tile the map as efficiently
as possible so you dont end up with thin tiles at the right or bottom.

``gdal2kml`` **DOES NOT** do any warping so the source image must be correctly georeferenced and in ``EPSG:4326``
projection or the conversion will fail.  
For other projections you need to get the GDAL utility programs and run it through ``gdal_warp`` first.  If you
are not sure about the projection run it through anyway as it will not adversly affect the output.
This may introduce a black border which you can then cut out using the --crop option to gdal2kml.

::
	gdalwarp -t_srs EPSG:4326 -r cubic <input.tif> <corrected.tif>
	gdal2kml.py corrected.tif output.kml --crop 20

Requirements
------------
You need the GDAL library and Python bindings installed. On Ubuntu
its as simple as::

	sudo apt-get install python-gdal
	
For windows there are prebuilt binaries at http://www.gisinternals.com
The current stable is 1.9.0 and I have tested with the MSVC2008 version and the
following packages but it can be a bit tricky to get all the paths right::

	(http://python.org/download)
	python-2.7.2.msi
	(http://www.gisinternals.com/sdk/PackageList.aspx?file=release-1500-gdal-1-9-mapserver-6-0.zip)
	gdal-19-1500-core.msi
	gdal-19-1500-ecw.msi
	GDAL-1.9.0.win32-py2.7.msi

Basic Usage
-----------
::

  python gdal2kml.py input.tif my_map.kml
  python kml2kmz.py my_map.kml
	
gdal2kml.py
-----------
Usage: gdal2kml.py [options] src_file dst_file

Options:
	-h, --help            show this help message and exit
	-d DIRECTORY, --dir=DIRECTORY
												Where to create jpeg tiles
	-c BORDER, --crop=BORDER
												Crop border
	-n NAME, --name=NAME  KML folder name for output
	-o ORDER, --draw-order=ORDER
												KML draw order
	-t TILE_SIZE, --tile-size=TILE_SIZE
												Max tile size [1024]
   -q, --quality=X       JPEG output quality 0-100 [75]
	-v, --verbose         Verbose output

kml2kmz.py
----------
Usage: kml2kmz.py [options] <kml>

Options:
	-h, --help            show this help message and exit
	-o FILE, --outfile=FILE
												Write output to FILE
	-v, --verbose         Verbose output



