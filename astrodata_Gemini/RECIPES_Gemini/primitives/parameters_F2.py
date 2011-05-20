# This parameter file contains the parameters related to the primitives located
# in the primitives_F2.py file, in alphabetical order.
{"addBPM":{
    "suffix":{
        # String to be post pended to the output of addBPM
        "default"       : "_bpmAdded",
        "recipeOverride": True,
        "type"          : "str",
        "userOverride"  : False,
        },
    },
 "standardizeHeaders":{
    "suffix":{
        # String to be post pended to the output of standardizeHeaders
        "default"       : "_sdzHdrs",
        "recipeOverride": True,
        "type"          : "str",
        "userOverride"  : False,
        },
    },
 "standardizeStructure":{
    "suffix":{
        # String to be post pended to the output of standardizeStructure
        "default"       : "_sdzStruct",
        "recipeOverride": True,
        "type"          : "str",
        "userOverride"  : False,
        },
    "add_mdf":{
        "default"       : True,
        "recipeOverride": True,
        "type"          : "bool",
        "userOverride"  : True,
        },
    },
 "validateData":{
    "suffix":{
        # String to be post pended to the output of validateData
        "default"       : "_validated",
        "recipeOverride": True,
        "type"          : "str",
        "userOverride"  : False,
        },
    "repair":{
        "default"       : True,
        "recipeOverride": True,
        "type"          : "bool",
        "userOverride"  : True,
        },
    },
}
