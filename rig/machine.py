'Identifiers for resources available in a SpiNNaker machine.\n'
from six import iteritems
from enum import IntEnum
from rig.utils.enum_doc import int_enum_doc
import sentinel
Cores=sentinel.create('Cores')
'Resource identifier for (monitor and application) processor cores.\n\nNote that this identifier does not trigger any kind of special-case behaviour\nin library functions. Users are free to define their own alternatives.\n'
SDRAM=sentinel.create('SDRAM')
'Resource identifier for shared off-die SDRAM (in bytes).\n\nNote that this identifier does not trigger any kind of special-case behaviour\nin library functions. Users are free to define their own alternatives.\n'
SRAM=sentinel.create('SRAM')
'Resource identifier for shared on-die SRAM (in bytes).\n\nNote that this identifier does not trigger any kind of special-case behaviour\nin library functions. Users are free to define their own alternatives.\n'
@int_enum_doc
class Links(IntEnum):
 'Enumeration of links from a SpiNNaker chip.\n\n    Note that the numbers chosen have two useful properties:\n\n    * The integer values assigned are chosen to match the numbers used to\n      identify the links in the low-level software API and hardware registers.\n    * The links are ordered consecutively in anticlockwise order meaning the\n      opposite link is `(link+3)%6`.\n    ';east=0;north_east=1;north=2;west=3;south_west=4;south=5
 @classmethod
 def from_vector(cls,vector):
  "Given a vector from one node to a neighbour, get the link direction.\n\n        Note that any vector whose magnitude in any given dimension is greater\n        than 1 will be assumed to use a machine's wrap-around links.\n\n        Note that this method assumes a system larger than 2x2. If a 2x2, 2xN\n        or Nx2 (for N > 2) system is provided the link selected will\n        arbitrarily favour either wrap-around or non-wrap-around links. This\n        function is not meaningful for 1x1 systems.\n\n        Parameters\n        ----------\n        vector : (x, y)\n            The vector from one node to its logical neighbour.\n\n        Returns\n        -------\n        :py:class:`~rig.machine.Links`\n            The link direction to travel in the direction indicated by the\n            vector.\n        ";x,y=vector
  if abs(x)>1:x=-1 if x>0 else 1
  if abs(y)>1:y=-1 if y>0 else 1
  return _link_direction_lookup[(x,y)]
 def to_vector(self):'Given a link direction, return the equivalent vector.';return _direction_link_lookup[self]
