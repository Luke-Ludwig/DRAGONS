from GeminiData import GeminiData
from AstroData import AstroData

import new
import socket # to get host name for local statistics
import ReductionObjects
from ReductionObjects import ReductionObject
import ConfigSpace

from datetime import datetime
from copy import deepcopy

from CalibrationDefinitionLibrary import CalibrationDefinitionLibrary

# this module operates like a singleton

centralPrimitivesIndex = {}
centralRecipeIndex = {}
centralReductionMap = { }
centralAstroTypeRecipeIndex = {}
  
class RecipeExcept:
    """ This is the general exception the classes and functions in the
    Structures.py module raise.
    """
    def __init__(self, msg="Exception Raised in Recipe System"):
        """This constructor takes a message to print to the user."""
        self.message = msg
    def __str__(self):
        """This str conversion member returns the message given by the user (or the default message)
        when the exception is not caught."""
        return self.message
        
        
class ContextObject(dict):
    """The ContextObject is used by primitives and recipies, hidden in the later case,
    to get input and report output. This allows primitives to be controlled in many different
    running environments, from pipelines to command line interactive reduction.
    """
    inputs = None
    originalInputs = None
    inputsHistory = None
    outputs = None
    calibrations = None
    calrqs = None
    status = "EXTANT"
    reason = "EXTANT"
    cmdRequest = "NONE"
    hostname = None
    
    stephistory = None
    def __init__(self):
        """The ContextObject constructor creates empty dictionaries and lists, members set to
        None in the class."""
        self.inputs = []
        self.inputsHistory = []
        self.calibrations = {}
        self.calrqs = []
        self.outputs = {"standard":[]}
        self.stephistory = {}
        self.hostname = socket.gethostname()
        # TESTING
        self.cdl = CalibrationDefinitionLibrary()
        # undeclared
        self.indent=0 
    
    def isFinished(self,arg = None):
        if arg == None:
            return self.status == "FINISHED"
        else:
            if arg == True:
                self.status = "FINISHED"
            elif self.status != "FINISHED":
                raise RecipeExcept("Attempt to change status from %s to FINISHED" % self.status)
        return self.isFinished()
    
    def finish(self):
        self.isFinished(True)
        
    finished = property(isFinished, isFinished)

    def isPaused(self, bpaused = None):
        if bpaused == None:
            return self.status == "PAUSED"
        else:
            if bpaused:
                self.status = "PAUSED"
            else:
                self.status = "RUNNING"
        
        return self.isPaused()

    def pause(self):
        self.isPaused(True)
    def unpause (self):
        self.isPaused(False)

    paused = property(isPaused, isPaused)

    def processCmdReq(self):
        if self.cmdRequest == "pause":
            self.cmdRequest = "NONE"
            self.pause()


    def getEndMark(self, stepname, indent= None):
        for time in self.stephistory.keys():
            if     self.stephistory[time]["stepname"] == stepname \
               and self.stephistory[time]["mark"] == "end":
                if indent != None:
                    if self.stephistory[time]["indent"] == indent:
                        return (time,self.stephistory[time])
                else:
                    return (time,self.stephistory[time])
                
    
        return None
        
    def getBeginMark(self, stepname, indent=None):
        for time in self.stephistory.keys():
            if     self.stephistory[time]["stepname"] == stepname \
               and self.stephistory[time]["mark"] == "begin":
                    if indent != None:
                        if self.stephistory[time]["indent"] == indent:
                            return (time,self.stephistory[time])
                    else:
                        return (time,self.stephistory[time])    
        return None

        
    def control(self, cmd = "NONE"):
        self.cmdRequest = cmd

    def requestPause(self):
        self.control("pause")

    def pauseRequested(self):
        return self.cmdRequest == "pause"
        
    def checkControl(self):
        return self.cmdRequest        
        
    def addInput(self, filename):
        self.inputs.append(filename)
        
    def reportOutput(self, filename, category="standard"):
        # note, other categories not supported yet
        if category != "standard":
            raise RecipeExcept("You may only use " +
                "'standard' category output at this time.")
        if type(filename) == str:
            self.outputs["standard"].append(filename)
        elif type(filename) == list:
            self.outputs["standard"].extend(filename)
    def finalizeOutputs(self):
        """ This function means there are no more outputs, generally called
        in a control loop when a generator function primitive ends.  Standard
        outputs become the new inputs. Calibrations and non-standard output
        is not affected.
        """
        # only push is outputs is filled
        if len(self.outputs["standard"]) != 0:
            # don't do this if the set is empty, it's a non-IO primitive
            if self.originalInputs == None:
                self.originalInputs = deepcopy(self.inputs)
                
            self.inputs = self.outputs["standard"]
            self.outputs.update({"standard":[]})
            
    
    def prependNames(self, prepend, currentDir = True):
        newlist = []
        for nam in self.inputs:
            if currentDir == True:
                path = os.getcwd()
            else:
                path = os.path.dirname(nam)
            fn   = os.path.basename(nam)
            newpath = path + "/" + prepend + fn
            newlist.append(newpath)
        return newlist
    
    def stepMoment(self, stepname, mark):
        val = { "stepname"  : stepname,
                "indent"    : self.indent,
                "mark"      : mark,
                "inputs"    : deepcopy(self.inputs),
                "outputs"   : deepcopy(self.outputs),
                "processed" : False
                }
        return val       
        
    def begin(self, stepname):
        key = datetime.now()
        # value = dictonary
        val = self.stepMoment(stepname, "begin")
        self.indent += 1
        self.stephistory.update({key: val}) 
        self.lastBeginDt = key
        return self
                
    def end(self,stepname):
        key = datetime.now()
        self.indent -= 1
        val = self.stepMoment(stepname,"end")
        # this step saves inputs
        self.stephistory.update({key: val})
        # this step moves outputs["standard"] to inputs
        # and clears outputs
        self.finalizeOutputs()
        return self
                
    def inputsAsStr(self, strippath = True):
        if self.inputs == None:
            return ""
        else:
            if strippath == False:
                print self.inputs
                return ", ".join(self.inputs)
            else:
                return ", ".join([os.path.basename(path) for path in self.inputs])

    def outputsAsStr(self, strippath = True):
        if self.outputs == None:
            return ""
        else:
            if strippath == False:
                # print self.inputs
                return ", ".join(self.outputs)
            else:
                return ", ".join([os.path.basename(path) for path in self.outputs])
        
    def addCal(self, fname, caltyp, calname, timestamp = None):
        if timestamp == None:
            timestamp = datetime.now()
        else:
            timestamp = timestamp
        # @@workpoint@@
        if self.calibrations == None:
            self.calibrations = {}
        
        key = (fname, caltyp)
        self.calibrations.update({key: calname})
    
    def getCal(self, filename, caltype):
        key = (filename, caltype)
        #print "RM241:", filename, caltype, self.calibrations.keys(), key in self.calibrations
        if key in self.calibrations.keys():
            return self.calibrations[(filename,caltype)]
        return None
        
    def addCalRq(self, calrq):
        if self.calrqs == None:
            self.calrqs = []
        self.calrqs.append(calrq)
    
    def rqCal(self, caltype):        
        addToCmdQueue = self.cdl.getCalReq( self.inputs, caltype )
        for re in addToCmdQueue:
            self.addCalRq(re)
        
        '''
        for cmd in addToCmdQueue:
            self.cmdQueue.add( cmd )
        '''
        
    def calFilename(self, caltype):
        """returns a local filename for a retrieved calibration"""
        if self.originalInputs == None:
            self.originalInputs = deepcopy(self.inputs)
        if len(self.originalInputs) == 0:
            return None
        elif len(self.originalInputs) == 1:
            fname = self.originalInputs[0]
            key = (fname, caltype)
            return self.calibrations[key]
        else:
            retl = []
            for inp in self.originalInputs:
                key = (inp, caltype)
                retl.append(self.calibrations[key])
        
    def reportHistory(self):
        
        sh = self.stephistory
        
        ks = self.stephistory.keys()
        
        ks.sort()
        
        # print sort(sh.keys())
        lastdt = None
        startdt = None
        enddt = None

        retstr = "RUNNING TIMES\n"
        retstr += "-------------\n"
        for dt in ks: # self.stephistory.keys():
            indent = sh[dt]["indent"]
            indentstr = "".join(["  " for i in range(0,indent)])
            
            mark = sh[dt]["mark"]
            if mark == "begin":
                elapsed = ""
                format = "%(indent)s%(stepname)s begin at %(time)s"
            elif mark == "end":
                elapsed = "("+str(dt-lastdt)+") "
                format="\x1b[1m%(indent)s%(stepname)s %(elapsed)s \x1b[22mends at %(time)s"
            else:
                elapsed = ""
                format = "%(indent)s%(stepname)s %(elapsed)s%(mark)s at %(time)s"
                
            lastdt = dt
            if startdt== None:
                startdt = dt

            pargs =  {  "indent":indentstr,
                        "stepname":str(sh[dt]['stepname']), 
                        "mark":str(sh[dt]['mark']),
                        "inputs":str(",".join(sh[dt]['inputs'])),
                        "outputs":str(sh[dt]['outputs']),
                        "time":str(dt),
                        "elapsed":elapsed,
                        "runtime":str(dt-startdt),
                    }
            retstr += format % pargs + "\n"
            retstr += "%(indent)sTOTAL RUNNING TIME: %(runtime)s (MM:SS:ms)" % pargs  + "\n"
       
        startdt = None
        lastdt = None
        enddt = None
        wide = 75
        retstr +=  "\n\n"
        retstr +=  "SHOW IO".center(wide)  + "\n"
        retstr +=  "-------".center(wide) + "\n"
        retstr +=  "\n"
        for dt in ks: # self.stephistory.keys():
            indent = sh[dt]["indent"]
            indentstr = "".join(["  " for i in range(0,indent)])
            
            mark = sh[dt]["mark"]
            if mark == "begin":
                elapsed = ""
            elif mark == "end":
                elapsed = "("+str(dt-lastdt)+") "
                
            pargs =  {  "indent":indentstr,
                        "stepname":str(sh[dt]['stepname']), 
                        "mark":str(sh[dt]['mark']),
                        "inputs":str(",".join(sh[dt]['inputs'])),
                        "outputs":str(",".join(sh[dt]['outputs']['standard'])),
                        "time":str(dt),
                        "elapsed":elapsed,
                    }
            if startdt == None:
                retstr +=  ("%(inputs)s" % pargs).center(wide) + "\n"

            if (pargs["mark"] == "end"):
                retstr +=  " | ".center(wide) + "\n"
                retstr +=  "\|/".center(wide) + "\n"
                retstr +=  " ' ".center(wide) + "\n"
                
                line = ("%(stepname)s" % pargs).center(wide)
                line = "\x1b[1m" + line + "\x1b[22m"  + "\n"
                retstr +=  line
                
            if len(sh[dt]["outputs"]["standard"]) != 0:
                retstr +=  " | ".center(wide) + "\n"
                retstr +=  "\|/".center(wide) + "\n"
                retstr +=  " ' ".center(wide) + "\n"
                retstr +=  ("%(outputs)s" % pargs).center(wide) + "\n"
                
                
            lastdt = dt
            if startdt== None:
                startdt = dt
        
        return retstr

