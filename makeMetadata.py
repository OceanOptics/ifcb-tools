from datetime import datetime
import pandas as pd
import numpy as np
import os.path
import glob
import warnings


ENV_COLS = {'DateTime': 'UTC date time', 'Latitude': 'latitude', 'Longitude': 'longitude',
            'Salinity': 'salinity', 'Temperature': 'temperature_intake'}
LOG_COLS = {'bin': 'IFCB_bin_id', 'Depth': 'depth', 'Type': 'source', 'Source': 'source_id',
            'Reference': 'reference', 'Epoch': 'stn', 'Cast': 'cast', 'EpochDay': 'epoch_day', 'Flag': 'flag'}
META_DEFAULTS = {'Type': 'inline', 'Depth': 5, 'Campaign': 2, 'Concentration': 1}


def read_env(filenames, keys=ENV_COLS):
    """
    Read Environmental Data typically consisting of GPS and TSG measurements.
    It concatenates data from multiple files into a single pandas dataframe/
    """
    if type(filenames) == str:
        filenames = [filenames]
    for k in ['DateTime', 'Latitude', 'Longitude']:
        if k not in keys:
            raise ValueError(f'Environmental data missing key: {k}')
    ikeys = {v: k for k, v in keys.items()}  # Remap dictionary
    env = list()
    for f in filenames:
        df = pd.read_csv(f, parse_dates=[keys['DateTime']])
        df.rename(columns=ikeys, inplace=True)
        df.drop(columns=[c for c in df.columns if c not in keys.keys()], inplace=True)
        env.append(df)
    return pd.concat(env)


def read_log(filename, sheet_name='Sheet1', keys=LOG_COLS):
    """
    Read IFCB log book entered manually to differentiate specific samples (e.g. CTD, Experiments)
    Required fields: bin
    """
    for k in ['bin']:
        if k not in keys:
            raise ValueError(f'IFCB Log missing key: {k}')
    ikeys = {v: k for k, v in keys.items()}  # Remap dictionary
    df = pd.read_excel(filename, sheet_name=sheet_name)
    df.rename(columns=ikeys, inplace=True)
    df.set_index('bin', inplace=True)
    df.drop(columns=[c for c in df.columns if c not in keys.keys()], inplace=True)
    df.dropna(how='all', inplace=True)
    return df


def read_events(filenames, index='name'):
    """
    Prepare long events such as Stations Epochs for make_metadata
    Filenames is a dictionary of keys: corresponding to a column of meta and value a filename
    Event files must contain columns: name, start, and end
    """
    d = {}
    for k, f in filenames.items():
        d[k] = pd.read_csv(f, parse_dates=['start', 'end']).set_index(index)
    return d


def make_metadata(path_to_raw, env, log, events={}, defaults=META_DEFAULTS):
    """
    Make metadata file containing environmental (GPS + TSG) and
    sample identification (CTD, Experiments) for every IFCB bin.

    Bin marked as flagged are moved into raw/ignored
    """
    path_to_ignored = os.path.join(path_to_raw, 'ignored')
    # List all samples
    bins = [os.path.splitext(os.path.basename(f))[0] for f in sorted(glob.glob(os.path.join(path_to_raw, '*.roi')))]
    # Ignore samples flagged with delete
    if 'Flag' in log.columns:
        for b in log.index[log.Flag == 'delete']:
            if b in bins:
                if not os.path.exists(path_to_ignored):
                    os.mkdir(path_to_ignored)
                if os.path.exists(os.path.join(path_to_raw, f'{b}.roi')):
                    os.rename(os.path.join(path_to_raw, f'{b}.roi'), os.path.join(path_to_ignored, f'{b}.roi'))
                if os.path.exists(os.path.join(path_to_raw, f'{b}.adc')):
                    os.rename(os.path.join(path_to_raw, f'{b}.adc'), os.path.join(path_to_ignored, f'{b}.adc'))
                if os.path.exists(os.path.join(path_to_raw, f'{b}.hdr')):
                    os.rename(os.path.join(path_to_raw, f'{b}.hdr'), os.path.join(path_to_ignored, f'{b}.hdr'))
                bins.pop(bins.index(b))
        log = log[log.Flag != 'delete']
    # Interpolate Env parameters to all samples
    seen = set()
    keys = [x for x in ['bin', *list(env.keys()), *list(log.keys())] if not (x in seen or seen.add(x))]
    meta = {c: [] for c in keys}
    meta['bin'] = bins
    ts = []
    for b in bins:
        meta['DateTime'].append(datetime.strptime(b[:-8], 'D%Y%m%dT%H%M%S'))
        ts.append(meta['DateTime'][-1].timestamp())
    for k in env.keys():
        if k == 'DateTime':
            continue
        meta[k] = np.interp(ts, env.DateTime.to_numpy(dtype=np.int64) / 10**9, env[k], left=np.nan, right=np.nan)
    # Set Default Parameters (if field absent from log or env it's added)
    for k, v in defaults.items():
        meta[k] = [v] * len(bins)
    # Set Remaining Fields to nan
    for k in [k for k in log.keys() if k not in ['bin', *list(env.keys()), *list(defaults.keys())]]:
        meta[k] = [np.nan] * len(bins)
    meta = pd.DataFrame(meta).set_index('bin')
    # Set Events
    for event_key, event_list in events.items():
        for name, e in event_list.iterrows():
            sel = (e.start <= meta.DateTime) & (meta.DateTime < e.end)
            meta.loc[sel, event_key] = name
    # Append log data to selected samples
    with warnings.catch_warnings():  # This task fragments the DataFrame in memory but is still really fast to run
        warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)
        for b, r in log.iterrows():
            i = meta.index[b == meta.index]
            if i.empty:
                print(f'Raw bin missing or invalid log bin: {b}')
                continue
            i = i[0]
            # Empty environmental data if Depth field is not empty likely incorrect except dt, lat, and lon
            if ('Depth' in r.keys() and not r.isnull()['Depth']) and \
                    ('Depth' in defaults.keys() and r['Depth'] > defaults['Depth']):
                for kk in env.keys():
                    if kk not in ['DateTime', 'Latitude', 'Longitude']:
                        meta.loc[i, kk] = np.nan
            for k, missing in r.isnull().items():
                if not missing:
                    meta.loc[i, k] = r[k]
    meta = meta.copy()  # Necessary as data is highly fragmented due to insertion of data at specific locations
    return meta


if __name__ == '__main__':
    root = '/Users/nils/Data/EXPORTS2/'
    env = read_env(sorted(glob.glob(os.path.join(root, 'TSG', '*.csv'))))
    log = read_log(os.path.join(root, 'IFCB107', 'IFCB_log_EXPORTS02.xlsx'))
    events = read_events({'Epoch': os.path.join(root, 'IFCB107', 'EXPORTS2.epochs.csv')})
    meta = make_metadata(os.path.join(root, 'IFCB107', 'raw'), env, log, events)
    meta.to_csv(os.path.join(root, 'IFCB107', 'EXPORTS2.metadata.csv'))
