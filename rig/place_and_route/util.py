'Utilities functions which assist in the generation of commonly required data\nstructures from the products of placement, allocation and routing.\n'
from collections import defaultdict,deque
from six import iteritems
from ..machine import Links,Cores
from ..routing_table import Routes,RoutingTableEntry
from .routing_tree import RoutingTree
def build_application_map(vertices_applications,placements,allocations,core_resource=Cores):
 'Build a mapping from application to a list of cores where the\n    application is used.\n\n    This utility function assumes that each vertex is associated with a\n    specific application.\n\n    Parameters\n    ----------\n    vertices_applications : {vertex: application, ...}\n        Applications are represented by the path of their APLX file.\n    placements : {vertex: (x, y), ...}\n    allocations : {vertex: {resource: slice, ...}, ...}\n        One of these resources should match the `core_resource` argument.\n    core_resource : object\n        The resource identifier which represents cores.\n\n    Returns\n    -------\n    {application: {(x, y) : set([c, ...]), ...}, ...}\n        For each application, for each used chip a set of core numbers onto\n        which the application should be loaded.\n    ';application_map=defaultdict(lambda:defaultdict(set))
 for vertex,application in iteritems(vertices_applications):chip_cores=application_map[application][placements[vertex]];core_slice=allocations[vertex].get(core_resource,slice(0,0));chip_cores.update(range(core_slice.start,core_slice.stop))
 return application_map
def build_routing_tables(routes,net_keys,omit_default_routes=True):
 'Convert a set of RoutingTrees into a per-chip set of routing tables.\n\n    This command produces routing tables with entries optionally omitted when\n    the route does not change direction.\n\n    Note: The routing trees provided are assumed to be correct and continuous\n    (not missing any hops). If this is not the case, the output is undefined.\n\n    Parameters\n    ----------\n    routes : {net: :py:class:`~rig.place_and_route.routing_tree.RoutingTree`,               ...}\n        The complete set of RoutingTrees representing all routes in the system.\n        (Note: this is the same datastructure produced by routers in the `par`\n        module.)\n    net_keys : {net: (key, mask), ...}\n        The key and mask associated with each net.\n    omit_default_routes : bool\n        Do not create routing entries for routes which do not change direction\n        (i.e. use default routing).\n\n    Returns\n    -------\n    {(x, y): [:py:class:`~rig.routing_table.RoutingTableEntry`, ...]\n    ';routing_tables=defaultdict(list)
 for net,routing_tree in iteritems(routes):
  key,mask=net_keys[net];to_visit=deque([(routing_tree,None)])
  while to_visit:
   node,direction=to_visit.popleft();x,y=node.chip;out_directions=set()
   for child in node.children:
    if isinstance(child,RoutingTree):cx,cy=child.chip;dx,dy=cx-x,cy-y;child_direction=Routes(Links.from_vector((dx,dy)));to_visit.append((child,child_direction));out_directions.add(child_direction)
    else:out_directions.add(child)
   if not omit_default_routes or set([direction])!=out_directions:routing_tables[(x,y)].append(RoutingTableEntry(out_directions,key,mask))
 return routing_tables
