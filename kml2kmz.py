#!/usr/bin/env python

import re, logging

def htc(m):
    return chr(int(m.group(1),16))

def urldecode(url):
    rex=re.compile('%([0-9a-hA-H][0-9a-hA-H])',re.M)
    return rex.sub(htc,url)


if __name__ == '__main__':
    from optparse import OptionParser
    import os.path
    
    usage = "%prog [options] <kml>"
    parser = OptionParser(usage)
    parser.add_option('-o', '--outfile', dest="outfile", metavar="FILE", help="Write output to FILE")
    parser.add_option('-v', '--verbose', dest='verbose', action='store_true', help='Verbose output')
    
    (options, args) = parser.parse_args()
	
    if options.verbose: logging.basicConfig(level=logging.DEBUG)
    
    # check for KML
    if len(args)<1: parser.error('Path to KML file is required')
    if not os.path.exists(args[0]): parser.error('Unable to find KML: %s' % args[0])
    
    if not options.outfile:
        options.outfile = os.path.basename(args[0])[:-4] + '.kmz';
    logging.info("Output to", options.outfile)
    
    # create the output zip file
    import zipfile
    zip = zipfile.ZipFile(options.outfile, 'w', zipfile.ZIP_DEFLATED)
    
    # read the source xml
    from xml.dom.minidom import parse
    kml = parse(args[0])
    nodes = kml.getElementsByTagName('href')
    
    base = os.path.dirname(args[0])
	
    for node in nodes:
        href = node.firstChild
    
        img = urldecode(href.nodeValue).replace('file:///', '')
        if not os.path.exists(img): img = base + '/' + img
        if not os.path.exists(img): parser.error('Unable to find image: %s' % img)
    
        # add the image
        filename = 'files/%s' % os.path.basename(img)
        logging.debug("Storing %s as %s" % (img, filename))
        zip.write(img, filename, zipfile.ZIP_STORED)
    
        # modify the xml to point to the correct image
        href.nodeValue = filename
        
    logging.debug("Storing KML as doc.kml")
    zip.writestr('doc.kml', kml.toxml("UTF-8"));
    
    zip.close()
    logging.info("Finished")
    