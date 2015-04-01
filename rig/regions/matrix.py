import enum
import numpy as np
from .region import Region
import struct
class MatrixPartitioning(enum.IntEnum):rows=0;columns=1
class NpIntFormatter(object):
 def __init__(self,dtype):self.dtype=dtype;self.bytes_per_element={np.uint8:1,np.int8:1,np.uint16:2,np.int16:2,np.uint32:4,np.int32:4}[dtype]
 __call__=lambda self,matrix,**kwargs:matrix.astype(dtype=self.dtype)
class MatrixRegion(Region):
 'A region of memory which represents data from a matrix.\n\n    The number of rows and columns may be prepended to the data as it is\n    written out.\n\n    Notes\n    -----\n    If the number of rows and columns are to be written out then they are\n    always written in the order: rows, columns.  By default they are\n    written as 4-byte values.\n\n    See also\n    --------\n     - :py:class:`NpIntFormatter` formats matrix elements as integers.\n     - :py:class:`rig.fixed_point.FixedPointFormatter` formats matrix\n       elements as fixed point values.\n    '
 def __init__(self,matrix,prepend_n_rows=False,prepend_n_columns=False,formatter=NpIntFormatter(np.uint32),sliced_dimension=None):'Create a new region to represent a matrix data structure in memory.\n\n        Parameters\n        ----------\n        matrix : :py:class:`numpy.ndarray`\n            A matrix that will be stored in memory, or nothing to indicate that\n            the data will be filled on SpiNNaker.  The matrix will be copied\n            and made read-only, so provide the matrix as it is ready to go into\n            memory.\n        prepend_n_rows : bool\n            Prepend the number of rows as a 4-byte integer to the matrix as it\n            is written out in memory.\n        prepend_n_columns : bool\n            Prepend the number of columns as a 4-byte integer to the matrix as\n            it is written out in memory.\n        formatter : callable\n            A formatter which will be applied to the NumPy matrix before\n            writing the value out.  The formatter must accept calls with a\n            NumPy matrix and must report as `bytes_per_element` the number of\n            bytes used to store each formatted element.\n        sliced_dimension : None or :py:class:`MatrixPartitioning` or int\n            Indicates the dimension on which the matrix will be partitioned.\n            None indicates no partitioning, 0 indicates partitioning of rows, 1\n            of columns.  The :py:class:`MatrixPartitioning` enum can make for\n            more readable code.\n        ';self.matrix=np.copy(matrix);self.matrix.flags.writeable=False;self.prepend_n_rows=prepend_n_rows;self.prepend_n_columns=prepend_n_columns;assert sliced_dimension is None or sliced_dimension<self.matrix.ndim;self.partition_index=sliced_dimension;self.formatter=formatter
 def expanded_slice(self,vertex_slice):
  if self.partition_index is None:return slice(None)
  return tuple(slice(None) for _ in range(self.partition_index))+(vertex_slice,)+tuple(slice(None) for _ in range(self.partition_index+1,self.matrix.ndim))
 def sizeof(self,vertex_slice):
  'Get the size of a slice of this region in bytes.\n\n        See :py:meth:`.region.Region.sizeof`\n        ';pp_size=0
  if self.prepend_n_rows:pp_size+=4
  if self.prepend_n_columns:pp_size+=4
  return pp_size+self.matrix[self.expanded_slice(vertex_slice)].size*self.formatter.bytes_per_element
 def write_subregion_to_file(self,vertex_slice,fp,**formatter_args):
  'Write the data contained in a portion of this region out to file.\n        ';data=self.matrix[self.expanded_slice(vertex_slice)]
  if self.prepend_n_rows:fp.write(struct.pack('I',data.shape[0]))
  if self.prepend_n_columns:
   if self.matrix.ndim>=2:fp.write(struct.pack('I',data.shape[1]))
   else:fp.write(struct.pack('I',1))
  formatted=self.formatter(data,**formatter_args);fp.write(formatted.reshape((formatted.size,1)).data)
