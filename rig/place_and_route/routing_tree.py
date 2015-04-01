'An explicit representation of a routing tree in a machine.\n\nThis representation of a route explicitly describes a tree-structure and the\ncomplete path taken by a route. This is used during place and route in\npreference to a set of RoutingTableEntry tuples since it is more easily\nverified and more accurately represents the problem at hand.\n'
class RoutingTree(object):
 'Explicitly defines a multicast route through a SpiNNaker machine.\n\n    Each instance represents a single hop in a route and recursively refers to\n    following steps.\n\n    Attributes\n    ----------\n    chip : (x, y)\n        The chip the route is currently passing through.\n    children : set\n        A :py:class:`set` of the next steps in the route. This may be one of:\n\n        * :py:class:`~.rig.place_and_route.routing_tree.RoutingTree`\n          representing a step onto the next chip\n        * :py:class:`~.rig.routing_table.Routes` representing a core or link to\n          terminate on.\n    ';__slots__=['chip','children']
 def __init__(self,chip,children=None):self.chip=chip;self.children=children if children is not None else set()
 def __iter__(self):
  'Iterate over this node and all its children, recursively and in no\n        specific order.\n        ';yield self
  for child in self.children:
   if isinstance(child,RoutingTree):
    for subchild in child:yield subchild
   else:yield child
 __repr__=lambda self:'<RoutingTree at {} with {} {}>'.format(self.chip,len(self.children),'child' if len(self.children)==1 else 'children')
