#!/usr/bin/env python
# name      : fgddem.py
# purpose   : translates digital elevation model of Fundamental Geospatial Data provided by GSI
#             into a GDAL supported format (write access).
# copyright : (c) 2012, Minoru Akagi
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

script_version = "0.7"

import sys, os
import datetime
import glob
import numpy
import re
import shutil
from xml.dom import minidom
import zipfile

try:
  from osgeo import gdal
except ImportError:
  import gdal

try:
  progress = gdal.TermProgress_nocb
except:
  progress = gdal.TermProgress

flush = sys.stdout.flush

verbose = 0
quiet = 0
debug_mode = 0


def translate_jpgis_gml(text, dest_file, driver, create_options=None, replace_nodata_by_zero=False):
  """translates JPGIS (GML) DEM into a GDAL supported format (write access)."""

  create_options = create_options or []

  # split document into 3 parts - header, body (tuple list) and footer
  header, body = text.split("<gml:tupleList>", 1)
  body, footer = body.rsplit("</gml:tupleList>", 1)

  # parse xml
  hf = header + footer
  if "Shift_JIS" in header.split("\n", 1)[0]:
    # minidom doesn't support Shift_JIS encoding (2012-03-08)
    hf = hf.decode("Shift_JIS").encode("UTF-8").replace("Shift_JIS", "UTF-8")
  doc = minidom.parseString(hf)
  lowerCorner = doc.getElementsByTagName("gml:lowerCorner")[0].childNodes[0].data.split(" ")
  upperCorner = doc.getElementsByTagName("gml:upperCorner")[0].childNodes[0].data.split(" ")
  lry = float2(lowerCorner[0])
  ulx = float2(lowerCorner[1])
  uly = float2(upperCorner[0])
  lrx = float2(upperCorner[1])

  high = doc.getElementsByTagName("gml:high")[0].childNodes[0].data.split(" ")
  xsize = int(high[0]) + 1
  ysize = int(high[1]) + 1

  startPoint = doc.getElementsByTagName("gml:startPoint")[0].childNodes[0].data.split(" ")
  startX = int(startPoint[0])
  startY = int(startPoint[1])

  psize_x = (lrx - ulx) / xsize
  psize_y = (lry - uly) / ysize
  geotransform = [ulx, psize_x, 0, uly, 0, psize_y]

  # create a new dataset
  dst_ds = driver.Create(dest_file, xsize, ysize, 1, gdal.GDT_Float32, create_options)
  if dst_ds is None:
    return "Cannot create file: " + dest_file

  # WKT is from: http://spatialreference.org/ref/epsg/4612/ogcwkt/
  dst_ds.SetProjection('GEOGCS["JGD2000",DATUM["Japanese_Geodetic_Datum_2000",SPHEROID["GRS 1980",6378137,298.257222101,AUTHORITY["EPSG","7019"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6612"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.01745329251994328,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4612"]]')
  dst_ds.SetGeoTransform(geotransform)

  rband = dst_ds.GetRasterBand(1)
  if replace_nodata_by_zero:
    nodata_value = 0.
  else:
    nodata_value = -9999.
    rband.SetNoDataValue(nodata_value)

  # create an array initialized with nodata value
  narray = numpy.empty((ysize, xsize), numpy.float32)
  narray.fill(nodata_value)

  # read tuple list
  tuples = body.strip().split("\n")    # no problem with \r character at line end: float("0.01\r") = 0.01
  num_tuples = len(tuples)
  i = 0
  sx = startX
  for y in range(startY, ysize):
    for x in range(sx, xsize):
      if i < num_tuples:
        vals = tuples[i].split(",")
        if len(vals) == 2 and vals[1].find("-99") == -1:
          narray[y][x] = float(vals[1])
        i += 1
      else:
        break
    if i == num_tuples:
      break
    sx = 0

  # write array
  rband.WriteRaster(0, 0, xsize, ysize, narray.tostring())

  # make sure that all data have been written
  dst_ds.FlushCache()

  if verbose:
    print "file: %s" % dest_file
    print "name: %s" % doc.getElementsByTagName("gml:name")[0].childNodes[0].data
    print "fid : %s" % doc.getElementsByTagName("fid")[0].childNodes[0].data
    print "type: %s" % doc.getElementsByTagName("type")[0].childNodes[0].data
    print "mesh: %s" % doc.getElementsByTagName("mesh")[0].childNodes[0].data
    print "bounds : %f, %f - %f, %f" % (lry, ulx, uly, lrx)
    print "cell size : %f, %f" % (psize_x, psize_y)
    print "size : %d, %d" % (xsize, ysize)
    print "start point : %d, %d\n" % (startX, startY)
  return 0


