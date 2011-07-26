# This module contains user level functions related to adding extensions to
# and removing extensions from the input dataset

import os, sys
import numpy as np
import pyfits as pf
from astrodata import AstroData
from astrodata import Errors
from astrodata import Lookups
from astrodata.adutils import gemLog
from astrodata.ConfigSpace import lookup_path
from gempy import geminiTools as gt

def add_dq(adinput=None, bpm=None):
    """
    This user level function (ulf) is used to add a DQ extension to the input
    AstroData object. The value of a pixel in the DQ extension will be the sum
    of the following: (0=good, 1=bad pixel (found in bad pixel mask), 2=pixel
    is in the non-linear regime, 4=pixel is saturated). This ulf will trim the
    BPM to match the input AstroData object(s). If only one BPM is provided,
    that BPM will be used to determine the DQ extension for all input AstroData
    object(s). If more than one BPM is provided, the number of BPM AstroData
    objects must match the number of input AstroData objects.
    
    :param adinput: Astrodata inputs to have a DQ extension added
    :type adinput: Astrodata
    
    :param bpm: The BPM(s) to be used to flag bad pixels in the DQ extension
    :type bpm: AstroData
    """
    
    # Instantiate the log. This needs to be done outside of the try block,
    # since the log object is used in the except block 
    log = gemLog.getGeminiLog()
    
    # The validate_input function ensures that the input is not None and
    # returns a list containing one or more AstroData objects
    adinput = gt.validate_input(adinput=adinput)
    
    # Define the keyword to be used for the time stamp for this user level
    # function
    keyword = "ADDDQ"
    
    # Initialize the list of output AstroData objects
    adoutput_list = []
    
    try:
        # Call the _select_bpm helper function to get the appropriate BPMs for 
        # the input AstroData objects in the form of a dictionary, where the
        # key is the input AstroData object and the value is the BPM for that
        # AstroData object
        bpm_dict = _select_bpm(adinput=adinput, bpm=bpm)
        
        # Loop over each input AstroData object in the input list
        for ad in adinput:
            
            # Check whether the add_dq user level function has been
            # run previously
            if ad.phu_get_key_value(keyword):
                raise Errors.InputError("%s has already been processed by " \
                                        "add_dq" % (ad.filename))
            
            # Get the appropriate BPM for this AstroData object
            bpm = bpm_dict[ad]
            
            # Loop over each science extension in each input AstroData object
            for ext in ad["SCI"]:
                
                # Get the non-linear level and the saturation level as integers
                # using the appropriate descriptors
                non_linear_level = ext.non_linear_level().as_pytype()
                saturation_level = ext.saturation_level().as_pytype()
                log.fullinfo("Non linear level = %d" % non_linear_level)
                log.fullinfo("Saturation level = %d" % saturation_level)
                
                # Create an array that contains pixels that have a value of 2
                # when that pixel is in the non-linear regime in the input
                # science extension
                if non_linear_level is not None:
                    non_linear_array = np.where(
                        ((ext.data >= non_linear_level) &
                        (ext.data < saturation_level)), 2, 0)
                    # Set the data type of the array to be int16
                    non_linear_array = non_linear_array.astype(np.int16)
                
                # Create an array that contains pixels that have a value of 4
                # when that pixel is saturated in the input science extension
                if saturation_level is not None:
                    saturation_array = np.where(
                        ext.data >= saturation_level, 4, 0)
                    # Set the data type of the array to be int16
                    saturation_array = saturation_array.astype(np.int16)
                
                # Create a single DQ extension from the three arrays (BPM,
                # non-linear and saturated). BPMs have an EXTNAME equal to "DQ"
                bpmext = bpm["DQ", ext.extver()]
                dq_array = np.add(bpmext.data, non_linear_array,
                                  saturation_array)
                
                # Create a data quality AstroData object
                log.fullinfo("Using %s[DQ, %d] BPM for %s[%s, %d]" % \
                             (bpm.filename, ext.extver(), ad.filename,
                              ext.extname(), ext.extver()))
                dq = AstroData(header=pf.Header(), data=dq_array)
                dq.rename_ext("DQ", ver=ext.extver())
                dq.filename = ad.filename
                gt.update_key_value(adinput=dq, function="bunit",
                                    value="bit", extname="DQ")
                # Should a BPMFILE=bpm.filename keyword be added?
                
                # Append the DQ AstroData object to the input AstroData object.
                # Check whether an extension with the same name as the DQ
                # AstroData object already exists in the input AstroData object
                if ad["DQ", ext.extver()]:
                    raise Errors.Error("A [DQ, %d] extension already exists " \
                                       "in %s" % (ext.extver(), ad.filename))
                log.info("Adding the [DQ, %d] extension to the input " \
                         "AstroData object %s" % (ext.extver(), ad.filename))
                ad.append(moredata=dq)
            
            # Add the appropriate time stamps to the PHU
            gt.mark_history(adinput=ad, keyword=keyword)
            
            # Append the output AstroData object to the list of output
            # AstroData objects
            adoutput_list.append(ad)
        
        # Return the list of output AstroData objects
        return adoutput_list
    
    except:
        # Log the message from the exception
        log.critical(repr(sys.exc_info()[1]))
        raise

