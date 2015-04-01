'Read struct files for SARK/SC&MP.\n'
import collections
import re
import six
import struct
def read_struct_file(struct_data):
 'Interpret a struct file defining the location of variables in memory.\n\n    Parameters\n    ----------\n    struct_data : :py:class:`bytes`\n        String of :py:class:`bytes` containing data to interpret as the struct\n        definition.\n\n    Returns\n    -------\n    {struct_name: :py:class:`~.Struct`}\n        A dictionary mapping the struct name to a :py:class:`~.Struct`\n        instance. **Note:** the struct name will be a string of bytes, e.g.,\n        `b"vcpu"`.\n    ';structs=dict();name=None
 for i,l in enumerate(struct_data.splitlines()):
  tokens=re_comment.sub(b'',l).strip().split()
  if len(tokens)==0:continue
  elif len(tokens)==3:
   key,_,value=tokens
   if key==b'name':
    if name is not None:
     if structs[name].size is None:raise ValueError("size value missing for struct '{}'".format(name))
     if structs[name].base is None:raise ValueError("base value missing for struct '{}'".format(name))
    name=value;structs[name]=Struct(name)
   elif key==b'size':structs[name].size=num(value)
   elif key==b'base':structs[name].base=num(value)
   else:raise ValueError(key)
  elif len(tokens)==5:
   field,pack,offset,printf,default=tokens;num_pack=re_numbered_pack.match(pack)
   if num_pack is not None:pack=num_pack.group('num')+perl_to_python_packs[num_pack.group('char')]
   else:pack=perl_to_python_packs[pack]
   length=1;field_exp=re_array_field.match(field)
   if field_exp is not None:field=field_exp.group('field');length=num(field_exp.group('length'))
   structs[name][field]=StructField(pack,num(offset),printf,num(default),length)
  else:raise ValueError('line {}: Invalid syntax in struct file'.format(i))
 if structs[name].size is None:raise ValueError("size value missing for struct '{}'".format(name))
 if structs[name].base is None:raise ValueError("base value missing for struct '{}'".format(name))
 return structs
def read_conf_file(conf_data):
 'Interpret a configuration file that provides default values for elements\n    in structs.\n\n    Parameters\n    ----------\n    conf_data : :py:class:`bytes`\n        A bytestring of the conf-file to read.  This conf file is NOT expected\n        to include comments, the structure should be pairs of field and value.\n\n    Returns\n    -------\n    {field_name: default_value}\n        Dictionary mapping field name to default value.\n    ';fields={}
 for i,l in enumerate(conf_data.splitlines()):
  l=l.strip()
  if len(l)==0:continue
  try:field,value=l.split();fields[field]=num(value)
  except:raise ValueError('line {}: syntax error in config file'.format(i))
 return fields
re_comment=re.compile(b'#.*$')
re_array_field=re.compile(b'(?P<field>\\w+)\\[(?P<length>\\d+)\\]')
re_numbered_pack=re.compile(b'(?P<char>\\w)(?P<num>\\d+)')
re_hex_num=re.compile(b'0(x|X)[0-9a-fA-F]+')
def num(value):
 'Convert a value from one of several bases to an int.'
 if re_hex_num.match(value):return int(value,base=16)
 else:return int(value)
class Struct(object):
 'Represents an instance of a struct.\n\n    Elements in the struct are accessible by name, e.g., `struct[b"link_up"]`\n    and are of type :py:class:`StructField`.\n\n    Attributes\n    ----------\n    name : str\n        Name of the struct.\n    size : int\n        Total size of the struct in bytes.\n    base : int\n        Base address of struct in memory.\n    fields : {field_name: :py:class:`~.StructField`}\n        Fields of the struct.\n    '
 def __init__(self,name,size=None,base=None):self.name=name;self.size=size;self.base=base;self.fields=dict()
 def update_default_values(self,**updates):
  "Replace the default values of specified fields.\n\n        Parameters\n        ----------\n        Parameters are taken as keyword-arguments of `field=new_value`.\n\n        Raises\n        ------\n        KeyError\n            If a field doesn't exist in the struct.\n        "
  for field,value in six.iteritems(updates):fname=six.b(field);self[fname]=self[fname]._replace(default=value)
 def __setitem__(self,name,field):'Set a field in the struct.';self.fields[name]=field
 def __getitem__(self,name):'Get a field in the struct.';return self.fields[name]
 __contains__=lambda self,name:name in self.fields
 def pack(self):
  'Pack the struct (and its default values) into a string of bytes.\n\n        Returns\n        -------\n        :py:class:`bytes`\n            Byte-string representation of struct containing default values.\n        ';data=bytearray(b'\x00'*self.size)
  for field in six.itervalues(self.fields):packed_data=struct.pack(b'<'+field.pack_chars,field.default);data[field.offset:len(packed_data)+field.offset]=packed_data
  return bytes(data)
StructField=collections.namedtuple('StructField','pack_chars offset printf default length')
perl_to_python_packs={b'A':b's',b'c':b'b',b'C':b'B',b'v':b'H',b'V':b'I'}
