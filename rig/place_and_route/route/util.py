'Utility functions which may be of value to router implementations.\n'
import random
from ...machine import Links
def longest_dimension_first(vector,start=(0,0),width=None,height=None):
 'Generate the (x, y) steps on a longest-dimension first route.\n\n    Note that when multiple dimensions are the same magnitude, one will be\n    chosen at random with uniform probability.\n\n    Parameters\n    ----------\n    vector : (x, y, z)\n        The vector which the path should cover.\n    start : (x, y)\n        The coordinates from which the path should start (note this is a 2D\n        coordinate).\n    width : int or None\n        The width of the topology beyond which we wrap around (0 <= x < width).\n        If None, no wrapping on the X axis will occur.\n    height : int or None\n        The height of the topology beyond which we wrap around (0 <= y <\n        height).  If None, no wrapping on the Y axis will occur.\n\n    Generates\n    ---------\n    (x, y)\n        Produces (in order) an (x, y) pair for every hop along the longest\n        dimension first route. Ties are broken randomly. The first generated\n        value is that of the first hop after the starting position, the last\n        generated value is the destination position.\n    ';x,y=start
 for dimension,magnitude in sorted(enumerate(vector),key=lambda x:abs(x[1])+random.random(),reverse=True):
  if magnitude==0:break
  sign=1 if magnitude>0 else -1
  for _ in range(abs(magnitude)):
   if dimension==0:x+=sign
   elif dimension==1:y+=sign
   elif dimension==2:x-=sign;y-=sign
   if width is not None:x%=width
   if height is not None:y%=height
   yield x,y
def links_between(a,b,machine):'Get the set of working links connecting chips a and b.\n\n    Parameters\n    ----------\n    a : (x, y)\n    b : (x, y)\n    machine : :py:class:`~rig.machine.Machine`\n\n    Returns\n    -------\n    set([:py:class:`~rig.machine.Links`, ...])\n    ';ax,ay=a;bx,by=b;return set(link for (link,(dx,dy)) in [(Links.east,(1,0)),(Links.north_east,(1,1)),(Links.north,(0,1)),(Links.west,(-1,0)),(Links.south_west,(-1,-1)),(Links.south,(0,-1))] if (ax+dx)%machine.width==bx and (ay+dy)%machine.height==by and (ax,ay,link) in machine)