def add_mdf(adinput=None, mdf=None):
    """
    This function is to attach the MDFs to the inputs as an extension. 
    It is assumed that the MDFs are single extensions fits files and will
    thus be appended as ('MDF',1) onto the inputs.
    
    Either a 'main' type logger object, if it exists, or a null logger 
    (ie, no log file, no messages to screen) will be retrieved/created in the 
    ScienceFunctionManager and used within this function.
    
    :param adinput: Astrodata inputs to have their headers standardized
    :type adinput: Astrodata objects, either a single or a list of objects
    
    :param mdf: The MDF(s) to be added to the input(s).
    :type mdf: AstroData objects in a list, or a single instance.
               Note: If there are multiple inputs and one MDF provided, 
               then the same MDF will be applied to all inputs; else the 
               MDFs list must match the length of the inputs.
    """
    
    # Instantiate the log. This needs to be done outside of the try block,
    # since the log object is used in the except block 
    log = gemLog.getGeminiLog()
    
    # The validate_input function ensures that the input is not None and
    # returns a list containing one or more AstroData objects
    adinput = gt.validate_input(adinput=adinput)
    
    # Define the keyword to be used for the time stamp for this user level
    # function
    keyword = "ADDMDF"
    
    # Initialize the list of output AstroData objects
    adoutput_list = []
    
    try:
        # Loop over each input AstroData object in the input list
        for ad in adinput:
            
            # Check whether the add_mdf user level function has been
            # run previously
            if ad.phu_get_key_value(keyword) or ad["MDF"]:
                raise Errors.InputError("%s has already been processed by " \
                                        "add_mdf" % (ad.filename))
            
            # Call the _select_mdf helper function to get the appropriate MDF
            # for the input AstroData object
            mdffile = _select_mdf(adinput=ad, mdf=mdf)
            
            # Append the MDF AstroData object to the input AstroData object
            ad.append(moredata=mdffile)
            log.info("Adding the MDF %s to the input AstroData object %s" \
                     % (mdffile.filename, ad.filename))
            
            # Add the appropriate time stamps to the PHU
            gt.mark_history(adinput=ad, keyword=keyword)
            
            # Append the output AstroData object to the list of output
            # AstroData objects
            adoutput_list.append(ad)
        
        # Return the list of output AstroData objects
        return adoutput_list
    
    except:
        # Log the message from the exception
        log.critical(repr(sys.exc_info()[1]))
        raise

