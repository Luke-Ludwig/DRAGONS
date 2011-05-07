#Author: Kyle Mede, January 2011
#For now, this module is to hold the code which performs the actual work of the 
#primitives that is considered generic enough to be at the 'gemini' level of
#the hierarchy tree.

import os, sys

import pyfits as pf
import numpy as np
import time
from copy import deepcopy
from datetime import datetime

from astrodata.AstroData import AstroData
from astrodata.adutils import varutil
from astrodata.adutils.gemutil import pyrafLoader
from astrodata.Errors import ScienceError
from gempy import geminiTools as gemt
from gempy import managers as man
from gempy.geminiCLParDicts import CLDefaultParamsDict

def add_bpm(adinput=None, output_names=None, suffix=None, bpm=None,
            matchSize=False):
    """
    This function will add the provided BPM (Bad Pixel Mask) to the inputs.  
    The BPM will be added as frames matching that of the SCI frames and ensure
    the BPM's data array is the same size as that of the SCI data array.  If the 
    SCI array is larger (say SCI's were overscan trimmed, but BPMs were not), 
    theBPMs will have their arrays padded with zero's to match the sizes and use  
    the data_section descriptor on the SCI data arrays to ensure the match is
    a correct fit.  There must be a matching number of DQ extensions in the BPM 
    as the input the BPM frames are to be added to 
    (ie. if input has 3 SCI extensions, the BPM must have 3 DQ extensions).
    
    Either a 'main' type logger object, if it exists, or a null logger 
    (ie, no log file, no messages to screen) will be retrieved/created in the 
    ScienceFunctionManager and used within this function.
          
    :param adInputs: Astrodata inputs to be converted to Electron pixel units
    :type adInputs: Astrodata objects, either a single or a list of objects
    
    :param BPMs: The BPM(s) to be added to the input(s).
    :type BPMs: 
       AstroData objects in a list, or a single instance.
       Note: If there are multiple inputs and one BPM provided, then the
       same BPM will be applied to all inputs; else the BPMs list  
       must match the length of the inputs.
           
    :param matchSize: A flag to use zeros and the key 'DETSEC' of the 'SCI'
                      extensions to match the size of the BPM arrays to those 
                      of for the 'SCI' data arrays.
    :type matchSize: Python boolean (True/False). Default: False.
                      
    :param outNames: filenames of output(s)
    :type outNames: String, either a single or a list of strings of same 
                    length as adInputs.
    
    :param suffix: string to add on the end of the input filenames 
                   (or outNames if not None) for the output filenames.
    :type suffix: string
    
    """

    # Instantiate ScienceFunctionManager object
    sfm = man.ScienceFunctionManager(adinput, output_names, suffix,
                                     funcName='add_bpm')
    # Perform start up checks of the inputs, prep/check of outnames, and get log
    adInputs, outNames, log = sfm.startUp()
                   
    if bpm is None:
        log.critical('There must be at least one BPM provided, the '+
                                        '"bpm" parameter must not be None.')
        raise ScienceError()
                   
    try:
        # Set up counter for looping through outNames/BPMs lists
        count=0
        
        # Creating empty list of ad's to be returned that will be filled below
        adOutputs=[]
        
        # Do the work on each ad in the inputs
        for ad in adInputs:
            # Getting the right BPM for this input
            if isinstance(bpm, list):
                if len(bpm)>1:
                    BPM = bpm[count]
                else:
                    BPM = bpm[0]
            else:
                BPM = bpm
            
            # Check if this input all ready has a BPM extension
            if not ad['BPM']:
                # Making a deepcopy of the input to work on
                # (ie. a truly new+different object that is a complete copy of the input)
                adOut = deepcopy(ad)
                
                # Getting the filename for the BPM and removing any paths
                BPMfilename = os.path.basename(BPM.filename)
                
                for sciExt in adOut['SCI']:
                    # Extracting the matching DQ extension from the BPM 
                    BPMArrayIn = BPM[('DQ',sciExt.extver())].data
                    
                    # logging the BPM file being used for this SCI extension
                    log.fullinfo('SCI extension number '+
                                 str(sciExt.extver())+', of file '+
                                 adOut.filename+ 
                                 ' is matched to DQ extension '
                                 +str(sciExt.extver())+' of BPM file '+
                                 BPMfilename)
                    
                    # Matching size of BPM array to that of the SCI data array
                    if matchSize:
                        # Getting the data section as a int list of form:
                        # [y1, y2, x1, x2] 0-based and non-inclusive
                        datsecList = sciExt.data_section().asPytype()
                        dsl = datsecList
                        datasecShape = (dsl[1]-dsl[0], dsl[3]-dsl[2])
                        
                        # Creating a zeros array the same size as SCI array
                        # for this extension
                        BPMArrayOut = np.zeros(sciExt.data.shape, 
                                               dtype=np.int16)
    
                        # Loading up zeros array with data from BPM array
                        # if the sizes match then there is no change, else
                        # output BPM array will be 'padded with zeros' or 
                        # 'not bad pixels' to match SCI's size.
                        if BPMArrayIn.shape==datasecShape:
                            log.fullinfo('BPM data was found to be of a'+
                                     ' different size than the SCI, so padding'+
                                     ' the BPM"s data to match the SCI.')                   
                            BPMArrayOut[dsl[0]:dsl[1], dsl[2]:dsl[3]] = \
                                                                BPMArrayIn
                        elif BPMArrayIn.shape==BPMArrayOut.shape:
                            BPMArrayOut = BPMArrayIn
                    
                    # Don't match size
                    else:
                        BPMArrayOut = BPMArrayIn
                    
                    # Creating a header for the BPM array and updating
                    # further updating to this header will take place in 
                    # addDQ primitive
                    BPMheader = pf.Header() 
                    BPMheader.update('BITPIX', 16, 
                                    'number of bits per data pixel')
                    BPMheader.update('NAXIS', 2)
                    BPMheader.update('PCOUNT', 0, 
                                    'required keyword; must = 0')
                    BPMheader.update('GCOUNT', 1, 
                                    'required keyword; must = 1')
                    BPMheader.update('BUNIT', 'bit', 'Physical units')
                    BPMheader.update('BPMFILE', BPMfilename, 
                                        'Bad Pixel Mask file name')
                    BPMheader.update('EXTVER', sciExt.extver(), 
                                        'Extension Version')
                    # This extension will be renamed DQ in addDQ
                    BPMheader.update('EXTNAME', 'BPM', 'Extension Name')
                    
                    # Creating an astrodata instance from the 
                    # DQ array and header
                    bpmAD = AstroData(header=BPMheader, data=BPMArrayOut)
                    
                    # Using renameExt to correctly set the EXTVER and 
                    # EXTNAME values in the header   
                    bpmAD.renameExt('BPM', ver=sciExt.extver())
                    
                    # Appending BPM astrodata instance to the input one
                    log.debug('Appending new BPM HDU onto the file '+ 
                              adOut.filename)
                    adOut.append(bpmAD)
                    log.status('Appending BPM complete for '+ adOut.filename)
        
            # If BPM frames exist, send a warning message to the logger
            else:
                log.warning('BPM frames all ready exist for '+
                             adOut.filename+', so add_bpm will add new ones')
                
            # Updating GEM-TLM (automatic) and ADDBPM time stamps to the PHU
            # and updating logger with updated/added time stamps
            sfm.markHistory(adOutputs=adOut, historyMarkKey='ADDBPM')

            # renaming the output ad filename
            adOut.filename = outNames[count]
                    
            log.status('File name updated to '+adOut.filename+'\n')
            
            # Appending to output list
            adOutputs.append(adOut)

            count=count+1
        
        log.status('**FINISHED** the add_bpm function')
        # Return the outputs list, even if there is only one output
        return adOutputs
    except:
        # logging the exact message from the actual exception that was raised
        # in the try block. Then raising a general ScienceError with message.
        log.critical(repr(sys.exc_info()[1]))
        raise 
    
