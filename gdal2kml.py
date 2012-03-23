import os, math, re, sys, subprocess, logging
from optparse import OptionParser
from osgeo import gdal	

def tiles(canvas, target=1024):
	""" 
	Brute force algorithm to determine the most efficient tiling method for a given canvas
	If anyone can figure out a prettier one please let me know
	"""
	best_case = (canvas[0] * canvas[1]) / float(target**2)
	
	# handle the trivial cases first
	if canvas[0] <= target: return [ 1, math.ceil(best_case) ]
	if canvas[1] <= target: return [ math.ceil(best_case), 1 ]
	
	r  = [ float(x) / target for x in canvas ]
	
	# brute force the 4 methods 
	
	a_up = [ math.ceil(x) for x in r ]
	b_up = [ math.ceil(best_case / x) for x in a_up ]
	
	a_down = [ math.floor(x) for x in r ]
	b_down = [ math.ceil(best_case / x) for x in a_down ]
	
	results = []
	for i in range(2):
		results.append((a_up[i], b_up[i], a_up[i] * b_up[i]))
		results.append((a_down[i], b_down[i], a_down[i] * b_down[i]))
	
	results.sort(key=lambda x: x[2])
	return [ int(x) for x in results[0][0:2] ]

usage = "usage: %prog [options] src_file dst_file"
parser = OptionParser(usage)
parser.add_option('-s', '--scale', default=100, dest='scale', type='int', help='A scale percentage for output [10-150]')
parser.add_option('-d', '--dir', dest='working', help='Where to create jpeg tiles')
parser.add_option('-c', '--crop', default=0, dest='border', type='int', help='Crop border')
#parser.add_option('-1', '--single', action='store_true', dest='single', help='Force single scaled tile generation')
parser.add_option('-n', '--name', dest='name', help='KML folder name for output')
parser.add_option('-o', '--draw-order', dest='order', type='int', default=20, help='KML draw order')
parser.add_option('-t', '--tile-size', dest='tile_size', default=1024, type='int', help='Max tile size [1024]')
parser.add_option('-v', '--verbose', dest='verbose', action='store_true', help='Verbose output')

options, args = parser.parse_args()

if len(args) != 2: parser.error('Missing file paths')
source, dest = args

if options.verbose: logging.basicConfig(level=logging.DEBUG)

# validate a few options
if not os.path.exists(source): parser.error('unable to file src_file')
if options.scale<10 or options.scale>150: parser.error('scale must be between 10% and 150%')

# set the default folder for jpegs
if not options.working: options.working = "%s.files" % os.path.splitext(dest)[0]
logging.info('Writing jpegs to %s' % options.working)

#print options

nw = re.compile(r'Upper Left\s+\( (\-?[0-9\.]+), (\-?[0-9\.]+)\)')
se = re.compile(r'Lower Right\s+\( (\-?[0-9\.]+), (\-?[0-9\.]+)\)')
size = re.compile(r'Size is (\-?[0-9\.]+), (\-?[0-9\.]+)')

img = gdal.Open(source);
img_size = [img.RasterXSize, img.RasterYSize]
img = None
logging.debug('Image size: %s' % img_size)

cropped_size = [ x - options.border * 2 for x in img_size ]

factor = float(options.tile_size * 100 / options.scale)

base, ext = os.path.splitext(os.path.basename(source))

if not options.name: options.name = base
if not options.order: options.order = options.scale / 5

if not os.path.exists(options.working): os.mkdir(options.working)
path = os.path.relpath(options.working, os.path.dirname(dest))

tile_layout = tiles(cropped_size)

tile_sizes = [ int(math.ceil(x)) for x in [ cropped_size[0] / tile_layout[0], cropped_size[1] / tile_layout[1] ] ]
logging.debug('Using tile layout %s -> %s' % (tile_layout, tile_sizes))

# load the exclude file
exclude_file = source + ".exclude"
exclude = []
if options.scale == 100 and os.path.exists(exclude_file):
  logging.debug("Using exclude file %s" % exclude_file)
  for line in open(exclude_file):
    exclude.append(line.rstrip())
  #logging.debug(exclude)

bob = open(dest, 'w')
	
bob.write("""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">
  <Folder>
    <name>%(name)s</name>
""" % options.__dict__)

for t_y in range(tile_layout[1]):
  for t_x in range(tile_layout[0]):
    tile = "%d,%d" % (t_y, t_x)
    #logging.debug(tile)
    if tile in exclude:
      logging.debug("Excluding tile %s" % tile)
    else:
      src_corner = (int(options.border + t_x * tile_sizes[0]), int(options.border + t_y * tile_sizes[1]))
      src_size = [tile_sizes[0], tile_sizes[1]]
      if src_corner[0] + tile_sizes[0] > img_size[0] - options.border: src_size[0] = int(tile_sizes[0])
      if src_corner[1] + tile_sizes[1] > img_size[1] - options.border: src_size[1] = int(tile_sizes[1])
      #if options.single: src_size = cropped_size
      
      outfile = "%s_%d_%d_%d.jpg" % (base, options.scale, t_x, t_y)
      out_scale = "%d%%" % options.scale
      cmd = [
      'gdal_translate', 
      '-of', 'JPEG', 
      '-srcwin', src_corner[0], src_corner[1], src_size[0], src_size[1],
      '-outsize', out_scale, out_scale,
      '-q',
      source,
      '%s/%s' % (options.working, outfile)
      ]
      cmd = [ str(x) for x in cmd ]
      subprocess.check_call(cmd)
      
      bob.write("""    <GroundOverlay>
      <name>%s</name>
      <color>ffffffff</color>
      <drawOrder>%d</drawOrder>
      <Icon>
        <href>%s/%s</href>
        <viewBoundScale>0.75</viewBoundScale>
      </Icon>
      <LatLonBox>
""" % (outfile, options.order, path, outfile))
    # get the bounds
      img = gdal.Open("%s/%s" %(options.working, outfile))
      wf = img.GetGeoTransform()
      north = wf[3]
      west = wf[0]
      east = west + (wf[1] * img.RasterXSize)
      south = north + (wf[5] * img.RasterYSize)
      img = None
      bob.write("""        <north>%s</north>
        <south>%s</south>
        <east>%s</east>
        <west>%s</west>
        <rotation>0</rotation>
""" % (north,south, east, west))
      bob.write("""        </LatLonBox>
    </GroundOverlay>
""");
  
bob.write("""  </Folder>
</kml>
""")

bob.close()

    
    