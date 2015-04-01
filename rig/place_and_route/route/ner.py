'Neighbour Exploring Routing (NER) algorithm from J. Navaridas et al.\n\nAlgorithm refrence: J. Navaridas et al. SpiNNaker: Enhanced multicast routing,\nParallel Computing (2014).\n\n`http://dx.doi.org/10.1016/j.parco.2015.01.002`\n'
import heapq
from collections import deque
from ...geometry import concentric_hexagons,to_xyz,shortest_mesh_path_length,shortest_mesh_path,shortest_torus_path_length,shortest_torus_path
from .util import longest_dimension_first,links_between
from ..exceptions import MachineHasDisconnectedSubregion
from ..constraints import RouteEndpointConstraint
from ...machine import Links,Cores
from ...routing_table import Routes
from ..routing_tree import RoutingTree
def ner_net(source,destinations,width,height,wrap_around=False,radius=10):
 'Produce a shortest path tree for a given net using NER.\n\n    This is the kernel of the NER algorithm.\n\n    Parameters\n    ----------\n    source : (x, y)\n        The coordinate of the source vertex.\n    destinations : iterable([(x, y), ...])\n        The coordinates of destination vertices.\n    width : int\n        Width of the system (nodes)\n    height : int\n        Height of the system (nodes)\n    wrap_around : bool\n        True if wrap-around links should be used, false if they should be\n        avoided.\n    radius : int\n        Radius of area to search from each node. 20 is arbitrarily selected in\n        the paper and shown to be acceptable in practice.\n\n    Returns\n    -------\n    (:py:class:`~.rig.place_and_route.routing_tree.RoutingTree`,\n     {(x,y): :py:class:`~.rig.place_and_route.routing_tree.RoutingTree`, ...})\n        A RoutingTree is produced rooted at the source and visiting all\n        destinations but which does not contain any vertices etc. For\n        convenience, a dictionarry mapping from destination (x, y) coordinates\n        to the associated RoutingTree is provided to allow the caller to insert\n        these items.\n    ';route={source:RoutingTree(source)}
 for destination in sorted(destinations,key=lambda destination:shortest_mesh_path_length(to_xyz(source),to_xyz(destination)) if not wrap_around else shortest_torus_path_length(to_xyz(source),to_xyz(destination),width,height)):
  neighbour=None
  for x,y in concentric_hexagons(radius,destination):
   if wrap_around:x%=width;y%=height
   if (x,y) in route and (x,y)!=destination:neighbour=x,y;break
  if neighbour is None:neighbour=source
  if wrap_around:vector=shortest_torus_path(to_xyz(neighbour),to_xyz(destination),width,height)
  else:vector=shortest_mesh_path(to_xyz(neighbour),to_xyz(destination))
  last_node=route[neighbour]
  for x,y in longest_dimension_first(vector,neighbour,width,height):
   this_node=route.get((x,y),None)
   if this_node is None:this_node=RoutingTree((x,y));route[(x,y)]=this_node
   last_node.children.add(this_node);last_node=this_node
 return route[source],route
def copy_and_disconnect_tree(root,machine):
 "Copy a RoutingTree (containing nothing but RoutingTrees), disconnecting\n    nodes which are not connected in the machine.\n\n    Note that if a dead chip is part of the input RoutingTree, no corresponding\n    node will be included in the copy. The assumption behind this is that the\n    only reason a tree would visit a dead chip is because a route passed\n    through the chip and wasn't actually destined to arrive at that chip. This\n    situation is impossible to confirm since the input routing trees have not\n    yet been populated with vertices. The caller is responsible for being\n    sensible.\n\n    Parameters\n    ----------\n    root : :py:class:`~rig.place_and_route.routing_tree.RoutingTree`\n        The root of the RoutingTree that contains nothing but RoutingTrees\n        (i.e. no vertices and links).\n    machine : :py:class:`~rig.machine.Machine`\n        The machine in which the routes exist.\n\n    Returns\n    -------\n    (root, lookup, broken_links)\n        Where:\n        * `root` is the new root of the tree\n          :py:class:`~rig.place_and_route.routing_tree.RoutingTree`\n        * `lookup` is a dict {(x, y):\n          :py:class:`~rig.place_and_route.routing_tree.RoutingTree`, ...}\n        * `broken_links` is a set ([(parent, child), ...]) containing all\n          disconnected parent and child (x, y) pairs due to broken links.\n    ";new_root=None;new_lookup={};broken_links=set();to_visit=deque([(None,root)])
 while to_visit:
  new_parent,old_node=to_visit.popleft()
  if old_node.chip in machine:new_node=RoutingTree(old_node.chip);new_lookup[new_node.chip]=new_node
  else:assert new_parent is not None,'Net cannot be sourced from a dead chip.';new_node=new_parent
  if new_parent is None:new_root=new_node
  elif new_node is not new_parent:
   if links_between(new_parent.chip,new_node.chip,machine):new_parent.children.add(new_node)
   else:broken_links.add((new_parent.chip,new_node.chip))
  for child in old_node.children:to_visit.append((new_node,child))
 return new_root,new_lookup,broken_links