def add_dq(adInputs, fl_nonlinear=True, fl_saturated=True, outNames=None, 
                suffix=None):
    """
    This function will create a numpy array for the data quality 
    of each SCI frame of the input data. This will then have a 
    header created and append to the input using AstroData as a DQ 
    frame. The value of a pixel will be the sum of the following: 
    (0=good, 1=bad pixel (found in bad pixel mask), 
    2=value is non linear, 4=pixel is saturated)
    
    NOTE: 
    Either a 'main' type logger object, if it exists, or a null logger 
    (ie, no log file, no messages to screen) will be retrieved/created in the 
    ScienceFunctionManager and used within this function.
          
    NOTE:
    FIND A WAY TO TAKE CARE OF NO BPM EXTENSION EXISTS ISSUE, OR ALLOWING THEM
    TO PASS IT IN...
    
    A string representing the name of the log file to write all log messages to
    can be defined, or a default of 'gemini.log' will be used.  If the file
    all ready exists in the directory you are working in, then this file will 
    have the log messages during this function added to the end of it.
    
    :param adInputs: Astrodata inputs to have DQ extensions added to
    :type adInputs: Astrodata objects, either a single or a list of objects
    
    :param fl_nonlinear: Flag to turn checking for nonlinear pixels on/off
    :type fl_nonLinear: Python boolean (True/False), default is True
    
    :param fl_saturated: Flag to turn checking for saturated pixels on/off
    :type fl_saturated: Python boolean (True/False), default is True
    
    :param outNames: filenames of output(s)
    :type outNames: String, either a single or a list of strings of same length 
                    as adInputs.
    
    :param suffix: 
       string to add on the end of the input filenames 
       (or outNames if not None) for the output filenames.
    :type suffix: string
    
    """
    
    # Instantiate ScienceFunctionManager object
    sfm = man.ScienceFunctionManager(adInputs, outNames, suffix, 
                                      funcName='add_dq')
    # Perform start up checks of the inputs, prep/check of outnames, and get log
    adInputs, outNames, log = sfm.startUp()
    
    try:
        # Set up counter for looping through outNames list
        count=0
        
        # Creating empty list of ad's to be returned that will be filled below
        adOutputs=[]
        
        # Loop through the inputs to perform the non-linear and saturated
        # pixel searches of the SCI frames to update the BPM frames into
        # full DQ frames. 
        for ad in adInputs:                
            # Check if DQ extensions all ready exist for this file
            if not ad['DQ']:
                # Making a deepcopy of the input to work on
                # (ie. a truly new+different object that is a complete copy of the input)
                adOut = deepcopy(ad)
                
                for sciExt in adOut['SCI']: 
                    # Retrieving BPM extension 
                    bpmAD = adOut[('BPM',sciExt.extver())]
                    
                    # Extracting the BPM data array for this extension
                    BPMArrayIn = bpmAD.data
                    
                    # Extracting the BPM header for this extension to be 
                    # later converted to a DQ header
                    dqheader = bpmAD.header
                    
                    ## Matching size of BPM array to that of the SCI data array
                    
                    # Getting the data section as a int list of form:
                    # [y1, y2, x1, x2] 0-based and non-inclusive
                    datsecList = sciExt.data_section().asPytype()
                    dsl = datsecList
                    datasecShape = (dsl[1]-dsl[0], dsl[3]-dsl[2])
                    
                    # Creating a zeros array the same size as SCI array
                    # for this extension
                    BPMArrayOut = np.zeros(sciExt.data.shape, 
                                           dtype=np.int16)

                    # Loading up zeros array with data from BPM array
                    # if the sizes match then there is no change, else
                    # output BPM array will be 'padded with zeros' or 
                    # 'not bad pixels' to match SCI's size.
                    if BPMArrayIn.shape==datasecShape:
                        log.fullinfo('BPM data was found to be of a'+
                                 ' different size than the SCI, so padding'+
                                 ' the BPM"s data to match the SCI.')                   
                        BPMArrayOut[dsl[0]:dsl[1], dsl[2]:dsl[3]] = BPMArrayIn
                    elif BPMArrayIn.shape==BPMArrayOut.shape:
                        BPMArrayOut = BPMArrayIn
                    
                    
                    # Preparing the non linear and saturated pixel arrays
                    # and their respective constants
                    nonLinArray = np.zeros(sciExt.data.shape, 
                                           dtype=np.int16)
                    saturatedArray = np.zeros(sciExt.data.shape, 
                                              dtype=np.int16)
                    linear = sciExt.non_linear_level().asPytype()
                    saturated = sciExt.saturation_level().asPytype()

                    if (linear is not None) and (fl_nonlinear): 
                        log.debug('Performing an np.where to find '+
                                  'non-linear pixels for extension '+
                                  str(sciExt.extver())+' of '+
                                  adOut.filename)
                        nonLinArray = np.where(sciExt.data>linear,2,0)
                        log.status('Done calculating array of non-linear'+
                                   ' pixels')
                    if (saturated is not None) and (fl_saturated):
                        log.debug('Performing an np.where to find '+
                                  'saturated pixels for extension '+
                                  str(sciExt.extver())+' of '+
                                  adOut.filename)
                        saturatedArray = np.where(sciExt.data>saturated,4,0)
                        log.status('Done calculating array of saturated'+
                                   ' pixels') 
                    
                    # Creating one DQ array from the three
                    dqArray=np.add(BPMArrayOut, nonLinArray, saturatedArray) 
                    # Updating data array for the BPM array to be the 
                    # newly calculated DQ array
                    adOut[('BPM',sciExt.extver())].data = dqArray
                    
                    # Renaming the extension to DQ from BPM
                    dqheader.update('EXTNAME', 'DQ', 'Extension Name')
                    
                    # Using renameExt to correctly set the EXTVER and 
                    # EXTNAME values in the header   
                    bpmAD.renameExt('DQ', ver=sciExt.extver(), force=True)

                    # Logging that the name of the BPM extension was changed
                    log.fullinfo('BPM Extension '+str(sciExt.extver())+
                                 ' of '+adOut.filename+' had its EXTVER '+
                                 'changed to '+
                                 adOut[('DQ',
                                        sciExt.extver())].header['EXTNAME'])
                    
            # If DQ frames exist, send a warning message to the logger
            else:
                log.warning('DQ frames all ready exist for '+
                             adOut.filename+
                             ', so addDQ will not calculate new ones')
                
            # Updating GEM-TLM (automatic) and ADDDQ time stamps to the PHU
            # and updating logger with updated/added time stamps
            sfm.markHistory(adOutputs=adOut, historyMarkKey='ADDDQ')

            # renaming the output ad filename
            adOut.filename = outNames[count]
                    
            log.status('File name updated to '+adOut.filename+'\n')
            
            # Appending to output list
            adOutputs.append(adOut)

            count=count+1
        
        log.status('**FINISHED** the add_dq function')
        # Return the outputs list, even if there is only one output
        return adOutputs
    except:
        # logging the exact message from the actual exception that was raised
        # in the try block. Then raising a general ScienceError with message.
        log.critical(repr(sys.exc_info()[1]))
        raise 