def openIfName(dataset):
    """Utility function to handle accepting datasets as AstroData
    instances or string filenames. Works in conjunction with closeIfName.
    The way it works, openIfName opens returns an GeminiData isntance"""
    
    bNeedsClosing = False
    
    if type(dataset) == str:
        bNeedsClosing = True
        gd = GeminiData(dataset)
    elif isinstance(dataset, AstroData):
        bNeedsClosing = False
        gd = dataset
    else:
        raise RecipeExcept("BadArgument in recipe utility function: openIfName(..)\n MUST be filename (string) or GeminiData instrument")
    
    return (gd, bNeedsClosing)
    
    
def closeIfName(dataset, bNeedsClosing):
    """Utility function to handle accepting datasets as AstroData
    instances or string filenames. Works in conjunction with openIfName."""

    if bNeedsClosing == True:
        dataset.close()
    
    return


class RecipeLibrary(object):

    primLoadTimes = {}
    
    def addLoadTime(self, source, start, end):
        key = datetime.now()
        pair = {key: {"source":source,"start":start, "end":end}}
        self.primLoadTimes.update(pair)
        
    def reportHistory(self):
        self.reportLoadTimes()
        
    def reportLoadTimes(self):
        skeys = self.primLoadTimes.keys()
        skeys.sort()
        
        for key in skeys:
            primrecord = self.primLoadTimes[key]
            source = primrecord["source"]
            start = primrecord["start"]
            end = primrecord["end"]
            duration = end - start
            
            pargs = {   "module":source, 
                        "duration":duration,
                        }
            print "Module '%(module)s took %(duration)s to load'" % pargs

    def loadAndBindRecipe(self,ro, name, file=None, astrotype=None):
        """
        Will load a single recipe, compile and bind it to the given reduction objects
        """
        # NOTE: sort out precedence of one type over another
        # in all cases.
        if astrotype != None:
            # get recipe source
            rec = self.retrieveRecipe(name, astrotype= astrotype)
    
            if rec:
                # compose to python source
                prec = self.composeRecipe(name, rec)
                # compile to unbound function (using the python interpretor obviously)
                rfunc = self.compileRecipe(name, prec)
                # bind the recipe to the reduction object
                ro = self.bindRecipe(ro, name, rfunc)
        elif file != None:
            gd, bnc = openIfName(file)
            types = gd.getTypes()
            for typ in types:
                rec   = self.retrieveRecipe(name, astrotype= typ)
                if rec:
                    prec  = self.composeRecipe(name, rec)
                    rfunc = self.compileRecipe(name, prec)
                    ro = self.bindRecipe(ro, name, rfunc)
        
            closeIfName(gd, bnc)
            

    def getApplicableRecipes(self, dataset, collate = False):
        """
        Get list of recipes associated with all the types that apply to this dataset.
        """
        if  type(dataset) == str:
            astrod = GeminiData(dataset)
            byfname = True
        elif isinstance(dataset, AstroData.AstroData):
            byfname = false
            astrod = dataset
        else:
            raise BadArgument()

        # get the types
        types = astrod.getTypes()
        # look up recipes, fill list
        reclist = []
        recdict = {}
        for typ in types:
            if typ in centralAstroTypeRecipeIndex.keys():
                recnames = centralAstroTypeRecipeIndex[typ]
                reclist.extend(recnames)
                recdict.update({typ: recnames})
            

        # if we opened the file we close it
        if byfname:
            astrod.close()
        
        if collate == False:
            return reclist
        else:
            return recdict
        
        
    def retrieveRecipe(self, name, astrotype=None):
        cri = centralRecipeIndex
        if astrotype:
            akey = name+"."+astrotype
            key = name 
        else:
            key = name
            akey = name+".None"

        bdefRecipe = key in cri
        bastroRecipe = akey in cri
        
        fname = None
        if bastroRecipe:
            fname = cri[akey]
        elif bdefRecipe:
            fname = cri[key]
        else:
            return None

        rfile = file(fname, "r")
        rtext = rfile.read()
        return rtext
            
    def retrieveReductionObject(self, dataset = None, astrotype=None):
        a = datetime.now()
        if (astrotype != None) and (astrotype in centralPrimitivesIndex):
            rfilename = centralPrimitivesIndex[astrotype][0]
            rpathname = centralReductionMap[rfilename]
            rootpath = os.path.dirname(rpathname)
            importname = os.path.splitext(rfilename)[0]
            a = datetime.now()
            exec ("import " + importname)
            b = datetime.now()
            ro = eval (importname+"."+centralPrimitivesIndex[astrotype][1]+"()")
            c = datetime.now()
        elif dataset != None:
            gd, bnc = openIfName(file)
            types = gd.getTypes()
            ropaths = []
            ropath = None
            for typ in types:
                if typ in centralPrimitivesIndex:
                    rfilename = centralPrimitivesIndex[typ][0]
                    if rfilename in centralReductionMap:
                        rpathname = centralReductionMap[rfilename]
                        rootpath = os.path.dirname(rpathname)
                    else:
                        raise RecipeExcept("Error in centralReductionMap")          
                newrotyp = typ
                newropath = rpathname
                if ropath == None:
                    # first one, then it's fine
                    ropath = newropath
                    rotyp  = newrotyp
                else:
                    # not first one, then 
                    #  a) there must be a type/subtype relationship
                    #  b) the subtype takes precedence as the 
                    #     "more special" type
                    nt = gd.getClasificationLibrary().getTypeObj(newrotyp)
                    if nt.isSubtypeOf(rotyp):
                        # subtypes "win" the assignment
                        ropath = newropath
                        rotyp = newrotyp
                    else:
                        ot = cl.getTypeObj(rotyp)
                        if not ot.isSubtypeOf(newrotyp):
                            raise RecipeExcept(
                                "CONFLICTING PRIMITIVES ASSIGNMENT\n"+ \
                                '\t type: "%s" conflicts with type: "%s"' % \
                                (rotyp, newrotype) )
            importname = os.path.splitext(ropath)[0]
            a = datetime.now()
            exec ("import " + importname)
            b = datetime.now()
            ro = eval (importname+"."+centralPrimitivesIndex[rotype][1]+"()")
            c = datetime.now()
            closeIfName(gd, bnc)
        else:
            ro = ReductionObjects.ReductionObject()
            raise ("Tried to retrive base Reduction Object,\n" + \
                   "not allowed at this time." )
            
        ro.recipeLib = self
        
        b = datetime.now()
        if astrotype != None:
            source = "TYPE: " + astrotype
        elif dataset != None:
            source = "FILE: " + dataset
        else:
            source = "UNKNOWN"
        self.addLoadTime(source, a, b)
        return ro
        
    def composeRecipe(self, name, recipebuffer):
        templ = """
def %(name)s(self,cfgObj):
\tprint "RECIPE STARTS %(name)s"
%(lines)s
\tprint "RECIPE ENDS   %(name)s"
\tyield cfgObj
"""
        recipelines = recipebuffer.splitlines()
        lines = ""
        # print recipelines
        for line in recipelines:
            line = line.strip()
            if line == "" or line[0]=="#":
                continue
            newl =  """
\tfor co in self.substeps('%s', cfgObj):
\t\tyield co""" % line
            lines += newl
            
        rets = templ % {    "name" : name,
                            "lines" : lines }
        
        return rets
        
    def compileRecipe(self, name, recipeinpython):
        exec(recipeinpython)
        func = eval(name)
        return func
        
    def bindRecipe(self, redobj, name, recipefunc):
        bindstr = "redobj.%s = new.instancemethod(recipefunc, redobj, None)" % name
        exec(bindstr)
        return redobj
    
    def checkMethod(self, redobj, primitivename):
        methstr = "redobj.%s" % primitivename
        try:
            # print methstr
            func = eval(methstr)
        except AttributeError:
            # then it does not exist
            return False
        
        return True
        
    def checkAndBind(self, redobj, name, context = None):
        dir (redobj)
        if self.checkMethod(redobj, name):
            return False
        else:
            self.loadAndBindRecipe(redobj, name, file=context.inputs[0])
            return True


