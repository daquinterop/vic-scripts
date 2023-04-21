# import dependencies
import os
import sys
import numpy as np
from osgeo import gdal,ogr,osr


def create_grid(baseShape, outputGrid, gridSize):
    NoData_value = -9999.

    #Define output coordinate system
    spatialRef = osr.SpatialReference()
    spatialRef.SetWellKnownGeogCS('WGS_84')

    # Open the data source and read in the extent
    source_ds = ogr.Open(os.path.join(baseShape))
    source_layer = source_ds.GetLayer()
    x_min, x_max, y_min, y_max = source_layer.GetExtent()

    # adjust the output domain to grid size floating point
    x_min = np.floor(x_min * 1/gridSize)*gridSize
    x_max = np.ceil(x_max * 1/gridSize)*gridSize
    y_max = np.ceil(y_max * 1/gridSize)*gridSize
    y_min = np.floor(y_min * 1/gridSize)*gridSize

    # Create high res source for boundary accuracy
    hiResRatio = 50
    highResGridsize = gridSize / hiResRatio

    # Get high res raster size
    x_hres_size = int(np.ceil((x_max - x_min) / highResGridsize))
    y_hres_size = int(np.ceil((y_max - y_min) / highResGridsize))

    # Create high res raster in memory
    mem_ds = gdal.GetDriverByName('MEM').Create('', x_hres_size, y_hres_size, gdal.GDT_Byte)
    mem_ds.SetGeoTransform((x_min, highResGridsize, 0, y_max, 0, -highResGridsize))
    band = mem_ds.GetRasterBand(1)
    band.SetNoDataValue(NoData_value)

    # Rasterize shapefile to high resolution grid
    gdal.RasterizeLayer(mem_ds, [1], source_layer, burn_values=[1])

    # Get rasterized high res shapefile
    array = band.ReadAsArray()

    # Flush memory file
    del mem_ds
    del band

    # Create the destination data source
    x_size = int(np.ceil((x_max - x_min) / gridSize))
    y_size = int(np.ceil((y_max - y_min) / gridSize))
    drv =  gdal.GetDriverByName('GTiff')
    target_ds = drv.Create(outputGrid, x_size, y_size, 1, gdal.GDT_Byte)
    target_ds.SetGeoTransform((x_min, gridSize, 0, y_max, 0, -gridSize))
    target_ds.SetProjection(spatialRef.ExportToWkt())

    # Create blank mask array at target res
    outMask = np.zeros([y_size,x_size])

    # Loop over array to find the elements the high res raster falls in
    for i, i_hres in enumerate(np.arange(0, y_hres_size, hiResRatio, int)):
        for j, j_hres in enumerate(np.arange(0, x_hres_size, hiResRatio, int)):
            subset = array[i_hres:i_hres+hiResRatio, j_hres:j_hres+hiResRatio]
            if subset.any():
                outMask[i,j] = 1

    # set the mask array to the target file
    band = target_ds.GetRasterBand(1)
    band.WriteArray(outMask)
    band.SetNoDataValue(NoData_value)
    return

# Execute the main level program if run as standalone
if __name__ == "__main__":
    create_grid(
        '/home/diego/vic-southeastern-us/data/shapefiles/sample_watershed.shp',
        '/home/diego/vic-southeastern-us/data/input/gis/grid-sample.tif',
        0.05
    )