def add_var(adInputs, outNames=None, suffix=None):
    """
    This function uses numpy to calculate the variance of each SCI frame
    in the input files and appends it as a VAR frame using AstroData.
    
    The calculation will follow the formula:
    variance = (read noise/gain)2 + max(data,0.0)/gain
    
    NOTE:
    Either a 'main' type logger object, if it exists, or a null logger 
    (ie, no log file, no messages to screen) will be retrieved/created in the 
    ScienceFunctionManager and used within this function.
    
    :param adInputs: Astrodata inputs to have DQ extensions added to
    :type adInputs: Astrodata objects, either a single or a list of objects
    
    :param outNames: filenames of output(s)
    :type outNames: String, either a single or a list of strings of same length 
                    as adInputs.
    
    :param suffix: 
        string to add on the end of the input filenames 
        (or outNames if not None) for the output filenames.
    :type suffix: string
    
    """

    # Instantiate ScienceFunctionManager object
    sfm = man.ScienceFunctionManager(adInputs, outNames, suffix, funcName='add_var')
    # Perform start up checks of the inputs, prep/check of outnames, and get log
    adInputs, outNames, log = sfm.startUp()
    
    try:
        # Set up counter for looping through outNames list
        count=0
        
        # Creating empty list of ad's to be returned that will be filled below
        adOutputs=[]
        
        # Loop through the inputs to perform the non-linear and saturated
        # pixel searches of the SCI frames to update the BPM frames into
        # full DQ frames. 
        for ad in adInputs:   
            # Making a deepcopy of the input to work on
            # (ie. a truly new+different object that is a complete copy of the input)
            adOut = deepcopy(ad)
            
            # To clean up log and screen if multiple inputs
            log.fullinfo('+'*50, category='format')
            # Check if there VAR frames all ready exist
            if not adOut['VAR']:                 
                # If VAR frames don't exist, loop through the SCI extensions 
                # and calculate a corresponding VAR frame for it, then 
                # append it
                for sciExt in adOut['SCI']:
                    # Using the toolbox function calculateInitialVarianceArray
                    # to conduct the actual calculation following:
                    # var = (read noise/gain)**2 + max(data,0.0)/gain
                    varArray = varutil.calculateInitialVarianceArray(sciExt)
                     
                    # Creating the variance frame's header and updating it     
                    varHeader = varutil.createInitialVarianceHeader(
                                                        extver=sciExt.extver(),
                                                        shape=varArray.shape)
                    
                    # Turning individual variance header and data 
                    # into one astrodata instance
                    varAD = AstroData(header=varHeader, data=varArray)
                    
                    # Appending variance astrodata instance onto input one
                    log.debug('Appending new VAR HDU onto the file '
                                 +adOut.filename)
                    adOut.append(varAD)
                    log.status('appending VAR frame '+str(sciExt.extver())+
                               ' complete for '+adOut.filename)
                    
            # If VAR frames all ready existed, 
            # make a warning message in the logger
            else:
                log.warning('VAR frames all ready exist for '+adOut.filename+
                             ', so addVAR will not calculate new ones')    
            
            # Updating GEM-TLM (automatic) and ADDVAR time stamps to the PHU
            # and updating logger with updated/added time stamps
            sfm.markHistory(adOutputs=adOut, historyMarkKey='ADDVAR')

            # renaming the output ad filename
            adOut.filename = outNames[count]
                    
            log.status('File name updated to '+adOut.filename+'\n')
            
            # Appending to output list
            adOutputs.append(adOut)

            count=count+1
        
        log.status('**FINISHED** the add_var function')
        # Return the outputs list, even if there is only one output
        return adOutputs
    except:
        # logging the exact message from the actual exception that was raised
        # in the try block. Then raising a general ScienceError with message.
        log.critical(repr(sys.exc_info()[1]))
        raise 

