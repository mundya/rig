import pytest
from ..packets import SDPPacket,SCPPacket
from .. import packets
class TestRangedIntAttribute(object):
 def test_min_exclusive(self):
  class X(object):y=packets.RangedIntAttribute(0,10,min_inclusive=False)
  x=X()
  with pytest.raises(ValueError):x.y=0
  x.y=1
 def test_max_inclusive(self):
  class X(object):y=packets.RangedIntAttribute(0,10,max_inclusive=True)
  x=X();x.y=10
 def test_min_max_fail(self):
  with pytest.raises(ValueError):
   class X(object):y=packets.RangedIntAttribute(100,0)
 def test_type_fail(self):
  class X(object):y=packets.RangedIntAttribute(0,100)
  x=X()
  with pytest.raises(TypeError):x.y='Oops!'
 def test_allow_none(self):
  class X(object):y=packets.RangedIntAttribute(0,10,allow_none=False)
  x=X()
  with pytest.raises(ValueError):x.y=None
  class Y(object):y=packets.RangedIntAttribute(0,10,allow_none=True)
  y=Y();y.y=None
class TestByteStringAttribute(object):
 def test_unlimited_length(self):
  class X(object):y=packets.ByteStringAttribute(default=b'default')
  x=X();assert x.y==b'default';x.y=b'';assert x.y==b'';x.y=b'hello';assert x.y==b'hello';x.y=b'01234567';assert x.y==b'01234567'
 def test_max_length(self):
  class X(object):y=packets.ByteStringAttribute(max_length=8)
  x=X();assert x.y==b'';x.y=b'';assert x.y==b'';x.y=b'hello';assert x.y==b'hello';x.y=b'01234567';assert x.y==b'01234567'
  with pytest.raises(ValueError):x.y=b'012345678'
class TestSDPPacket(object):
 'Test SDPPacket representations.'
 def test_from_bytestring_to_bytestring(self):'Test creating a new SDPPacket from a bytestring.';packet=b'\x87\xf0\xef\xeeZ\xa5\xf0\x0f\xde\xad\xbe\xef';sdp_packet=SDPPacket.from_bytestring(packet);assert isinstance(sdp_packet,SDPPacket);assert sdp_packet.reply_expected;assert sdp_packet.tag==240;assert sdp_packet.dest_port==7;assert sdp_packet.dest_cpu==15;assert sdp_packet.src_port==7;assert sdp_packet.src_cpu==14;assert sdp_packet.dest_x==165;assert sdp_packet.dest_y==90;assert sdp_packet.src_x==15;assert sdp_packet.src_y==240;assert sdp_packet.data==b'\xde\xad\xbe\xef';assert sdp_packet.bytestring==packet
 def test_from_bytestring_no_reply(self):'Test creating a new SDPPacket from a bytestring.';packet=b'\x07\xf0\xef\xee\xa5Z\x0f\xf0\xde\xad\xbe\xef';sdp_packet=SDPPacket.from_bytestring(packet);assert isinstance(sdp_packet,SDPPacket);assert not sdp_packet.reply_expected
 def test_values(self):
  'Check that errors are raised when values are out of range.'
  with pytest.raises(TypeError):SDPPacket(False,3.,0,0,0,0,0,0,0,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,300,0,0,0,0,0,0,0,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,-1,0,0,0,0,0,0,0,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,8,0,0,0,0,0,0,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,-1,0,0,0,0,0,0,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,7,18,0,0,0,0,0,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,7,-1,0,0,0,0,0,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,7,17,8,0,0,0,0,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,7,17,-1,0,0,0,0,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,7,17,7,18,0,0,0,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,7,17,7,-1,0,0,0,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,7,17,7,17,256,0,0,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,7,17,7,17,-1,0,0,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,7,17,7,17,255,256,0,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,7,17,7,17,255,-1,0,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,7,17,7,17,255,255,256,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,7,17,7,17,255,255,-1,0,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,7,17,7,17,255,255,255,256,b'')
  with pytest.raises(ValueError):SDPPacket(False,255,7,17,7,17,255,255,255,-1,b'')
