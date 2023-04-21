import numpy as np
from osgeo import gdal
from osgeo.gdalnumeric import *
from osgeo.gdalconst import *

DATATYPES = {
    'Byte': gdal.GDT_Byte, 'Int16': gdal.GDT_Int16, 
    'UInt16': gdal.GDT_UInt16, 'UInt32': gdal.GDT_UInt32, 
    'Int32': gdal.GDT_Int32, 'Float32': gdal.GDT_Float32,
    'Float64': gdal.GDT_Float64
}
SAMPS = {
    'nearest': GRA_NearestNeighbour, 'bilinear': GRA_Bilinear, 
    'cubic': GRA_Cubic, 'spline': GRA_CubicSpline, 'mean': GRA_Average, 
    'mode': GRA_Mode
}

def snap_raster(inputRas, outputRas, templateRas, subGrid, resample):
    """
    Snap raster to a reference raster. 
    Parameters
    ----------
    inputRas : str
        input raster file to be snapped with TIF file extension
    outputRas: str
        output snapped raster file with TIF file extension
    templateRas: str
        input raster that the raster will be snapped to with TIF file extension
    subGrid: bool
        boolean value to set whether the output raster's resolution will be at 
        the input raster resoltion or not.
    resample: 
        resampling method to be used when snapping (nearest, bilinear, cubic, 
        spline, mean, mode)
    """
    src = gdal.Open(inputRas, GA_ReadOnly)
    src_proj = src.GetProjection()
    srcXSize = src.RasterXSize
    srcYSize = src.RasterYSize
    # NoData = int(src.GetRasterBand(1).GetNoDataValue())
    dtype = gdal.GetDataTypeName(src.GetRasterBand(1).DataType)
    src_geotrans = src.GetGeoTransform()

    src_dtype = DATATYPES[dtype]

    try:
        sampMethod = SAMPS[resample]
    except KeyError:
        raise KeyError('{0} is not a valid resampling method'.format(resample))

    # check to make sure that the output data type will make sense with the resampling method
    if (resample != 'nearest') and (resample != 'mode'):
        if 'Int' in dtype:
            src_dtype = DATATYPES['Float32']
        elif 'Byte' in dtype:
            src_dtype = DATATYPES['Float32']
        else:
            pass

    # We want a section of source that matches this:
    match_ds = gdal.Open(templateRas, GA_ReadOnly)
    match_proj = match_ds.GetProjection()
    match_geotrans = match_ds.GetGeoTransform()
    matchXSize = match_ds.RasterXSize
    matchYSize = match_ds.RasterYSize

    if subGrid:
        # xRatio = int(np.round(srcXSize / matchXSize))
        # yRatio = int(np.round(srcYSize / matchYSize))
        xRatio = int(np.round(match_geotrans[1]/src_geotrans[1]))
        yRatio = int(np.round(match_geotrans[5]/src_geotrans[5]))
        wide = matchXSize * xRatio
        high = matchYSize * yRatio
        outGeom = [
            match_geotrans[0], (match_geotrans[1]/xRatio) , 0,
            match_geotrans[3], 0, (match_geotrans[5]/yRatio)
        ]
    else:
        wide = matchXSize
        high = matchYSize
        outGeom = match_geotrans

    dst = gdal.GetDriverByName('GTiff').Create(outputRas, wide, high, 1, src_dtype)
    dst.SetGeoTransform(outGeom)
    dst.SetProjection(match_proj)
    band = dst.GetRasterBand(1)
    band.SetNoDataValue(-9999.)

    gdal.ReprojectImage(src, dst, src_proj, 'EPSG:4326', sampMethod)
    return

# Execute the main level program if run as standalone
if __name__ == "__main__":
    import os
    WD = '/home/diego/vic-southeastern-us/data/input/gis'
    os.chdir(WD)
    ARGS = [
        ('srtm-southeastern-us-500m-filled.tif', 'sample-strm-snap.tif', 
         'grid-sample.tif', True, 'bilinear'),
        ('srtm-southeastern-us-500m-filled.tif', 'sample-strm-avg.tif', 
         'grid-sample.tif', False, 'bilinear'),
        ('slope-southeastern-us-500m.tif', 'sample-slope-avg.tif', 
         'grid-sample.tif', False, 'mean'),
        ('modis-lc-southeastern-us.tif', 'sample-lc-igbp.tif', 
         'grid-sample.tif', True, 'nearest'),
        ('hswd-southeastern-us.tif', 'sample-soils-agg.tif', 
         'grid-sample.tif', False, 'mode'),
        ('precip.tif', 'sample-precip-snap.tif', 
         'grid-sample.tif', False, 'mode'),
    ]
    for args in ARGS:
        snap_raster(*args)