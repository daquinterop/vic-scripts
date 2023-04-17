import os
import sys
import glob
import json
import warnings
import numpy as np
from osgeo import gdal
from osgeo.gdalnumeric import *
from osgeo.gdalconst import *
from scipy import ndimage

# set system to ignore simple warnings
warnings.simplefilter("ignore")

def make_veg_lib(LCFile, LAIFolder, ALBFolder, outVeg, scheme='IGBP'):

    # define script file path for relative path definitions
    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__))
    )

    # get land cover classification scheme and create path to lookup table
    if scheme == 'IGBP':
        attriFile = os.path.join(__location__,'veg_type_attributes_igbp.json')
        waterCls = 0
    elif scheme == 'GLCC':
        attriFile = os.path.join(__location__,'veg_type_attributes_glcc.json')
        waterCls = 12
    elif scheme == 'IPCC':
        attriFile = os.path.join(__location__,'veg_type_attributes_ipcc.json')
        waterCls = 0
    else:
        raise SyntaxError('Land cover classification scheme not supported')

    band = 1 # constant variable for reading in data

    # open/read veg scheme json file
    with open(attriFile) as data_file:
        attriData = json.load(data_file)

    # pass look up information into variable
    clsAttributes = attriData['classAttributes']

    ds = gdal.Open(os.path.join(__location__, LCFile), GA_ReadOnly)
    b1 = ds.GetRasterBand(band)
    lccls = BandReadAsArray(b1)
    clsRes = ds.GetGeoTransform()[1]
    ds = None
    b1 = None

    # get list of paths to LAI and albedo data
    # laifiles = sorted(glob.glob(os.path.join(__location__, LAIFolder, '*.tif')))
    # albfiles = sorted(glob.glob(os.path.join(__location__, ALBFolder, '*.tif')))
    laifiles = [os.path.join(LAIFolder, f'{i}.tif') for i in range(12)]
    albfiles = [os.path.join(ALBFolder, f'{i}.tif') for i in range(12)]
    # loop over each month in the year
    for i in range(12):
        # read LAI data
        laids = gdal.Open(laifiles[i], GA_ReadOnly)
        b1 = laids.GetRasterBand(band)
        lsRes = laids.GetGeoTransform()[1] # geotransform of land surface data

        zoomFactor = lsRes / clsRes # factor for resampling land surface data

        # resample LAI land surface data
        laidata = ndimage.zoom(BandReadAsArray(b1), zoomFactor, order=0)

        min_height = min(laidata.shape[0], lccls.shape[0])
        min_width = min(laidata.shape[1], lccls.shape[1])
        laidata = laidata[:min_height, :min_width]
        lccls = lccls[:min_height, :min_width]
        # if first iteration then create blank arrays to pass data to
        if i == 0:
            laiMon = np.zeros([laidata.shape[0],laidata.shape[1],12])
            albMon = np.zeros([laidata.shape[0],laidata.shape[1],12])

        laiMon[:,:,i] = laidata[:,:] # pass lai data in array

        # Flush
        laids = None
        b1 = None

        # read albedo data
        albds = gdal.Open(albfiles[i],GA_ReadOnly)
        b1 = albds.GetRasterBand(band)

        # resmaple albedo land surface data
        albdata = ndimage.zoom(BandReadAsArray(b1),zoomFactor,order=0)
        albdata = albdata[:min_height, :min_width]
        albMon[:,:,i] = albdata[:,:] # pass albedo data in array

        # Flush
        albds = None
        b1 = None


    # mask nodata values
    # albMon[np.where(albMon>=1000)] = np.nan

    # get file path to output file
    veglib = os.path.join(__location__,outVeg)

    # check if the output parameter file exists, if so delete it
    if os.path.exists(veglib)==True:
        os.remove(veglib)

    # open output file for writing
    with open(veglib, 'w') as f:
        # loop over each class
        for i in range(len(clsAttributes)):

            # get attributes
            attributes = clsAttributes[i]['properties']

            if i == waterCls: # set default values for water
                lai = [0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01]
                alb = [0.08,0.08,0.08,0.08,0.08,0.08,0.08,0.08,0.08,0.08,0.08,0.08]

            else: # grab lai and albedo data from rasters
                # set blank lists
                lai = []
                alb = []
                # loop over each month
                for j in range(12):
                    # find which elements are equal to the class
                    clsidx = np.where(lccls==i)

                    # grab the month time slice
                    laiStep = laiMon[:,:,j]
                    albStep = albMon[:,:,j]

                    # grab the data at location
                    lai.append(np.nanmean(laiStep[clsidx])*0.0001 )
                    alb.append(np.nanmean(albStep[clsidx])*0.001)

            # grab other attributes from lookup table
            overstory = int(attributes['overstory']) # overstory value
            rarc = str(attributes['rarc']) # veg architectural resistance
            rmin= str(attributes['rmin']) # veg minimum stomatal resistance
            vegHeight = float(attributes['h']) # veg height
            rgl = str(attributes['rgl']) # Minimum incoming shortwave radiation for ET
            rad_atten = str(attributes['rad_atn']) # radiation attenuation factor
            wind_atten = str(attributes['wnd_atn']) # wind speed attenuation
            trunk_ratio = str(attributes['trnk_r']) # ratio of total tree height that is trunk

            rough = 0.123 * vegHeight # vegetation roughness length
            dis = 0.67 * vegHeight # vegetation displacement height

            # adjust wind height value if overstory is true
            if overstory == 1:
                wind_h = vegHeight+10
            else:
                wind_h = vegHeight+2

            comment = str(attributes['classname']) # grab class name

            if i == 0: # write header information
                f.write('#Class\tOvrStry\tRarc\tRmin\tJAN-LAI\tFEB-LAI\tMAR-LAI\tAPR-LAI\tMAY-LAI\tJUN-LAI\tJUL-LAI\tAUG-LAI\tSEP-LAI\tOCT-LAI\tNOV-LAI\tDEC-LAI\tJAN-ALB\tFEB_ALB\tMAR-ALB\tAPR-ALB\tMAY-ALB\tJUN-ALB\tJUL-ALB\tAUG-ALB\tSEP-ALB\tOCT-ALB\tNOV-ALB\tDEC-ALB\tJAN-ROU\tFEB-ROU\tMAR-ROU\tAPR-ROU\tMAY-ROU\tJUN-ROU\tJUL-ROU\tAUG-ROU\tSEP-ROU\tOCT-ROU\tNOV-ROU\tDEC-ROU\tJAN-DIS\tFEB-DIS\tMAR-DIS\tAPR-DIS\tMAY-DIS\tJUN-DIS\tJUL-DIS\tAUG-DIS\tSEP-DIS\tOCT-DIS\tNOV-DIS\tDEC-DIS\tWIND_H\tRGL\trad_atten\twind_atten\ttruck_ratio\tCOMMENT\n')

            # write the land surface parameterization data
            f.write('{0}\t{1}\t{2}\t{3}\t{4:.4f}\t{5:.4f}\t{6:.4f}\t{7:.4f}\t{8:.4f}\t{9:.4f}\t{10:.4f}\t{11:.4f}\t{12:.4f}\t{13:.4f}\t{14:.4f}\t{15:.4f}\t{16:.4f}\t{17:.4f}\t{18:.4f}\t{19:.4f}\t{20:.4f}\t{21:.4f}\t{22:.4f}\t{23:.4f}\t{24:.4f}\t{25:.4f}\t{26:.4f}\t{27:.4f}\t{28}\t{28}\t{28}\t{28}\t{28}\t{28}\t{28}\t{28}\t{28}\t{28}\t{28}\t{28}\t{29}\t{29}\t{29}\t{29}\t{29}\t{29}\t{29}\t{29}\t{29}\t{29}\t{29}\t{29}\t{30}\t{31}\t{32}\t{33}\t{34}\t{35}\n'.format(i,
                    overstory,rarc,rmin,lai[0],lai[1],lai[2],lai[3],lai[4],lai[5],lai[6],lai[7],lai[8],lai[9],lai[10],lai[11],alb[0],alb[1],alb[2],alb[3],alb[4],alb[5],alb[6],alb[7],alb[8],alb[9],alb[10],alb[11],rough,dis,wind_h,rgl,rad_atten,wind_atten,trunk_ratio,comment))

    return


# Execute the main level program if run as standalone
if __name__ == "__main__":
    INPUT_PATH = '/home/diego/vic-southeastern-us/data/input'
    make_veg_lib(
        os.path.join(INPUT_PATH, 'gis', 'al_ga-lc-igbp.tif'),
        os.path.join(INPUT_PATH, 'ndvi_al-ga'),
        os.path.join(INPUT_PATH, 'albedo_al-ga'),
        os.path.join(INPUT_PATH, 'veg.lib'),
        'IGBP'
    )
