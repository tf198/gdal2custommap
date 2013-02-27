#!/usr/bin/env python

import os, math, re, sys, subprocess, logging
from optparse import OptionParser
from osgeo import gdal        

def tiles(canvas, target=1024):
    """ 
    Brute force algorithm to determine the most efficient tiling method for a given canvas
    If anyone can figure out a prettier one please let me know - is actually harder then you'd think!
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

def create_tile(source, filename, offset, size, quality=75):
    """
    Create a jpeg of the given area and return the bounds.
    """
    mem_drv = gdal.GetDriverByName('MEM')
    mem_ds = mem_drv.Create('', size[0], size[1], source.RasterCount)
    bands = range(1, source.RasterCount+1)

    data = source.ReadRaster(offset[0], offset[1], size[0], size[1], size[0], size[1], band_list=bands)
    mem_ds.WriteRaster(0, 0, size[0], size[1], data, band_list=bands)

    jpeg_drv = gdal.GetDriverByName('JPEG')
    jpeg_ds = jpeg_drv.CreateCopy(filename, mem_ds, strict=0, options=["QUALITY={}".format(quality)])

    t = source.GetGeoTransform()
    if t[2]!=0 or t[4]!=0: raise Exception("Source projection not compatible")
    def transform((x, y)):
        return ( t[0] + x*t[1] + y*t[2], t[3] + x*t[4] + y*t[5] )
    
    nw = transform(offset)
    se = transform([ offset[0] + size[0], offset[1] + size[1] ])
    
    result = {
        'north': nw[1],
        'east': se[0],
        'south': se[1],
        'west': nw[0],
    }
    
    jpeg_ds = None
    mem_ds = None
    
    return result

def create_kml(source, filename, directory, tile_size=1024, border=0, name=None, order=20, exclude=[], quality=75):
    """
    Create a kml file and associated images for the given georeferenced image 
    """
    img = gdal.Open(source)
    img_size = [img.RasterXSize, img.RasterYSize]

    logging.debug('Image size: %s' % img_size)

    cropped_size = [ x - border * 2 for x in img_size ]

    base, ext = os.path.splitext(os.path.basename(source))

    if not name: name = base
    path = os.path.relpath(directory, os.path.dirname(filename))

    tile_layout = tiles(cropped_size, tile_size)

    tile_sizes = [ int(math.ceil(x)) for x in [ cropped_size[0] / tile_layout[0], cropped_size[1] / tile_layout[1] ] ]
    logging.debug('Using tile layout %s -> %s' % (tile_layout, tile_sizes))

    bob = open(filename, 'w')
    
    bob.write("""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">
  <Folder>
    <name>%s</name>
""" % name)

    for t_y in range(tile_layout[1]):
        for t_x in range(tile_layout[0]):
            tile = "%d,%d" % (t_y, t_x)
            logging.debug(tile)
            if tile in exclude:
                logging.debug("Excluding tile %s" % tile)
            else:
                src_corner = (border + t_x * tile_sizes[0], border + t_y * tile_sizes[1])
                src_size = [ tile_sizes[0], tile_sizes[1] ]
                if src_corner[0] + tile_sizes[0] > img_size[0] - options.border: src_size[0] = int(tile_sizes[0])
                if src_corner[1] + tile_sizes[1] > img_size[1] - options.border: src_size[1] = int(tile_sizes[1])
                
                outfile = "%s_%d_%d.jpg" % (base, t_x, t_y)
                bounds = create_tile(img, "%s/%s" % (directory, outfile), src_corner, src_size, quality)
                
                bob.write("""    <GroundOverlay>
                <name>%s</name>
                <color>ffffffff</color>
                <drawOrder>%d</drawOrder>
                <Icon>
                    <href>%s/%s</href>
                    <viewBoundScale>0.75</viewBoundScale>
                </Icon>
                <LatLonBox>
    """ % (outfile, order, path, outfile))
            
                bob.write("""        <north>%(north)s</north>
                    <south>%(south)s</south>
                    <east>%(east)s</east>
                    <west>%(west)s</west>
                    <rotation>0</rotation>
    """ % bounds)
                bob.write("""        </LatLonBox>
            </GroundOverlay>
    """);
        
    bob.write("""  </Folder>
    </kml>
    """)

    bob.close()
    img = None
    
if __name__=='__main__':
    usage = "usage: %prog [options] src_file dst_file"
    parser = OptionParser(usage)
    parser.add_option('-d', '--dir', dest='directory', help='Where to create jpeg tiles')
    parser.add_option('-c', '--crop', default=0, dest='border', type='int', help='Crop border')
    parser.add_option('-n', '--name', dest='name', help='KML folder name for output')
    parser.add_option('-o', '--draw-order', dest='order', type='int', default=20, help='KML draw order')
    parser.add_option('-t', '--tile-size', dest='tile_size', default=1024, type='int', help='Max tile size [1024]')
    parser.add_option('-q', '--quality', dest='quality', default=75, type='int', help='JPEG quality [75]')
    parser.add_option('-v', '--verbose', dest='verbose', action='store_true', help='Verbose output')

    options, args = parser.parse_args()

    if len(args) != 2: parser.error('Missing file paths')
    source, dest = args

    if options.verbose: logging.basicConfig(level=logging.DEBUG)

    # validate a few options
    if not os.path.exists(source): parser.error('unable to file src_file')
    #if options.scale<10 or options.scale>150: parser.error('scale must be between 10% and 150%')

    # set the default folder for jpegs
    if not options.directory: options.directory = "%s.files" % os.path.splitext(dest)[0]
    if not os.path.exists(options.directory): os.mkdir(options.directory)
    logging.info('Writing jpegs to %s' % options.directory)

    # load the exclude file
    exclude_file = source + ".exclude"
    exclude = []
    if os.path.exists(exclude_file):
        logging.debug("Using exclude file %s" % exclude_file)
        for line in open(exclude_file):
            exclude.append(line.rstrip())
        logging.debug(exclude)
        
    create_kml(source, dest, options.directory, 
        tile_size=options.tile_size, border=options.border, name=options.name, order=options.order, exclude=exclude, quality=options.quality)