def adu_to_electrons(adInputs, outNames=None, suffix=None):
    """
    This function will convert the inputs from having pixel values in ADU to 
    that of electrons by use of the arith 'toolbox'.
    
    Either a 'main' type logger object, if it exists, or a null logger 
    (ie, no log file, no messages to screen) will be retrieved/created in the 
    ScienceFunctionManager and used within this function.

    Note: 
    the SCI extensions of the input AstroData objects must have 'GAIN'
    header key values available to multiply them by for conversion to 
    e- units.
          
    :param adInputs: Astrodata inputs to be converted to Electron pixel units
    :type adInputs: Astrodata objects, either a single or a list of objects
    
    :param outNames: filenames of output(s)
    :type outNames: 
        String, either a single or a list of strings of same length as adInputs.
    
    :param suffix: 
        string to add on the end of the input filenames 
        (or outNames if not None) for the output filenames.
    :type suffix: string
    
    """
    
    # Instantiate ScienceFunctionManager object
    sfm = man.ScienceFunctionManager(adInputs, outNames, suffix,
                                      funcName='adu_to_electrons')
    # Perform start up checks of the inputs, prep/check of outnames, and get log
    adInputs, outNames, log = sfm.startUp()
    
    try:
        # Set up counter for looping through outNames list
        count=0
        
        # Creating empty list of ad's to be returned that will be filled below
        adOutputs=[]
        
        # Do the work on each ad in the inputs
        for ad in adInputs:
            log.fullinfo('calling ad.mult on '+ad.filename)
            
            # mult in this primitive will multiply the SCI frames by the
            # frame's gain, VAR frames by gain^2 (if they exist) and leave
            # the DQ frames alone (if they exist).
            log.debug('Calling ad.mult to convert pixel units from '+
                      'ADU to electrons')

            adOut = ad.mult(ad['SCI'].gain(asDict=True))  
            
            log.status('ad.mult completed converting the pixel units'+
                       ' to electrons')  
            
            # Updating SCI headers
            for sciExt in adOut['SCI']:
                # Retrieving this SCI extension's gain
                gainorigDict = sciExt.gain()
                gainorig = gainorigDict[(sciExt.extname(), sciExt.extver())] 
                # Updating this SCI extension's header keys
                sciExt.header.update('GAINORIG', gainorig, 
                                   'Gain prior to unit conversion (e-/ADU)')
                sciExt.header.update('GAIN', 1.0, 
                                  'Physical units is electrons') 
                sciExt.header.update('BUNIT','electrons' , 'Physical units')
                # Logging the changes to the header keys
                log.fullinfo('SCI extension number '+str(sciExt.extver())+
                             ' keywords updated/added:\n', 
                             category='header')
                log.fullinfo('GAINORIG = '+str(gainorig), 
                             category='header' )
                log.fullinfo('GAIN = '+str(1.0), category='header' )
                log.fullinfo('BUNIT = '+'electrons', category='header' )
                log.fullinfo('-'*50, category='header')
                
            # Updating VAR headers if they exist (not updating any 
            # DQ headers as no changes were made to them here)  
            for varExt in adOut['VAR']:
                # Ensure there are no GAIN and GAINORIG header keys for 
                # the VAR extension. No errors are thrown if they aren't 
                # there initially, so all good not to check ahead. 
                del varExt.header['GAINORIG']
                del varExt.header['GAIN']
                
                # Updating then logging the change to the BUNIT 
                # key in the VAR header
                varExt.header.update('BUNIT','electrons squared' , 
                                   'Physical units')
                # Logging the changes to the VAR extensions header keys
                log.fullinfo('VAR extension number '+str(varExt.extver())+
                             ' keywords updated/added:\n',
                              category='header')
                log.fullinfo('BUNIT = '+'electrons squared', 
                             category='header' )
                log.fullinfo('-'*50, category='header')
            
            # Updating GEM-TLM (automatic) and ADU2ELEC time stamps to the PHU
            # and updating logger with updated/added time stamps
            sfm.markHistory(adOutputs=adOut, historyMarkKey='ADU2ELEC')

            # renaming the output ad filename
            adOut.filename = outNames[count]
                    
            log.status('File name updated to '+adOut.filename+'\n')
            
            # Appending to output list
            adOutputs.append(adOut)

            count=count+1
        
        log.status('**FINISHED** the adu_to_electrons function')
        # Return the outputs list, even if there is only one output
        return adOutputs
    except:
        # logging the exact message from the actual exception that was raised
        # in the try block. Then raising a general ScienceError with message.
        log.critical(repr(sys.exc_info()[1]))
        raise                                          

