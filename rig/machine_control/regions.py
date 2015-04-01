'SpiNNaker machine regions.\n\n.. todo::\n    Neaten this documentation!\n\nRegions (not to be confused with rig Regions) are used to specify areas of a\nSpiNNaker machine for the purposes of transmitting nearest neighbour packets or\nfor determining which chips should be included in any flood-fill of data or\napplication loading.\n\nA complete introduction and specification of the region system is given in\n"Managing Big SpiNNaker Machines" By Steve Temple.\n\nA 32-bit value representing a region uses the top 16 bits (31:16) to represent\nthe x- and y-coordinates of the region and the level and the lower 16 bits\n(15:0) to represent which of the 16 blocks contained within the chunk should be\nselected.\n\nA complete introduction and specification of the region system is given in\n"Managing Big SpiNNaker Machines" By Steve Temple.\n'
import collections
from six import iteritems
def get_region_for_chip(x,y,level=3):'Get the region word for the given chip co-ordinates.\n\n    Parameters\n    ----------\n    x : int\n        x co-ordinate\n    y : int\n        y co-ordinate\n    level : int\n        Level of region to build. 0 is the most coarse and 3 is the finest.\n        When 3 is used the specified region will ONLY select the given chip,\n        for other regions surrounding chips will also be selected.\n\n    Returns\n    -------\n    int\n        A 32-bit value representing the co-ordinates of the chunk of SpiNNaker\n        chips that should be selected and the blocks within this chunk that are\n        selected.  As long as bits (31:16) are the same these values may be\n        OR-ed together to increase the number of sub-blocks selected.\n    ';shift=6-2*level;bit=(x>>shift&3)+4*(y>>shift&3);mask=65535^(4<<shift)-1;nx=x&mask;ny=y&mask;region=nx<<24|ny<<16|level<<16|1<<bit;return region
def minimise_regions(chips):
 'Create a reduced set of regions by minimising a hierarchy tree.\n\n    Parameters\n    ----------\n    chips : iterable\n        An iterable returning x and y co-ordinate pairs.\n\n    Returns\n    -------\n    generator\n        A generator which yields 32-bit region codes which minimally cover the\n        set of given chips.\n    ';t=RegionTree()
 for x,y in chips:t.add_coordinate(x,y)
 return t.get_regions()
def compress_flood_fill_regions(targets):
 'Generate a reduced set of flood fill parameters.\n\n    Parameters\n    ----------\n    targets : {(x, y) : set([c, ...]), ...}\n        For each used chip a set of core numbers onto which an application\n        should be loaded.  E.g., the output of\n        :py:func:`~rig.place_and_route.util.build_application_map` when indexed\n        by an application.\n\n    Returns\n    -------\n    generator\n        A generator which yields region and core mask pairs indicating\n        parameters to use to flood-fill an application.  `region` and\n        `core_mask` are both integer representations of bit fields that are\n        understood by SCAMP.\n    ';cores_to_targets=collections.defaultdict(set)
 for (x,y),cores in iteritems(targets):
  core_mask=0
  for c in cores:core_mask|=1<<c
  cores_to_targets[core_mask].add((x,y))
 for core_mask,coordinates in iteritems(cores_to_targets):
  regions=minimise_regions(coordinates)
  for r in regions:yield r,core_mask
class RegionTree(object):
 "A tree structure for use in minimising sets of regions.\n\n    A tree is defined which reflects the definition of SpiNNaker regions like\n    so: The tree's root node represents a 256x256 grid of SpiNNaker chips. This\n    grid is broken up into 64x64 grids which are represented by the (level 1)\n    child nodes of the root.  Each of these level 1 nodes' 64x64 grids are\n    broken up into 16x16 grids which are represented by their (level 2)\n    children. These level 2 nodes have their 16x16 grids broken up into 4x4\n    grids represented by their (level 3) children. Level 3 children explicitly\n    list which of their sixteen cores are part of the region.\n\n    If any of a level 2 node's level 3 children have all of their cores\n    selected, these level 3 nodes can be removed and replaced by a level 2\n    region with the corresponding 4x4 grid selected. If multiple children can\n    be replaced with level 2 regions, these can be combined into a single level\n    2 region with the corresponding 4x4 grids selected, resulting in a\n    reduction in the number of regions required. The same process can be\n    repeated at each level of the hierarchy eventually producing a minimal set\n    of regions.\n\n    This data structure is specified by supplying a sequence of (x, y)\n    coordinates of chips to be represented by a series of regions using\n    :py:meth:`.add_coordinate`. This method minimises the tree during insertion\n    meaning a minimal set of regions can be extracted by\n    :py:meth:`.get_regions` which simply traverses the tree.\n    "
 def __init__(self,base_x=0,base_y=0,level=0):
  self.base_x=base_x;self.base_y=base_y;self.scale=4**(4-level);self.shift=6-2*level;self.level=level;self.locally_selected=set()
  if level<3:self.subregions=[None]*16
 def get_regions(self):
  'Generate a set of integer region representations.\n\n        Returns\n        -------\n        generator\n            Generator which yields 32-bit region codes as might be generated by\n            :py:func:`.get_region_for_chip`.\n        ';region_code=self.base_x<<24|self.base_y<<16|self.level<<16
  if self.locally_selected!=set():
   elements=0
   for e in self.locally_selected:elements|=1<<e
   yield region_code|elements
  if self.level<3:
   for i,sr in enumerate(self.subregions):
    if i not in self.locally_selected and sr is not None:
     for r in sr.get_regions():yield r
 def add_coordinate(self,x,y):
  'Add a new coordinate to the region tree.\n\n        Raises\n        ------\n        ValueError\n            If the co-ordinate is not contained within the region.\n\n        Returns\n        -------\n        bool\n            If all contained subregions are full.\n        '
  if x<self.base_x or x>=self.base_x+self.scale or (y<self.base_y or y>=self.base_y+self.scale):raise ValueError((x,y))
  subregion=(x>>self.shift&3)+4*(y>>self.shift&3)
  if self.level==3:self.locally_selected.add(subregion)
  else:
   if self.subregions[subregion] is None:base_x=int(self.base_x+self.scale/4*(subregion%4));base_y=int(self.base_y+self.scale/4*(subregion//4));self.subregions[subregion]=RegionTree(base_x,base_y,self.level+1)
   if self.subregions[subregion].add_coordinate(x,y):self.locally_selected.add(subregion)
  return self.locally_selected=={i for i in range(16)}