def add_var(adinput=None, read_noise=False, poisson_noise=False):
    """
    The add_var user level function calculates the variance of each science
    extension in the input AstroData object and adds the variance as an
    additional extension. This function will determine the units of the pixel
    data in the input science extension and calculate the variance in the same
    units. The two main components of the variance can be calculated and added
    separately, if desired, using the following formula:
    
    variance(read_noise) [electrons] = (read_noise [electrons])^2 
    variance(read_noise) [ADU] = ((read_noise [electrons]) / gain)^2
    
    variance(poisson_noise) [electrons] = (number of electrons in that pixel)
    variance(poisson_noise) [ADU] = (number of electrons in that pixel) / gain
    
    The pixel data in the variance extensions will be the same size as the
    pixel data in the science extension.
    
    The read noise component of the variance can be calculated and added to the
    variance extension at any time, but should be done before performing
    operations with other datasets.
    
    The Poisson noise component of the variance can be calculated and added to
    the variance extension only after any bias levels have been subtracted from
    the pixel data in the science extension.
    
    The variance of a raw bias frame contains only a read noise component
    (which represents the uncertainty in the bias level of each pixel), since
    the Poisson noise component of a bias frame is meaningless.
    
    :param adinput: input AstroData object that will have a variance extension
                    added 
    :type adinput: Astrodata
    :param read_noise: set to True to add the read noise component of the
                       variance to the variance extension
    :type read_noise: Python boolean
    :param poisson_noise: set to True to add the Poisson noise component of the
                          variance to the variance extension
    :type poisson_noise: Python boolean
    :return: output AstroData object with additional variance extension(s)
    :rtype: AstroData
    """
    
    # Instantiate the log. This needs to be done outside of the try block,
    # since the log object is used in the except block 
    log = gemLog.getGeminiLog()
    
    # The validate_input function ensures that the input is not None and
    # returns a list containing one or more AstroData objects
    adinput = gt.validate_input(adinput=adinput)
    
    # Define the keyword to be used for the time stamp for this user level
    # function
    keyword = "ADDVAR"
    
    # Initialize the list of output AstroData objects
    adoutput_list = []
    
    try:
        # Loop over each input AstroData object in the input list
        for ad in adinput:
            
            # Call the _calculate_var helper function to calculate and add the
            # variance extension to the input AstroData object
            ad = _calculate_var(adinput=ad, add_read_noise=read_noise,
                                add_poisson_noise=poisson_noise)
            
            # Add the appropriate time stamps to the PHU
            gt.mark_history(adinput=ad, keyword=keyword)
            
            # Append the output AstroData object to the list of output
            # AstroData objects
            adoutput_list.append(ad)
        
        # Return the list of output AstroData objects
        return adoutput_list
    
    except:
        # Log the message from the exception
        log.critical(repr(sys.exc_info()[1]))
        raise

##############################################################################
# Below are the helper functions for the user level functions in this module #
##############################################################################

def _select_bpm(adinput=None, bpm=None):
    """
    The _select_bpm helper function is used to select the appropriate BPM
    depending on the single input AstroData object. The returned BPM will have
    the same dimensions as the input AstroData object.
    """
    
    if bpm is not None:
        # The user supplied an input to the bpm parameter
        if not isinstance(bpm, list):
            bpm_list = [bpm]
    else:
        # Initialize the list of output BPM AstroData objects
        bpm_list = []
        
        # If no BPM is supplied, try to find an appropriate one. Get the
        # dictionary containing the list of BPMs for all instruments and modes 
        all_bpm_dict = Lookups.get_lookup_table("Gemini/BPMDict", "bpm_dict")
        
        # Loop over each input AstroData object in the input list
        for ad in adinput:
            
            # The BPMs are keyed by the instrument and the binning. Get the
            # instrument, the x binning and the y binning values using the
            # appropriate descriptors 
            instrument = ad.instrument()
            detector_x_bin = ad.detector_x_bin()
            detector_y_bin = ad.detector_y_bin()
            
            # Create the key
            if instrument is None or detector_x_bin is None or detector_x_bin \
               is None:
                if hasattr(ad, "exception_info"):
                    raise ad.exception_info
            key = "%s_%s_%s" % (instrument, detector_x_bin, detector_y_bin)
            
            # Get the BPM from the look up table
            if key in all_bpm_dict:
                bpm = AstroData(lookup_path(all_bpm_dict[key]))
            else:
                raise Errors.TableKeyError("Unable to find a BPM for %s" % key)
            bpm_list.append(bpm)
    
    # Check that the returned BPM is the same size as the input AstroData
    # object. Loop over each input AstroData object in the input list
    for ad in adinput:
        
        # Loop over each science extension in each input AstroData object
        for ext in ad["SCI"]:
            
            # BPMs have an EXTNAME equal to "DQ"
            bpmext = bpm["DQ", ext.extver()]
            
            # Ensure that the bpm has a data type of int16
            bpmext.data = bpmext.data.astype(np.int16)
            
            if bpmext.data.shape != ext.data.shape:
                # Get the data_section value of the science extension using the
                # appropriate descriptor
                x1, x2, y1, y2 = ext.data_section().as_pytype()
                # Copy the pixel data of the BPM into the data section of an
                # array that is the same size as the pixel data of the science
                # extension
                new_bpm_data = np.zeros(ext.data.shape, dtype=np.int16)
                new_bpm_data[y1:y2,x1:x2] = bpmext.data
                bpmext.data = new_bpm_data
    
    # Create a dictionary that has the AstroData objects specified by adinput
    # as the key and the AstroData objects specified by bpm as the value
    ret_bpm_dict = gt.make_dict(key_list=adinput, value_list=bpm_list)
    
    return ret_bpm_dict

