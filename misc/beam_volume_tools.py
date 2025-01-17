'''
beam_volume_tools.py
'''

import numpy as np
from scipy import ndimage, signal
from os import path

from spectral_cube import SpectralCube
from astropy import units as u
from radio_beam import Beam, Beams
from astropy.convolution import convolve_fft #, convolve
from astropy.io import fits

def epsilon_from_psf(psf_image, max_npix_peak=100, export_clean_beam=True):

    #if not path.exists(psf_image):
    #    print('CASA image file of PSF not found.')

    max_npix_peak = int(max_npix_peak)


    psf = SpectralCube.read(psf_image, format='casa_image')

    # Add check on psf.beams.major.max() and .min() ?
    common_beam = psf.beams.common_beam()

    # In pixels (clean beam per channel):
    npix_clean_beam = psf.pixels_per_beam
    #psf.beams

    #epsilon_arr = np.zeros(5)
    epsilon_arr = np.zeros(len(psf))

    for chan in range(len(psf)):
    #for chan in range(5):

        center = np.unravel_index(np.argmax(psf[chan]), psf[chan].shape)
        cy, cx = center

        cutout = psf[chan,cy-max_npix_peak:cy+max_npix_peak+1, cx-max_npix_peak:cx+max_npix_peak+1]
        shape = cutout.shape
        sy, sx = shape
        Y, X = np.mgrid[0:sy, 0:sx]

        center = np.unravel_index(np.argmax(cutout), cutout.shape)
        cy, cx = center

        dy = (Y - cy)
        dx = (X - cx)
        # I guess these definitions already take into account the definition of PA (east from north)?
        costh = np.cos(psf.beams.pa[chan].to('rad'))
        sinth = np.sin(psf.beams.pa[chan].to('rad'))
        # Changed variable name to rminmaj (it was rmajmin)
        rminmaj =  psf.beams.minor[chan] / psf.beams.major[chan]

        rr = ((dx * costh + dy * sinth)**2 / rminmaj**2 +
              (dx * sinth - dy * costh)**2 / 1**2)**0.5
        rbin = (rr).astype(int)

        #From plots taking the abs looks better centered by ~ 1 pix.
        #radial_mean = ndimage.mean(cutout**2, labels=rbin, index=np.arange(max_npix_peak))
        radial_mean = ndimage.mean(np.abs(cutout), labels=rbin, index=np.arange(max_npix_peak))
        first_min_ind = signal.find_peaks(-radial_mean)[0][0]

        #cutout_posit = np.where(cutout > 0, cutout, 0.)
        radial_sum = ndimage.sum(cutout, labels=rbin, index=np.arange(first_min_ind))
        psf_sum = np.sum(radial_sum)

        clean_psf_sum = npix_clean_beam[chan]
        epsilon = clean_psf_sum/psf_sum
        epsilon_arr[chan] = epsilon

        print('\n')
        print('Clean beam area of channel {0} is {1} pixels:'.format(chan, clean_psf_sum))
        print('Dirty beam area of channel {0} is {1} pixels:'.format(chan, psf_sum))
        print('epsilon = Omega_clean / Omega_dirty = {}'.format(epsilon))

    if export_clean_beam:
        output = {'epsilon': epsilon_arr, 'clean_beam': common_beam}
    else:
        output = {'epsilon': epsilon_arr}
    return output


def conv_model(model_image, clean_beam):
    model = SpectralCube.read(model_image, format='casa_image')
    beam = clean_beam

    pix_scale = model.header['CDELT2']*u.deg
    pix_scale = pix_scale.to(u.arcsec)
    clean_beam_kernel = beam.as_kernel(pix_scale)

    omega_beam = beam.sr
    omega_pix = pix_scale.to('rad') **2
    npix_beam = (omega_beam/omega_pix).value

    fwhm_gauss_pix = (4*np.log(2)/np.pi)**0.5 * pix_scale
    pix_beam = Beam(fwhm_gauss_pix, fwhm_gauss_pix, 0*u.deg)
    model = model.with_beam(pix_beam)

    conv = model.convolve_to(beam)

    return conv


def rescale(conv_model, epsilon, residual_image, export_fits=True):
    residual = SpectralCube.read(residual_image, format='casa_image')

    header = conv_model.header

    conv_model._unit = u.dimensionless_unscaled
    epsilon = epsilon*u.dimensionless_unscaled
    restor = conv_model + epsilon[:,None,None]*residual

    if export_fits:
        restor.write(residual_image.replace('.residual','.resc_restored.fits'), overwrite=True)

    return restor
