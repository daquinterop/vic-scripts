import os
import sys
from netCDF4 import Dataset
import numpy as np
from osgeo import gdal
from osgeo.gdalnumeric import *
from osgeo.gdalconst import *
from datetime import datetime, timedelta
from tqdm import tqdm

import multiprocessing

VAR_PREFIX = {
    'tmax': '2m_temperature-24_hour_maximum', 
    'tmin': '2m_temperature-24_hour_minimum',
    'precip': 'precipitation_flux-total', 
    'wind': '10m_wind_speed-24_hour_mean'
}

VAR_NCNAME = {
    'tmax': 'Temperature_Air_2m_Max_24h', 
    'tmin': 'Temperature_Air_2m_Min_24h',
    'precip': 'Precipitation_Flux', 
    'wind': 'Wind_Speed_10m_Mean'
}
COLUMNS = ['precip', 'tmax', 'tmin', 'wind']
VAR_PREFIX = {k: VAR_PREFIX[k] for k in COLUMNS}


def write_forcings(x, y, mode, nc_datasets, outpath):
    meteofile = os.path.join(outpath,'forcing_{0:.4f}_{1:.4f}'.format(y,x))
    ncds = nc_datasets['precip'][0]
    latnc = ncds.variables['lat'][:]
    lonnc = ncds.variables['lon'][:]
    x_idx = (np.abs(lonnc - x)).argmin()
    y_idx = (np.abs(latnc - y)).argmin()
    cols = [] 
    for var, ts in nc_datasets.items():
        cols.append([])
        for t in ts:
            val = t.variables[VAR_NCNAME[var]][:][0][y_idx, x_idx]
            cols[-1].append(val)
    cols = np.array(cols).T
    cols[:, 1] = cols[:, 1] - 273.15
    cols[:, 2] = cols[:, 2] - 273.15
    lines = list(map(lambda x: '{0:.4f} {1:.4f} {2:.4f} {3:.4f}\n'.format(*x), cols))
    with open(meteofile, mode) as f:
        f.writelines(lines)


def format_meteo_forcing(basin_mask, inpath, outpath, startyr, endyr):
    band = 1
    ds = gdal.Open(basin_mask, GA_ReadOnly)
    b1 = ds.GetRasterBand(band)
    data = BandReadAsArray(b1)
    gt = ds.GetGeoTransform()
    lon0 = gt[0] + (gt[1] / 2.)
    lon1 = gt[0] + (data.shape[1]*gt[1])
    lat0 = gt[3] + (data.shape[0]*gt[-1])
    lat1 = gt[3] + (gt[-1] / 2.)

    del ds
    del b1
    # lons = np.linspace(lon0, lon1, data.shape[1])
    # lats = np.linspace(lat0, lat1, data.shape[0])
    lons = [gt[0]+gt[1]/2 + i*gt[1] for i in range(data.shape[1])]
    lats = [gt[3]-gt[5]/2 + i*gt[5] for i in range(data.shape[0])]
    xx, yy = np.meshgrid(lons, lats)
    # yy = np.flipud(yy)
    mask = data.astype(uint8)
    mask = np.ma.masked_where(mask!=1,mask)
    dates = [datetime(startyr, 1, 1)]
    while dates[-1] < datetime(endyr, 12, 31):
        dates.append(dates[-1] + timedelta(days=1))

    lons = xx[~mask.mask]
    lats = yy[~mask.mask]

    # Write it yearly batches
    for year in sorted(set(map(lambda x: x.year, dates))):
        if year == startyr:
            mode = 'w'
        else:
            mode = 'a'
        dates_year = sorted(filter(lambda x: x.year == year, dates))
        # dates_year = sorted(dates)
        # Open netCDF Datasets for the year
        nc_datasets = {}
        for variable, prefix in VAR_PREFIX.items():
            nc_datasets[variable] = []
            for date in dates_year:
                nc_datasets[variable].append(
                    Dataset(os.path.join(inpath, f'{prefix}-{date.strftime("%Y%m%d")}.nc'))
                )
        # For all the pixels
        N_CORES = 8
        all_pixels = list(zip(lons, lats))
        batches = [
            all_pixels[i*N_CORES: (i+1)*N_CORES]
            for i in range(int(np.ceil(len(all_pixels)/N_CORES)))
        ]
        for batch in tqdm(batches[:]):
            processes = []
            for x, y in batch:
                p = multiprocessing.Process(
                    target=write_forcings, args=(x, y, mode, nc_datasets, outpath)
                )
                processes.append(p)
                p.start()

            for p in processes:
                p.join()

        for var, vards in nc_datasets.items():
            for ds in vards:
                ds.close()
    return

# Execute the main level program if run as standalone
if __name__ == "__main__":
    INPUT_PATH = '/home/diego/vic-southeastern-us/data/input'
    format_meteo_forcing(
        os.path.join(INPUT_PATH, 'gis', 'grid-sample.tif'),
        os.path.join(INPUT_PATH, 'weather'),
        os.path.join(INPUT_PATH, 'forcing'),
        2010, 2021
    )
