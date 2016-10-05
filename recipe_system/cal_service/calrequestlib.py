#
#                                                               calrequestlib.py
# ------------------------------------------------------------------------------
import os
from datetime import datetime

# Handle 2.x and 3.x. Module urlparse is urllib.parse in 3.x
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from urllib2  import HTTPError

# Legacy AstroData can recieve a url and will implicitly request 
# and open the file as an AstroData instance. See end of process_requests()
#
# ad = AstroData(calurl, store=caldname)
#
# It is not yet clear what implemention will be needed to emulate this with the
# new astrodata.
# import astrodata
# import gemini_instruments
from astrodata import AstroData
from gempy.utils  import logutils

from ..stacks import IDFactory
from .caches  import set_caches

from recipe_system.cal_service import cal_search_factory
# ------------------------------------------------------------------------------
log = logutils.get_logger(__name__)
# ------------------------------------------------------------------------------
# Currently delivers transport_request.calibration_search fn.
calibration_search = cal_search_factory()
# ------------------------------------------------------------------------------
descriptor_list = ['amp_read_area','camera','central_wavelength','coadds',
                   'data_label','data_section','detector_roi_setting',
                   'detector_x_bin','detector_y_bin','disperser','exposure_time',
                   'filter_name','focal_plane_mask','gain_setting','gcal_lamp',
                   'instrument','lyot_stop','nod_count','nod_pixels','object',
                   'observation_class','observation_type','program_id',
                   'read_speed_setting', 'ut_datetime','read_mode',
                   'well_depth_setting']

# ------------------------------------------------------------------------------
class CalibrationRequest(object):
    """
    Request objects are passed to a calibration_search() function
    
    """
    def __init__(self, ad, caltype=None, source ='all'):
        self.ad = ad
        self.caltype  = caltype
        self.datalabel = ad.data_label().for_db()
        self.descriptors = None
        self.filename = ad.filename
        self.source = source
        self.types = ad.types

    def as_dict(self):
        retd = {}
        retd.update({'filename' : self.filename,
                     'caltype'  : self.caltype,
                     'datalabel': self.datalabel,
                     "descriptors": self.descriptors,
                     'source'   : self.source,
                     "types"    : self.types,
                 }
                )
        return retd

    def __str__(self):
        tempStr = "filename: {}\nDescriptors: {}\nTypes: {}".format(self.filename,
                                                                    self.descriptors,
                                                                    self.types)
        return tempStr


def get_cal_requests(inputs, caltype):
    """
    Builds a list of CalibrationRequest objects, one for each 'ad' input.
    
    @param inputs: list of input AstroData instances
    @type inputs:  <list>
    
    @param caltype: Calibration type, eg., 'processed_bias', 'flat', etc.
    @type caltype:  <str>
    
    @return: Returns a list of CalibrationRequest instances, one for
             each passed 'ad' instance in 'inputs'.
    @rtype:  <list>

    """        
    rqEvents = []
    for ad in inputs:
        log.stdinfo("Recieved calibration request for {}".format(ad.filename))
        rq = CalibrationRequest(ad, caltype)
        options = {'central_wavelength':'asMicrometers=True'}
        
        # Check that each descriptor works and returns a 
        # sensible value before adding it to the dictionary
        desc_dict = {}
        for desc_name in descriptor_list:
            descriptor = getattr(ad, desc_name)
            dv = descriptor(options.get(desc_name, ''))
            desc_dict[desc_name] = None if dv.is_none() else dv.for_db()

        rq.descriptors = desc_dict
        rqEvents.append(rq)
            
    return rqEvents


def process_cal_requests(cal_requests):
    """
    Conduct a search for calibration files for the passed list of calibration
    requests. This passes the requests to the calibration_search() function,
    and then examines the search results to see if a matching file, if any,
    is cached. If not, then the calibration file is retrieved from the
    calibration manager, either local or fitsstore.

    :parameter cal_requests: list of CalibrationRequest objects
    :type cal_requests: <list>

    :returns: @@@TODO
    :rtype: @@@TODO

    """
    cache = set_caches()
    for rq in cal_requests:
        calname = None
        calmd5 = None
        calurl = None
        sci_ad = rq.ad
        calurl, calmd5 = calibration_search(rq.as_dict())
        if calurl is None:
            log.error("START CALIBRATION SERVICE REPORT\n")
            log.error(calmd5)
            log.error("END CALIBRATION SERVICE REPORT\n")
            log.warning("No {} calibration file found for {}".format(rq.caltype, 
                                                                     rq.filename)
                        )
            continue

        log.info("found calibration (url): " + calurl)
        components = urlparse(calurl)

        # This logic needs fixing. It appears to work, but it is inscrutable
        # and much of it probably unnecessary.
        if components.scheme == 'file':
            calfile = components.path
            calurl = calfile
        else:
            calfile = None
                
        if calfile:
            calfname = os.path.basename(calfile)
            caldname = os.path.dirname(calfile)
        elif os.path.exists(calurl):
            calfname = calurl
            caldname = None
        else:
            calfname = os.path.join(cache["retrievedcals"], rq.caltype,
                                    os.path.basename(calurl))
            caldname = os.path.dirname(calfname)

        if caldname and not os.path.exists(caldname):
            os.mkdir(caldname)

        if os.path.exists(calfname) and caldname:
            ondiskmd5 = IDFactory.generate_md5_file(calfname)
            calbname = os.path.basename(calfnam)
            if calmd5 == ondiskmd5:
                log.stdinfo("Cached calibration {} matched.".format(calbname))
                ad = AstroData(calfname)
            else:
                log.stdinfo("File {} is cached but".format(calbname))
                log.stdinfo("md5 checksums DO NOT MATCH")
                log.stdinfo("Making request on calibration service")
                try:
                    ad = AstroData(calurl, store=caldname)
                except HTTPError, error:
                    errstr = "Could not retrieve {}".format(calurl)
                    log.error(errstr)

    return # something  ...
