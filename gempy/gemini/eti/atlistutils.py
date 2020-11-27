
from gempy.gemini import gemini_tools

from ..utils import logutils
log = logutils.get_logger(__name__)

class AtListUtils:

	def __init__(self):
		log.debug("AtListUtils __init__")

	def prepare_adinput(self, adinput, prefix, diskinlist, taskname):
		for ad in adinput:
            ad = gemini_tools.obsmode_add(ad)
            origname = ad.filename
            ad.update_filename(prefix=prefix, strip=True)
            diskinlist.append(ad.filename)
            log.fullinfo("Temporary image (%s) on disk for the IRAF task %s" % \
                          (ad.filename, taskname))
            ad.write(ad.filename, overwrite=True)
            ad.filename = origname

    def prepare_atlist(self, atlist, pid_task, diskinlist, taskname):
        atlist = "tmpImageList" + pid_task
        fhdl = open(atlist, "w")
        for fil in diskinlist:
            fhdl.writelines(fil + "\n")
        fhdl.close()
        log.fullinfo("Temporary list (%s) on disk for the IRAF task %s" % \
                      (atlist, taskname))

    def remove_files(self, filelist, atlist):
    	log.debug("AtListUtils remove_files()")
    	for a_file in filelist:
            os.remove(a_file)
            log.fullinfo("%s was deleted from disk" % a_file)
        os.remove(atlist)
        log.fullinfo("%s was deleted from disk" % atlist)
