# This parameter file contains the parameters related to the primitives located
# in the primitives_spect.py file, in alphabetical order.
from gempy.library import config
from astrodata import AstroData
from astropy import units as u


class adjustWCSToReferenceConfig(config.Config):
    suffix = config.Field("Filename suffix",
                          str, "_wcsCorrected", optional=True)
    method = config.ChoiceField("Alignment method", str,
                                allowed={"sources_wcs": "Match sources using WCS",
                                         "sources_offsets": "Match sources using telescope offsets",
                                         "offsets": "Use telescope offsets only"},
                                default="sources_wcs")
    fallback = config.ChoiceField("Fallback method", str,
                                  allowed={"sources_offsets": "Match sources using telescope offsets",
                                           "offsets": "Use telescope offsets only"},
                                  default="offsets", optional=True)
    tolerance = config.RangeField("Maximum distance from the header offset, "
                                  "for the correlation method (arcsec)",
                                  float, 1, min=0., optional=True)


class calculateSensitivityConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_sensitivityCalculated", optional=True)
    filename = config.Field("Name of spectrophotometric data file", str, None, optional=True)
    suffix = config.Field("Filename suffix",
                          str, "_sensitivityCalculated", optional=True)
    order = config.RangeField("Order of spline fit", int, 6, min=1)
    bandpass = config.RangeField("Bandpass width (nm) if not supplied",
                                 float, 5., min=0.1, max=10.)
    debug_plot = config.Field("Plot sensitivity curve?", bool, False)


class determineDistortionConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_distortionDetermined", optional=True)
    spatial_order = config.RangeField("Fitting order in spatial direction", int, 3, min=1)
    spectral_order = config.RangeField("Fitting order in spectral direction", int, 4, min=1)
    id_only = config.Field("Use only lines identified for wavelength calibration?", bool, False)
    min_snr = config.RangeField("Minimum SNR for peak detection", float, 5., min=3.)
    fwidth = config.RangeField("Feature width in pixels if reidentifying",
                               float, None, min=2., optional=True)
    nsum = config.RangeField("Number of lines to sum", int, 10, min=1)
    step = config.RangeField("Step in rows/columns for tracing", int, 10, min=1)
    max_shift = config.RangeField("Maximum shift per pixel in line position",
                                  float, 0.05, min=0.001, max=0.1)
    max_missed = config.RangeField("Maximum number of steps to miss before a line is lost", int, 5, min=0)
    debug = config.Field("Display line traces on image display?", bool, False)


def min_lines_check(value):
    [int(x) for x in str(value).split(',')]
    return True


class determineWavelengthSolutionConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_wavelengthSolutionDetermined", optional=True)
    order = config.RangeField("Order of fitting polynomial", int, 2, min=1)
    center = config.RangeField("Central row/column to extract", int, None, min=1, optional=True)
    nsum = config.RangeField("Number of lines to sum", int, 10, min=1)
    min_snr = config.RangeField("Minimum SNR for peak detection", float, 10., min=1.)
    min_sep = config.RangeField("Minimum feature separation (pixels)", float, 2., min=1.)
    weighting = config.ChoiceField("Weighting of identified peaks", str,
                                   allowed={"none": "no weighting",
                                            "natural": "natural weighting",
                                            "relative": "relative to local peaks"},
                                   default="natural")
    fwidth = config.RangeField("Feature width in pixels", float, None, min=2., optional=True)
    min_lines = config.Field("Minimum number of lines to fit each segment", (str, int), '15,20',
                             check=min_lines_check)
    central_wavelength = config.RangeField("Estimated central wavelength (nm)", float, None,
                                           min=300., max=25000., optional=True)
    dispersion = config.Field("Estimated dispersion (nm/pixel)", float, None, optional=True)
    linelist = config.Field("Filename of arc line list", str, None, optional=True)
    alternative_centers = config.Field("Try alternative wavelength centers?", bool, False)
    debug = config.Field("Make diagnostic plots?", bool, False)


class distortionCorrectConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_distortionCorrected", optional=True)
    arc = config.ListField("Arc(s) with distortion map", (AstroData, str), None,
                           optional=True, single=True)
    order = config.RangeField("Interpolation order", int, 3, min=0, max=5, inclusiveMax=True)
    subsample = config.RangeField("Subsampling", int, 1, min=1)


class extract1DSpectraConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_extracted", optional=True)
    method = config.ChoiceField("Extraction method", str,
                                allowed={"standard": "no weighting",
                                         "weighted": "inverse-variance weighted",
                                         "optimal": "optimal extraction"},
                                default="standard")
    width = config.RangeField("Width of extraction aperture (pixels)", float, None, min=1, optional=True)
    grow = config.RangeField("Source aperture avoidance region (pixels)", float, 10, min=0, optional=True)
    subtract_sky = config.Field("Subtract sky spectra if the data have not been sky corrected?", bool, True)
    debug = config.Field("Draw extraction apertures on image display?", bool, False)


def check_section(value):
    # Check for validity of a section string
    subsections = value.split(',')
    for i, (x1, x2) in enumerate(s.split(':') for s in subsections):
        try:
            int(x1)
        except ValueError:
            if i > 0 or x1 != '':
                return False
            else:
                x1 = 0
        try:
            int(x2)
        except ValueError:
            if i < len(subsections) - 1 or x2 != '':
                return False
        else:
            if x2 <= x1:
                raise ValueError("Section(s) do not have end pixel number "
                                 "greater than start pixel number")
    return True

class findSourceAperturesConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_aperturesFound", optional=True)
    max_apertures = config.RangeField("Maximum number of sources to find",
                                      int, None, min=1, optional=True)
    percentile = config.RangeField("Percentile to determine signal for each spatial pixel",
                                   float, 95, min=1, max=100, optional=True)
    section = config.Field("Pixel section(s) for measuring the spatial profile",
                           str, None, optional=True, check=check_section)
    min_sky_region = config.RangeField("Minimum number of contiguous pixels "
                                       "between sky lines", int, 20, min=1)
    use_snr = config.Field("Use signal-to-noise ratio rather than data to find peaks?",
                           bool, True)
    threshold = config.RangeField("Threshold for automatic width determination",
                                  float, 0.01, min=0, max=1)
    sizing_method = config.ChoiceField("Method for automatic width determination", str,
                                       allowed={"peak": "height relative to peak",
                                                "integral": "integrated flux"},
                                       default="peak")


