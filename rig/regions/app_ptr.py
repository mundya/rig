'Generate app_ptr tables for data stored in SDRAM.\n'
import struct
def create_app_ptr_table(regions,vertex_slice=slice(0,1),magic_num=2903706326,version=65536,timer_period=1000):
 'Create a bytestring representing the application pointer table\n    indicating the location of regions in SDRAM.\n\n    Parameters\n    ----------\n    regions : dict\n        A mapping on integers to `rig.regions.Region` instances that are to be\n        stored in memory.  The integer is the "number" of the region.\n    vertex_slice : :py:func:`slice`\n        The slice that should be applied to each region.  In the case of\n        unsliced regions this may be left with its default value.\n    magic_num : int\n    version : int\n    timer_period : int\n\n    Returns\n    -------\n    bytestring\n        A string of bytes which should be written into memory immediately\n        before any region data.\n    ';header=[magic_num,version,timer_period];max_index=0;table=[]
 if len(regions)>0:max_index=max(sorted(regions.keys()))+1;table=[0]*max_index;offset=(max_index+len(header))*4
 for index in sorted(regions.keys()):table[index]=offset;offset+=regions[index].sizeof(vertex_slice);offset+=4-(offset&3)&3
 return struct.pack('<'+'I'*(max_index+len(header)),*header+table)
