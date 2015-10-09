# Gives IQ band constraints for given filter + wavefront sensor combination
iqConstraints = {
'u':  {'20':0.60, '70':0.90, '85':1.20},
'g':  {'20':0.60, '70':0.85, '85':1.10},
'r':  {'20':0.50, '70':0.75, '85':1.05},
'i':  {'20':0.50, '70':0.75, '85':1.05},
'Z':  {'20':0.50, '70':0.70, '85':0.95},
'Y':  {'20':0.40, '70':0.70, '85':0.95},
'J':  {'20':0.40, '70':0.60, '85':0.85},
'H':  {'20':0.40, '70':0.60, '85':0.85},
'K':  {'20':0.35, '70':0.55, '85':0.80},
'L':  {'20':0.35, '70':0.50, '85':0.75},
'M':  {'20':0.35, '70':0.50, '85':0.70},
'N':  {'20':0.34, '70':0.37, '85':0.45},
'Q':  {'20':0.54, '70':0.54, '85':0.54},

'AO': {'20':0.45, '70':0.80, '85':1.20}  # from view_wfs.py (telops ~/bin)
}
