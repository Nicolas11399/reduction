import glob
import os
from astropy.io import fits
from astropy import visualization
from spectral_cube import SpectralCube
import pylab as pl


def make_comparison_image(preselfcal, postselfcal):
    #fh_pre = fits.open(preselfcal)
    #fh_post = fits.open(postselfcal)
    if 'fits' in preselfcal:
        cube_pre = SpectralCube.read(preselfcal)
    else:
        cube_pre = SpectralCube.read(preselfcal, format='casa_image')
    if 'fits' in postselfcal:
        cube_post = SpectralCube.read(postselfcal)
    else:
        cube_post = SpectralCube.read(postselfcal, format='casa_image')
    cube_pre = cube_pre.with_mask(cube_pre != 0*cube_pre.unit)
    cube_post = cube_post.with_mask(cube_post != 0*cube_post.unit)
    # these break shapes!
    #cube_pre = cube_pre.minimal_subcube()
    #cube_post = cube_post.minimal_subcube()
    data_pre = cube_pre[0].value
    data_post = cube_post[0].value

    try:
        diff = (data_post - data_pre)
    except Exception as ex:
        print(preselfcal, postselfcal, cube_pre.shape, cube_post.shape)
        raise ex

    fig = pl.figure(1, figsize=(14,6))
    fig.clf()


    norm = visualization.simple_norm(data=diff.squeeze(), stretch='asinh',
                                     min_cut=-0.001)
    if norm.vmax < 0.001:
        norm.vmax = 0.001

    ax1 = pl.subplot(1,3,1)
    ax2 = pl.subplot(1,3,2)
    ax3 = pl.subplot(1,3,3)
    ax1.imshow(data_pre, norm=norm, origin='lower', interpolation='none')
    ax1.set_title("preselfcal")
    ax2.imshow(data_post, norm=norm, origin='lower', interpolation='none')
    ax2.set_title("postselfcal")
    ax3.imshow(diff.squeeze(), norm=norm, origin='lower', interpolation='none')
    ax3.set_title("post-pre")

    for ax in (ax1,ax2,ax3):
        ax.set_xticks([])
        ax.set_yticks([])

    pl.subplots_adjust(wspace=0.0)

    return ax1,ax2,ax3,fig

def get_selfcal_number(fn):
    numberstring = fn.split("selfcal")[1][0]
    try:
        return int(numberstring)
    except:
        return 0

for field in "G008.67 G337.92 W43-MM3 G328.25 G351.77 G012.80 G327.29 W43-MM1 G010.62 W51-IRS2 W43-MM2 G333.60 G338.93 W51-E G353.41".split():
    for band in (3,6):
        for config in ('7M12M', '12M'):

            # for all-in-the-same-place stuff
            fns = [x for x in glob.glob(f"{field}*_B{band}_*_{config}_*selfcal[0-9]*.image.tt0")
                   if 'robust0' in x]
            # for not all-in-the-same-place stuff
            fns = [x for x in glob.glob(f"{field}/B{band}/{field}*_B{band}_*_{config}_*selfcal[0-9]*.image.tt0.fits")
                   if 'robust0' in x]

            if any(fns):
                selfcal_nums = [get_selfcal_number(fn) for fn in fns]

                last_selfcal = max(selfcal_nums)

                postselfcal_name = [x for x in fns if f'selfcal{last_selfcal}' in x][0]

                preselfcal_name = fns[0].replace(f"_selfcal{last_selfcal}","_preselfcal")
                if not os.path.exists(preselfcal_name):
                    # try alternate naming scheme
                    preselfcal_name = fns[0].replace(f"_selfcal{last_selfcal}","")
                if "_finaliter" in preselfcal_name:
                    preselfcal_name = preselfcal_name.replace("_finaliter","")

                try:
                    make_comparison_image(preselfcal_name, postselfcal_name)
                    if not os.path.exists(f"{field}/B{band}/comparisons/"):
                        os.mkdir(f"{field}/B{band}/comparisons/")
                    pl.savefig(f"{field}/B{band}/comparisons/{field}_B{band}_{config}_selfcal{last_selfcal}_comparison.png", bbox_inches='tight')
                except Exception as ex:
                    print(field, band, config, ex)
                    continue

                print(f"{field}_B{band}:{last_selfcal}")
            else:
                print(f"No hits for {field}_B{band}_{config}")