def _select_mdf(adinput=None, mdf=None):
    """
    The _select_mdf helper function is used to select the appropriate MDF
    depending on the single input AstroData object. The returned MDF will have
    a single extension.
    """
    
    if mdf is not None:
        # The user supplied an input to the mdf parameter
        if not isinstance(mdf, list):
            mdf_list = [mdf]
    else:
        # Initialize the list of output MDF AstroData objects
        mdf_list = []
        
        # If no MDF is supplied, try to find an appropriate one. Get the
        # dictionary containing the list of MDFs for all instruments and modes 
        all_mdf_dict = Lookups.get_lookup_table("Gemini/MDFDict", "mdf_dict")
        
        # Loop over each input AstroData object in the input list
        for ad in adinput:
            
            # The MDFs are keyed by the instrument and the MASKNAME. Get the
            # instrument and the MASKNAME values using the appropriate
            # descriptors 
            instrument = ad.instrument()
            mask_name = ad.phu_get_key_value("MASKNAME")
            
            # Create the key
            if instrument is None or mask_name is None:
                if hasattr(ad, "exception_info"):
                    raise ad.exception_info
            key = "%s_%s" % (instrument, mask_name)
            
            # Get the MDF from the look up table
            if key in all_mdf_dict:
                mdf = AstroData(lookup_path(all_mdf_dict[key]))
            else:
                # The MASKNAME keyword defines the actual name of an MDF
                if not mask_name.endswith(".fits"):
                    mdf_name = "%s.fits" % mask_name
                else:
                    mdf_name = str(maskname)
                # Check if the MDF exists in the current working directory
                if os.path.exists(mdf_name):
                    mdf = AstroData(mdf_name)
                else:
                    msg = "The MDF file %s was not found either in the " \
                          "current working directory or in the " \
                          "gemini_python package" % (mdf_name)
                    raise Errors.InputError(msg)
            mdf_list.append(mdf)
    
    # Name the extension appropriately
    mdf.rename_ext("MDF", 1)
    
    # Check if the MDF is a single extension fits file
    if len(mdf) > 1:
        raise Errors.InputError("The MDF is not a single extension fits file")
    
    # Create a dictionary that has the AstroData objects specified by adinput
    # as the key and the AstroData objects specified by mdf as the value
    ret_mdf_dict = gt.make_dict(key_list=adinput, value_list=mdf_list)
    
    return ret_mdf_dict

