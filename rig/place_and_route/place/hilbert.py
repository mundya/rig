'A minimal and dumb placement algorithm.\n'
from six import next
from math import log,ceil
from collections import deque
from ..exceptions import InsufficientResourceError,InvalidConstraintError
from ..constraints import LocationConstraint,ReserveResourceConstraint
from .util import subtract_resources,overallocated,resources_after_reservation
def hilbert(level,angle=1,s=None):
 "Generator of points along a 2D Hilbert curve.\n\n    This implements the L-system as described on\n    `http://en.wikipedia.org/wiki/Hilbert_curve`.\n\n    Parameters\n    ----------\n    level : int\n        Number of levels of recursion to use in generating the curve. The\n        resulting curve will be `(2**level)-1` wide/tall.\n    angle : int\n        **For internal use only.** `1` if this is the 'positive' expansion of\n        the grammar and `-1` for the 'negative' expansion.\n    s : HilbertState\n        **For internal use only.** The current state of the system.\n    "
 class HilbertState(object):
  def __init__(self,x=0,y=0,dx=1,dy=0):self.x,self.y,self.dx,self.dy=x,y,dx,dy
 if s is None:s=HilbertState();yield s.x,s.y
 if level<=0:return
 s.dx,s.dy=s.dy*-angle,s.dx*angle
 for s.x,s.y in hilbert(level-1,-angle,s):yield s.x,s.y
 s.x,s.y=s.x+s.dx,s.y+s.dy;yield s.x,s.y;s.dx,s.dy=s.dy*angle,s.dx*-angle
 for s.x,s.y in hilbert(level-1,angle,s):yield s.x,s.y
 s.x,s.y=s.x+s.dx,s.y+s.dy;yield s.x,s.y
 for s.x,s.y in hilbert(level-1,angle,s):yield s.x,s.y
 s.dx,s.dy=s.dy*angle,s.dx*-angle;s.x,s.y=s.x+s.dx,s.y+s.dy;yield s.x,s.y
 for s.x,s.y in hilbert(level-1,-angle,s):yield s.x,s.y
 s.dx,s.dy=s.dy*-angle,s.dx*angle
def place(vertices_resources,nets,machine,constraints):
 'Places vertices greedily and dumbly along a Hilbert-curve through the\n    machine.\n    ';placements={};unplaced_vertices=set(vertices_resources);machine=machine.copy()
 for constraint in constraints:
  if isinstance(constraint,LocationConstraint):
   loc=constraint.location
   if loc not in machine:raise InvalidConstraintError('Chip requested by {} unavailable'.format(constraint))
   vertex_resources=vertices_resources[constraint.vertex];machine[loc]=subtract_resources(machine[loc],vertex_resources)
   if overallocated(machine[loc]):raise InsufficientResourceError('Cannot meet {}'.format(constraint))
   unplaced_vertices.remove(constraint.vertex);placements[constraint.vertex]=loc
  elif isinstance(constraint,ReserveResourceConstraint):
   if constraint.location is None:
    machine.chip_resources=resources_after_reservation(machine.chip_resources,constraint)
    for location in machine.chip_resource_exceptions:machine.chip_resource_exceptions[location]=resources_after_reservation(machine.chip_resource_exceptions[location],constraint)
   else:machine[constraint.location]=resources_after_reservation(machine[constraint.location],constraint)
 max_dimen=max(machine.width,machine.height);hilbert_levels=int(ceil(log(max_dimen,2.))) if max_dimen>=1 else 0;hilbert_iter=hilbert(hilbert_levels);cur_chip=None;cur_chip_resources=None;vertex_queue=deque()
 while vertex_queue or unplaced_vertices:
  if not vertex_queue:vertex_queue.append(next(iter(unplaced_vertices)))
  vertex=vertex_queue.popleft()
  if vertex not in unplaced_vertices:continue
  resources=vertices_resources[vertex]
  while True:
   try:
    if cur_chip is None:
     cur_chip=next(hilbert_iter)
     if cur_chip not in machine:cur_chip=None;continue
     cur_chip_resources=machine[cur_chip].copy()
   except StopIteration:raise InsufficientResourceError('Ran out of chips while {} vertices remain unplaced'.format(len(unplaced_vertices)))
   cur_chip_resources=subtract_resources(cur_chip_resources,resources)
   if not overallocated(cur_chip_resources):break
   else:cur_chip=None;continue
  unplaced_vertices.remove(vertex);placements[vertex]=cur_chip
  for net in nets:
   if vertex in net:vertex_queue.append(net.source);vertex_queue.extend(net.sinks)
 return placements
