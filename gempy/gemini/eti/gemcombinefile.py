import os
import tempfile
import re

import astrodata
import gemini_instruments
from gempy.utils import logutils
from gempy.eti_core.pyrafetifile import PyrafETIFile
from gempy.eti_core.atlistutils import AtListUtils

from gempy.gemini import gemini_tools

log = logutils.get_logger(__name__)

class GemcombineFile(PyrafETIFile):
    """This class coordinates the ETI files as it pertains to the IRAF
    task gemcombine directly.
    """
    inputs = None
    params = None

    diskinlist = None
    pid_str = None
    pid_task = None
    adinput = None

    def __init__(self, inputs=None, params=None):
        """
        :param rc: Used to store reduction information
        :type rc: ReductionContext
        """
        log.debug("GemcombineFile __init__")
        PyrafETIFile.__init__(self, inputs, params)
        self.diskinlist = []
        self.taskname = "gemcombine"
        self.pid_str = str(os.getpid())
        self.pid_task = self.pid_str + self.taskname
        self.adinput = inputs

    def get_prefix(self):
        return "tmp" + self.pid_task

class InAtList(GemcombineFile):
    inputs = None
    params = None

    atlist = None

    def __init__(self, inputs=None, params=None):
        """
        :param rc: Used to store reduction information
        :type rc: ReductionContext
        """
        log.debug("InAtList __init__")
        GemcombineFile.__init__(self, inputs, params)
        self.atlist = ""
        self.atlistutils = AtListUtils()

    def prepare(self):
        log.debug("InAtList prepare()")
        self.atlistutils.prepare_adinput(self.adinput, self.get_prefix(), self.diskinlist, self.taskname)
        self.atlistutils.prepare_atlist(self.atlist, self.pid_task, self.diskinlist, self.taskname)
        self.filedict.update({"input": "@" + self.atlist})

    def clean(self):
        log.debug("InAtList clean()")
        self.atlistutils.remove_files(self.diskinlist, self.atlist)

class OutFile(GemcombineFile):
    inputs = None
    params = None

    suffix = None
    recover_name = None
    ad_name = None
    tmp_name = None

    def __init__(self, inputs, params):
        """
        :param rc: Used to store reduction information
        :type rc: ReductionContext
        """
        log.debug("OutFile __init__")
        GemcombineFile.__init__(self, inputs, params)
        self.suffix = params["suffix"]
        self.ad_name = ""
        self.tmp_name = ""

    def prepare(self):
        log.debug("Outfile prepare()")
        origname = self.adinput[0].filename
        self.adinput[0].update_filename(suffix=self.suffix, strip=True)
        outname = self.adinput[0].filename
        self.adinput[0].filename = origname
        self.ad_name = outname
        self.tmp_name = self.get_prefix() + outname
        self.filedict.update({"output": self.tmp_name})

    def recover(self):
        log.debug("OufileETIFile recover()")
        ad = astrodata.open(self.tmp_name)
        ad.filename = self.ad_name
        ad = gemini_tools.obsmode_del(ad)
        log.fullinfo(self.tmp_name + " was loaded into memory")
        return ad

    def clean(self):
        log.debug("Outfile clean()")
        os.remove(self.tmp_name)
        log.fullinfo(self.tmp_name + " was deleted from disk")


class LogFile(GemcombineFile):
    inputs = None
    params = None
    def __init__(self, inputs=None, params=None):
        """
        :param rc: Used to store reduction information
        :type rc: ReductionContext
        """
        log.debug("LogFile __init__")
        GemcombineFile.__init__(self, inputs, params)

    def prepare(self):
        log.debug("LogFile prepare()")
        tmplog = tempfile.NamedTemporaryFile()
        self.filedict.update({"logfile": tmplog.name})

