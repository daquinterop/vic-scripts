import numpy as np
from osgeo import gdal, osr
from netCDF4 import Dataset 
from datetime import datetime, timedelta 
import os
from tqdm import tqdm

def get_array(filename, geotrans=False):
    '''
    Returns the data array for a netcdf file. if geotrans is True then it also
    returns the geotransform for the array.
    '''
    ncdf_ds = Dataset(filename)
    array = ncdf_ds.variables['Precipitation_Flux'][0]
    out = array
    # Get geotransform
    if geotrans:
        width = ncdf_ds.variables['lon'].size
        height = ncdf_ds.variables['lat'].size
        x_min = ncdf_ds.variables['lon'][:].min()
        x_max = ncdf_ds.variables['lon'][:].max()
        y_min = ncdf_ds.variables['lat'][:].min()
        y_max = ncdf_ds.variables['lat'][:].max()
        x_size = (x_max - x_min)/width
        y_size = (y_max - y_min)/height
        geotransform = (
            x_min - x_size/2, x_size, 0,
            y_max + y_size/2, 0, -y_size
        )
        geotransform = tuple(map(lambda x: round(x, 2), geotransform))
        out = (array, geotransform)
    ncdf_ds.close()
    return out

def aggregate_rasters(prefix, start, end, dst, statistic='mean'):
    '''
    Aggregates a series of netcdf datasets into a single raster. The files are
    named following a {prefix}{YYYYmmdd}.nc structure. It assumes that all the 
    netCDF datasets have the same grid.
    Parameters
    ----------
    inputRas : prefix
        prefix of the rasters timeseries including path.
    start, end: datetime.datetime
        start and end dates
    dst: str
        path to the output tif, including filename and tif extension
    statistic: str
        sum, mean
    '''
    dates = [
        start + timedelta(days=i) 
        for i in range((end - start).days + 1)
    ]
    array = get_array(f'{prefix}{dates[0].strftime("%Y%m%d")}.nc')
    
    for date in tqdm(dates[1:]):
        filename = f'{prefix}{date.strftime("%Y%m%d")}.nc'
        array += get_array(filename)
    if statistic == 'mean':
        array = array / ((end - start).days + 1)
    array = array * 365 # Yearly average
    array = array.data 
    height, width = array.shape
    _, geotransform = get_array(filename, geotrans=True)
    dst = gdal.GetDriverByName('GTiff').Create(
        dst, width, height, 1, gdal.GDT_Float32
    )
    dst.SetGeoTransform(geotransform)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    dst.SetProjection(srs.ExportToWkt())
    band = dst.GetRasterBand(1)
    band.WriteArray(array)
    band.SetNoDataValue(-9999.)
    dst.FlushCache() 

if __name__ == '__main__':
    PREFIX = '/home/diego/vic-southeastern-us/data/input/weather/precipitation_flux-total-'
    START_DATE = datetime(2010, 1, 1)
    END_DATE = datetime(2021, 12, 31)
    aggregate_rasters(
        PREFIX, START_DATE, END_DATE,
        '/home/diego/vic-southeastern-us/data/input/gis/precip.tif', 
        statistic='mean'
    )