# CODE THAT RUNS ON IMPORT
# THIS MODULE ACTS AS A SINGLETON FOR RECIPE FEATURES

# NOTE: The issue of a central service for recipes implies a need for
# a singleton as with the ClassificationLibrary and the Descriptors.py module.
# I have adopted the module-as-singleton approach for Structures as it does
# not involve the message try-instantiate-except block used in the 
# ClassificationLibrary.  I'm checking into
# possible complications but it seems acceptable python.

#: recipeIndexREMask used to identify which files by filename
#: are those with tables relating type names to structure types
primitivesIndexREMask = r"primitivesIndex\.(?P<modname>.*?)\.py$"
recipeIndexREMask = r"recipeIndex\.(?P<modname>.*?)\.py$"
#theorectically could be automatically correlated by modname

reductionObjREMask = r"reduction_(?P<redname>.*?)\.py$"


recipeREMask = r"recipe\.(?P<recipename>.*?)$"
recipeAstroTypeREMask = r"(?P<recipename>.*?)\.(?P<astrotype>.*?)$"



import os,sys,re

if True: # was firstrun logic... python interpreter makes sure this module only runs once already

    # WALK the directory structure
    # add each directory to the sytem path (from which import can be done)
    # and exec the structureIndex.***.py files
    # These indexes are meant to append it to the centralDescriptorIndex

    for root, dirn, files in ConfigSpace.configWalk("recipes"):
        sys.path.append(root)
        for sfilename in files:
            m = re.match(recipeREMask, sfilename)
            mpI = re.match(primitivesIndexREMask, sfilename)
            mri = re.match(recipeIndexREMask, sfilename)
            mro = re.match(reductionObjREMask,sfilename)            
            fullpath = os.path.join(root, sfilename)
            
            if m:
                recname = m.group("recipename")
                if False:
                    print sfilename
                    print "complete recipe name(%s)" % m.group("recipename")
                centralRecipeIndex.update({recname: fullpath})
                
                am = re.match(recipeAstroTypeREMask, m.group("recipename"))
                # print str(am)
                if False: # am:
                    print "recipe:(%s) for type:(%s)" % (am.group("recipename"), am.group("astrotype"))
            elif mpI: # this is an primitives index
                efile = open(fullpath,"r")
                exec (efile)
                efile.close()
                centralPrimitivesIndex.update(localPrimitiveIndex)
            elif mro: # reduction object file... contains  primitives as members
                centralReductionMap.update({sfilename: fullpath})
            elif mri: # this is a recipe index
                efile = open(fullpath, "r")
                # print fullpath
                exec efile
                efile.close()
                for key in localAstroTypeRecipeIndex.keys():
                    if centralRecipeIndex.has_key(key):
                        curl = centralRecipeIndex[key]
                        curl.append(localAstroTypeRecipeIndex[key])
                        localAstroTypeRecipeIndex.update({key: curl})
                
                centralAstroTypeRecipeIndex.update(localAstroTypeRecipeIndex)
            
            # look for recipe
            # 
        
    if False:
        print "----- DICTIONARIES -----"
        print str(centralRecipeIndex)
        print str(centralAstroTypeRecipeIndex)
        print str(centralPrimitivesIndex)
        print str(centralReductionMap)
        print "--EOF DICTIONARIES EOF--"
    
        
        
    if False:
            # (re.match(structureIndexREMask, sfilename)):
                fullpath = os.path.join(root, sfilename)
                siFile = open(fullpath)
                exec siFile
                siFile.close()
                # file must declare structureIndex = {...}, keys are types, 
                # values are string names of structure classes that can
                # be instantiated when needed (should refer to modules
                # and classes in structures subdirectory, all of which is
                # in the import path.
                
                # note: make sure one index does not stomp another
                # Means misconfigured structureIndex.
                
                for key in structureIndex.keys():
                    if centralStructureIndex.has_key(key):
                        # @@log
                        msg = "Scructure Index CONFLICT\n"
                        msg += "... structure for type %s\n" % key
                        msg += "redefined in\n" 
                        msg += "... %s\n" % fullpath
                        msg += "... was already set to %s\n" %centralStructureIndex[key]
                        msg += "... this is a fatal error"
                        raise StructureExcept(msg)
                        
                centralStructureIndex.update(structureIndex)


