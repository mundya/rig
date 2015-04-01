'General-purpose SpiNNaker-related geometry functions.\n'
import random
def to_xyz(xy):'Convert a two-tuple (x, y) coordinate into an (x, y, 0) coordinate.';x,y=xy;return x,y,0
def minimise_xyz(xyz):'Minimise an (x, y, z) coordinate.';x,y,z=xyz;m=max(min(x,y),min(max(x,y),z));return x-m,y-m,z-m
def shortest_mesh_path_length(source,destination):'Get the length of a shortest path from source to destination without\n    using wrap-around links.\n\n    Parameters\n    ----------\n    source : (x, y, z)\n    destination : (x, y, z)\n\n    Returns\n    -------\n    int\n    ';x,y,z=(d-s for (s,d) in zip(source,destination));return max(x,y,z)-min(x,y,z)
def shortest_mesh_path(source,destination):'Calculate the shortest vector from source to destination without using\n    wrap-around links.\n\n    Parameters\n    ----------\n    source : (x, y, z)\n    destination : (x, y, z)\n\n    Returns\n    -------\n    (x, y, z)\n    ';return minimise_xyz(d-s for (s,d) in zip(source,destination))
def shortest_torus_path_length(source,destination,width,height):'Get the length of a shortest path from source to destination using\n    wrap-around links.\n\n    See http://jhnet.co.uk/articles/torus_paths for an explanation of how this\n    method works.\n\n    Parameters\n    ----------\n    source : (x, y, z)\n    destination : (x, y, z)\n    width : int\n    height : int\n\n    Returns\n    -------\n    int\n    ';w,h=width,height;x,y,z=(d-s for (s,d) in zip(source,destination));x,y=x-z,y-z;x%=w;y%=h;return min(max(x,y),w-x+y,x+h-y,max(w-x,h-y))
def shortest_torus_path(source,destination,width,height):
 'Calculate the shortest vector from source to destination using\n    wrap-around links.\n\n    See http://jhnet.co.uk/articles/torus_paths for an explanation of how this\n    method works.\n\n    Note that when multiple shortest paths exist, one will be chosen at random\n    with uniform probability.\n\n    Parameters\n    ----------\n    source : (x, y, z)\n    destination : (x, y, z)\n    width : int\n    height : int\n\n    Returns\n    -------\n    (x, y, z)\n    ';w,h=width,height;sx,sy,sz=source;sx,sy=sx-sz,sy-sz;dx,dy,dz=destination;dx,dy=(dx-dz-sx)%w,(dy-dz-sy)%h;approaches=[(max(dx,dy),(dx,dy,0)),(w-dx+dy,(-(w-dx),dy,0)),(dx+h-dy,(dx,-(h-dy),0)),(max(w-dx,h-dy),(-(w-dx),-(h-dy),0))];_,vector=min(approaches,key=lambda a:a[0]+random.random());x,y,z=minimise_xyz(vector)
 if abs(x)>=height:max_spirals=x//height;d=random.randint(min(0,max_spirals),max(0,max_spirals))*height;x-=d;z-=d
 elif abs(y)>=width:max_spirals=y//width;d=random.randint(min(0,max_spirals),max(0,max_spirals))*width;y-=d;z-=d
 return x,y,z
def concentric_hexagons(radius,start=(0,0)):
 'A generator which produces coordinates of concentric rings of hexagons.\n\n    Parameters\n    ----------\n    radius : int\n        Number of layers to produce (0 is just one hexagon)\n    start : (x, y)\n        The coordinate of the central hexagon.\n    ';x,y=start;yield x,y
 for r in range(1,radius+1):
  y-=1
  for dx,dy in [(1,1),(0,1),(-1,0),(-1,-1),(0,-1),(1,0)]:
   for _ in range(r):yield x,y;x+=dx;y+=dy
