import cdsapi
import zipfile
import os
from datetime import datetime, timedelta

DOWNLOAD_PATH = '/home/diego/vic-southeastern-us/data/input/weather'

c = cdsapi.Client()

START_DATE = datetime(2012, 1, 1)
END_DATE = datetime(2012, 1, 31)

VARIABLES = [
    ('2m_temperature', '24_hour_maximum'),
    ('2m_temperature', '24_hour_minimum'),
    ('10m_wind_speed', '24_hour_mean'),
    ('precipitation_flux', False)
]

date = START_DATE
while date <= END_DATE:
    for variable, statistic in VARIABLES:
        retrieve_pars = {
            'format': 'zip',
            'variable': variable,
            'month': date.strftime('%m'),
            'day': date.strftime('%d'),
            'year': date.strftime('%Y'),
            'area': [37.6, -90.7, 24.4, -75.4,],
        }
        if statistic:
            retrieve_pars['statistic'] = statistic
        else:
            statistic = 'total'
        zip_filename = os.path.join(DOWNLOAD_PATH, 'download.zip')
        
        c.retrieve(
            'sis-agrometeorological-indicators',
            retrieve_pars,
            zip_filename
        )

        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            for file in zip_ref.filelist:
                extension = file.filename.split('.')[-1]
                filename = f'{variable}-{statistic}-{date.strftime("%Y%m%d")}.{extension}'
                zip_ref.extract(file.filename, path=DOWNLOAD_PATH)
                os.rename(
                    os.path.join(DOWNLOAD_PATH, file.filename),
                    os.path.join(DOWNLOAD_PATH, filename)
                )
    date += timedelta(days=1)