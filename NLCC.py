#!/usr/bin/env python3

import xarray as xr
import numpy as np
import pandas as pd
import os, datetime, shutil, string
import io
from optparse import OptionParser

# chunked netcdf input speedup 15x comapred to regular netcdf !!!

dataInfo = {'title':  'PGF v2 Climate Data',
            'source': 'Princeton University Hydroclimatology Group Bias Corrected 59-yr (1948-2006) Meteorological Forcing Dataset',
            'data':   'PGF v2 0.5 degrees 1901-2012',
            'project': 'not applicable',
            'contact': 'Christian Werner (christian.werner@senckenberg.de)',
            'date':    str(datetime.datetime.today())  }

# -----------------------------------------------------------
# -----------------------------------------------------------

def main(years=range(1901,2013), coords=None, names=None, INPATH='.', outName='climate.txt', fcnt = None, fcnttot=None):

    if coords == None:
        print('need to specify coords')
        exit(1)



    if fcnt != None:
        outName += '.' + str(fcnt).zfill(3)
        print('processing subset %s (%d/%d)' % (outName, fcnt+1, fcnttot))

    xL = []

    prcp_yr = []
    tamp_yr = []
    tavg_yr = []
    wind_yr = []

    lats, lons = zip(*coords)

    nce = xr.open_dataset( 'misc/elevation_05deg.nc' ).squeeze()
    nce = nce.drop(['time','z'])

    ele = nce.sel_points(lat=list(lats), lon=list(lons), method='nearest')

    print("Starting year loop")

 
    for year in years:
        #if year % years[0] == 0:
        print('year', year, '...')
        nc = xr.open_dataset( os.path.join(INPATH, 'pgf2_05deg_v2_%s.nc' % year) )
        #nc.variables['prcp']

        # limit big file
        nc = nc.sel(lat=slice(min(lats)-1, max(lats)+1), lon=slice(min(lons)-1, max(lons)+1))
        #print lats, lons
        x = nc.sel_points(lat=list(lats), lon=list(lons), method='nearest')
        xL.append( x ) #x.copy(deep=True) )

        # do extrac calculations for header info

        prcp_yr.append( x['prcp'].sum(dim='time') )
        tamp_yr.append( x['tas'].max(dim='time') -  x['tas'].min(dim='time') )
        tavg_yr.append( x['tas'].mean(dim='time') )
        wind_yr.append( x['wind'].mean(dim='time') )

        #
        #nc.close()

    ds = xr.concat(xL, dim='time')

    # compute annual values for header
    prcp_yr = np.array( prcp_yr ).mean(axis=0)
    tavg_yr = np.array( tavg_yr ).mean(axis=0)
    tamp_yr = np.array( tamp_yr ).mean(axis=0)
    wind_yr = np.array( wind_yr ).mean(axis=0)


    coord_data = [x for _, x in list(ds.groupby('points'))]

    # optimize here (no copy !!!)

    i = 0
    for _, cd in ds.groupby('points'):
    #for i, cd in enumerate(coord_data):

        if names != None:
            name = names[i]

        # cid
        lons = np.arange(-179.75, 180.0, 0.5)
        lats = np.arange(89.75,-90, -0.5)

        ix = np.where( lons == cd.lon.values )[0]
        jx = np.where( lats == cd.lat.values )[0]

        cid = jx * 1000 + ix

        df = cd.to_dataframe()

        # reset index (date) to getr actual column
        df = df.reset_index()

        df['year'], df['doy'] = df['time'].dt.year, df['time'].dt.dayofyear

        df=df.rename(columns = {'tas':'tavg', 'prcp':'prec', 'rhum':'rh', 'dswrf':'grad', 'time':'date'})

        # conversions
        df['rh'] = df['rh'] * 100

        # new order and drop some cols
        df = df[['date', 'year', 'doy', 'tavg', 'tmin', 'tmax', 'prec', 'grad', 'rh', 'wind']]

        # write section

        if i == 0:

            # create buffer
            sbuffer = io.StringIO()

            # write file info
            dataInfo['file'] = outName

            infoStr = """# -----------------------------------------------------------
# LandscapeDNDC v 1.0 climate file
# file:   : %(file)s
# -----------------------------------------------------------
# title   : %(title)s
# source  : %(source)s
# data    : %(data)s
# project : %(project)s
# contact : %(contact)s
# date    : %(date)s
# -----------------------------------------------------------

""" % dataInfo

            sbuffer.write(infoStr)

            startDate = df['date'].dt.date[0]

            globalStr = """%%global
    time = %s/1
    
""" % str(startDate)
            sbuffer.write(globalStr)


        if np.isfinite( ele['data'][i].values ):
            elevation = int(ele['data'][i].values.round(0))
        else:
            # default elevation
            elevation = 10

        # infor per cid
        generalD = {'id':    str(cid[0]),
                    'name':  "not_given",
                    'lat':   str(cd.lat.values),
                    'lon':   str(cd.lon.values),
                    'ele':   str(elevation),
                    'wind':  str(round(wind_yr[i], 1)),
                    'tavg':  str(round(tavg_yr[i], 1)),
                    'tamp':  str(round(tamp_yr[i], 1)),
                    'prec':  str(int(round(prcp_yr[i], 0)))}

        if names != None:
            generalD.update({'name': name})

        generalStr = """
%% climate
    id   = %(id)s
    name = %(name)s

%% attributes
    latitude   = %(lat)s
    longitude  = %(lon)s
    elevation  = %(ele)s
    windspeed  = %(wind)s
    cloudiness = -99.99
    temperature average   = %(tavg)s
    temperature amplitude = %(tamp)s
    annual precipitation  = %(prec)s

%% data
""" % generalD


        # write gernal info
        sbuffer.write(generalStr)

        # data section
        df.to_csv(sbuffer, index=False, sep='\t', float_format='%.1f', \
                header=['*', '*', '*', 'tavg', 'tmin', 'tmax', 'prec', 'grad', 'rh', 'wind'])


        i += 1


    # write buffer to file

    print('writing file to drive')
    with open(outName, 'w') as fd:
        sbuffer.seek(0)
        shutil.copyfileobj(sbuffer, fd)

    sbuffer.close()



