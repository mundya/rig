from ..geometry import concentric_hexagons,to_xyz,minimise_xyz,shortest_mesh_path_length,shortest_mesh_path,shortest_torus_path_length,shortest_torus_path
def test_concentric_hexagons():
 assert set(concentric_hexagons(0))==set([(0,0)]);assert set(concentric_hexagons(0,(3,2)))==set([(3,2)]);assert set(concentric_hexagons(1))==set([(0,0),(+1,0),(-1,0),(0,+1),(0,-1),(+1,+1),(-1,-1)]);assert set(concentric_hexagons(1,(10,100)))==set([(10,100),(11,100),(9,100),(10,101),(10,99),(11,101),(9,99)]);num_layers=10;hexagons=set(concentric_hexagons(num_layers));total_hexagons=3*num_layers*(num_layers+1)+1;assert len(hexagons)==total_hexagons;outer_hexagons=set();inner_hexagons=set()
 for x,y in hexagons:
  m=sorted((x,y,0))[1];layer=abs(x-m)+abs(y-m)+abs(-m)
  if set([(x,y),(x+1,y),(x-1,y),(x,y+1),(x,y-1),(x+1,y+1),(x-1,y-1)]).issubset(hexagons):inner_hexagons.add((x,y));assert layer<num_layers
  else:outer_hexagons.add((x,y));assert layer==num_layers
 assert len(outer_hexagons)==6*num_layers;assert len(inner_hexagons)==total_hexagons-6*num_layers
def test_to_xyz():assert to_xyz((0,0))==(0,0,0);assert to_xyz((1,0))==(1,0,0);assert to_xyz((0,1))==(0,1,0);assert to_xyz((1,1))==(1,1,0);assert to_xyz((-1,0))==(-1,0,0);assert to_xyz((-1,1))==(-1,1,0);assert to_xyz((0,-1))==(0,-1,0);assert to_xyz((1,-1))==(1,-1,0);assert to_xyz((-1,-1))==(-1,-1,0)
test_mesh_vectors=[((0,0,0),(0,0,0)),((1,0,0),(1,0,0)),((0,1,0),(0,1,0)),((0,0,1),(0,0,1)),((-1,0,0),(-1,0,0)),((0,-1,0),(0,-1,0)),((0,0,-1),(0,0,-1)),((1,-1,0),(1,-1,0)),((0,1,-1),(0,1,-1)),((-1,0,1),(-1,0,1)),((0,-1,1),(0,-1,1)),((1,1,0),(0,0,-1)),((-1,-1,0),(0,0,1)),((2,1,0),(1,0,-1)),((-2,-1,0),(-1,0,1)),((1,0,1),(0,-1,0)),((-1,0,-1),(0,1,0)),((2,0,1),(1,-1,0)),((-2,0,-1),(-1,1,0)),((0,1,1),(-1,0,0)),((0,-1,-1),(1,0,0)),((0,2,1),(-1,1,0)),((0,-2,-1),(1,-1,0)),((1,1,1),(0,0,0)),((1,2,3),(-1,0,1)),((-1,-2,-3),(1,0,-1)),((-1,-2,3),(0,-1,4)),((-1,2,-3),(0,3,-2)),((1,-2,-3),(3,0,-1))]
def test_minimise_xyz():
 for vector,minimised in test_mesh_vectors:assert minimise_xyz(vector)==minimised,(vector,minimised)
def test_shortest_mesh_path_length():
 for offset in [(0,0,0),(1,2,3),(-1,-2,-3),(-1,2,-3)]:
  for end,minimised in test_mesh_vectors:start=offset;end=tuple(e+o for (e,o) in zip(end,offset));magnitude=sum(map(abs,minimised));assert shortest_mesh_path_length(start,end)==magnitude,(start,end,magnitude);assert shortest_mesh_path_length(end,start)==magnitude,(end,start,magnitude)
def test_shortest_mesh_path():
 for offset in [(0,0,0),(1,2,3),(-1,-2,-3),(-1,2,-3)]:
  for end,minimised in test_mesh_vectors:start=offset;end=tuple(e+o for (e,o) in zip(end,offset));neg_minimised=tuple(-m for m in minimised);assert shortest_mesh_path(start,end)==minimised,(start,end,minimised);assert shortest_mesh_path(end,start)==neg_minimised,(end,start,neg_minimised)
