import pytest
from collections import deque
from rig.machine import Machine,Links
from rig.place_and_route.routing_tree import RoutingTree
from rig.place_and_route.route.util import links_between
from rig.place_and_route.route.ner import ner_net,copy_and_disconnect_tree,a_star,avoid_dead_links
from rig.place_and_route.exceptions import MachineHasDisconnectedSubregion
def test_ner_net_childless():root,lookup=ner_net((0,0),[],1,1);assert root.chip==(0,0);assert root.children==set();assert lookup[(0,0)] is root;assert len(lookup)==1;root,lookup=ner_net((0,1),[],2,2);assert root.chip==(0,1);assert root.children==set();assert lookup[(0,1)] is root;assert len(lookup)==1
ner_net_testcases=[((0,0),[],1,1,True,20),((0,1),[],2,2,True,20),((1,1),[(2,1)],3,3,True,20),((1,1),[(2,1)],3,3,False,20),((1,1),[(0,1)],3,3,True,20),((1,1),[(0,1)],3,3,False,20),((1,1),[(1,2)],3,3,True,20),((1,1),[(1,2)],3,3,False,20),((1,1),[(1,0)],3,3,True,20),((1,1),[(1,0)],3,3,False,20),((1,1),[(2,2)],3,3,True,20),((1,1),[(2,2)],3,3,False,20),((1,1),[(0,0)],3,3,True,20),((1,1),[(0,0)],3,3,False,20),((0,0),[(9,0)],10,10,True,20),((0,0),[(9,0)],10,10,False,20),((0,0),[(0,9)],10,10,True,20),((0,0),[(0,9)],10,10,False,20),((0,0),[(9,9)],10,10,True,20),((0,0),[(9,9)],10,10,False,20),((0,0),[(1,0),(2,0)],3,3,True,20),((0,0),[(1,0),(2,0)],3,3,False,20),((0,0),[(0,1),(0,2)],3,3,True,20),((0,0),[(0,1),(0,2)],3,3,False,20),((0,0),[(1,1),(2,2)],3,3,True,20),((0,0),[(1,1),(2,2)],3,3,False,20),((0,0),[(x,y) for x in range(9) for y in range(9) if x%2==1 and y%2==1],9,9,True,20),((0,0),[(x,y) for x in range(9) for y in range(9) if x%2==1 and y%2==1],9,9,False,20),((0,0),[(x,y) for x in range(9) for y in range(9) if (x,y)!=(0,0)],9,9,True,20),((0,0),[(x,y) for x in range(9) for y in range(9) if (x,y)!=(0,0)],9,9,False,20),((0,0),[(8,8)],9,9,False,3),((0,0),[(5,5)],9,9,True,3),((0,0),[(10,10),(11,11),(30,30),(31,31)],100,100,False,1),((0,0),[(10,10),(11,11),(30,30),(29,29)],40,40,True,1)]
def test_ner_net():
 for source,destinations,width,height,wrap_around,radius in ner_net_testcases:
  root,lookup=ner_net(source,destinations,width,height,wrap_around,radius);assert source in lookup
  for destination in destinations:assert destination in lookup
  assert lookup[source] is root;visited=set();to_visit=deque([(source,root)])
  while to_visit:
   (x,y),node=to_visit.popleft();assert (x,y)==node.chip;assert (x,y) not in visited,'Loop detected';visited.add((x,y))
   if (x,y)==source or (x,y) in destinations:assert (x,y) in lookup;assert lookup[(x,y)] is node
   if len(node.children)==0:assert (x,y)==source or (x,y) in destinations
   else:
    for child in node.children:
     dx=node.chip[0]-child.chip[0];dy=node.chip[1]-child.chip[1]
     if wrap_around:assert (dx,dy) in set([(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(width-1,0),(-(width-1),0),(0,height-1),(0,-(height-1)),(width-1,height-1),(-(width-1),-(height-1))])
     else:assert (dx,dy) in set([(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1)])
     to_visit.append((child.chip,child))
  assert source in visited
  for destination in destinations:assert destination in visited
def test_copy_and_disconnect_tree():
 working_machine=Machine(10,10);dead_link_machine=Machine(10,10,dead_links=set([(0,0,Links.north)]));dead_chip_machine=Machine(10,10,dead_chips=set([(1,1)]));test_cases=[];test_cases.append((RoutingTree((0,0)),working_machine,set()));t11=RoutingTree((1,2));t10=RoutingTree((0,2));t1=RoutingTree((0,1),set([t10,t11]));t01=RoutingTree((2,0));t00=RoutingTree((2,1));t0=RoutingTree((1,0),set([t00,t01]));t=RoutingTree((0,0),set([t0,t1]));test_cases.append((t0,working_machine,set()));test_cases.append((t,dead_link_machine,set([((0,0),(0,1))])));t3=RoutingTree((1,2));t2=RoutingTree((2,1));t1=RoutingTree((1,1),set([t2,t3]));t0=RoutingTree((0,0),set([t1]));test_cases.append((t0,dead_chip_machine,set([((0,0),(2,1)),((0,0),(1,2))])))
 for old_root,machine,expected_broken_links in test_cases:
  old_lookup=dict((node.chip,node) for node in old_root);new_root,new_lookup,new_broken_links=copy_and_disconnect_tree(old_root,machine);assert new_root is not old_root;assert new_root.chip==old_root.chip;old_chips=set(old_lookup);new_chips=set(new_lookup);assert old_chips.issuperset(new_chips);assert old_chips.difference(new_chips)==set(c for c in old_chips if c not in machine);assert new_broken_links==expected_broken_links;nodes_with_parents=set([new_root.chip])
  for chip in old_lookup:
   old_node=old_lookup[chip]
   if old_node.chip not in machine:continue
   new_node=new_lookup[chip];assert old_node is not new_node;assert chip==old_node.chip==new_node.chip
   for child in new_node.children:assert old_lookup[child.chip] is not child;assert new_lookup[child.chip] is child;assert child not in nodes_with_parents;nodes_with_parents.add(child)
   old_children=set(c.chip for c in old_node.children);new_children=set(c.chip for c in new_node.children);assert old_children.issuperset(new_children);assert old_children.difference(new_children)==set(c for c in old_children if c not in machine or not links_between(chip,c,machine))
def test_a_star():
 working_machine=Machine(10,10);dead_link_machine=Machine(10,10,dead_links=set([(0,0,Links.north)]));test_cases=[((1,0),(0,0),set([(0,0)])),((2,0),(0,0),set([(0,0)])),((9,9),(0,0),set([(0,0)])),((0,2),(0,0),set([(0,0)])),((0,3),(0,0),set([(0,2),(0,1),(0,0)])),((0,3),(0,2),set([(0,2),(0,1),(0,0)])),((0,0),(4,4),set([(4,4),(0,1),(0,2)])),((0,0),(0,1),set([(4,4),(5,5),(0,1)]))]
 for machine in [working_machine,dead_link_machine]:
  for wrap_around in [True,False]:
   for sink,heuristic_source,sources in test_cases:
    path=a_star(sink,heuristic_source,sources,machine,wrap_around);assert path[0] in sources;assert len(set(path).intersection(sources))==1;last_step=path[0]
    for step in path[1:]+[sink]:assert links_between(last_step,step,machine);last_step=step
    visited=set([sink])
    for step in path:assert step not in visited;visited.add(step)
def test_a_star_impossible():
 machine=Machine(2,1,dead_links=set((x,0,l) for l in Links for x in range(2) if not (x==1 and l==Links.west)))
 with pytest.raises(MachineHasDisconnectedSubregion):a_star((1,0),(0,0),set([(0,0)]),machine,True)
 assert a_star((0,0),(1,0),set([(1,0)]),machine,True)==[(1,0)]
def test_avoid_dead_links_no_change():
 machine=Machine(10,10,dead_links=set([(0,0,Links.west)]),dead_chips=set([(1,1)]));test_cases=[];test_cases.append(RoutingTree((0,0)));t002=RoutingTree((1,3),set([]));t001=RoutingTree((0,3),set([]));t000=RoutingTree((1,2),set([]));t00=RoutingTree((0,2),set([t000,t001,t002]));t0=RoutingTree((0,1),set([t00]));t=RoutingTree((0,0),set([t0]));test_cases.append(t)
 for old_root in test_cases:
  new_root,new_lookup=avoid_dead_links(old_root,machine);assert new_root.chip==old_root.chip;assert set(new_lookup)==set(r.chip for r in old_root)
  for node in new_root:assert new_lookup[node.chip] is node
  for old_node in old_root:new_node=new_lookup[old_node.chip];assert new_node.chip==old_node.chip;assert set(n.chip for n in new_node.children)==set(n.chip for n in old_node.children)
def test_avoid_dead_links_change():
 machine=Machine(10,10,dead_links=set([(4,4,Links.north)]),dead_chips=set([(1,1),(2,1),(3,1),(4,1),(1,2),(1,3),(1,4)]));test_cases=[];t1=RoutingTree((4,5));t0=RoutingTree((4,4),set([t1]));test_cases.append(t0);t2=RoutingTree((4,2));t1=RoutingTree((4,1),set([t2]));t0=RoutingTree((4,0),set([t1]));test_cases.append(t0);t002=RoutingTree((3,3));t001=RoutingTree((2,3));t000=RoutingTree((3,2));t00=RoutingTree((2,2),set([t000,t001,t002]));t0=RoutingTree((1,1),set([t00]));t=RoutingTree((0,0),set([t0]));test_cases.append(t);t55=RoutingTree((2,5),set([]));t54=RoutingTree((3,5),set([t55]));t53=RoutingTree((4,5),set([t54]));t52=RoutingTree((5,2),set([]));t51=RoutingTree((5,3),set([t52]));t50=RoutingTree((5,4),set([t51]));t4=RoutingTree((5,5),set([t50,t53]));t3=RoutingTree((4,4),set([t4]));t2=RoutingTree((3,3),set([t3]));t1=RoutingTree((2,2),set([t2]));t0=RoutingTree((1,1),set([t1]));t=RoutingTree((0,0),set([t0]));test_cases.append(t)
 for old_root in test_cases:
  new_root,new_lookup=avoid_dead_links(old_root,machine);assert new_root.chip==old_root.chip
  for node in new_root:assert new_lookup[node.chip] is node
  assert set(n.chip for n in old_root if n.chip in machine).issubset(set(n.chip for n in new_root));visited=set();to_visit=deque([new_root])
  while to_visit:
   node=to_visit.popleft();assert node not in visited;visited.add(node);assert node.chip in new_lookup
   for child in node.children:assert links_between(node.chip,child.chip,machine);to_visit.append(child)