def combine(adInputs, fl_vardq=True, fl_dqprop=True, method='average', 
            outNames=None, suffix=None):
    """
    This function will average and combine the SCI extensions of the 
    inputs. It takes all the inputs and creates a list of them and 
    then combines each of their SCI extensions together to create 
    average combination file. New VAR frames are made from these 
    combined SCI frames and the DQ frames are propagated through 
    to the final file.
    
    NOTE: The inputs to this function MUST be prepared. 

    Either a 'main' type logger object, if it exists, or a null logger 
    (ie, no log file, no messages to screen) will be retrieved/created in the 
    ScienceFunctionManager and used within this function.
    
    :param adInputs: Astrodata inputs to be combined
    :type adInputs: Astrodata objects, either a single or a list of objects
    
    :param fl_vardq: Create variance and data quality frames?
    :type fl_vardq: Python boolean (True/False), OR string 'AUTO' to do 
                    it automatically if there are VAR and DQ frames in the 
                    inputs. NOTE: 'AUTO' uses the first input to determine if 
                    VAR and DQ frames exist, so, if the first does, then the 
                    rest MUST also have them as well.
    
    :param fl_dqprop: propogate the current DQ values?
    :type fl_dqprop: Python boolean (True/False)
    
    :param method: type of combining method to use.
    :type method: string, options: 'average', 'median'.
    
    :param outNames: filenames of output(s)
    :type outNames: String, either a single or a list of strings of same length
                    as adInputs.
    
    :param suffix: string to add on the end of the input filenames 
                    (or outNames if not None) for the output filenames.
    :type suffix: string
    
    """
    
    # Instantiate ScienceFunctionManager object
    sfm = man.ScienceFunctionManager(adInputs, outNames, suffix, 
                                      funcName='combine', combinedInputs=True)
    # Perform start up checks of the inputs, prep/check of outnames, and get log
    adInputs, outNames, log = sfm.startUp()
    
    try:
        # Set up counter for looping through outNames list
        count=0
        
        # Ensuring there is more than one input to combine
        if (len(adInputs)>1):
            
            # loading and bringing the pyraf related modules into the name-space
            pyraf, gemini, yes, no = pyrafLoader()
            
            # Converting input True/False to yes/no or detecting fl_vardq value
            # if 'AUTO' chosen with autoVardq in the ScienceFunctionManager
            fl_vardq = sfm.autoVardq(fl_vardq)
                
            # Preparing input files, lists, parameters... for input to 
            # the CL script
            clm=man.CLManager(imageIns=adInputs, imageOutsNames=outNames, 
                               suffix=suffix, funcName='combine', 
                               combinedImages=True, log=log)
            
            # Check the status of the CLManager object, True=continue, False= issue warning
            if clm.status:
            
                # Creating a dictionary of the parameters set by the CLManager  
                # or the definition of the primitive 
                clPrimParams = {
                    # Retrieving the inputs as a list from the CLManager
                    'input'       :clm.imageInsFiles(type='listFile'),
                    # Maybe allow the user to override this in the future. 
                    'output'      :clm.imageOutsFiles(type='string'), 
                    # This returns a unique/temp log file for IRAF  
                    'logfile'     :clm.templog.name,   
                    'reject'      :'none'                
                              }
                
                # Creating a dictionary of the parameters from the Parameter 
                # file adjustable by the user
                clSoftcodedParams = {
                    'fl_vardq'      :fl_vardq,
                    # pyrafBoolean converts the python booleans to pyraf ones
                    'fl_dqprop'     :gemt.pyrafBoolean(fl_dqprop),
                    'combine'       :method,
                                    }
                # Grabbing the default parameters dictionary and updating 
                # it with the two above dictionaries
                clParamsDict = CLDefaultParamsDict('gemcombine')
                clParamsDict.update(clPrimParams)
                clParamsDict.update(clSoftcodedParams)
                
                # Logging the parameters that were not defaults
                log.fullinfo('\nParameters set automatically:', 
                             category='parameters')
                # Loop through the parameters in the clPrimParams dictionary
                # and log them
                gemt.logDictParams(clPrimParams)
                
                log.fullinfo('\nParameters adjustable by the user:', 
                             category='parameters')
                # Loop through the parameters in the clSoftcodedParams 
                # dictionary and log them
                gemt.logDictParams(clSoftcodedParams)
                
                log.debug('Calling the gemcombine CL script for input '+
                                 'list '+clm.imageInsFiles(type='listFile'))
                
                gemini.gemcombine(**clParamsDict)
                
                if gemini.gemcombine.status:
                    raise ScienceError('gemcombine failed for inputs '+
                                 clm.imageInsFiles(type='string'))
                else:
                    log.status('Exited the gemcombine CL script '+
                                                            'successfully')
                
                # Renaming CL outputs and loading them back into memory 
                # and cleaning up the intermediate temp files written to disk
                # refOuts and arrayOuts are None here
                imageOuts, refOuts, arrayOuts = clm.finishCL() 
            
                # Renaming for symmetry
                adOutputs=imageOuts
                
                # Updating GEM-TLM (automatic) and COMBINE time stamps to the PHU
                # and updating logger with updated/added time stamps
                sfm.markHistory(adOutputs=adOutputs, historyMarkKey='COMBINE')
            else:
                raise ScienceError('One of the inputs has not been prepared,'+
                'the combine function can only work on prepared data.')
        else:
            log.warning('Only one input was passed in for adInputs, so combine'+
                    'is simply passing the inputs into the outputs list '+
                    'without doing anything to them.')
            adOutputs = adInputs
        
        log.status('**FINISHED** the combine function')
        
        # Return the outputs list, even if there is only one output
        return adOutputs
    except:
        # logging the exact message from the actual exception that was raised
        # in the try block. Then raising a general ScienceError with message.
        log.critical(repr(sys.exc_info()[1]))
        raise 
                
