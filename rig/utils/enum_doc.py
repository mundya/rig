'Docstring sanitisers for Sphinx'
def int_enum_doc(enum):
 "Decorator which re-writes documentation strings for an IntEnum so that\n    Sphinx presents it correctly.\n\n    This is a work-around for Sphinx autodoc's inability to properly document\n    IntEnums.\n    ";enum.__doc__+='\n\nAttributes\n==========\n'
 for val in list(enum):enum.__doc__+='{} = {}\n'.format(val.name,int(val))
 return enum