def _calculate_var(adinput=None, add_read_noise=False,
                   add_poisson_noise=False):
    """
    The _calculate_var helper function is used to calculate the variance and
    add a variance extension to the single input AstroData object.
    """
    
    # Instantiate the log
    log = gemLog.getGeminiLog()
    
    # Check to see what component of variance will be added and whether it
    # is sensible to do so
    if not add_read_noise and not add_poisson_noise:
        raise Errors.InputError("Cannot add a variance extension since " \
                                "no variance component has been selected")
    if add_poisson_noise and "BIAS" in adinput.types:
        log.warning("It is not recommended to add a poisson noise " \
                    "component to the variance of a bias frame")
    if add_poisson_noise and "GMOS" in adinput.types and \
       not adinput.phu_get_key_value("BIASCORR"):
        log.warning("It is not recommended to calculate a poisson noise " \
                    "component of the variance using data that still " \
                    "contains a bias level")
    
    # Loop over the science extensions in the dataset
    for ext in adinput["SCI"]:
        
        # Determine the units of the pixel data in the input science
        # extension
        bunit = ext.get_key_value("BUNIT")
        if bunit == "adu":
            # Get the gain value using the appropriate descriptor. The gain
            # is only if the units are in ADU
            gain = ext.gain().as_pytype()
            log.fullinfo("Gain for %s[SCI,%d] = %f" \
                         % (adinput.filename, ext.extver(), gain))
            units = "ADU"
        elif bunit == "electron" or bunit == "electrons":
            units = "electrons"
        else:
            # Perhaps something more sensible should be done here?
            raise Errors.InputError("No units found. Not calculating" \
                                    "calculating variance")
        
        if add_read_noise:
            # Get the read noise value (in units of electrons) using the
            # appropriate descriptor. The read noise is only used if
            # add_read_noise is True 
            read_noise = ext.read_noise()
            log.fullinfo("Read noise for %s[SCI,%d] = %f" \
                         % (adinput.filename, ext.extver(), read_noise))
            
            # Determine the variance value to use when calculating the read
            # noise component of the variance.
            read_noise_var_value = read_noise
            if units == "ADU":
                read_noise_var_value = read_noise / gain
            
            # Add the read noise component of the variance to a zeros array
            # that is the same size as the pixel data in the science
            # extension
            log.stdinfo("Calculating the read noise component of the " \
                        "variance in %s" % units)
            var_array_rn = np.add(np.zeros(ext.data.shape,
                                           dtype=np.float32),
                                  (read_noise_var_value)**2)
        
        if add_poisson_noise:
            # Determine the variance value to use when calculating the
            # poisson noise component of the variance
            poisson_noise_var_value = ext.data
            if units == "ADU":
                poisson_noise_var_value = ext.data / gain
            
            # Calculate the poisson noise component of the variance. Set
            # pixels that are less than or equal to zero to zero.
            log.stdinfo("Calculating the poisson noise component of " \
                        "the variance in %s" % units)
            var_array_pn = np.where(ext.data > 0,
                                    poisson_noise_var_value, 0)
        
        # Create the final variance array
        if add_read_noise and add_poisson_noise:
            var_array_final = np.add(var_array_rn, var_array_pn)
        
        if add_read_noise and not add_poisson_noise:
            var_array_final = var_array_rn
        
        if not add_read_noise and add_poisson_noise:
            var_array_final = var_array_pn
        
        # If the read noise component and the poisson noise component are
        # calculated and added separately, then a variance extension will
        # already exist in the input AstroData object. In this case, just
        # add this new array to the current variance extension
        if adinput["VAR", ext.extver()]:
            # If both the read noise component and the poisson noise
            # component have been calculated, don't add to the variance
            # extension
            if add_read_noise and add_poisson_noise:
                raise Errors.InputError("Cannot add read noise " \
                    "component and poisson noise component to variance " \
                    "extension as the variance extension already exists")
            else:
                log.info("Combining the newly calculated variance with " \
                            "the current variance extension %s[VAR,%d]" \
                            % (adinput.filename, ext.extver()))
                adinput["VAR", ext.extver()].data = np.add(
                    adinput["VAR", ext.extver()].data, var_array_final)
        else:
            # Create the variance AstroData object
            var = AstroData(header=pf.Header(), data=var_array_final)
            var.rename_ext("VAR", ver=ext.extver())
            var.filename = adinput.filename
            gt.update_key_value(adinput=var, function="bunit",
                                value="%s*%s" % (bunit, bunit),
                                extname="VAR")
            
            # Append the variance AstroData object to the input AstroData
            # object. 
            log.info("Adding the [VAR, %d] extension to the input " \
                     "AstroData object %s" % (ext.extver(),adinput.filename))
            adinput.append(moredata=var)
    
    return adinput
