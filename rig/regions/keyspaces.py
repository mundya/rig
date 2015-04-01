from six import iteritems
import struct
from .region import Region
class KeyspacesRegion(Region):
 'A region of memory which represents data formed from a list of\n    :py:class:`~rig.bitfield.BitField` instances representing SpiNNaker routing\n    keys.\n\n    Each "row" represents a keyspace, and each "column" is formed by getting\n    the result of a function applied to the keyspace.  Each field will be one\n    word long, and all keyspaces are expected to be 32-bit long.\n    '
 def __init__(self,keyspaces,fields=list(),partitioned_by_atom=False,prepend_num_keyspaces=False):
  'Create a new region representing keyspace information.\n\n        Parameters\n        ----------\n        keyspaces : iterable\n            An iterable containing instances of\n            :py:class:`~rig.bitfield.BitField`\n        fields : iterable\n            An iterable of callables which will be called on each key and must\n            return an appropriate sized bytestring representing the data to\n            write to memory.  The appropriate size is the number of bytes\n            required to represent a full key or mark (e.g., 4 bytes for 32 bit\n            keyspaces).\n        partitioned_by_atom : bool\n            If True then one set of fields will be written out per atom, if\n            False then fields for all keyspaces are written out regardless of\n            the vertex slice.\n        prepend_num_keyspaces : bool\n            Prepend a word containing the number of keyspaces to the region\n            data when it is written out.\n        '
  for ks in keyspaces:assert ks.length==32
  self.keyspaces=keyspaces[:];self.fields=fields[:];self.partitioned=partitioned_by_atom;self.prepend_num_keyspaces=prepend_num_keyspaces;self.bytes_per_field=4
 def sizeof(self,vertex_slice):
  'Get the size of a slice of this region in bytes.\n\n        See :py:meth:`.region.Region.sizeof`\n        '
  if not self.partitioned:n_keys=len(self.keyspaces)
  else:assert vertex_slice.stop<len(self.keyspaces)+1;n_keys=vertex_slice.stop-vertex_slice.start
  pp_size=0 if not self.prepend_num_keyspaces else 4;return self.bytes_per_field*n_keys*len(self.fields)+pp_size
 def write_subregion_to_file(self,vertex_slice,fp,**field_args):
  'Write the data contained in a portion of this region out to file.\n        ';data=b''
  if self.partitioned:assert vertex_slice.stop<len(self.keyspaces)+1
  key_slice=vertex_slice if self.partitioned else slice(None)
  if self.prepend_num_keyspaces:nks=len(self.keyspaces[key_slice]);data+=struct.pack('<I',nks)
  for ks in self.keyspaces[key_slice]:
   for field in self.fields:data+=struct.pack('<I',field(ks,**field_args))
  fp.write(data)
def KeyField(maps={},field=None,tag=None):
 "Create new field for a :py:class:`~KeyspacesRegion` that will fill in\n    specified fields of the key and will then write out a key.\n\n    Parameters\n    ----------\n    maps : dict\n        A mapping from keyword-argument of the field to the field of the key\n        that this value should be inserted into.\n    field : string or None\n        The field to get the key or None for all fields.\n\n    For example:\n\n        ks = Keyspace()\n        ks.add_field(i)\n        # ...\n\n        kf = KeyField(maps={'subvertex_index': 'i'})\n        k = Keyspace()\n        kf(k, subvertex_index=11)\n\n    Will return the key with the 'i' key set to 11.\n    ";key_field=field
 def key_getter(keyspace,**kwargs):
  fills={}
  for kwarg,field in iteritems(maps):fills[field]=kwargs[kwarg]
  key=keyspace(**fills);return key.get_value(field=key_field,tag=tag)
 return key_getter
def MaskField(**kwargs):
 'Create a new field for a :py:class:`~.KeyspacesRegion` that will write\n    out a mask value from a keyspace.\n\n    Parameters\n    ----------\n    field : string\n        The name of the keyspace field to store the mask for.\n    tag : string\n        The name of the keyspace tag to store the mask for.\n\n    Raises\n    ------\n    TypeError\n        If both or neither field and tag are specified.\n\n    Returns\n    -------\n    function\n        A function which can be used in the `fields` argument to\n        :py:class:`~.KeyspacesRegion` that will include a specified mask in the\n        region data.\n    ';field=kwargs.get('field');tag=kwargs.get('tag')
 if field is not None and tag is None:
  def mask_getter(keyspace,**kwargs):return keyspace.get_mask(field=field)
  return mask_getter
 elif tag is not None and field is None:
  def mask_getter(keyspace,**kwargs):return keyspace.get_mask(tag=tag)
  return mask_getter
 else:raise TypeError("MaskField expects 1 argument, either 'field' or 'tag'.")