def measure_iq(adInputs, function='both', display=True, qa=True,
               keepDats=False):
    """
    This function will detect the sources in the input images and fit
    both Gaussian and Moffat models to their profiles and calculate the 
    Image Quality and seeing from this.
    
    Since the resultant parameters are formatted into one nice string and 
    normally recorded in a logger message, the returned dictionary of these 
    parameters may be ignored. 
    The dictionary's format is:
    {adIn1.filename:formatted results string for adIn1, 
    adIn2.filename:formatted results string for adIn2,...}
    
    There are also .dat files that result from this function written to the 
    current working directory under the names 'measure_iq'+adIn.filename+'.dat'.
    ex: input filename 'N20100311S0090.fits', 
    .dat filename 'measure_iqN20100311S0090.dat'
    
    NOTE:
    Either a 'main' type logger object, if it exists, or a null logger 
    (ie, no log file, no messages to screen) will be retrieved/created in the 
    ScienceFunctionManager and used within this function.
    
    Warning:
    ALL inputs of adInputs must have either 1 SCI extension, indicating they 
    have been mosaic'd, or 3 like a normal un-mosaic'd GMOS image.
    
    :param adInputs: Astrodata inputs to have their image quality measured
    :type adInputs: Astrodata objects, either a single or a list of objects
    
    :param function: Function for centroid fitting
    :type function: string, can be: 'moffat','gauss' or 'both'; 
                    Default 'both'
                    
    :param display: Flag to turn on displaying the fitting to ds9
    :type display: Python boolean (True/False)
                   Default: True
                  
    :param qa: flag to use a grid of sub-windows for detecting the sources in 
               the image frames, rather than the entire frame all at once.
    :type qa: Python boolean (True/False)
              default: True
    
    :param keepDats: flag to keep the .dat files that provide detailed results 
                     found while measuring the input's image quality.
    :type keepDats: Python boolean (True/False)
                    default: False
    
    :param outNames: filenames of output(s)
    :type outNames: String, either a single or a list of strings of same length
                    as adInputs.
    
    :param suffix: string to add on the end of the input filenames 
                    (or outNames if not None) for the output filenames.
    :type suffix: string
    
    """
    
    # Instantiate ScienceFunctionManager object
    sfm = man.ScienceFunctionManager(adInputs, None, 'tmp', 
                                      funcName='measure_iq') 
    # Perform start up checks of the inputs, prep/check of outnames, and get log
    # NOTE: outNames are not needed, but sfm.startUp creates them automatically.
    adInputs, outNames, log = sfm.startUp()
    
    
    try:
        # Importing getiq module to perform the source detection and IQ
        # measurements of the inputs
        from iqtool.iq import getiq
        
        # Initializing a total time sum variable for logging purposes 
        total_IQ_time = 0
        
        # Creating dictionary for output strings to be returned in
        outDict = {}
        
        # Loop through the inputs to perform the non-linear and saturated
        # pixel searches of the SCI frames to update the BPM frames into
        # full DQ frames. 
        for ad in adInputs:                     
            # Writing the input to disk under a temp name in the current 
            # working directory for getiq to use to be deleted after getiq
            tmpWriteName = 'measure_iq'+os.path.basename(ad.filename)
            log.fullinfo('The inputs to measureIQ must be in the'+
                         ' current working directory for it to work '+\
                         'correctly, so writting it temperarily to file '+
                         tmpWriteName)
            ad.write(tmpWriteName, rename=False)
            
            # Automatically determine the 'mosaic' parameter for gemiq
            # if there are 3 SCI extensions -> mosaic=False
            # if only one -> mosaic=True, else raise error
            numExts = ad.countExts('SCI')
            if numExts==1:
                mosaic = True
            elif numExts==3:
                mosaic = False
            else:
                raise ScienceError('The input '+ad.filename+' had '+\
                                   str(numExts)+' SCI extensions and inputs '+
                                   'with only 1 or 3 extensions are allowed')
            
            # Start time for measuring IQ of current file
            st = time.time()
            
            log.debug('Calling getiq.gemiq for input '+ad.filename)
            
            # Calling the gemiq function to detect the sources and then
            # measure the IQ of the current image 
            iqdata = getiq.gemiq(tmpWriteName, function=function, 
                                  verbose=True, display=display, 
                                  mosaic=mosaic, qa=qa,
                                  debug=True)####
            
            # End time for measuring IQ of current file
            et = time.time()
            total_IQ_time = total_IQ_time + (et - st)
            # Logging the amount of time spent measuring the IQ 
            log.debug('MeasureIQ time: '+repr(et - st), category='IQ')
            log.fullinfo('~'*45, category='format')
            
            # If input was writen to temp file on disk, delete it
            if os.path.exists(tmpWriteName):
                os.remove(tmpWriteName)
                log.fullinfo('The temporarily written to disk file, '+
                             tmpWriteName+ ', was removed from disk.')
            
            # Deleting the .dat file from disk if requested
            if not keepDats:
                datName = os.path.splitext(tmpWriteName)[0]+'.dat'
                os.remove(datName)
                log.fullinfo('The temporarily written to disk file, '+
                             datName+ ', was removed from disk.')
                
            # iqdata is list of tuples with image quality metrics
            # (ellMean, ellSig, fwhmMean, fwhmSig)
            # First check if it is empty (ie. gemiq failed in someway)
            if len(iqdata) == 0:
                log.warning('Problem Measuring IQ Statistics, '+
                            'none reported')
            # If it all worked, then format the output and log it
            else:
                # Formatting this output for printing or logging                
                fnStr = 'Filename:'.ljust(19)+ad.filename
                emStr = 'Ellipticity Mean:'.ljust(19)+str(iqdata[0][0])
                esStr = 'Ellipticity Sigma:'.ljust(19)+str(iqdata[0][1])
                fmStr = 'FWHM Mean:'.ljust(19)+str(iqdata[0][2])
                fsStr = 'FWHM Sigma:'.ljust(19)+str(iqdata[0][3])
                sStr = 'Seeing:'.ljust(19)+str(iqdata[0][2])
                psStr = 'PixelScale:'.ljust(19)+str(ad.pixel_scale()[('SCI',1)])
                vStr = 'VERSION:'.ljust(19)+'None' #$$$$$ made on ln12 of ReductionsObjectRequest.py, always 'None' it seems.
                tStr = 'TIMESTAMP:'.ljust(19)+str(datetime.now())
                # Create final formated string
                finalStr = '-'*45+'\n'+fnStr+'\n'+emStr+'\n'+esStr+'\n'\
                                +fmStr+'\n'+fsStr+'\n'+sStr+'\n'+psStr+\
                                '\n'+vStr+'\n'+tStr+'\n'+'-'*45
                # Log final string
                log.stdinfo(finalStr, category='IQ')
                
                # appending formated string to the output dictionary
                outDict[ad.filename] = finalStr
                
        # Logging the total amount of time spent measuring the IQ of all
        # the inputs
        log.debug('Total measureIQ time: '+repr(total_IQ_time), 
                    category='IQ')
        
        #returning complete dictionary for use by the user if desired
        return outDict
    except:
        # logging the exact message from the actual exception that was raised
        # in the try block. Then raising a general ScienceError with message.
        log.critical(repr(sys.exc_info()[1]))
        raise                             
                
