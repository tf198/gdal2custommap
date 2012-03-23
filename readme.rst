GDAL to CustomMap Tools
=======================
Some python scripts to generate Garmin CustomMap compatible KMZ from
geo-referenced images.

Requirements
------------
You need the GDAL library and Python bindings installed. On Ubuntu
its as simple as
::
	sudo apt-get install python-gdal

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
		-v, --verbose         Verbose output

kml2kmz.py
----------
	Usage: kml2kmz.py [options] <kml>

	Options:
		-h, --help            show this help message and exit
		-o FILE, --outfile=FILE
													Write output to FILE
		-v, --verbose         Verbose output



