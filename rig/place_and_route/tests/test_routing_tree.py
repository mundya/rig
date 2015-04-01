from rig.place_and_route.routing_tree import RoutingTree
class TestRoutingTree(object):
 def test_init_default(self):assert RoutingTree((0,0)).children==set()
 def test_iter(self):t=RoutingTree((0,0));assert set(t)==set([t]);t2=RoutingTree((2,0));t1=RoutingTree((1,0));t0=RoutingTree((0,0),set([t1,t2]));assert set(t0)==set([t0,t1,t2]);t2=RoutingTree((2,0));t1=RoutingTree((1,0),set([t2]));t0=RoutingTree((0,0),set([t1]));assert set(t0)==set([t0,t1,t2]);t2=object();t1=RoutingTree((1,0),set([t2]));t0=RoutingTree((0,0),set([t1]));assert set(t0)==set([t0,t1,t2])
 def test_repr(self):t=RoutingTree((123,321));assert 'RoutingTree' in repr(t);assert '123' in repr(t);assert '321' in repr(t)