class flagCosmicRaysConfig(config.Config):
    suffix = config.Field(
        doc="Filename suffix",
        dtype=str,
        default="_CRMasked",
        optional=True,
    )
    x_order = config.Field(
        doc="Order for fitting and subtracting object continuum and sky line "
        "models, prior to running the main cosmic ray detection algorithm. "
        "When None, defaults are used, according to the image size (as in "
        "the IRAF task gemcrspec). When 0, no fit is done.",
        dtype=int,
        optional=True,
        default=None,
    )
    y_order = config.Field(
        doc="Order for fitting and subtracting object continuum and sky line "
        "models, prior to running the main cosmic ray detection algorithm. "
        "When None, defaults are used, according to the image size (as in "
        "the IRAF task gemcrspec). When 0, no fit is done.",
        dtype=int,
        optional=True,
        default=None,
    )
    bitmask = config.Field(
        doc="Bits in the input data quality `flags` that are to be used to "
        "exclude bad pixels from cosmic ray detection and cleaning. Default "
        "65535 (all non-zero bits, up to 16 planes).",
        dtype=int,
        optional=True,
        default=65535,
    )
    sigclip = config.Field(
        doc="Laplacian-to-noise limit for cosmic ray detection. Lower "
        "values will flag more pixels as cosmic rays.",
        dtype=float,
        optional=True,
        default=4.5,
    )
    sigfrac = config.Field(
        doc="Fractional detection limit for neighboring pixels. For cosmic "
        "ray neighbor pixels, a lapacian-to-noise detection limit of"
        "sigfrac * sigclip will be used.",
        dtype=float,
        optional=True,
        default=0.3,
    )
    objlim = config.Field(
        doc="Minimum contrast between Laplacian image and the fine structure "
        "image.  Increase this value if cores of bright stars are flagged as "
        "cosmic rays.",
        dtype=float,
        optional=True,
        default=5.0,
    )
    pssl = config.Field(
        doc="Previously subtracted sky level in ADU. We always need to work "
        "in electrons for cosmic ray detection, so we need to know the sky "
        "level that has been subtracted so we can add it back in.",
        dtype=float,
        optional=True,
        default=0.0,
    )
    # gain = config.Field(
    #     doc="Gain of the image (electrons / ADU). We always need to work in "
    #     "electrons for cosmic ray detection.",
    #     dtype=float,
    #     optional=True,
    #     default=1.0,
    # )
    # readnoise = config.Field(
    #     doc="Read noise of the image (electrons). Used to generate the noise "
    #     "model of the image.",
    #     dtype=float,
    #     optional=True,
    #     default=6.5,
    # )
    # satlevel = config.Field(
    #     doc="Saturation of level of the image (electrons). This value is "
    #     "used to detect saturated stars and pixels at or above this level "
    #     "are added to the mask.",
    #     dtype=float,
    #     optional=True,
    #     default=65536.0,
    # )
    niter = config.Field(
        doc="Number of iterations of the LA Cosmic algorithm to perform",
        dtype=int,
        optional=True,
        default=4,
    )
    sepmed = config.Field(
        doc="Use the separable median filter instead of the full median "
        "filter. The separable median is not identical to the full median "
        "filter, but they are approximately the same and the separable median "
        "filter is significantly faster and still detects cosmic rays well.",
        dtype=bool,
        optional=True,
        default=True,
    )
    cleantype = config.ChoiceField(
        doc="Set which clean algorithm is used.",
        allowed={
            'median': 'An umasked 5x5 median filter',
            'medmask': 'A masked 5x5 median filter',
            'meanmask': 'A masked 5x5 mean filter',
            'idw': 'A masked 5x5 inverse distance weighted interpolation',
        },
        dtype=str,
        optional=True,
        default="meanmask",
    )
    fsmode = config.ChoiceField(
        doc="Method to build the fine structure image.",
        allowed={
            'median': 'Use the median filter in the standard LA Cosmic '
            'algorithm',
            'convolve': 'Convolve the image with the psf kernel to calculate '
            'the fine structure image.',
        },
        dtype=str,
        optional=True,
        default='median',
    )
    psfmodel = config.ChoiceField(
        doc="Model to use to generate the psf kernel if fsmode == 'convolve' "
        "and psfk is None. The current choices are Gaussian and Moffat "
        "profiles.",
        allowed={
            'gauss': 'Circular Gaussian kernel',
            'moffat': 'Circular Moffat kernel',
            'gaussx': 'Gaussian kernel in the x direction',
            'gaussy': 'Gaussian kernel in the y direction',
        },
        dtype=str,
        optional=True,
        default="gauss",
    )
    psffwhm = config.Field(
        doc="Full Width Half Maximum of the PSF to use for the kernel.",
        dtype=float,
        optional=True,
        default=2.5,
    )
    psfsize = config.Field(
        doc="Size of the kernel to calculate. Returned kernel will have size "
        "psfsize x psfsize. psfsize should be odd.",
        dtype=int,
        optional=True,
        default=7,
    )
    # ndarray is not supported as dtype, and anyway it seems unprobable
    # that we want to pass a kernel array?
    # psfk = config.Field(
    #     doc="PSF kernel array to use for the fine structure image if "
    #     "fsmode == 'convolve'. If None and fsmode == 'convolve', we "
    #     "calculate the psf kernel using 'psfmodel'.",
    #     dtype=np.ndarray,
    #     optional=True,
    #     default=7,
    # )
    psfbeta = config.Field(
        doc="Moffat beta parameter. Only used if psfmodel=='moffat'.",
        dtype=float,
        optional=True,
        default=4.765,
    )
    verbose = config.Field(
        doc="Print to the screen or not.",
        dtype=bool,
        optional=True,
        default=False,
    )


