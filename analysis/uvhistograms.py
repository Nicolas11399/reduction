import numpy as np
from astropy.table import Table
import scipy.stats
import scipy
from casatools import msmetadata, ms
import glob
import pylab as pl
from astropy import units as u

def savefig(path, bbox_inches='tight', **kwargs):
    pl.savefig(path, bbox_inches=bbox_inches, **kwargs)
    pl.savefig(path.replace(".pdf", ".png"), bbox_inches=bbox_inches, **kwargs)

def make_figure(data, wavelength, beam, bins=50):
    uvcts = np.concatenate([data[spw]['uvdist'][~data[spw]['flag'].any(axis=(0,1))] for spw in data]).ravel()
    uvwts = np.concatenate([data[spw]['weight'].mean(axis=0)[~data[spw]['flag'].any(axis=(0,1))] for spw in data]).ravel()

    beam_to_bl = (wavelength / beam).to(u.m, u.dimensionless_angles())

    pl.figure(figsize=(8,4))
    ax1 = pl.subplot(1,2,1)
    _=pl.hist(uvcts, bins=bins)
    _=pl.xlabel('Baseline Length (m)')
    _=pl.ylabel("Number of Visibilities")
    yl = pl.ylim()

    pl.fill_betweenx(yl, beam_to_bl[0].value, beam_to_bl[1].value, zorder=-5, color='orange', alpha=0.5)
    pl.fill_betweenx(yl, np.percentile(uvcts, 25), np.percentile(uvcts, 75), zorder=-5, color='red', alpha=0.25)

    pl.ylim(yl)
    ax1t = ax1.secondary_xaxis('top', functions=(lambda x: x/1e3/wavelength.to(u.m).value, lambda x:x/1e3/wavelength.to(u.m).value))
    ax1t.set_xlabel("Baseline Length (k$\lambda$)")
    #ax1t.set_ticks(np.linspace(1000,100000,10))
    ax2 = pl.subplot(1,2,2)
    _=pl.hist(uvcts,
            weights=uvwts,
            bins=bins, density=True)
    _=pl.xlabel('Baseline Length (m)')
    _=pl.ylabel("Fractional Weight")
    def forward(x):
        return (wavelength.to(u.m)/(x*u.arcsec)).to(u.m, u.dimensionless_angles()).value
    def inverse(x):
        return (wavelength.to(u.m)/(x*u.m)).to(u.arcsec, u.dimensionless_angles()).value
    ax2t = ax2.secondary_xaxis('top', functions=(forward, inverse))
    ax2t.set_xlabel("Angular size $\lambda/D$ (arcsec)")
    if ax2.get_xlim()[1] > 1000:
        ax2t.set_ticks([10,1,0.5,0.4,0.3,0.2,0.1])
    elif ax2.get_xlim()[1] > 600:
        ax2t.set_ticks([10,2,1,0.6,0.5,0.4,0.3])
    else:
        ax2t.set_ticks([10,2,1,0.8,0.7,0.6,0.2])
    yl = pl.ylim()
    pl.fill_betweenx(yl, beam_to_bl[0].value, beam_to_bl[1].value, zorder=-5, color='orange', alpha=0.5)
    #pl.fill_betweenx(yl, np.percentile(uvcts, 25), np.percentile(uvcts, 75), zorder=-5, color='red', alpha=0.25)
    pl.ylim(yl)
    #pl.subplots_adjust(wspace=0.3)
    pl.tight_layout()

    print(f"25th pctile={forward(np.percentile(uvcts, 25))}, 75th pctile={forward(np.percentile(uvcts, 75))}")
    return (forward(np.percentile(uvcts,
                                  [1,5,10,25,50,75,90,95,99])),
            scipy.stats.percentileofscore(uvcts, beam_to_bl[0].value),
            scipy.stats.percentileofscore(uvcts, beam_to_bl[1].value))

