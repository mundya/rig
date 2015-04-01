'Representations of SDP and SCP Packets.'
import six
import struct
from weakref import WeakKeyDictionary
FLAG_REPLY=135
FLAG_NO_REPLY=7
class RangedIntAttribute(object):
 'Descriptor that ensures values fit within a range of values.'
 def __init__(self,minimum,maximum,min_inclusive=True,max_inclusive=False,allow_none=False,accept=list()):
  'Create a new ranged descriptor with specified minimum and maximum\n        values.\n        '
  if not min_inclusive:minimum+=1
  if max_inclusive:maximum+=1
  if not minimum<=maximum:raise ValueError('min should be smaller than max')
  self.accept=accept[:];self.default=minimum;self.min=minimum;self.max=maximum;self.data=WeakKeyDictionary();self.allow_none=allow_none
 __get__=lambda self,instance,owner:self.data.get(instance,self.default)
 def __set__(self,instance,value):
  if value is not None:
   if not isinstance(value,six.integer_types):raise TypeError('Value should be an integer: {!s}'.format(value))
   if not self.min<=value<self.max and value not in self.accept:raise ValueError('Value outside range {}: [{} to {})'.format(value,self.min,self.max))
   self.data[instance]=value
  elif self.allow_none:self.data[instance]=None
  else:raise ValueError('Value may not be None')
class ByteStringAttribute(object):
 'Descriptor that ensures values are bytestrings of the correct length.'
 def __init__(self,default=b'',max_length=None):self.max_length=max_length;self.default=default;self.data=WeakKeyDictionary()
 __get__=lambda self,instance,owner:self.data.get(instance,self.default)
 def __set__(self,instance,value):
  if self.max_length is not None and len(value)>self.max_length:raise ValueError('Byte string is too long: should be less than {} bytes'.format(self.max_length))
  self.data[instance]=value
class SDPPacket(object):
 'An SDP Packet';tag=RangedIntAttribute(0,256);dest_port=RangedIntAttribute(0,8);dest_cpu=RangedIntAttribute(0,18,accept=[31]);src_port=RangedIntAttribute(0,8);src_cpu=RangedIntAttribute(0,18,accept=[31]);dest_x=RangedIntAttribute(0,256);dest_y=RangedIntAttribute(0,256);src_x=RangedIntAttribute(0,256);src_y=RangedIntAttribute(0,256);data=ByteStringAttribute()
 def __init__(self,reply_expected,tag,dest_port,dest_cpu,src_port,src_cpu,dest_x,dest_y,src_x,src_y,data):'Create a new SDPPacket.\n\n        Parameters\n        ----------\n        reply_expected : bool\n            True if a reply is expected, otherwise False.\n        tag : int\n            An integer representing the IPTag that should be used to transmit\n            the packer over an IPv4 network.\n        ';self.reply_expected=reply_expected;self.tag=tag;self.dest_port=dest_port;self.dest_cpu=dest_cpu;self.src_port=src_port;self.src_cpu=src_cpu;self.dest_x=dest_x;self.dest_y=dest_y;self.src_x=src_x;self.src_y=src_y;self.data=data
 @classmethod
 def unpack_packet(cls,bytestring):'Unpack the SDP header from a bytestring.';header=bytestring[0:8];data=bytestring[8:];flags,tag,dest_cpu_port,src_cpu_port,dest_p2p,src_p2p=struct.unpack('<4B2H',header);dest_x=(dest_p2p&65280)>>8;dest_y=dest_p2p&255;src_x=(src_p2p&65280)>>8;src_y=src_p2p&255;dest_cpu,dest_port=cls.unpack_dest_cpu_port(dest_cpu_port);src_cpu,src_port=cls.unpack_dest_cpu_port(src_cpu_port);return dict(reply_expected=flags==FLAG_REPLY,tag=tag,dest_port=dest_port,dest_cpu=dest_cpu,src_port=src_port,src_cpu=src_cpu,dest_x=dest_x,dest_y=dest_y,src_x=src_x,src_y=src_y,data=data)
 @classmethod
 def from_bytestring(cls,bytestring):'Create a new SDPPacket from a bytestring.\n\n        Returns\n        -------\n        SDPPacket\n            An SDPPacket containing the data from the bytestring.\n        ';return cls(**cls.unpack_packet(bytestring))
 @staticmethod
 def pack_dest_cpu_port(port,cpu):return (port&7)<<5|cpu&31
 @staticmethod
 def unpack_dest_cpu_port(portcpu):return portcpu&31,portcpu>>5&7
 @property
 def packed_dest_cpu_port(self):return self.pack_dest_cpu_port(self.dest_port,self.dest_cpu)
 @property
 def packed_src_cpu_port(self):return self.pack_dest_cpu_port(self.src_port,self.src_cpu)
 @property
 def packed_data(self):return self.data
 @property
 def bytestring(self):'Convert the packet into a bytestring.';dest_p2p=self.dest_x<<8|self.dest_y;src_p2p=self.src_x<<8|self.src_y;header=struct.pack('<4B2H',FLAG_REPLY if self.reply_expected else FLAG_NO_REPLY,self.tag,self.packed_dest_cpu_port,self.packed_src_cpu_port,dest_p2p,src_p2p);return header+self.packed_data