def flux_units_check(value):
    # Confirm that the specified units can be converted to a flux density
    try:
        unit = u.Unit(value)
    except:
        raise ValueError("{} is not a recognized unit".format(value))
    try:
        unit.to(u.W / u.m ** 3, equivalencies=u.spectral_density(1. * u.m))
    except:
        raise ValueError("Cannot convert {} to a flux density".format(value))
    return True


class fluxCalibrateConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_fluxCalibrated", optional=True)
    standard = config.ListField("Standard(s) with sensitivity function", (AstroData, str),
                                None, optional=True, single=True)
    units = config.Field("Units for output spectrum", str, "W m-2 nm-1",
                         check=flux_units_check)


class linearizeSpectraConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_linearized", optional=True)
    w1 = config.RangeField("Starting wavelength (nm)", float, None, min=0., optional=True)
    w2 = config.RangeField("Ending wavelength (nm)", float, None, min=0., optional=True)
    dw = config.RangeField("Dispersion (nm/pixel)", float, None, min=0.01, optional=True)
    npix = config.RangeField("Number of pixels in spectrum", int, None, min=2, optional=True)
    conserve = config.Field("Conserve flux?", bool, False)
    order = config.RangeField("Order of interpolation", int, 1, min=0, max=5, inclusiveMax=True)

    def validate(self):
        config.Config.validate(self)
        if [self.w1, self.w2, self.dw, self.npix].count(None) not in (1, 4):
            raise ValueError("Exactly 0 or 3 of w1, w2, dw, npix must be specified")
        if self.w1 is not None and self.w2 is not None and self.w2 <= self.w1:
            raise ValueError("Ending wavelength must be greater than starting wavelength")


class normalizeFlatConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_normalized", optional=True)
    center = config.RangeField("Central row/column to extract", int, None, min=1, optional=True)
    nsum = config.RangeField("Number of lines to sum", int, 10, min=1)
    spectral_order = config.RangeField("Fitting order in spectral direction", int, 20, min=1)
    hsigma = config.RangeField("High rejection threshold (sigma)", float, 3., min=0)
    lsigma = config.RangeField("Low rejection threshold (sigma)", float, 3., min=0)
    grow = config.RangeField("Growth radius for bad pixels", int, 0, min=0)


class resampleToCommonFrameConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_align", optional=True)
    w1 = config.RangeField("Starting wavelength (nm)", float, None, min=0., optional=True)
    w2 = config.RangeField("Ending wavelength (nm)", float, None, min=0., optional=True)
    dw = config.RangeField("Dispersion (nm/pixel)", float, None, min=0.01, optional=True)
    npix = config.RangeField("Number of pixels in spectrum", int, None, min=2, optional=True)
    conserve = config.Field("Conserve flux?", bool, False)
    order = config.RangeField("Order of interpolation", int, 1, min=0, max=5, inclusiveMax=True)
    trim_data = config.Field("Trim to field of view of reference image?", bool, False)
    force_linear = config.Field("Force linear wavelength solution?", bool, True)

    def validate(self):
        config.Config.validate(self)
        if [self.w1, self.w2, self.dw, self.npix].count(None) == 0:
            raise ValueError("Maximum 3 of w1, w2, dw, npix must be specified")
        if self.w1 is not None and self.w2 is not None and self.w2 <= self.w1:
            raise ValueError("Ending wavelength must be greater than starting wavelength")


class skyCorrectFromSlitConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_skyCorrected", optional=True)
    regions = config.Field("Sample regions", str, None, optional=True)
    order = config.RangeField("Sky spline fitting order", int, 5, min=1, optional=True)
    grow = config.RangeField("Aperture growth distance (pixels)", float, 0, min=0)


class traceAperturesConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_aperturesTraced", optional=True)
    trace_order = config.RangeField("Fitting order in spectral direction", int, 2, min=1)
    nsum = config.RangeField("Number of lines to sum", int, 10, min=1)
    step = config.RangeField("Step in rows/columns for tracing", int, 10, min=1)
    max_shift = config.RangeField("Maximum shift per pixel in line position",
                                  float, 0.05, min=0.001, max=0.1)
    max_missed = config.RangeField("Maximum number of steps to miss before a line is lost", int, 5, min=0)
    debug = config.Field("Draw aperture traces on image display?", bool, False)