class MyParser( OptionParser ):
    def format_epilog(self, formatter):
        return self.epilog


if __name__ == "__main__":

    parser = MyParser( "usage: %prog [options] indir outfile", epilog=
"""

USAGE examples:

(1) Vietnam with coords:
> python NLCC_v01.py -b "5,25,100,110" -y "2005-2012" pgf2_dir clim_vietnam.txt

(2) Single site (Spain):
> python NLCC_v01.py -c "39.42416,4.07138,Spanien" pgf2_dir clim_spanien.txt  

(3) Multiple sites from coord file:
> python NLCC_v01.py -s sites.txt pgf2_dir clim_sites.txt

___________________________________________
2016/05/15, christian.werner@senckenberg.de
""")

    parser.add_option("-b", "--box", dest="bbox", default=None, 
            help="bounding box (in lat/lon), format: y1,y2,x1,x2")

    parser.add_option("-c", "--coord", dest="coord", default=None, 
            help="individual coord (in lat/lon), format: lat,lon(,name)")

    parser.add_option("-s", "--sites", dest="sites", default=None, 
            help="read coords from site file, format: lat lon name")

    # modes not yet implemented:
    #parser.add_option("-m", "--mask", dest="mask", default=None, 
    #        help="read coords from mask netcdf file")
    #parser.add_option("-i", "--individual", dest="indivi", action='store_true',
    #        default = False, help="split into individual files")

    parser.add_option("-y", "--years", dest="years", default="1901-2012", 
            help="give the range of years to consider")

    parser.add_option("--chunks", dest="chunks", default=None, 
            help="split into chunks with this max. number of ids")


    (options, args) = parser.parse_args()

    print("____________________________________________________________________________")
    print()
    print("        [N]etCDF [L]DNDC [C]limate [C]onverter (v0.1) (NLCC v0.1)")
    print()
    print("            ... use this tool to build TXT LDNDC climate files")
    print("____________________________________________________________________________")
    print("2016/05/15, christian.werner@senckenberg.de")
    print()

    # defaults
    coords   = []
    names    = []
    INPATH = '.'
    RUNNAME  = 'climate.txt'     # default name
    CELL_RES  = 0.5
    CELL_HALF = CELL_RES * 0.5
    COORDTHRESHOLD = 100
    
    if options.chunks != None:
        COORDTHRESHOLD = int(options.chunks)

    # year range
    a = [int(x) for x in options.years.split('-')]
    YEARS = range(a[0], a[1]+1)

    # too few arguments
    if len(args) == 0:
        print(args)
        parser.print_help()
        exit(1)
    elif len(args) == 1:
        INPATH  = args[0]
    else:
        INPATH  = args[0]
        RUNNAME = args[1]


    # Works very well for < 100 coords
    # hits memory limitations with bigger lists !!! 

    if options.bbox != None:
        # bounding box mode
        sep = ','
        if '/' in options.bbox: sep = '/'
        if ';' in options.bbox: sep = ';'
        x = options.bbox.split(sep)
        x = [float(a) for a in x]
        if len(x) != 4:
            print('Please specify 4 coordinates as bounding box.')
            exit(1)

        # do we have corner edges or cell centers?
        if (x[0]).is_integer():
            # lats
            # check latitude sorting
            if x[0] < x[1]:
                # S first, then N
                # flip them
                x0 = x[0]; x1=x[1]
                x[1] = x0
                x[0] = x1
            #else:
            # N first, then S
            x[0] -= CELL_HALF
            x[1] += CELL_HALF

            # lons (always left to right)
            x[2] += CELL_HALF
            x[3] -= CELL_HALF

        # lats fron from north to south
        lons = np.arange(x[2], x[3]+CELL_RES, CELL_RES)
        lats = np.arange(x[0], x[1]-CELL_RES, -CELL_RES)

        bboxStr = 'bbox: %.2f-%.2f Lat, %.2f-%.2f Lon' % (lats[0], lats[-1], lons[0], lons[-1])

        #
        for la in lats:
            for lo in lons:
                coords.append( (la, lo) )
                names.append('none')

    elif options.sites != None:
        # use sites file 

        for lcnt, line in enumerate(open(options.sites, 'r')):
            if lcnt > 0:
                lat, lon, name = line[:-1].split()
                coord = (float(lat), float(lon))
                names.append( name )
                coords.append( coord )
    
    elif options.coord != None:
        sep = ','
        if '/' in options.coord: sep = '/'
        if ';' in options.coord: sep = ';'
        x = options.coord.split(sep)

        # lat,lon,(name)
        if len(x) == 3:
            lat, lon, name = x
        else:
            name = 'none'
            lat, lon = x

        coords=[(float(lat), float(lon))]
        names=[name]

    elif options.mask != None:
        pass

    else:
        print('No mode sected.')
        exit(1)


    print('------------------------------------------')
    print('Dataset: PGF2 v2 0.5 deg')
    print('Climate data range : %d-%d' % (YEARS[0], YEARS[-1]))
    print('Coords to process  :', len(coords))
    if options.bbox != None:
        print(bboxStr)
    print('------------------------------------------')

    if len(coords) > COORDTHRESHOLD:
        # run in chunked mode
        print('\nLarge number of coords selected. Splitting into files')
        coords2d = [coords[i:i+COORDTHRESHOLD] for i in range(0, len(coords), COORDTHRESHOLD)]
        names2d  = [names[i:i+COORDTHRESHOLD] for i in range(0, len(names), COORDTHRESHOLD)]

        fcnt = 0
        for coords, names in zip(coords2d, names2d):
            main(years=YEARS, coords=coords, names=names, INPATH=INPATH, outName=RUNNAME, fcnt=fcnt, fcnttot=len(coords2d))
            fcnt += 1
    
    else:
        # run in regular mode
        main(years=YEARS, coords=coords, names=names, INPATH=INPATH, outName=RUNNAME)
