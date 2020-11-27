from .etifile import ETIFile

from ..utils import logutils
log = logutils.get_logger(__name__)

class PyrafETIFile(ETIFile):
    """This class coordinates the ETI files as it pertains to Pyraf
    tasks in general.
    """
    inputs = None
    params = None
    filedict = None
    def __init__(self, inputs=None, params=None):
        """
        :param rc: Used to store reduction information
        :type rc: ReductionContext
        """
        log.debug("PyrafETIFile __init__")
        ETIFile.__init__(self, name=None, inputs=inputs, params=params)
        self.filedict = {}

    def get_parameter(self):
        """This returns a parameter as a key value pair to be added
        to a master parameter dict (xcldict) that is used by ETI execute
        """
        log.debug("PyrafETIParam get_parameter()")
        return self.filedict

    def prepare(self):
        log.debug("PyrafETIFile prepare()")

    def recover(self):
        log.debug("PyrafETIFile recover(): pass")

    def clean(self):
        log.debug("PyrafETIFile clean(): pass")

    def _remove_files(self, file_list, _at_list):
        """A common way for subclasses to implement clean, pass in the file_list and _at_list
        and the corresponding files will be removed from disk
        """
        log.debug("PyrafETIFile _remove_files()")
        for a_file in file_list:
            os.remove(a_file)
            log.fullinfo("%s was deleted from disk" % a_file)
        os.remove(_at_list)
        log.fullinfo("%s was deleted from disk" % _at_list)