def translate_zip(src_file, dst_file, driver, create_options=None, replace_nodata_by_zero=False):
  if not os.path.isfile(src_file):
    return "Source is not a file: " + src_file

  # create temporary directory
  temp_dir = os.path.splitext(dst_file)[0] + "_temp" + datetime.datetime.today().strftime("%Y%m%d%H%M%S")
  os.makedirs(temp_dir)

  # open zip file and translate xml files
  zf = zipfile.ZipFile(src_file, mode="r")
  namelist = zf.namelist()
  demlist = []

  if not quiet and not verbose:
    progress(0.0)

  for i, name in enumerate(namelist):
    if name[-4:].lower() == ".xml" and not "meta" in name:
      tif_name = os.path.join(temp_dir, os.path.basename(name) + ".tif")
      with zf.open(name) as f:
        translate_jpgis_gml(f.read(), tif_name, driver, create_options, replace_nodata_by_zero)
      demlist.append(tif_name)
    if not quiet and not verbose:
      progress((i + 1.) / len(namelist))
  zf.close()
  if len(demlist) == 0:
    return "Zip file includes no xml file: " + src_file

  if len(demlist) == 1:
    os.rename(demlist[0], dst_file)
  else:
    # create merge command
    gdal_merge_options = ""
    gdalwarp_options = ""
    gdal_merge_ext = ""
    if os.name != "nt":   # nt: windows
      gdal_merge_ext = ".py"
    if quiet:
      gdal_merge_options += " -q"
    if not verbose:
      gdalwarp_options += " -q"
    if not replace_nodata_by_zero:
      gdal_merge_options += " -a_nodata -9999"
      gdalwarp_options += " -dstnodata -9999"
    gdal_version = int(gdal.VersionInfo())
    re_non_ascii = re.compile(r"[^\x20-\x7E]")
    if gdal_version >= 1900 and re_non_ascii.search(src_file + dst_file) == None:
      # write demlist into a file
      demlist_filename = os.path.join(temp_dir, 'demlist.txt')
      with open(demlist_filename, 'w') as f:
        f.write("\n".join(demlist))
        f.write("\n")

      merge_command = 'gdal_merge%s%s -o "%s" --optfile "%s"' % (gdal_merge_ext,
                                                               gdal_merge_options,
                                                               dst_file,
                                                               demlist_filename)
      # TODO: testing in Linux
      # Wildcards cannot be used for arguments now. See http://trac.osgeo.org/gdal/ticket/4542 (2012/04/08)
    else:
      merge_command = 'gdalwarp%s "%s" "%s"' % (gdalwarp_options,
                                                os.path.join(temp_dir, "*.tif"),
                                                dst_file)

    # do merge
    if not quiet:
      print "merging"
      flush()
    if verbose:
      print "execute %s" % merge_command
    os.system(merge_command)

  # remove temporary directory
  shutil.rmtree(temp_dir)
  if not quiet:
    print "temporary files removed\n"
    flush()
  return 0