class TestSCPPacket(object):
 'Test packets conforming to the SCP protocol.'
 def test_from_bytestring_short(self):'Test creating an SCP Packet from a bytestring when the SCP Packet is\n        short (no arguments, no data).\n        ';packet=b'\x87\xf0\xef\xeeZ\xa5\xf0\x0f\xad\xde\xef\xbe';scp_packet=SCPPacket.from_bytestring(packet);assert isinstance(scp_packet,SCPPacket);assert scp_packet.reply_expected;assert scp_packet.tag==240;assert scp_packet.dest_port==7;assert scp_packet.dest_cpu==15;assert scp_packet.src_port==7;assert scp_packet.src_cpu==14;assert scp_packet.dest_x==165;assert scp_packet.dest_y==90;assert scp_packet.src_x==15;assert scp_packet.src_y==240;assert scp_packet.cmd_rc==57005;assert scp_packet.seq==48879;assert scp_packet.arg1 is None;assert scp_packet.arg2 is None;assert scp_packet.arg3 is None;assert scp_packet.data==b'';assert scp_packet.bytestring==packet
 def test_from_bytestring(self):'Test creating a new SCPPacket from a bytestring.';packet=b'\x87\xf0\xef\xeeZ\xa5\xf0\x0f\xad\xde\xef\xbe'+b'\xb7\xb7\xa5\xa5\xfe\xca\xfe\xca{{ZZ'+b'\xfe\xed\xde\xaf\x01';scp_packet=SCPPacket.from_bytestring(packet);assert isinstance(scp_packet,SCPPacket);assert scp_packet.reply_expected;assert scp_packet.tag==240;assert scp_packet.dest_port==7;assert scp_packet.dest_cpu==15;assert scp_packet.src_port==7;assert scp_packet.src_cpu==14;assert scp_packet.dest_x==165;assert scp_packet.dest_y==90;assert scp_packet.src_x==15;assert scp_packet.src_y==240;assert scp_packet.cmd_rc==57005;assert scp_packet.seq==48879;assert scp_packet.arg1==2779101111;assert scp_packet.arg2==3405695742;assert scp_packet.arg3==1515879291;assert scp_packet.data==b'\xfe\xed\xde\xaf\x01';assert scp_packet.bytestring==packet
 def test_from_bytestring_0_args(self):'Test creating a new SCPPacket from a bytestring.';packet=b'\x87\xf0\xef\xee\xa5Z\x0f\xf0\xad\xde\xef\xbe'+b'\xb7\xb7\xa5\xa5\xfe\xca\xfe\xca{{ZZ'+b'\xfe\xed\xde\xaf\x01';scp_packet=SCPPacket.from_bytestring(packet,n_args=0);assert scp_packet.cmd_rc==57005;assert scp_packet.seq==48879;assert scp_packet.arg1 is None;assert scp_packet.arg2 is None;assert scp_packet.arg3 is None;assert scp_packet.data==b'\xb7\xb7\xa5\xa5\xfe\xca\xfe\xca{{ZZ'+b'\xfe\xed\xde\xaf\x01';assert scp_packet.bytestring==packet
 def test_from_bytestring_0_args_short(self):'Test creating a new SCPPacket from a bytestring.';packet=b'\x87\xf0\xef\xee\xa5Z\x0f\xf0\xad\xde\xef\xbe';scp_packet=SCPPacket.from_bytestring(packet);assert scp_packet.arg1 is None;assert scp_packet.arg2 is None;assert scp_packet.arg3 is None;assert scp_packet.data==b'';assert scp_packet.bytestring==packet
 def test_from_bytestring_1_args(self):'Test creating a new SCPPacket from a bytestring.';packet=b'\x87\xf0\xef\xee\xa5Z\x0f\xf0\xad\xde\xef\xbe'+b'\xb7\xb7\xa5\xa5\xfe\xca\xfe\xca{{ZZ'+b'\xfe\xed\xde\xaf\x01';scp_packet=SCPPacket.from_bytestring(packet,n_args=1);assert scp_packet.arg1==2779101111;assert scp_packet.arg2 is None;assert scp_packet.arg3 is None;assert scp_packet.data==b'\xfe\xca\xfe\xca{{ZZ'+b'\xfe\xed\xde\xaf\x01';assert scp_packet.bytestring==packet
 def test_from_bytestring_1_args_short(self):'Test creating a new SCPPacket from a bytestring.';packet=b'\x87\xf0\xef\xee\xa5Z\x0f\xf0\xad\xde\xef\xbe'+b'\xb7\xb7\xa5\xa5';scp_packet=SCPPacket.from_bytestring(packet);assert scp_packet.arg1==2779101111;assert scp_packet.arg2 is None;assert scp_packet.arg3 is None;assert scp_packet.data==b'';assert scp_packet.bytestring==packet
 def test_from_bytestring_2_args(self):'Test creating a new SCPPacket from a bytestring.';packet=b'\x87\xf0\xef\xee\xa5Z\x0f\xf0\xad\xde\xef\xbe'+b'\xb7\xb7\xa5\xa5\xfe\xca\xfe\xca{{ZZ'+b'\xfe\xed\xde\xaf\x01';scp_packet=SCPPacket.from_bytestring(packet,n_args=2);assert scp_packet.arg1==2779101111;assert scp_packet.arg2==3405695742;assert scp_packet.arg3 is None;assert scp_packet.data==b'{{ZZ\xfe\xed\xde\xaf\x01';assert scp_packet.bytestring==packet
 def test_from_bytestring_2_args_short(self):'Test creating a new SCPPacket from a bytestring.';packet=b'\x87\xf0\xef\xee\xa5Z\x0f\xf0\xad\xde\xef\xbe'+b'\xb7\xb7\xa5\xa5\xfe\xca\xfe\xca';scp_packet=SCPPacket.from_bytestring(packet);assert scp_packet.arg1==2779101111;assert scp_packet.arg2==3405695742;assert scp_packet.arg3 is None;assert scp_packet.data==b'';assert scp_packet.bytestring==packet
 def test_values(self):
  'Check that SCP packets respect data values.'
  with pytest.raises(ValueError):SCPPacket(False,0,0,0,0,0,0,0,0,0,1<<16,0,0,0,0,b'')
  with pytest.raises(ValueError):SCPPacket(False,0,0,0,0,0,0,0,0,0,-1,0,0,0,0,b'')
  with pytest.raises(ValueError):SCPPacket(False,0,0,0,0,0,0,0,0,0,65535,1<<16,0,0,0,b'')
  with pytest.raises(ValueError):SCPPacket(False,0,0,0,0,0,0,0,0,0,65535,-1,0,0,0,b'')
  with pytest.raises(ValueError):SCPPacket(False,0,0,0,0,0,0,0,0,0,65535,65535,1<<32,0,0,b'')
  with pytest.raises(ValueError):SCPPacket(False,0,0,0,0,0,0,0,0,0,65535,65535,-1,0,0,b'')
  with pytest.raises(ValueError):SCPPacket(False,0,0,0,0,0,0,0,0,0,65535,65535,4294967295,1<<32,0,b'')
  with pytest.raises(ValueError):SCPPacket(False,0,0,0,0,0,0,0,0,0,65535,65535,4294967295,-1,0,b'')
  with pytest.raises(ValueError):SCPPacket(False,0,0,0,0,0,0,0,0,0,65535,65535,4294967295,4294967295,1<<32,b'')
  with pytest.raises(ValueError):SCPPacket(False,0,0,0,0,0,0,0,0,0,65535,65535,4294967295,4294967295,-1,b'')
