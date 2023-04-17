import cdsapi
import zipfile
import os
from datetime import datetime, timedelta

def download_era5(variable, date, statistic=False, path='.', box=[90, -180, -90, 180]):
    '''
    Download datset from sis-agrometeorological-indicators. 
    https://cds.climate.copernicus.eu/cdsapp#!/dataset/sis-agrometeorological-indicators?tab=overview. 

    Parameters
    ----------
    variable : str
    date: datetime.datetime
    statistic: str (optional)
    path: str
        Path to download the data to
    '''
    retrieve_pars = {
        'format': 'zip',
        'variable': variable,
        'month': date.strftime('%m'),
        'day': date.strftime('%d'),
        'year': date.strftime('%Y'),
        'area': box,
    }
    if statistic:
        retrieve_pars['statistic'] = statistic
    else:
        statistic = 'total'
    zip_filename = os.path.join(path, 'download.zip')

    c = cdsapi.Client()
    c.retrieve(
        'sis-agrometeorological-indicators',
        retrieve_pars,
        zip_filename
    )

    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        for file in zip_ref.filelist:
            extension = file.filename.split('.')[-1]
            filename = f'{variable}-{statistic}-{date.strftime("%Y%m%d")}.{extension}'
            zip_ref.extract(file.filename, path=path)
            os.rename(
                os.path.join(path, file.filename),
                os.path.join(path, filename)
            )


if __name__ == '__main__':
    DOWNLOAD_PATH = '/home/diego/vic-southeastern-us/data/input/weather'

    START_DATE = datetime(2010, 1, 1)
    END_DATE = datetime(2011, 12, 31)

    VARIABLES = [
        ('2m_temperature', '24_hour_maximum'),
        ('2m_temperature', '24_hour_minimum'),
        ('10m_wind_speed', '24_hour_mean'),
        ('precipitation_flux', False)
    ]
    
    date = START_DATE
    while date <= END_DATE:
        for variable, statistic in VARIABLES:
            download_era5(
                variable, date, statistic, DOWNLOAD_PATH,
                [37.6, -90.7, 24.4, -75.4]
            )
        date += timedelta(days=1)