test_torus_vectors=[((0,0,0),set([(0,0,0)]),(10,10)),((1,0,0),set([(1,0,0)]),(10,10)),((0,1,0),set([(0,1,0)]),(10,10)),((0,0,1),set([(0,0,1)]),(10,10)),((1,1,0),set([(0,0,-1)]),(10,10)),((-1,0,-1),set([(0,1,0)]),(10,10)),((0,-1,-1),set([(1,0,0)]),(10,10)),((4,0,0),set([(-1,0,0)]),(5,10)),((0,9,0),set([(0,-1,0)]),(5,10)),((0,0,1),set([(0,0,1)]),(5,10)),((0,0,9),set([(0,0,-1)]),(5,10)),((5,1,1),set([(-1,0,0)]),(5,10)),((1,10,1),set([(0,-1,0)]),(5,10)),((1,1,2),set([(0,0,1)]),(5,10)),((1,1,10),set([(0,0,-1)]),(5,10)),((3,-1,-1),set([(-1,0,0)]),(5,10)),((-1,8,-1),set([(0,-1,0)]),(5,10)),((-1,-1,0),set([(0,0,1)]),(5,10)),((-1,-1,8),set([(0,0,-1)]),(5,10)),((0,0,0),set([(0,0,0)]),(8,16)),((1,0,0),set([(1,0,0)]),(8,16)),((0,1,0),set([(0,1,0)]),(8,16)),((0,0,-1),set([(0,0,-1)]),(8,16)),((1,1,0),set([(0,0,-1)]),(8,16)),((7,0,0),set([(-1,0,0)]),(8,16)),((6,0,0),set([(-2,0,0)]),(8,16)),((7,1,0),set([(-1,1,0)]),(8,16)),((6,1,0),set([(-2,1,0)]),(8,16)),((0,15,0),set([(0,-1,0)]),(8,16)),((1,15,0),set([(1,-1,0)]),(8,16)),((0,14,0),set([(0,-2,0)]),(8,16)),((1,14,0),set([(1,-2,0)]),(8,16)),((7,15,0),set([(0,0,1)]),(8,16)),((6,15,0),set([(-1,0,1)]),(8,16)),((7,14,0),set([(0,-1,1)]),(8,16)),((7,15,1),set([(0,0,2)]),(8,16)),((6,14,0),set([(0,0,2)]),(8,16)),((2,0,0),set([(2,0,0),(-2,0,0)]),(4,4)),((0,2,0),set([(0,2,0),(0,-2,0)]),(4,4)),((2,2,0),set([(0,0,-2),(0,0,2)]),(4,4)),((4,0,0),set([(4,0,0),(2,0,-2),(0,0,-4)]),(16,2)),((12,0,0),set([(-4,0,0),(-2,0,2),(0,0,4)]),(16,2)),((0,4,0),set([(0,4,0),(0,2,-2),(0,0,-4)]),(2,16)),((0,12,0),set([(0,-4,0),(0,-2,2),(0,0,4)]),(2,16)),((2,0,0),set([(-1,0,0),(0,0,1)]),(3,1)),((2,0,0),set([(2,0,0),(0,0,-2)]),(8,2)),((1,0,0),set([(1,0,0),(0,0,-1)]),(3,1)),((1,0,0),set([(1,0,0),(-1,0,0),(0,0,-1),(0,0,1)]),(2,1))]
def test_shortest_torus_path_length():
 for offset in [(0,0,0),(1,2,3),(-1,-2,-3),(-1,2,-3)]:
  for end,minimiseds,(width,height) in test_torus_vectors:start=offset;end=tuple(e+o for (e,o) in zip(end,offset));magnitude=sum(map(abs,next(iter(minimiseds))));assert shortest_torus_path_length(start,end,width,height)==magnitude,(start,end,width,height,magnitude);assert shortest_torus_path_length(end,start,width,height)==magnitude,(end,start,width,height,magnitude)
def test_shortest_torus_path():
 for offset in [(0,0,0),(1,2,3),(-1,-2,-3),(-1,2,-3)]:
  for end,minimiseds,(width,height) in test_torus_vectors:
   start=offset;end=tuple(e+o for (e,o) in zip(end,offset));unseen_minimiseds=minimiseds.copy();neg_minimiseds=set(tuple(-m for m in minimised) for minimised in minimiseds);unseen_neg_minimiseds=neg_minimiseds.copy()
   for _ in range(1000):
    path=shortest_torus_path(start,end,width,height);assert path in minimiseds,(start,end,width,height,minimiseds)
    try:unseen_minimiseds.remove(path)
    except KeyError:pass
    if not unseen_minimiseds:break
   assert unseen_minimiseds==set(),(start,end,width,height,minimiseds)
   for _ in range(1000):
    path=shortest_torus_path(end,start,width,height);assert path in neg_minimiseds,(end,start,width,height,neg_minimiseds)
    try:unseen_neg_minimiseds.remove(path)
    except KeyError:pass
    if not unseen_neg_minimiseds:break
   assert unseen_neg_minimiseds==set(),(start,end,width,height,neg_minimiseds)