if  __name__ == "__main__":
    tbl = Table.read('/orange/adamginsburg/ALMA_IMF/2017.1.01355.L/February2021Release/tables/metadata_image.tt0.ecsv')
    np.seterr('ignore')


    mslist = {(row['region'],row['band']): {'msname': glob.glob(f'/orange/adamginsburg/ALMA_IMF/2017.1.01355.L/{row["region"]}_{row["band"]}*_12M_selfcal.ms'),
                                            'beam': (row['bmaj'], row['bmin'])}
            for row in tbl if row['robust'] == 'r0.0' and row['suffix'] == 'finaliter' and not row['bsens']}

    msmd = msmetadata()
    ms = ms()

    uvdata = []

    for (region, band) in mslist:

        if len(mslist[(region,band)]['msname']) == 1:
            msname = mslist[(region,band)]['msname'][0]
        else:
            raise ValueError('msname borked')

        msmd.open(msname)
        spws = msmd.spwsforfield(region)
        freqs = np.concatenate([msmd.chanfreqs(spw) for spw in spws])
        freqweights = np.concatenate([msmd.chanfreqs(spw) for spw in spws])
        msmd.close()
        print(msname)

        avfreq = np.average(freqs, weights=freqweights)
        wavelength = (avfreq*u.Hz).to(u.m, u.spectral())          

        data = {}
        for spw in spws:
            ms.open(msname)
            ms.selectinit(spw)
            data[spw] = ms.getdata(items=['weight', 'uvdist', 'flag'])
            ms.close()

        beam = mslist[(region,band)]['beam']#*u.arcsec

        with np.errstate(divide='ignore'):
            pctiles,majpct,minpct = make_figure(data, wavelength, beam)
        savefig(f'/orange/adamginsburg/ALMA_IMF/2017.1.01355.L/paper_figures/uvhistograms/{region}_{band}_uvhistogram.pdf', bbox_inches='tight')

        uvdata.append({
                       'region': region,
                       'band': band,
                       '1%': pctiles[0],
                       '5%': pctiles[1],
                       '10%': pctiles[2],
                       '25%': pctiles[3],
                       '50%': pctiles[4],
                       '75%': pctiles[5],
                       '90%': pctiles[6],
                       '95%': pctiles[7],
                       '99%': pctiles[8],
                       'beam_major': beam[0],
                       'beam_minor': beam[1],
                       'beam_major_pctile': majpct,
                       'beam_minor_pctile': minpct,
                       'wavelength': wavelength.to(u.um).value,
                       })
        print(uvdata[-1])
    uvtbl = Table(uvdata, units={'beam_major':u.arcsec, 'beam_minor':u.arcsec, 'wavelength':u.um, '1%':u.arcsec, '5%':u.arcsec, '10%':u.arcsec, '25%':u.arcsec, '50%':u.arcsec, '75%':u.arcsec, '90%':u.arcsec, '95%':u.arcsec, '99%':u.arcsec})
    uvtbl.write('/orange/adamginsburg/ALMA_IMF/2017.1.01355.L/May2021Release/tables/uvspacings.ecsv', overwrite=True)

    fontsize=16
    pl.rcParams['font.size'] = fontsize

    for band in ('B3','B6'):
        rows = {key: uvtbl[(uvtbl['region']==key) & (uvtbl['band'] == band)] for key in sorted(uvtbl['region'])}
        stats = [{
            "label": key,
            "med": row['50%'][0],
            "q1": row['25%'][0],
            "q3": row['75%'][0],
            "whislo": row['10%'][0],
            "whishi": row['90%'][0],
            "fliers": [],
            } for key,row in rows.items() if len(row)>0]

        fig, axes = pl.subplots(nrows=1, ncols=1, figsize=(12, 12), sharey=True)
        fig.clf()
        axes.bxp(stats, vert=False)
        #axes.set_title(f'{band} UV distribution overview', fontsize=fontsize)
        axes.set_xlabel("Angular Scale (\")", fontsize=fontsize)
        axes.set_xlim(0.1,15)
        rad_to_as = u.radian.to(u.arcsec)
        def fcn(x):
            return rad_to_as / x / 1000
        ax1t = axes.secondary_xaxis('top', functions=(fcn, fcn))
        ax1t.set_xlabel("Baseline Length (k$\lambda$)")
        ax1t.set_ticks([20, 30, 50, 100, 400])
        savefig(f'/orange/adamginsburg/ALMA_IMF/2017.1.01355.L/paper_figures/uvhistograms/{band}_summary_uvdistribution.pdf', bbox_inches='tight')