def mosaic_detectors(adInputs, fl_paste=False, interp_function='linear',  
                fl_vardq='AUTO', outNames=None, suffix=None):
    """
    This function will mosaic the SCI frames of the input images, 
    along with the VAR and DQ frames if they exist.  
    
    WARNING: The gmosaic script used here replaces the previously 
    calculated DQ frames with its own versions.  This may be corrected 
    in the future by replacing the use of the gmosaic
    with a Python routine to do the frame mosaicing.
    
    NOTE: The inputs to this function MUST be prepared. 

    Either a 'main' type logger object, if it exists, or a null logger 
    (ie, no log file, no messages to screen) will be retrieved/created in the 
    ScienceFunctionManager and used within this function.
    
    :param adInputs: Astrodata inputs to mosaic the extensions of
    :type adInputs: Astrodata objects, either a single or a list of objects
    
    :param fl_paste: Paste images instead of mosaic?
    :type fl_paste: Python boolean (True/False)
    
    :param interp_function: type of interpolation algorithm to use for between 
                            the chip gaps.
    :type interp_function: string, options: 'linear', 'nearest', 'poly3', 
                           'poly5', 'spine3', 'sinc'.
    
    :param fl_vardq: Also mosaic VAR and DQ frames?
    :type fl_vardq: Python boolean (True/False), OR string 'AUTO' to do 
                    it automatically if there are VAR and DQ frames in the 
                    inputs.
                    NOTE: 'AUTO' uses the first input to determine if VAR and  
                    DQ frames exist, so, if the first does, then the rest MUST 
                    also have them as well.
    
    :param outNames: filenames of output(s)
    :type outNames: String, either a single or a list of strings of same length 
                    as adInputs.
    
    :param suffix: string to add on the end of the input filenames 
                    (or outNames if not None) for the output filenames.
    :type suffix: string
    
    """
    
    # Instantiate ScienceFunctionManager object
    sfm = man.ScienceFunctionManager(adInputs, outNames, suffix, 
                                      funcName='mosaic_detectors') 
    # Perform start up checks of the inputs, prep/check of outnames, and get log
    adInputs, outNames, log = sfm.startUp()
    
    try:
        # loading and bringing the pyraf related modules into the name-space
        pyraf, gemini, yes, no = pyrafLoader()  
            
        # Converting input True/False to yes/no or detecting fl_vardq value
        # if 'AUTO' chosen with autoVardq in the ScienceFunctionManager
        fl_vardq = sfm.autoVardq(fl_vardq)
        
        # To clean up log and screen if multiple inputs
        log.fullinfo('+'*50, category='format')    
        
        # Preparing input files, lists, parameters... for input to 
        # the CL script
        clm=man.CLManager(imageIns=adInputs, imageOutsNames=outNames, 
                           suffix=suffix, funcName='mosaicDetectors', log=log)
        
        # Check the status of the CLManager object, True=continue, False= issue warning
        if clm.status: 
            # Parameters set by the man.CLManager or the definition of the prim 
            clPrimParams = {
              # Retrieving the inputs as a string of filenames
              'inimages'    :clm.imageInsFiles(type='string'),
              'outimages'   :clm.imageOutsFiles(type='string'),
              # Setting the value of FL_vardq set above
              'fl_vardq'    :fl_vardq,
              # This returns a unique/temp log file for IRAF 
              'logfile'     :clm.templog.name,               
                          }
            # Parameters from the Parameter file adjustable by the user
            clSoftcodedParams = {
              # pyrafBoolean converts the python booleans to pyraf ones
              'fl_paste'    :gemt.pyrafBoolean(fl_paste),
              'outpref'     :suffix,
              'geointer'    :interp_function,
                              }
            # Grabbing the default params dict and updating it with 
            # the two above dicts
            clParamsDict = CLDefaultParamsDict('gmosaic')
            clParamsDict.update(clPrimParams)
            clParamsDict.update(clSoftcodedParams)      
                
            # Logging the parameters that were not defaults
            log.fullinfo('\nParameters set automatically:', 
                         category='parameters')
            # Loop through the parameters in the clPrimParams dictionary
            # and log them
            gemt.logDictParams(clPrimParams)
            
            log.fullinfo('\nParameters adjustable by the user:', 
                         category='parameters')
            # Loop through the parameters in the clSoftcodedParams 
            # dictionary and log them
            gemt.logDictParams(clSoftcodedParams)
            
            log.debug('calling the gmosaic CL script for inputs '+
                                        clm.imageInsFiles(type='string'))
        
            gemini.gmos.gmosaic(**clParamsDict)
    
            if gemini.gmos.gmosaic.status:
                raise ScienceError('gireduce failed for inputs '+
                             clm.imageInsFiles(type='string'))
            else:
                log.status('Exited the gmosaic CL script successfully')    
                
                
            # Renaming CL outputs and loading them back into memory 
            # and cleaning up the intermediate temp files written to disk
            # refOuts and arrayOuts are None here
            imageOuts, refOuts, arrayOuts = clm.finishCL()   
            
            # Renaming for symmetry
            adOutputs = imageOuts
                
            # Wrap up logging
            i=0
            for ad in adOutputs:
                log.fullinfo('-'*50, category='header')
                
                # Varifying gireduce was actually ran on the file
                # then logging file names of successfully reduced files
                if ad.phuGetKeyValue('GMOSAIC'): 
                    log.fullinfo('\nFile '+clm.preCLimageNames()[i]+\
                                 ' mosaiced successfully')
                    log.fullinfo('New file name is: '+ad.filename)
                i=i+1

                # Updating GEM-TLM (automatic) and BIASCORR time stamps to the PHU
                # and updating logger with updated/added time stamps
                sfm.markHistory(adOutputs=ad, historyMarkKey='MOSAIC')
        else:
            raise ScienceError('One of the inputs has not been prepared, the'+
             ' mosaicDetectors function can only work on prepared data.')
                
        log.status('**FINISHED** the mosaic_detectors function')
        
        # Return the outputs list, even if there is only one output
        return adOutputs
    except:
        # logging the exact message from the actual exception that was raised
        # in the try block. Then raising a general ScienceError with message.
        log.critical(repr(sys.exc_info()[1]))
        raise 


