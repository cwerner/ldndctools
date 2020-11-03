#!/usr/bin/env python3
import gzip
import sys

# read the NLCC 1.0 file(s)


climate_dbfile = sys.argv[1]

climate_lines = gzip.open(climate_dbfile, "rt").readlines()
fileOpen = False

global_header = None
f = None

for lcnt, cl in enumerate(climate_lines):

    if "climate" in cl:
        if fileOpen:
            f.close()
        else:
            # should only occure once
            global_header = "".join(climate_lines[0:lcnt])

        # sneek-peek at next line to get filename

        next_line = climate_lines[lcnt + 1]

        if "id" in next_line:
            theId = int(next_line.split("=")[-1])
            f = gzip.open("db/climate_%08d.txt.gz" % theId, "wt")
            f.write(global_header)
            fileOpen = True
    if fileOpen:
        f.write(cl)
