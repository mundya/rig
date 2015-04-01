'A system for defining and representing bit fields.\n\nA common use-ase for this module is defining SpiNNaker routing keys based on\nhierarchical bit-fields.\n\nSee the :py:class:`.BitField` class.\n'
from collections import OrderedDict
from math import log
class BitField(object):
 "Defines a hierarchical bit field and the values of those fields.\n\n    Conceptually, a bit field is a sequence of bits which are logically broken\n    up into individual fields which represent independent, unsigned integer\n    values. For example, one could represent a pair of eight-bit values `x` and\n    `y` as a sixteen-bit bit field where the upper eight bits are `x` and the\n    lower eight bits are `y`. Bit fields are used when multiple pieces of\n    information must be conveyed by a single binary value.\n\n    For example, one method of allocating SpiNNaker routing keys (which are\n    32-bit values) is to define each route a key as bit field with three\n    fields. The fields `x`, `y`, and `p` can be used to represent the x- and\n    y-chip-coordinate and processor id of a route's source.\n\n    A hierarchical bit field is a bit field with fields which only exist\n    dependent on the values of other fields. For a further routing-key related\n    example, different key formats may be used by external devices and the rest\n    of the SpiNNaker application. In these cases, a single bit could be used in\n    the key to determine which key format is in use. Depending on the value of\n    this bit, different fields would become available.\n\n    This class supports the following key features:\n\n    * Construction of guaranteed-safe hierarchical bit field formats.\n    * Generation of bit-masks which select only defined fields\n    * Automatic allocation of field sizes based on values actually used.\n    * Partial-definition of a bit field (i.e. defining only a subset of\n      available fields).\n    "
 def __init__(self,length=32,_fields=None,_field_values=None):
  "Create a new BitField.\n\n        An instance, `b`, of :py:class:`.BitField` represents a fixed-length\n        hierarchical bit field with initially no fields. Fields can be added\n        using :py:meth:`.BitField.add_field`. Derivatives of this instance\n        with fields set to specific values can be created using the 'call'\n        syntax: `b(field_name=value, other_field_name=other_value)` (see\n        :py:meth:`.BitField.__call__`).\n\n        .. Note::\n            Only one :py:class:`.BitField` instance should be explicitly\n            created for each bit field.\n\n        Parameters\n        ----------\n        length : int\n            The total number of bits in the bit field.\n        _fields : dict\n            For internal use only. The shared, global field dictionary.\n        _field_values : dict\n            For internal use only. Mapping of field-identifier to value.\n        ";self.length=length;self.fields=_fields if _fields is not None else OrderedDict()
  if _field_values is not None:self.field_values=_field_values
  else:self.field_values=dict()
 def add_field(self,identifier,length=None,start_at=None,tags=None):
  "Add a new field to the BitField.\n\n        If any existing fields' values are set, the newly created field will\n        become a child of those fields. This means that this field will exist\n        only when the parent fields' values are set as they are currently.\n\n        Parameters\n        ----------\n        identifier : str\n            A identifier for the field. Must be a valid python identifier.\n            Field names must be unique and users are encouraged to sensibly\n            name-space fields in the `prefix_` style to avoid collisions.\n        length : int or None\n            The number of bits in the field. If None the field will be\n            automatically assigned a length long enough for the largest value\n            assigned.\n        start_at : int or None\n            0-based index of least significant bit of the field within the\n            bit field. If None the field will be automatically located in free\n            space in the bit field.\n        tags : string or collection of strings or None\n            A (possibly empty) set of tags used to classify the field.  Tags\n            should be valid Python identifiers. If a string, the string must be\n            a single tag or a space-separated list of tags. If *None*, an empty\n            set of tags is assumed. These tags are applied recursively to all\n            fields of which this field is a child.\n\n        Raises\n        ------\n        ValueError\n            If any the field overlaps with another one or does not fit within\n            the bit field. Note that fields with unspecified lengths and\n            positions do not undergo such checks until their length and\n            position become known.\n        "
  if identifier in self.fields:raise ValueError("Field with identifier '{}' already exists.".format(identifier))
  if length is not None and length<=0:raise ValueError('Fields must be at least one bit in length.')
  if start_at is not None and (0<=start_at>=self.length or start_at+(length or 1)>self.length):raise ValueError("Field doesn't fit within {}-bit bit field.".format(self.length))
  if start_at is not None:
   end_at=start_at+(length or 1)
   for other_identifier,other_field in self._potential_fields():
    if other_field.start_at is not None:
     other_start_at=other_field.start_at;other_end_at=other_start_at+(other_field.length or 1)
     if end_at>other_start_at and other_end_at>start_at:raise ValueError("Field '{}' (range {}-{}) overlaps field '{}' (range {}-{})".format(identifier,start_at,end_at,other_identifier,other_start_at,other_end_at))
  if type(tags) is str:tags=set(tags.split())
  elif tags is None:tags=set()
  else:tags=set(tags)
  parent_identifiers=list(self.field_values.keys())
  while parent_identifiers:parent_identifier=parent_identifiers.pop(0);parent=self.fields[parent_identifier];parent.tags.update(tags);parent_identifiers.extend(parent.conditions.keys())
  self.fields[identifier]=BitField._Field(length,start_at,tags,dict(self.field_values))
 def __call__(self,**field_values):
  'Return a new BitField instance with fields assigned values as\n        specified in the keyword arguments.\n\n        Returns\n        -------\n        :py:class:`.BitField`\n            A `BitField` derived from this one but with the specified fields\n            assigned a value.\n\n        Raises\n        ------\n        ValueError\n            If any field has already been assigned a value or the value is too\n            large for the field.\n        AttributeError\n            If a field is specified which is not present.\n        '
  for identifier in field_values.keys():
   if identifier not in self.fields:raise ValueError("Field '{}' not defined.".format(identifier))
  for identifier,value in self.field_values.items():
   if identifier in field_values:raise ValueError("Field '{}' already has value.".format(identifier))
  field_values.update(self.field_values)
  for identifier in field_values:self._assert_field_available(identifier,field_values)
  for identifier,value in field_values.items():
   field_length=self.fields[identifier].length
   if value<0:raise ValueError('Fields must be positive.')
   elif field_length is not None and value>=1<<field_length:raise ValueError("Value {} too large for {}-bit field '{}'.".format(value,field_length,identifier))
  for identifier,value in field_values.items():self.fields[identifier].max_value=max(self.fields[identifier].max_value,value)
  return BitField(self.length,self.fields,field_values)
 def __getattr__(self,identifier):'Get the value of a field.\n\n        Returns\n        -------\n        int or None\n            The value of the field (or None if the field has not been given a\n            value).\n\n        Raises\n        ------\n        AttributeError\n            If the field requested does not exist or is not available given\n            current field values.\n        ';self._assert_field_available(identifier);return self.field_values.get(identifier,None)
 def get_value(self,tag=None,field=None):
  "Generate an integer whose bits are set according to the values of\n        fields in this bit field. All bits not in a field are set to zero.\n\n        Parameters\n        ----------\n        tag : str\n            Optionally specifies that the value should only include fields with\n            the specified tag.\n        field : str\n            Optionally specifies that the value should only include the\n            specified field.\n\n        Raises\n        ------\n        ValueError\n            If a field whose length or position has not been defined. (i.e.\n            `assign_fields()` has not been called when a field's\n            length/position has not been fixed.\n        ";assert not (tag is not None and field is not None),'Cannot filter by tag and field simultaneously.'
  if field is not None:self._assert_field_available(field);selected_field_idents=[field]
  elif tag is not None:self._assert_tag_exists(tag);selected_field_idents=[i for (i,f) in self._enabled_fields() if tag in f.tags]
  else:selected_field_idents=[i for (i,f) in self._enabled_fields()]
  missing_fields_idents=set(selected_field_idents)-set(self.field_values.keys())
  if missing_fields_idents:raise ValueError('Cannot generate value with undefined fields {}.'.format(', '.join(missing_fields_idents)))
  value=0
  for identifier in selected_field_idents:
   field=self.fields[identifier]
   if field.length is None or field.start_at is None:raise ValueError("Field '{}' does not have a fixed size/position.".format(identifier))
   value|=self.field_values[identifier]<<field.start_at
  return value
 def get_mask(self,tag=None,field=None):
  "Get the mask for all fields which exist in the current bit field.\n\n        Parameters\n        ----------\n        tag : str\n            Optionally specifies that the mask should only include fields with\n            the specified tag.\n        field : str\n            Optionally specifies that the mask should only include the\n            specified field.\n\n        Raises\n        ------\n        ValueError\n            If a field whose length or position has not been defined. (i.e.\n            `assign_fields()` has not been called when a field's size/position\n            has not been fixed.\n        ";assert not (tag is not None and field is not None)
  if field is not None:self._assert_field_available(field);selected_field_idents=[field]
  elif tag is not None:self._assert_tag_exists(tag);selected_field_idents=[i for (i,f) in self._enabled_fields() if tag in f.tags]
  else:selected_field_idents=[i for (i,f) in self._enabled_fields()]
  mask=0
  for identifier in selected_field_idents:
   field=self.fields[identifier]
   if field.length is None or field.start_at is None:raise ValueError("Field '{}' does not have a fixed size/position.".format(identifier))
   mask|=(1<<field.length)-1<<field.start_at
  return mask
 def assign_fields(self):
  'Assign a position & length to any fields which do not have one.\n\n        Users should typically call this method after all field values have\n        been assigned, otherwise fields may be fixed at an inadequate size.\n        ';unsearched_heirarchy=[BitField(self.length,self.fields)]
  while unsearched_heirarchy:
   ks=unsearched_heirarchy.pop(0);ks._assign_enabled_fields()
   for identifier,field in ks._potential_fields():
    enabled_field_idents=set(i for (i,f) in ks._enabled_fields());set_fields={}
    for cond_ident,cond_value in field.conditions.items():
     if cond_ident not in enabled_field_idents:self.set_fields={};break
     if getattr(ks,cond_ident) is None:set_fields[cond_ident]=cond_value
    if set_fields:unsearched_heirarchy.append(ks(**set_fields))
 def __eq__(self,other):'Test that this :py:class:`.BitField` is equivalent to another.\n\n        In order to be equal, the other :py:class:`.BitField` must be a\n        descendent of the same original :py:class:`.BitField` (and thus will\n        *always* have exactly the same set of fields). It must also have the\n        same field values defined.\n        ';return self.length==other.length and self.fields is other.fields and self.field_values==other.field_values
 def __repr__(self):'Produce a human-readable representation of this bit field and its\n        current value.\n        ';enabled_field_idents=[i for (i,f) in self._enabled_fields()];return '<{}-bit BitField {}>'.format(self.length,', '.join("'{}':{}".format(identifier,self.field_values.get(identifier,'?')) for identifier in enabled_field_idents))
 class _Field(object):
  'Internally used class which defines a field.\n        '
  def __init__(self,length=None,start_at=None,tags=None,conditions=None,max_value=1):'Field definition used internally by :py:class:`.BitField`.\n\n            Parameters/Attributes\n            ---------------------\n            length : int\n                The number of bits in the field. *None* if this should be\n                determined based on the values assigned to it.\n            start_at : int\n                0-based index of least significant bit of the field within the\n                bit field.  *None* if this field is to be automatically placed\n                into an unused area of the bit field.\n            tags : set\n                A (possibly empty) set of tags used to classify the field.\n            conditions : dict\n                Specifies conditions when this field is valid. If empty, this\n                field is always defined. Otherwise, keys in the dictionary\n                specify field-identifers and values specify the desired value.\n                All listed fields must match the specified values for the\n                condition to be met.\n            max_value : int\n                The largest value ever assigned to this field (used for\n                automatically determining field sizes.\n            ';self.length=length;self.start_at=start_at;self.tags=tags or set();self.conditions=conditions or dict();self.max_value=max_value
 def _assert_field_available(self,identifier,field_values=None):
  'Raise a human-readable :py:exc:`ValueError` if the specified field\n        does not exist or is not enabled by the current field values.\n\n        Parameters\n        ----------\n        identifier : str\n            The field to check for availability.\n        field_values : dict or None\n            The values currently assigned to fields.\n        '
  if field_values is None:field_values=self.field_values
  if identifier not in self.fields:raise AttributeError("Field '{}' does not exist.".format(identifier))
  elif identifier not in (i for (i,f) in self._enabled_fields(field_values)):
   unmet_conditions=[];unchecked_fields=[identifier]
   while unchecked_fields:
    field=self.fields[unchecked_fields.pop(0)]
    for cond_identifier,cond_value in field.conditions.items():
     actual_value=field_values.get(cond_identifier,None)
     if actual_value!=cond_value:unmet_conditions.append((cond_identifier,cond_value));unchecked_fields.append(cond_identifier)
   raise AttributeError("Field '{}' requires that {}.".format(identifier,', '.join("'{}' == {}".format(cond_ident,cond_val) for (cond_ident,cond_val) in unmet_conditions)))
 def _assert_tag_exists(self,tag):
  'Raise a human-readable :py:exc:`ValueError` if the supplied tag is\n        not used by any enabled field.\n        '
  for identifier,field in self._enabled_fields():
   if tag in field.tags:return
  raise ValueError("Tag '{}' does not exist.".format(tag))
 def _enabled_fields(self,field_values=None):
  'Generator of (identifier, field) tuples which iterates over the\n        fields which can be set based on the currently specified field values.\n\n        Parameters\n        ----------\n        field_values : dict or None\n            Dictionary of field identifier to value mappings to use in the\n            test. If None, uses `self.field_values`.\n        '
  if field_values is None:field_values=self.field_values
  for identifier,field in self.fields.items():
   if not field.conditions or all(field_values.get(cond_field,None)==cond_value for (cond_field,cond_value) in field.conditions.items()):yield identifier,field
 def _potential_fields(self):
  'Generator of (identifier, field) tuples iterating over every field\n        which could potentially be defined given the currently specified field\n        values.\n        ';blocked=set()
  for identifier,field in self.fields.items():
   if not field.conditions or all(cond_field not in blocked and self.field_values.get(cond_field,cond_value)==cond_value for (cond_field,cond_value) in field.conditions.items()):yield identifier,field
   else:blocked.add(identifier)
 def _assign_enabled_fields(self):
  'For internal use only. Assign a position & length to any enabled\n        fields which do not have one.\n        ';assigned_bits=0;unassigned_fields=[]
  for identifier,field in self._enabled_fields():
   if field.length is not None and field.start_at is not None:assigned_bits|=(1<<field.length)-1<<field.start_at
   else:unassigned_fields.append((identifier,field))
  for identifier,field in unassigned_fields:
   length=field.length
   if length is None:length=int(log(field.max_value,2))+1
   start_at=field.start_at
   if start_at is None:
    start_at=self.length
    for bit in range(0,self.length-length):
     field_bits=(1<<length)-1<<bit
     if not assigned_bits&field_bits:start_at=bit;assigned_bits|=field_bits;break
   if start_at+length<=self.length:field.length=length;field.start_at=start_at
   else:raise ValueError("{}-bit field '{}' does not fit in bit field.".format(field.length,identifier))