def a_star(sink,heuristic_source,sources,machine,wrap_around):
 "Use A* to find a path from any of the sources to the sink.\n\n    Note that the heuristic means that the search will proceed towards\n    heuristic_source without any concern for any other sources. This means that\n    the algorithm may miss a very close neighbour in order to pursue its goal\n    of reaching heuristic_source. This is not considered a problem since 1) the\n    heuristic source will typically be in the direction of the rest of the tree\n    and near by and often the closest entity 2) it prevents us accidentally\n    forming loops in the rest of the tree since we'll stop as soon as we touch\n    any part of it.\n\n    Parameters\n    ----------\n    sink : (x, y)\n    heuristic_source : (x, y)\n        An element from `sources` which is used as a guiding heuristic for the\n        A* algorithm.\n    sources : set([(x, y), ...])\n    machine : :py:class:`~rig.machine.Machine`\n    wrap_around : bool\n        Consider wrap-around links in heuristic distance calculations.\n\n    Returns\n    -------\n    [(x, y), ...]\n        A path starting with a coordinate in `sources` and terminating at\n        connected neighbour of `sink` (i.e. the path does not include `sink`).\n\n    Raises\n    ------\n    :py:class:~rig.place_and_route.exceptions.MachineHasDisconnectedSubregion`\n        If a path cannot be found.\n    "
 if wrap_around:heuristic=lambda node:shortest_torus_path_length(to_xyz(node),to_xyz(heuristic_source),machine.width,machine.height)
 else:heuristic=lambda node:shortest_mesh_path_length(to_xyz(node),to_xyz(heuristic_source))
 visited={sink:None};selected_source=None;to_visit=[(heuristic(sink),sink)]
 while to_visit:
  _,node=heapq.heappop(to_visit)
  if node in sources:selected_source=node;break
  for neighbour_link,vector in [(Links.east,(-1,0)),(Links.west,(1,0)),(Links.north,(0,-1)),(Links.south,(0,1)),(Links.north_east,(-1,-1)),(Links.south_west,(1,1))]:
   neighbour=(node[0]+vector[0])%machine.width,(node[1]+vector[1])%machine.height
   if (neighbour[0],neighbour[1],neighbour_link) not in machine:continue
   if neighbour in visited:continue
   visited[neighbour]=node;heapq.heappush(to_visit,(heuristic(neighbour),neighbour))
 if selected_source is None:raise MachineHasDisconnectedSubregion('Could not find path from {} to {}'.format(sink,heuristic_source))
 path=[selected_source]
 while visited[path[-1]]!=sink:path.append(visited[path[-1]])
 return path
def avoid_dead_links(root,machine,wrap_around=False):
 'Modify a RoutingTree to route-around dead links in a Machine.\n\n    Uses A* to reconnect disconnected branches of the tree (due to dead links\n    in the machine).\n\n    Parameters\n    ----------\n    root : :py:class:`~rig.place_and_route.routing_tree.RoutingTree`\n        The root of the RoutingTree which contains nothing but RoutingTrees\n        (i.e. no vertices and links).\n    machine : :py:class:`~rig.machine.Machine`\n        The machine in which the routes exist.\n    wrap_around : bool\n        Consider wrap-around links in pathfinding heuristics.\n\n    Returns\n    -------\n    (:py:class:`~.rig.place_and_route.routing_tree.RoutingTree`,\n     {(x,y): :py:class:`~.rig.place_and_route.routing_tree.RoutingTree`, ...})\n        A new RoutingTree is produced rooted as before. A dictionarry mapping\n        from (x, y) to the associated RoutingTree is provided for convenience.\n\n    Raises\n    ------\n    :py:class:~rig.place_and_route.exceptions.MachineHasDisconnectedSubregion`\n        If a path to reconnect the tree cannot be found.\n    ';root,lookup,broken_links=copy_and_disconnect_tree(root,machine)
 for parent,child in broken_links:
  child_chips=set(c.chip for c in lookup[child]);path=a_star(child,parent,set(lookup).difference(child_chips),machine,wrap_around);last_node=lookup[path[0]]
  for x,y in path[1:]:
   if (x,y) not in child_chips:new_node=RoutingTree((x,y));assert (x,y) not in lookup,'Cycle must not be created.';lookup[(x,y)]=new_node
   else:
    new_node=lookup[(x,y)]
    for node in lookup[child]:
     if new_node in node.children:node.children.remove(new_node);break
   last_node.children.add(new_node);last_node=new_node
  last_node.children.add(lookup[child])
 return root,lookup
def route(vertices_resources,nets,machine,constraints,placements,allocation,core_resource=Cores,radius=20):
 'Routing algorithm based on Neighbour Exploring Routing (NER).\n\n    Algorithm refrence: J. Navaridas et al. SpiNNaker: Enhanced multicast\n    routing, Parallel Computing (2014).\n    http://dx.doi.org/10.1016/j.parco.2015.01.002\n\n    This algorithm attempts to use NER to generate routing trees for all nets\n    and routes around broken links using A* graph search. If the system is\n    fully connected, this algorithm will always succeed though no consideration\n    of congestion or routing-table usage is attempted.\n\n    Parameters\n    ----------\n    radius : int\n        Radius of area to search from each node. 20 is arbitrarily selected in\n        the paper and shown to be acceptable in practice. If set to zero, this\n        method is becomes longest dimension first routing.\n    ';wrap_around=machine.has_wrap_around_links();route_to_endpoint={}
 for constraint in constraints:
  if isinstance(constraint,RouteEndpointConstraint):route_to_endpoint[constraint.vertex]=constraint.route
 routes={}
 for net in nets:
  root,lookup=ner_net(placements[net.source],set(placements[sink] for sink in net.sinks),machine.width,machine.height,wrap_around,radius);root,lookup=avoid_dead_links(root,machine,wrap_around)
  for sink in net.sinks:
   if sink in route_to_endpoint:lookup[placements[sink]].children.add(route_to_endpoint[sink])
   else:
    cores=allocation[sink].get(core_resource,slice(0,0))
    for core in range(cores.start,cores.stop):lookup[placements[sink]].children.add(Routes.core(core))
  routes[net]=root
 return routes
