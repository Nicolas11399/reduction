import numpy as np
from astropy.io import fits
from astropy.stats import mad_std
from radio_beam import Beam
import os


def imstats(fn):
    fh = fits.open(fn)

    bm = Beam.from_fits_header(fh[0].header)

    data = fh[0].data

    mad = mad_std(data, ignore_nan=True)
    peak = np.nanmax(data)

    return {'beam': bm.to_header_keywords(),
            'mad': mad,
            'peak': peak,
            'peak/mad': peak/mad,
           }

def parse_fn(fn):

    basename = os.path.basename(fn)

    split = basename.split("_")

    selfcal_entry = 'selfcal0'
    for entry in split:
        if 'selfcal' in entry and 'pre' not in entry:
            selfcal_entry = entry

    robust_entry = 'robust999'
    for entry in split:
        if 'robust' in entry:
            robust_entry = entry


    selfcaliter = int(selfcal_entry.split('selfcal')[-1])
    robust = float(robust_entry.split('robust')[-1])

    return {'region': split[0],
            'band': split[1],
            'array': '12M' if '12M' in split else '7M12M' if '7M12M' in split else '????',
            'selfcaliter': selfcal_entry[-1],
            'robust': robust,
            'suffix': split[-1],
           }

def assemble_stats(globstr, ditch_suffix=None):
    import glob
    from astropy.utils.console import ProgressBar

    allstats = []

    for fn in ProgressBar(glob.glob(globstr)):
        if ditch_suffix is not None:
            meta = parse_fn(fn.split(ditch_suffix)[0])
        else:
            meta = parse_fn(fn)
        stats = imstats(fn)
        allstats.append({'meta': meta, 'stats': stats})

    return allstats

class MyEncoder(json.JSONEncoder):
    "https://stackoverflow.com/a/27050186/814354"
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(MyEncoder, self).default(obj)

def savestats():
    stats = assemble_stats("/bio/web/secure/adamginsburg/ALMA-IMF/October31Release/*/*/*.image.tt0*.fits", ditch_suffix=".image.tt")
    with open('/bio/web/secure/adamginsburg/ALMA-IMF/October31Release/metadata.json', 'w') as fh:
        json.dump(stats, fh, cls=MyEncoder)

    meta_keys = ['region', 'band', 'array', 'selfcaliter', 'robust', 'suffix']
    stats_keys = ['bmaj', 'bmin', 'bpa', 'peak', 'mad', 'peak/mad']

    rows = []
    for entry in stats:
        rows += [[entry['meta'][key] for key in meta_keys] +
                 [entry['stats'][key] for key in stats_keys]]

    tbl = Table(rows=rows, names=meta_keys+stats_keys)

    tbl.write('/bio/web/secure/adamginsburg/ALMA-IMF/October31Release/metadata.ecsv', overwrite=True)
    tbl.write('/bio/web/secure/adamginsburg/ALMA-IMF/October31Release/metadata.html',
              format='ascii.html', overwrite=True)
    tbl.write('/bio/web/secure/adamginsburg/ALMA-IMF/October31Release/metadata.tex')
    tbl.write('/bio/web/secure/adamginsburg/ALMA-IMF/October31Release/metadata.js.html',
              format='jsviewer')

    return tbl

if __name__ == "__main__":
    import socket
    if 'ufhpc' in socket.gethostname():
        tbl = savestats()
