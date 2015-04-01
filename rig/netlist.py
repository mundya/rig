'Represent and work with vertices and netlists.\n'
class Net(object):
 'A net represents connectivity from one vertex to many vertices.\n\n    Attributes\n    ----------\n    source : vertex\n        The vertex which is the source of the net.\n    weight : float or int\n        The "strength" of the net, in application specific units.\n    sinks : list\n        A list of vertices that the net connects to.\n    ';__slots__=['source','weight','sinks']
 def __init__(self,source,sinks,weight=1.):
  'Create a new Net.\n\n        Parameters\n        ----------\n        source : vertex\n        sinks : list or vertex\n            If a list of vertices is provided then the list is copied, whereas\n            if a single vertex is provided then this used to create the list of\n            sinks.\n        weight : float or int\n        ';self.source=source;self.weight=weight
  if isinstance(sinks,list):self.sinks=sinks[:]
  else:self.sinks=[sinks]
 def __contains__(self,vertex):'Test if a supplied vertex is a source or sink of this net.';return vertex==self.source or vertex in self.sinks