def unzip(src_file, dest=None):
  if os.path.isfile(src_file):
    if dest is None:
      dest = os.path.splitext(src_file)[0]
    zf = zipfile.ZipFile(src_file, mode="r")
    zf.extractall(dest)
    zf.close()
    if verbose:
      print "unzipped : %s" % dest


def Usage():
  print "=== Usage ==="
  print "python fgddem.py [-replace_nodata_by_zero] [-f format] [-out_dir output_directory] [-q] [-v] src_files*\n"
  print "src_files: The source file name(s). JPGIS(GML) DEM zip/xml files."
  return 0


def main(argv=None):
  global verbose, quiet, debug_mode

  format = "GTiff"
  filenames = []
  out_dir = ""
  replace_nodata_by_zero = False

  gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "NO")
  os.putenv("GDAL_FILENAME_IS_UTF8", "NO")  # for merging process

  # Parse command line arguments.
  i = 1
  while i < len(argv):
    arg = argv[i]
    if arg == "-replace_nodata_by_zero":
      replace_nodata_by_zero = True
    elif arg == "-f":
      i += 1
      format = argv[i]
    elif arg == "-out_dir":
      i += 1
      out_dir = argv[i]
    elif arg == "-v":
      verbose = 1
    elif arg == "-q":
      quiet = 1
    elif arg == "-debug":
      debug_mode = 1
    elif arg == "-help" or arg == "--help":
      Usage()
      return 0
    elif arg == "-version":
      print "fgddem.py Version %s" % script_version
      return 0
    elif arg[:1] == "-":
      return "Unrecognised command option: %s" % arg
    else:
      # expand wildcards
      f = glob.glob(arg)
      if len(f) == 0:
        sys.stderr.write("File not found: %s\n" % arg)
      filenames += f
    i = i + 1

  if debug_mode:
    print "args: %s" % " ".join(argv)
    print "files: %s" % ",".join(filenames)

  if len(filenames) == 0:
    return "No input files selected"

  # create output directory
  if out_dir and os.path.exists(out_dir) == False:
    os.makedirs(out_dir)
    if verbose:
      print "Directory has been created: %s" % out_dir

  # get gdal driver
  driver = gdal.GetDriverByName(format)
  if driver is None:
    return "Driver %s not found" % format

  err_count = 0
  for i, src_file in enumerate(filenames):
    if not quiet:
      if len(filenames) > 1:
        print "(%d/%d): translating %s" % (i+1, len(filenames), src_file)
      else:
        print "translating " + src_file
      flush()

    if out_dir:
      filetitle, ext = os.path.splitext(os.path.basename(src_file))
      dst_root = os.path.join(out_dir, filetitle)
    else:
      src_root, ext = os.path.splitext(src_file)
      dst_root = src_root

    dst_file = dst_root + ".tif"
    ext = ext.lower()

    # translate zip/xml file
    err = 0
    if ext == ".zip":
      err = translate_zip(src_file, dst_file, driver, [], replace_nodata_by_zero)
    elif ext == ".xml" and not "meta" in src_file:
      with open(src_file) as f:
        err = translate_jpgis_gml(f.read(), dst_file, driver, [], replace_nodata_by_zero)
    else:
      err = "Not supported file: %s" % src_file

    if err:
      sys.stderr.write(err + "\n")
      err_count += 1

  if not quiet and err_count == 0:
    print "completed"
  return 0


def float2(val, min_repeat=6):
  """Increase number of decimal places of a repeating decimal.
     e.g. 34.111111 -> 34.1111111111111111"""
  repeat = 0
  lc = ""
  for i in range(len(val)):
    c = val[i]
    if c == lc:
      repeat += 1
      if repeat == min_repeat:
        return float(val[:i+1] + c * 10)
    else:
      lc = c
      repeat = 1
  return float(val)


if __name__ == "__main__":
  err = main(sys.argv)
  if err:
    sys.stderr.write(err + "\n")
    Usage()
    sys.exit(1)
  sys.exit(0)