class SCPPacket(SDPPacket):
 'An SCP Packet';cmd_rc=RangedIntAttribute(0,65535,max_inclusive=True);seq=RangedIntAttribute(0,65535,max_inclusive=True);arg1=RangedIntAttribute(0,4294967295,max_inclusive=True,allow_none=True);arg2=RangedIntAttribute(0,4294967295,max_inclusive=True,allow_none=True);arg3=RangedIntAttribute(0,4294967295,max_inclusive=True,allow_none=True);data=ByteStringAttribute(max_length=256)
 def __init__(self,reply_expected,tag,dest_port,dest_cpu,src_port,src_cpu,dest_x,dest_y,src_x,src_y,cmd_rc,seq,arg1,arg2,arg3,data):super(SCPPacket,self).__init__(reply_expected,tag,dest_port,dest_cpu,src_port,src_cpu,dest_x,dest_y,src_x,src_y,data);self.cmd_rc=cmd_rc;self.seq=seq;self.arg1=arg1;self.arg2=arg2;self.arg3=arg3
 @classmethod
 def from_bytestring(cls,scp_packet,n_args=3):'Create a new SCPPacket from a bytestring.\n\n        Parameters\n        ----------\n        scp_packet : bytestring\n            Bytestring containing an SCP packet.\n        n_args : int\n            The number of arguments to unpack from the SCP data.\n        ';sdp_data=cls.unpack_packet(scp_packet);sdp_data.update(cls.unpack_scp_header(sdp_data['data'],n_args));return cls(**sdp_data)
 @classmethod
 def unpack_scp_header(cls,data,n_args=3):
  'Unpack the SCP header from a bytestring.';cmd_rc,seq=struct.unpack('<2H',data[0:4]);data=data[4:];arg1=arg2=arg3=None
  if n_args>=1 and len(data)>=4:arg1=struct.unpack('<I',data[0:4])[0];data=data[4:]
  if n_args>=2 and len(data)>=4:arg2=struct.unpack('<I',data[0:4])[0];data=data[4:]
  if n_args>=3 and len(data)>=4:arg3=struct.unpack('<I',data[0:4])[0];data=data[4:]
  scp_header={'cmd_rc':cmd_rc,'seq':seq,'arg1':arg1,'arg2':arg2,'arg3':arg3,'data':data};return scp_header
 @property
 def packed_data(self):
  'Pack the data for the SCP packet.';scp_header=struct.pack('<2H',self.cmd_rc,self.seq)
  for arg in (self.arg1,self.arg2,self.arg3):
   if arg is not None:scp_header+=struct.pack('<I',arg)
  return scp_header+self.data