_link_direction_lookup={(+1,+0):Links.east,(-1,+0):Links.west,(+0,+1):Links.north,(+0,-1):Links.south,(+1,+1):Links.north_east,(-1,-1):Links.south_west}
_direction_link_lookup={l:v for (v,l) in iteritems(_link_direction_lookup)}
class Machine(object):
 "Defines the resources available in a SpiNNaker machine.\n\n    This datastructure makes the assumption that in most systems almost\n    everything is uniform and working.\n\n    This data-structure intends to be completely transparent. Its contents are\n    described below. A number of utility methods are available but should be\n    considered just that: utilities.\n\n    Attributes\n    ----------\n    width : int\n        The width of the system in chips: chips will thus have x-coordinates\n        between 0 and width-1 inclusive.\n    height : int\n        The height of the system in chips: chips will thus have y-coordinates\n        between 0 and height-1 inclusive.\n    chip_resources : {resource_key: requirement, ...}\n        The resources available on chips (unless otherwise stated in\n        `chip_resource_exceptions). `resource_key` must be some unique\n        identifying object for a given resource. `requirement` must be a\n        positive numerical value. For example: `{Cores: 17, SDRAM:\n        128*1024*1024}` would indicate 17 cores and 128 MBytes of SDRAM.\n    chip_resource_exceptions : {(x,y): resources, ...}\n        If any chip's resources differ from those specified in\n        `chip_resources`, an entry in this dictionary with the key being the\n        chip's coordinates as a tuple `(x, y)` and `resources` being a\n        dictionary of the same format as `chip_resources`. Note that every\n        exception must specify exactly the same set of keys as\n        `chip_resources`.\n    dead_chips : set\n        A set of `(x,y)` tuples enumerating all chips which completely\n        unavailable. Links leaving a dead chip are implicitly marked as dead.\n    dead_links : set\n        A set `(x,y,link)` where `x` and `y` are a chip's coordinates and\n        `link` is a value from the Enum :py:class:`~rig.machine.Links`. Note\n        that links have two directions and both should be defined if a link is\n        dead in both directions (the typical case).\n    ";__slots__=['width','height','chip_resources','chip_resource_exceptions','dead_chips','dead_links']
 def __init__(self,width,height,chip_resources={Cores:18,SDRAM:128*1024*1024,SRAM:32*1024},chip_resource_exceptions={},dead_chips=set(),dead_links=set()):'Defines the resources available within a SpiNNaker system.\n\n        Parameters\n        ----------\n        width : int\n        height : int\n        chip_resources : {resource_key: requirement, ...}\n        chip_resource_exceptions : {(x,y): resources, ...}\n        dead_chips : set([(x,y,p), ...])\n        dead_links : set([(x,y,link), ...])\n        ';self.width=width;self.height=height;self.chip_resources=chip_resources.copy();self.chip_resource_exceptions=chip_resource_exceptions.copy();self.dead_chips=dead_chips.copy();self.dead_links=dead_links.copy()
 def copy(self):'Produce a copy of this datastructure.';return Machine(self.width,self.height,self.chip_resources,self.chip_resource_exceptions,self.dead_chips,self.dead_links)
 def __contains__(self,chip_or_link):
  'Test if a given chip or link is present and alive.\n\n        Parameter\n        ---------\n        chip_or_link : tuple\n            If of the form `(x, y, link)`, checks a link. If of the form `(x,\n            y)`, checks a core.\n        '
  if len(chip_or_link)==2:x,y=chip_or_link;return 0<=x<self.width and 0<=y<self.height and (x,y) not in self.dead_chips
  elif len(chip_or_link)==3:x,y,link=chip_or_link;return (x,y) in self and (x,y,link) not in self.dead_links
  else:raise ValueError('Expect either (x, y) or (x, y, link).')
 def __getitem__(self,xy):
  'Get the resources available to a given chip.\n\n        Raises\n        ------\n        IndexError\n            If the given chip is dead or not within the bounds of the system.\n        '
  if xy not in self:raise IndexError('{} is not part of the machine.'.format(repr(xy)))
  return self.chip_resource_exceptions.get(xy,self.chip_resources)
 def __setitem__(self,xy,resources):
  'Specify the resources available to a given chip.\n\n        Raises\n        ------\n        IndexError\n            If the given chip is dead or not within the bounds of the system.\n        '
  if xy not in self:raise IndexError('{} is not part of the machine.'.format(repr(xy)))
  self.chip_resource_exceptions[xy]=resources
 def has_wrap_around_links(self,minimum_working=.9):
  'Test if a machine has wrap-around connections installed.\n\n        Since the Machine object does not explicitly define whether a machine\n        has wrap-around links they must be tested for directly. This test\n        performs a "fuzzy" test on the number of wrap-around links which are\n        working to determine if wrap-around links are really present.\n\n        Parameters\n        ----------\n        minimum_working : 0.0 <= float <= 1.0\n            The minimum proportion of all wrap-around links which must be\n            working for this function to return True.\n\n        Returns\n        -------\n        bool\n            True if the system has wrap-around links, False if not.\n        ';working=0
  for x in range(self.width):
   if (x,0,Links.south) in self:working+=1
   if (x,self.height-1,Links.north) in self:working+=1
   if (x,0,Links.south_west) in self:working+=1
   if (x,self.height-1,Links.north_east) in self:working+=1
  for y in range(self.height):
   if (0,y,Links.west) in self:working+=1
   if (self.width-1,y,Links.east) in self:working+=1
   if y!=0 and (0,y,Links.south_west) in self:working+=1
   if y!=self.height-1 and (self.width-1,y,Links.north_east) in self:working+=1
  total=4*self.width+4*self.height-2;return float(working)/float(total)>=minimum_working
