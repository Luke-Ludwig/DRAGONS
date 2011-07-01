# This module contains functions that calculate variance using the input
# dataset

import numpy as np
import astrodata
from astrodata.AstroData import AstroData
from astrodata.Errors import ArithError

def varianceArrayCalculator(sciExtA=None, sciExtB=None, constB=None,  
                            sciOut=None, varExtA=None, varExtB=None, div=False, 
                                            mult=False, sub=False, add=False):
    """    
    This function will update a currently existing variance plane due to a 
    mathematical operation performed on the science data.    
    
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    For multiplications and division operations:
    --------------------------------------------
    If sciExtB is an AstroData instance:
    varOut=sciOut^2 * ( varA/(sciA^2) + varB/(sciB^2) )
    
    Else:
    varOut=varA * constB^2
    
    For addition and subtraction operations:
    ----------------------------------------
    If sciExtB is an AstroData instance:
    varOut= varA + varB
    
    Else:
    varOut=varA 
    variance is not affected if the science data is just consistently raised
    or lowered by a constant.
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    The A input MUST have a varExtA defined!
    
    If both A and B inputs are AstroData's then they must BOTH have varExt's.
    
    Only ONE mathematical operation can be performed at a time!!
    
    :param sciExtA: science extension of an AstroData instance being multiplied
                    or divided by sciExtB
    :type sciExtA: AstroData single extension. ex. sciExtA = adA['SCI',#]
    
    :param sciExtB: science extension of an AstroData instance being multiplied
                    by sciExtA OR dividing sciExtA by
    :type sciExtB: AstroData single extension.ex. sciExtB = adB['SCI',#]
    
    :param sciOut: science extension of an output AstroData instance
                   ie. the science frame resulting from the operation.
    :type sciOut: AstroData single extension.ex. sciOut = adOut['SCI',#]
    
    :param constB: constant multiplying sciExtA by
    :tyep constB: float
    
    :param varExtA: variance extension of an AstroData instance being multiplied
                    or divided by extB
    :type varExtA: AstroData single extension. ex. varExtA = adA['VAR',#]
    
    :param varExtB: variance extension of an AstroData instance being multiplied
                    or divided by extB. 
    :type varExtB: AstroData single extension. ex. varExtB = adA['VAR',#]
    
    :param mult: was a multiplication performed between A and B?
    :type mult: Python boolean (True/False)
    
    :param div: was a division performed between A and B?
    :type div: Python boolean (True/False)
    
    :param add: was an addition performed between A and B?
    :type add: Python boolean (True/False)
    
    :param sub: was a subtraction performed between A and B?
    :type sub: Python boolean (True/False)
    """
    try:
        # checking if it more than one math operation is set True
        yup = False
        ops = [mult,div,sub,add]
        for op in ops:
            if op:
                if yup:
                    raise ArithError('only ONE math operation can be True')
                else:
                    yup = True
        if (sciExtB is not None) and (constB is not None):
            raise ArithError('sciExtB and constB cannot both be defined')
        
        ## Perform all checks and math needed for mult and div cases
        if mult or div:
            # Checking all the inputs are AstroData's then grabbing their 
            # data arrays
            if sciExtA is not None:
                if isinstance(sciExtA, astrodata.AstroData) or \
                            isinstance(sciExtA, astrodata.AstroData.AstroData):
                    sciA = sciExtA.data
                    if isinstance(varExtA, astrodata.AstroData) or \
                            isinstance(varExtA, astrodata.AstroData.AstroData):
                        varA = varExtA.data
                    else:
                        raise ArithError('varExtA must be an AstroData '+
                                         'instances')
            if sciExtB is not None:
                if isinstance(sciExtB, astrodata.AstroData) or \
                            isinstance(sciExtB, astrodata.AstroData.AstroData):
                    sciB = sciExtB.data
                    if isinstance(varExtB, astrodata.AstroData) or \
                            isinstance(varExtB, astrodata.AstroData.AstroData):
                        varB = varExtB.data
                    else:
                        raise ArithError('varExtB must be an AstroData '+
                                         'instances')
            elif isinstance(constB,float):
                pass
            else:
                raise ArithError('Either sciExtB must be an AstroData '+
                                 'instances OR constB is a float, neither '+
                                 'case satisfied.')
            # calculate the output variance array if mult or div
            if constB is None:
                # Science was multiplied/divided by an array so follow:
                # varOut=sciOut^2 * ( varA/(sciA^2) + varB/(sciB^2) )
                
                sciOutSquared = np.multiply(sciOut, sciOut)
                sciAsquared = np.multiply(sciA, sciA)
                sciBsquared = np.multiply(sciB, sciB)
                # Now varA/sciAsquared and varB/sciBsquared
                varAoverSciASquared = np.divide(varA, sciAsquared)
                varBoverSciBSquared = np.divide(varB, sciBsquared)
                # Now varAoverSciASquared + varBoverSciBSquared
                varOverAplusB = np.add(varAoverSciASquared, varBoverSciBSquared) 
                # Put it all together 
                # varOut=sciOut^2 * ( varA/(sciA^2) + varB/(sciB^2) )
                varOut = np.multiply(sciOutSquared,varOverAplusB)
            else:
                # Science was multiplied/divided by constant so follow:
                # varOut = varA * constB^2
                varOut = np.multiply(varA,constB*constB)
                
        ## Perform all checks and math needed for add and sub cases        
        elif add or sub:
            if varExtA is not None:
                if isinstance(varExtA, astrodata.AstroData) or \
                            isinstance(varExtA, astrodata.AstroData.AstroData):
                            varA = varExtA.data
            else:
                raise ArithError('varExtA must be not be None')
            if varExtB is not None:
                if isinstance(varExtB, astrodata.AstroData) or \
                            isinstance(varExtB, astrodata.AstroData.AstroData):
                            varB = varExtB.data
                else:
                    raise ArithError('varExtB must be an AstroData instances')
                # calculate the output variance array varOut=varA+varB
                varOut = np.add(varA, varB)
            else:
                # No second variance array defined so just pass the first 
                # through to the output
                varOut = varA

        # return final variance data array
        return varOut
    except:
        
        raise 
