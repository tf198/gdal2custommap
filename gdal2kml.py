import os, math, re, sys, subprocess, logging
from optparse import OptionParser
from osgeo import gdal	

logging.basicConfig(level=logging.DEBUG)

usage = "usage: %prog [options] src_file dst_file"
parser = OptionParser(usage)
parser.add_option('-o', '--outfile', dest='outfile', help='Write output to file instead of stdout')
parser.add_option('-s', '--scale', default=100, dest='scale', type='int', help='A scale percentage for output [10-150]')
parser.add_option('-w', '--working', default='temp', dest='working', help='Where to create files')
parser.add_option('-c', '--crop', default=0, dest='border', type='int', help='Crop border')
parser.add_option('-1', '--single', action='store_true', dest='single', help='Force single scaled tile generation')
parser.add_option('-n', '--name', dest='name', help='KML folder name for output')
parser.add_option('-d', '--draw-order', dest='order', type='int', help='KML draw order')
parser.add_option('-t', '--tile-size', dest='tile_size', default=1024, type='int', help='Max tile size [1024]')

options, (source, dest) = parser.parse_args()

# validate a few options
if not os.path.exists(source): parser.error('unable to file src_file')
if options.scale<10 or options.scale>150: parser.error('scale must be between 10% and 150%')

#print options

nw = re.compile(r'Upper Left\s+\( (\-?[0-9\.]+), (\-?[0-9\.]+)\)')
se = re.compile(r'Lower Right\s+\( (\-?[0-9\.]+), (\-?[0-9\.]+)\)')
size = re.compile(r'Size is (\-?[0-9\.]+), (\-?[0-9\.]+)')

#gdalbin = "C:/Program Files/GDAL/bin/gdal/apps"
gdalbin = "C:\\Program Files\\GDAL\\bin\\gdal\\apps"
gdalinfo = "%s\\gdalinfo.exe" % gdalbin
gdaltranslate = "\"%s\\gdal_translate.exe\"" % gdalbin

img = gdal.Open(source);
img_size = [img.RasterXSize, img.RasterYSize]
img = None
#print "SIZE", img_size

cropped_size = [ x - options.border * 2 for x in img_size ]

factor = float(options.tile_size * 100 / options.scale)

base, ext = os.path.splitext(os.path.basename(source))

if not options.name: options.name = base
if not options.order: options.order = options.scale / 5

if not os.path.exists(options.working): os.mkdir(options.working)
path = os.path.relpath(options.working, os.path.dirname(dest))

m_x = math.ceil(cropped_size[0] / factor)
m_y = math.ceil(cropped_size[1] / factor)

#print m_x, m_y

# special case for where a single tile can be created
pixel_size = cropped_size[0] * cropped_size[1]
if pixel_size <= factor**2:
  m_y = 1.0
  m_x = 1.0
  options.single = True

if options.single and pixel_size > factor**2: # need to downscale
  options.scale = int(factor**2 * 100 / pixel_size)
  m_y = 1.0
  m_x = 1.0

#print factor, options.scale

# equalise the tiles
t_w = cropped_size[0] / m_x
t_h = cropped_size[1] / m_y

# load the exclude file
exclude_file = source + ".exclude"
exclude = []
if options.scale == 100 and os.path.exists(exclude_file):
  logging.debug("Using exclude file %s" % exclude_file)
  for line in open(exclude_file):
    exclude.append(line.rstrip())
  #logging.debug(exclude)

bob = open(dest, 'w');

bob.write("""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">
  <Folder>
    <name>%(name)s</name>
""" % options.__dict__)




for t_y in range(int(m_y)):
  for t_x in range(int(m_x)):
    tile = "%d,%d" % (t_y, t_x)
    #logging.debug(tile)
    if tile in exclude:
      logging.debug("Excluding tile %s" % tile)
    else:
      src_corner = (int(options.border + t_x * t_w), int(options.border + t_y * t_h))
      src_size = [t_w, t_h]
      if src_corner[0] + t_w > img_size[0] - options.border: src_size[0] = int(t_w)
      if src_corner[1] + t_h > img_size[1] - options.border: src_size[1] = int(t_h)
      if options.single: src_size = cropped_size
      
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

    
    