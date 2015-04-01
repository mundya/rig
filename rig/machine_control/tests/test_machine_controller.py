import mock
import pkg_resources
import pytest
import six
from six import iteritems,itervalues
import struct
import tempfile
import os
from .test_scp_connection import SendReceive,mock_conn
from ..consts import DataType,SCPCommands,LEDAction,NNCommands,NNConstants
from ..machine_controller import MachineController,SpiNNakerMemoryError,MemoryIO,SpiNNakerRouterError,SpiNNakerLoadingError,CoreInfo,ProcessorStatus,unpack_routing_table_entry
from ..packets import SCPPacket
from .. import regions,consts,struct_file
from rig.machine import Cores,SDRAM,SRAM,Links,Machine
from rig.routing_table import RoutingTableEntry,Routes
@pytest.fixture(scope='module')
def controller(spinnaker_ip):return MachineController(spinnaker_ip)
@pytest.fixture(scope='module')
def live_machine(controller):return controller.get_machine()
@pytest.fixture
def cn():cn=MachineController('localhost');cn._scp_data_length=256;return cn
@pytest.fixture
def controller_rw_mock():
 'Create a controller with mock _read and _write methods.';cn=MachineController('localhost');cn._read=mock.Mock(spec_set=[]);cn._write=mock.Mock(spec_set=[]);cn._scp_data_length=256
 def read_mock(x,y,p,address,length_bytes,data_type=DataType.byte):return b'\x00'*length_bytes
 cn._read.side_effect=read_mock;return cn
@pytest.fixture
def mock_controller():cn=mock.Mock(spec=MachineController);return cn
@pytest.fixture
def aplx_file(request):
 'Create an APLX file containing nonsense data.';aplx_file=tempfile.NamedTemporaryFile(delete=False);test_string=b'Must be word aligned';assert len(test_string)%4==0;aplx_file.write(test_string*100);aplx_file.close()
 def teardown():aplx_file.close();os.unlink(aplx_file.name)
 request.addfinalizer(teardown);return aplx_file.name
@pytest.mark.order_id('spinnaker_boot','spinnaker_hw_test')
@pytest.mark.order_after('bmp_power_cycle')
@pytest.mark.no_boot
def test_boot(controller,spinnaker_width,spinnaker_height):'Test that the board can be booted.';controller.boot(width=spinnaker_width,height=spinnaker_height);sver=controller.get_software_version(0,0,0);assert sver.version>=1.3
@pytest.mark.order_id('spinnaker_hw_test')
@pytest.mark.order_after('spinnaker_boot')
@pytest.mark.incremental
class TestMachineControllerLive(object):
 'Test the machine controller against a running SpiNNaker machine.'
 def test_get_software_version(self,controller,spinnaker_width,spinnaker_height):
  'Test getting the software version data.'
  for x in range(2):
   for y in range(2):sver=controller.get_software_version(x=x,y=y,processor=0);assert sver.virt_cpu==0;assert 'SpiNNaker' in sver.version_string;assert sver.version>=1.3;assert sver.position==(x,y)
 def test_write_and_read(self,controller):
  'Test write and read capabilities by writing a string to SDRAM and\n        then reading back in a different order.\n        ';data=b'Hello, SpiNNaker'
  with controller(x=0,y=0,p=0):controller.write(1610612736,data[0:4]);controller.write(1610612740,data[4:6]);controller.write(1610612742,data[6:])
  with controller(x=0,y=0,p=1):assert controller.read(1610612736,1)==data[0:1];assert controller.read(1610612736,2)==data[0:2];assert controller.read(1610612736,4)==data[0:4]
  with controller(x=0,y=0,p=1):assert controller.read(1610612736,len(data))==data
 def test_set_get_clear_iptag(self,controller):
  ip_addr=controller.connections[0].sock.getsockname()[0];port=1234;iptag=7
  with controller(x=0,y=0):controller.iptag_set(iptag,ip_addr,port);ip_tag=controller.iptag_get(iptag);assert ip_addr==ip_tag.addr;assert port==ip_tag.port;assert ip_tag.flags!=0;controller.iptag_clear(iptag);ip_tag=controller.iptag_get(iptag);assert ip_tag.flags==0
 def test_led_on(self,controller):
  for x in range(2):
   for y in range(2):controller.set_led(1,x=x,y=y,action=True)
 def test_led_off(self,controller):
  for x in range(2):
   for y in range(2):controller.set_led(1,x=x,y=y,action=False)
 def test_led_toggle(self,controller):
  for _ in range(2):
   for x in range(2):
    for y in range(2):controller.set_led(1,x=x,y=y,action=None)
 def test_count_cores_in_state_idle(self,controller):'Check that we have no idle cores as there are no cores assigned to\n        the application yet.\n        ';assert controller.count_cores_in_state(consts.AppState.idle)==0
 @pytest.mark.parametrize('targets',[{(1,1):{3,4},(1,0):{5}},{(0,1):{2}}])
 def test_load_application(self,controller,targets):
  'Test loading an APLX.  The given APLX writes (x << 24) | (y << 16) |\n        p into sdram_base + p*4; so we can check everything works by looking at\n        that memory address.\n        ';assert isinstance(controller,MachineController);assert len(controller.structs)>0,'Controller has no structs, check test fixture.';controller.load_application(pkg_resources.resource_filename('rig','binaries/rig_test.aplx'),targets)
  for (t_x,t_y),cores in iteritems(targets):
   with controller(x=t_x,y=t_y):
    print(t_x,t_y);addr_base=controller.read_struct_field('sv','sdram_base')
    for t_p in cores:addr=addr_base+4*t_p;data=struct.unpack('<I',controller.read(addr,4,t_x,t_y))[0];print(hex(data));x=(data&4278190080)>>24;y=(data&16711680)>>16;p=data&65535;assert p==t_p and x==t_x and y==t_y
 @pytest.mark.parametrize('all_targets',[{(1,1):{3,4},(1,0):{5},(0,1):{2}}])
 def test_count_cores_in_state_run(self,controller,all_targets):expected=sum(len(cs) for cs in itervalues(all_targets));assert expected==controller.count_cores_in_state(consts.AppState.run)
 @pytest.mark.parametrize('targets',[{(1,1):{3,4},(1,0):{5}},{(0,1):{2}}])
 def test_get_processor_status(self,controller,targets):
  for (x,y),cores in iteritems(targets):
   with controller(x=x,y=y):
    for p in cores:status=controller.get_processor_status(p);assert status.app_name=='rig_test';assert status.cpu_state is consts.AppState.run;assert status.rt_code is consts.RuntimeException.none
 def test_get_machine(self,live_machine,spinnaker_width,spinnaker_height):
  m=live_machine;assert m.width==spinnaker_width;assert m.height==spinnaker_height;assert len(m.chip_resource_exceptions)<m.width*m.height/2;assert len(m.dead_chips)<m.width*m.height/2;assert len(m.dead_links)<m.width*m.height*6/2
  for x,y in m.chip_resource_exceptions:assert 0<=x<m.width;assert 0<=y<m.height
  for x,y in m.dead_chips:assert 0<=x<m.width;assert 0<=y<m.height;assert (x,y) not in m.chip_resource_exceptions
  for x,y,link in m.dead_links:assert 0<=x<m.width;assert 0<=y<m.height;assert (x,y) not in m.chip_resource_exceptions;assert link in Links
 def test_get_machine_spinn_5(self,live_machine,spinnaker_width,spinnaker_height,is_spinn_5_board):
  m=live_machine;nominal_live_chips=set([(4,7),(5,7),(6,7),(7,7),(3,6),(4,6),(5,6),(6,6),(7,6),(2,5),(3,5),(4,5),(5,5),(6,5),(7,5),(1,4),(2,4),(3,4),(4,4),(5,4),(6,4),(7,4),(0,3),(1,3),(2,3),(3,3),(4,3),(5,3),(6,3),(7,3),(0,2),(1,2),(2,2),(3,2),(4,2),(5,2),(6,2),(0,1),(1,1),(2,1),(3,1),(4,1),(5,1),(0,0),(1,0),(2,0),(3,0),(4,0)]);nominal_dead_chips=set((x,y) for x in range(m.width) for y in range(m.height))-nominal_live_chips;assert nominal_dead_chips.issubset(m.dead_chips)
  for link,(dx,dy) in ((Links.north,(+0,+1)),(Links.west,(-1,+0)),(Links.south_west,(-1,-1)),(Links.south,(+0,-1)),(Links.east,(+1,+0)),(Links.north_east,(+1,+1))):
   for x,y in nominal_live_chips:
    neighbour=x+dx,y+dy
    if neighbour not in nominal_live_chips:assert (x,y,link) in m.dead_links
 @pytest.mark.parametrize('data',[b'Hello, SpiNNaker',b'Bonjour SpiNNaker'])
 def test_sdram_alloc_as_filelike_read_write(self,controller,data):
  with controller(x=1,y=0):mem=controller.sdram_alloc_as_filelike(len(data));assert mem.write(data)==len(data);mem.seek(0);assert mem.read(len(data))==data
 @pytest.mark.parametrize('routes, app_id',[([RoutingTableEntry({Routes.east},65535,4294967295),RoutingTableEntry({Routes.west},4294901760,4294901760)],67)])
 def test_load_and_retrieve_routing_tables(self,controller,routes,app_id):
  with controller(x=0,y=0,app_id=app_id):controller.load_routing_table_entries(routes);loaded=controller.get_routing_table_entries()
  for route in routes:assert (route,app_id,0) in loaded
 def test_app_stop_and_count(self,controller):controller.send_signal(consts.AppSignal.stop);assert controller.count_cores_in_state(consts.AppState.run)==0
class TestMachineController(object):
 'Test the machine controller against the ideal protocol.\n\n        - Check that transmitted packets are sensible.\n        - Check that error codes / correct returns are dealt with correctly.\n    '
 def test_supplied_structs(self):'Check that when struct data is supplied, it is used.';structs={b'test_struct':struct_file.Struct('test_struct',base=3735879680)};structs[b'test_struct'][b'test_field']=struct_file.StructField(b'I',48879,'%d',1234,1);cn=MachineController('localhost',structs=structs);cn.read=mock.Mock();cn.read.return_value=b'\x01\x00\x00\x00';assert cn.read_struct_field('test_struct','test_field',0,0,0)==1;cn.read.assert_called_once_with(3735928559,4,0,0,0)
 def test_send_scp(self):
  'Check that arbitrary SCP commands can be sent using the context\n        system.\n        ';cn=MachineController('localhost');cn._send_scp=mock.Mock(spec_set=[])
  with pytest.raises(TypeError):cn.send_scp(SCPCommands.sver,y=0,p=0)
  with pytest.raises(TypeError):cn.send_scp(SCPCommands.sver,x=0,p=0)
  with pytest.raises(TypeError):cn.send_scp(SCPCommands.sver,x=0,y=0)
  with cn(x=3,y=2,p=0):cn.send_scp(SCPCommands.sver)
  cn._send_scp.assert_called_once_with(3,2,0,SCPCommands.sver)
  with cn(x=3,y=2,p=0):cn.send_scp(SCPCommands.sver,x=4)
  cn._send_scp.assert_called_with(4,2,0,SCPCommands.sver)
  with cn(x=3,y=2,p=0):cn.send_scp(SCPCommands.sver,y=4)
  cn._send_scp.assert_called_with(3,4,0,SCPCommands.sver)
  with cn(x=3,y=2,p=0):cn.send_scp(SCPCommands.sver,p=4)
  cn._send_scp.assert_called_with(3,2,4,SCPCommands.sver)
 def test_get_software_version(self,mock_conn):'Check that the reporting of the software version is correct.\n\n        SCP Layout\n        ----------\n        The command code is: 0 "sver"\n        There are no arguments.\n\n        The returned packet is of form:\n        arg1 : - p2p address in bits 31:16\n               - physical CPU address in bits 15:8\n               - virtual CPU address in bits 7:0\n        arg2 : - version number * 100 in bits 31:16\n               - buffer size (number of extra data bytes that can be included\n                 in an SCP packet) in bits 15:0\n        arg3 : build data in seconds since the Unix epoch.\n        data : String encoding of build information.\n        ';cn=MachineController('localhost');cn._send_scp=mock.Mock();cn._send_scp.return_value=mock.Mock(spec_set=SCPPacket);cn._send_scp.return_value.arg1=(1<<8|2)<<16|3<<8|4;cn._send_scp.return_value.arg2=256<<16|256;cn._send_scp.return_value.arg3=888999;cn._send_scp.return_value.data=b'Hello, World!';sver=cn.get_software_version(0,1,2);assert sver.position==(1,2);assert sver.physical_cpu==3;assert sver.virt_cpu==4;assert sver.version==2.56;assert sver.buffer_size==256;assert sver.build_date==888999;assert sver.version_string=='Hello, World!'
 @pytest.mark.parametrize('size',[128,256])
 def test_scp_data_length(self,size):cn=MachineController('localhost');cn._scp_data_length=None;cn.get_software_version=mock.Mock();cn.get_software_version.return_value=CoreInfo(None,None,None,None,size,None,None);assert cn.scp_data_length==size;cn.get_software_version.assert_called_once_with(0,0)
 @pytest.mark.parametrize('address, data, dtype',[(1610612736,b'Hello, World',DataType.byte),(1610612738,b'Hello, World',DataType.short),(1610612740,b'Hello, World',DataType.word)])
 def test__write(self,mock_conn,address,data,dtype):'Check writing data can be performed correctly.\n\n        SCP Layout\n        ----------\n        Outgoing:\n            cmd_rc : 3\n            arg_1 : address to write to\n            arg_2 : number of bytes to write\n            arg_3 : Type of data to write:\n                        - 0 : byte\n                        - 1 : short\n                        - 2 : word\n                    This only affects the speed of the operation on SpiNNaker.\n\n        Return:\n            cmd_rc : 0x80 -- success\n        ';cn=MachineController('localhost');cn._send_scp=mock.Mock();cn._write(0,1,2,address,data,dtype);call=cn._send_scp.call_args[0];assert call==(0,1,2,SCPCommands.write,address,len(data),int(dtype),data)
 @pytest.mark.parametrize('start_address,data,data_type',[(1610612736,b'\x00',DataType.byte),(1610612737,b'\x00',DataType.byte),(1610612737,b'\x00\x00',DataType.byte),(1610612737,b'\x00\x00\x00\x00',DataType.byte),(1610612736,b'\x00\x00',DataType.short),(1610612738,b'\x00\x00\x00\x00',DataType.short),(1610612740,b'\x00\x00\x00\x00',DataType.word),(1610612737,512*b'\x00\x00\x00\x00',DataType.byte),(1610612738,512*b'\x00\x00\x00\x00',DataType.short),(1610612736,512*b'\x00\x00\x00\x00',DataType.word)])
 def test_write(self,controller_rw_mock,start_address,data,data_type):
  controller_rw_mock.write(start_address,data,x=0,y=1,p=2);segments=[];address=start_address;addresses=[]
  while len(data)>0:addresses.append(address);segments.append(data[0:controller_rw_mock._scp_data_length]);data=data[controller_rw_mock._scp_data_length:];address+=len(segments[-1])
  controller_rw_mock._write.assert_has_calls([mock.call(0,1,2,a,d,data_type) for (a,d) in zip(addresses,segments)])
 @pytest.mark.parametrize('address, data, dtype',[(1610612736,b'Hello, World',DataType.byte),(1610612738,b'Hello, World',DataType.short),(1610612740,b'Hello, World',DataType.word)])
 def test__read(self,address,data,dtype):'Check reading data can be performed correctly.\n\n        SCP Layout\n        ----------\n        Outgoing:\n            cmd_rc : 2\n            arg_1 : address to read from\n            arg_2 : number of bytes to read\n            arg_3 : Type of data to read:\n                        - 0 : byte\n                        - 1 : short\n                        - 2 : word\n                    This only affects the speed of the operation on SpiNNaker.\n\n        Return:\n            cmd_rc : 0x80 -- success\n            data : data read from memory\n        ';cn=MachineController('localhost');cn._send_scp=mock.Mock();cn._send_scp.return_value=mock.Mock(spec_set=SCPPacket);cn._send_scp.return_value.data=data;read=cn._read(0,1,2,address,len(data),dtype);assert cn._send_scp.call_count==1;call=cn._send_scp.call_args[0];assert call==(0,1,2,SCPCommands.read,address,len(data),int(dtype));assert read==data
 @pytest.mark.parametrize('n_bytes, data_type, start_address, n_packets',[(1,DataType.byte,1610612736,1),(3,DataType.byte,1610612736,1),(2,DataType.byte,1610612737,1),(4,DataType.byte,1610612737,1),(2,DataType.short,1610612738,1),(6,DataType.short,1610612738,1),(4,DataType.short,1610612738,1),(4,DataType.word,1610612740,1),(257,DataType.byte,1610612737,2),(511,DataType.byte,1610612737,2),(258,DataType.byte,1610612737,2),(256,DataType.byte,1610612737,1),(258,DataType.short,1610612738,2),(514,DataType.short,1610612738,3),(516,DataType.short,1610612738,3),(256,DataType.word,1610612740,1)])
 def test_read(self,controller_rw_mock,n_bytes,data_type,start_address,n_packets):
  data=controller_rw_mock.read(start_address,n_bytes,x=0,y=0,p=0);assert len(data)==n_bytes;offset=start_address;offsets=[];lens=[]
  while n_bytes>0:offsets+=[offset];lens+=[min((controller_rw_mock._scp_data_length,n_bytes))];offset+=lens[-1];n_bytes-=controller_rw_mock._scp_data_length
  assert len(lens)==len(offsets)==n_packets,'Test is broken';controller_rw_mock._read.assert_has_calls([mock.call(0,0,0,o,l,data_type) for (o,l) in zip(offsets,lens)])
 @pytest.mark.parametrize('iptag, addr, port',[(1,'localhost',54321),(3,'127.0.0.1',65432)])
 def test_iptag_set(self,iptag,addr,port):'Set an IPTag.\n\n        Note: the hostnames picked here should *always* resolve to 127.0.0.1...\n\n        SCP Layout\n        ----------\n        Outgoing:\n            **Always to VCPU0!**\n            cmd_rc : 26\n            arg1 : 0x00010000 | iptag number\n            arg2 : port\n            arg3 : IP address (127.0.0.1 == 0x0100007f)\n        ';cn=MachineController('localhost');cn._send_scp=mock.Mock();cn.iptag_set(iptag,addr,port,x=0,y=1);assert cn._send_scp.call_count==1;call=cn._send_scp.call_args[0];assert call==(0,1,0,SCPCommands.iptag,65536|iptag,port,16777343)
 @pytest.mark.parametrize('iptag',[1,2,3])
 def test_iptag_get(self,iptag):'Check getting an IPTag.\n\n        Outgoing:\n            *Always to VCPU0!**\n            cmd_rc : 26\n            arg1 : 0x00020000 | iptag number\n            arg2 : number of iptags to get (== 1)\n\n        Incoming:\n            cmd_rc : OK\n            data : IPtag in form (4s 6s 3H I 2H B) ->\n                   (ip, "max", port, timeout, flags, count, rx_port,\n                    spin_addr, spin_port)\n\n        The function returns a namedtuple containing the unpacked version of\n        this data.\n        ';data=struct.pack('4s 6s 3H I 2H B',b'\x7f\x00\x00\x01',b''*6,54321,10,17,12,13,14,15);cn=MachineController('localhost');cn._send_scp=mock.Mock();cn._send_scp.return_value=SCPPacket(False,1,0,0,0,0,0,0,0,0,128,0,0,0,0,data);r_iptag=cn.iptag_get(iptag,x=1,y=2);assert cn._send_scp.call_count==1;call=cn._send_scp.call_args[0];assert call==(1,2,0,SCPCommands.iptag,131072|iptag,1);assert r_iptag.addr=='127.0.0.1';assert r_iptag.port==54321;assert r_iptag.timeout==10;assert r_iptag.flags==17;assert r_iptag.count==12;assert r_iptag.rx_port==13;assert r_iptag.spin_addr==14;assert r_iptag.spin_port==15
 @pytest.mark.parametrize('iptag',[1,2,3])
 def test_iptag_clear(self,iptag):'Check clearing IPtags.\n\n        Outgoing:\n            **Always to VCPU0!**\n            cmd_rc : 26\n            arg1 : 0x0003 | iptag number\n        ';cn=MachineController('localhost');cn._send_scp=mock.Mock();cn.iptag_clear(iptag,x=1,y=2);assert cn._send_scp.call_count==1;call=cn._send_scp.call_args[0];assert call==(1,2,0,SCPCommands.iptag,196608|iptag)
 @pytest.mark.parametrize('action,led_action',[(True,LEDAction.on),(False,LEDAction.off),(None,LEDAction.toggle),(None,LEDAction.toggle)])
 @pytest.mark.parametrize('x',[0,1])
 @pytest.mark.parametrize('y',[0,1])
 @pytest.mark.parametrize('led,leds',[(0,[0]),(1,[1]),([2],[2]),([0,1,2],[0,1,2])])
 def test_led_controls(self,action,led_action,x,y,led,leds):'Check setting/clearing/toggling an LED.\n\n        Outgoing:\n            cmd_rc : 25\n            arg1 : (on | off | toggle) << (led * 2)\n        ';cn=MachineController('localhost');cn._send_scp=mock.Mock();cn.set_led(led,x=x,y=y,action=action);assert cn._send_scp.call_count==1;call,kwargs=cn._send_scp.call_args;assert call==(x,y,0,SCPCommands.led);assert kwargs['arg1']==sum(led_action<<led*2 for led in leds)
 @pytest.mark.parametrize('app_id',[30,33])
 @pytest.mark.parametrize('size',[8,200])
 @pytest.mark.parametrize('tag',[0,2])
 @pytest.mark.parametrize('addr',[1728053248,1627389952])
 def test_sdram_alloc_success(self,app_id,size,tag,addr):'Check allocating a region of SDRAM.\n\n        Outgoing:\n            cmd_rc : 28\n            arg1 : app_id << 8 | op code (0)\n            arg2 : size (bytes)\n            arg3 : tag\n        ';cn=MachineController('localhost');cn._send_scp=mock.Mock();cn._send_scp.return_value=SCPPacket(False,1,0,0,0,0,0,0,0,0,128,0,addr,None,None,b'');address=cn.sdram_alloc(size,tag,1,2,app_id=app_id);assert address==addr;cn._send_scp.assert_called_once_with(1,2,0,28,app_id<<8,size,tag)
 @pytest.mark.parametrize('x, y',[(1,3),(5,6)])
 @pytest.mark.parametrize('size',[8,200])
 def test_sdram_alloc_fail(self,x,y,size):
  'Test that sdram_alloc raises an exception when ALLOC fails.';cn=MachineController('localhost');cn._send_scp=mock.Mock();cn._send_scp.return_value=SCPPacket(False,1,0,0,0,0,0,0,0,0,128,0,0,None,None,b'')
  with pytest.raises(SpiNNakerMemoryError) as excinfo:cn.sdram_alloc(size,x=x,y=y,app_id=30)
  assert str((x,y)) in str(excinfo.value);assert str(size) in str(excinfo.value)
 @pytest.mark.parametrize('x, y',[(0,1),(3,4)])
 @pytest.mark.parametrize('app_id',[30,33])
 @pytest.mark.parametrize('size',[8,200])
 @pytest.mark.parametrize('tag',[0,2])
 @pytest.mark.parametrize('addr',[1728053248,1627389952])
 def test_sdram_alloc_and_open(self,app_id,size,tag,addr,x,y):'Test allocing and getting a file-like object returned.';cn=MachineController('localhost');cn._send_scp=mock.Mock();cn._send_scp.return_value=SCPPacket(False,1,0,0,0,0,0,0,0,0,128,0,addr,None,None,b'');fp=cn.sdram_alloc_as_filelike(size,tag,x,y,app_id=app_id);assert fp._start_address==addr;assert fp._end_address==addr+size;assert fp._machine_controller is cn;assert fp._x==x;assert fp._y==y
 @pytest.mark.parametrize('x, y, p',[(0,1,2),(2,5,6)])
 @pytest.mark.parametrize('which_struct, field, expected',[('sv','dbg_addr',0),('sv','status_map',(0,)*20)])
 def test_read_struct_field(self,x,y,p,which_struct,field,expected):
  struct_data=pkg_resources.resource_string('rig','boot/sark.struct');structs=struct_file.read_struct_file(struct_data);assert six.b(which_struct) in structs and six.b(field) in structs[six.b(which_struct)],'Test is broken';cn=MachineController('localhost');cn.structs=structs;cn.read=mock.Mock();cn.read.return_value=b'\x00'*struct.calcsize(structs[six.b(which_struct)][six.b(field)].pack_chars)*structs[six.b(which_struct)][six.b(field)].length
  with cn(x=x,y=y,p=p):returned=cn.read_struct_field(which_struct,field)
  assert returned==expected;which_struct=six.b(which_struct);field=six.b(field);assert cn.read.called_once_with(structs[which_struct].base+structs[which_struct][field].offset,struct.calcsize(structs[which_struct][field].pack_chars),x,y,p)
 @pytest.mark.parametrize('x, y, p, vcpu_base',[(0,0,5,1736441856),(1,0,5,0),(3,2,10,16711935)])
 @pytest.mark.parametrize('field, data, converted',[('app_name',b'rig_test\x00\x00\x00\x00\x00\x00\x00\x00','rig_test'),('cpu_flags',b'\x08',8)])
 def test_read_vcpu_struct(self,x,y,p,vcpu_base,field,data,converted):
  struct_data=pkg_resources.resource_string('rig','boot/sark.struct');structs=struct_file.read_struct_file(struct_data);vcpu_struct=structs[b'vcpu'];assert six.b(field) in vcpu_struct,'Test is broken';field_=vcpu_struct[six.b(field)]
  def mock_read_struct_field(struct_name,field,x,y,p=0):
   if six.b(struct_name)==b'sv' and six.b(field)==b'vcpu_base':return vcpu_base
   assert False,'Unexpected struct field read.'
  cn=MachineController('localhost');cn.read_struct_field=mock.Mock();cn.read_struct_field.side_effect=mock_read_struct_field;cn.structs=structs;cn.read=mock.Mock();cn.read.return_value=data;assert cn.read_vcpu_struct_field(field,x,y,p)==converted;cn.read.assert_called_once_with(vcpu_base+vcpu_struct.size*p+field_.offset,len(data),x,y)
 @pytest.mark.parametrize('x, y, p, vcpu_base',[(0,1,11,1736446516),(1,4,17,858984720)])
 def test_get_processor_status(self,x,y,p,vcpu_base):
  struct_data=pkg_resources.resource_string('rig','boot/sark.struct');structs=struct_file.read_struct_file(struct_data);vcpu_struct=structs[b'vcpu']
  def mock_read_struct_field(struct_name,field,x,y,p=0):
   if six.b(struct_name)==b'sv' and six.b(field)==b'vcpu_base':return vcpu_base
   assert False,'Unexpected struct field read.'
  cn=MachineController('localhost');cn.read_struct_field=mock.Mock();cn.read_struct_field.side_effect=mock_read_struct_field;cn.structs=structs;cn.read=mock.Mock();vcpu_struct.update_default_values(r0=0,r1=1,r2=2,r3=3,r4=4,r5=5,r6=6,r7=7,psr=8,sp=9,lr=10,rt_code=int(consts.RuntimeException.api_startup_failure),cpu_flags=12,cpu_state=int(consts.AppState.sync0),app_id=30,app_name=b'Hello World!\x00\x00\x00\x00');cn.read.return_value=vcpu_struct.pack()
  with cn(x=x,y=y,p=p):ps=cn.get_processor_status()
  cn.read_struct_field.assert_called_once_with('sv','vcpu_base',x,y);cn.read.assert_called_once_with(vcpu_base+vcpu_struct.size*p,vcpu_struct.size,x,y);assert isinstance(ps,ProcessorStatus);assert ps.registers==[0,1,2,3,4,5,6,7];assert ps.program_state_register==8;assert ps.stack_pointer==9;assert ps.link_register==10;assert ps.cpu_flags==12;assert ps.cpu_state is consts.AppState.sync0;assert ps.app_id==30;assert ps.app_name=='Hello World!';assert ps.rt_code is consts.RuntimeException.api_startup_failure
 @pytest.mark.parametrize('n_args',[0,3])
 def test_flood_fill_aplx_args_fails(self,n_args):
  'Test that calling flood_fill_aplx with an invalid number of\n        arguments raises a TypeError.\n        ';cn=MachineController('localhost')
  with pytest.raises(TypeError):cn.flood_fill_aplx(*[0]*n_args)
  with pytest.raises(TypeError):cn.load_application(*[0]*n_args)
 def test_get_next_nn_id(self):
  cn=MachineController('localhost')
  for i in range(1,127):assert cn._get_next_nn_id()==2*i
  assert cn._get_next_nn_id()==2
 @pytest.mark.parametrize('app_id, wait, cores',[(31,False,[1,2,3]),(12,True,[5])])
 @pytest.mark.parametrize('present_map',[False,True])
 def test_flood_fill_aplx_single_aplx(self,cn,aplx_file,app_id,wait,cores,present_map):
  'Test loading a single APLX to a set of cores.';BASE_ADDRESS=1754267648;cn._send_scp=mock.Mock();cn.read_struct_field=mock.Mock();cn.read_struct_field.return_value=BASE_ADDRESS;targets={(0,1):set(cores)}
  with cn(app_id=app_id,wait=wait):
   if present_map:cn.flood_fill_aplx({aplx_file:targets})
   else:cn.flood_fill_aplx(aplx_file,targets)
  cn.read_struct_field.assert_called_once_with('sv','sdram_sys',0,0);coremask=0
  for c in cores:coremask|=1<<c
  with open(aplx_file,'rb') as f:aplx_data=f.read()
  n_blocks=(len(aplx_data)+cn._scp_data_length-1)//cn._scp_data_length;assert cn._send_scp.call_count==n_blocks+2;x,y,p,cmd,arg1,arg2,arg3=cn._send_scp.call_args_list[0][0];assert x==y==p==0;assert cmd==SCPCommands.nearest_neighbour_packet;op=(arg1&4278190080)>>24;assert op==NNCommands.flood_fill_start;blocks=(arg1&65280)>>8;assert blocks==n_blocks;assert arg2==regions.get_region_for_chip(0,1,level=3);assert arg3&2147483648;assert arg3&65280==NNConstants.forward<<8;assert arg3&255==NNConstants.retry;address=BASE_ADDRESS
  for n in range(0,n_blocks):block_data,aplx_data=aplx_data[:cn._scp_data_length],aplx_data[cn._scp_data_length:];x_,y_,p_,cmd,arg1,arg2,arg3,data=cn._send_scp.call_args_list[n+1][0];assert x_==x and y_==y and p_==p;assert cmd==SCPCommands.flood_fill_data;assert arg1&4278190080==NNConstants.forward<<24;assert arg1&16711680==NNConstants.retry<<16;assert arg2&16711680==n<<16;assert arg2&65280==len(data)//4-1<<8;assert arg3==address;assert data==block_data;address+=len(data)
  x_,y_,p_,cmd,arg1,arg2,arg3=cn._send_scp.call_args_list[-1][0];assert x_==x and y_==y and p_==p;assert cmd==SCPCommands.nearest_neighbour_packet;print(hex(NNCommands.flood_fill_end<<24));assert arg1&4278190080==NNCommands.flood_fill_end<<24;assert arg2&4278190080==app_id<<24;assert arg2&262143==coremask;exp_flags=0
  if wait:exp_flags|=consts.AppFlags.wait
  assert arg2&16515072==exp_flags<<18
 def test_load_and_check_aplxs(self):
  'Test that APLX loading takes place multiple times if one of the\n        chips fails to be placed in the wait state.\n        ';cn=MachineController('localhost');cn._send_scp=mock.Mock();cn.flood_fill_aplx=mock.Mock();cn.read_vcpu_struct_field=mock.Mock();cn.send_signal=mock.Mock();app_id=27;targets={(0,1):{2,4}};failed_targets={(0,1,4)};faileds={(0,1):{4}}
  def read_struct_field(fn,x,y,p):
   if (x,y,p) in failed_targets:failed_targets.remove((x,y,p));return consts.AppState.idle
   else:return consts.AppState.wait
  cn.read_vcpu_struct_field.side_effect=read_struct_field
  with cn(app_id=app_id):cn.load_application('test.aplx',targets,wait=True)
  cn.flood_fill_aplx.assert_has_calls([mock.call({'test.aplx':targets},app_id=app_id,wait=True),mock.call({'test.aplx':faileds},app_id=app_id,wait=True)]);cn.read_vcpu_struct_field.assert_has_calls([mock.call('cpu_state',x,y,p) for ((x,y),ps) in iteritems(targets) for p in ps]+[mock.call('cpu_state',x,y,p) for ((x,y),ps) in iteritems(faileds) for p in ps]);assert not cn.send_signal.called
 def test_load_and_check_aplxs_no_wait(self):
  'Test that APLX loading takes place multiple times if one of the\n        chips fails to be placed in the wait state.\n        ';cn=MachineController('localhost');cn._send_scp=mock.Mock();cn.flood_fill_aplx=mock.Mock();cn.read_vcpu_struct_field=mock.Mock();cn.send_signal=mock.Mock();app_id=27;targets={(0,1):{2,4}};failed_targets={(0,1,4)};faileds={(0,1):{4}}
  def read_struct_field(fn,x,y,p):
   if (x,y,p) in failed_targets:failed_targets.remove((x,y,p));return consts.AppState.idle
   else:return consts.AppState.wait
  cn.read_vcpu_struct_field.side_effect=read_struct_field
  with cn(app_id=app_id):cn.load_application({'test.aplx':targets})
  cn.flood_fill_aplx.assert_has_calls([mock.call({'test.aplx':targets},app_id=app_id,wait=True),mock.call({'test.aplx':faileds},app_id=app_id,wait=True)]);cn.read_vcpu_struct_field.assert_has_calls([mock.call('cpu_state',x,y,p) for ((x,y),ps) in iteritems(targets) for p in ps]+[mock.call('cpu_state',x,y,p) for ((x,y),ps) in iteritems(faileds) for p in ps]);cn.send_signal.assert_called_once_with(consts.AppSignal.start,app_id)
 def test_load_and_check_aplxs_fails(self):
  'Test that APLX loading takes place multiple times if one of the\n        chips fails to be placed in the wait state.\n        ';cn=MachineController('localhost');cn._send_scp=mock.Mock();cn.flood_fill_aplx=mock.Mock();cn.read_vcpu_struct_field=mock.Mock();cn.send_signal=mock.Mock();app_id=27;targets={(0,1):{2,4}};failed_targets={(0,1,4)}
  def read_struct_field(fn,x,y,p):
   if (x,y,p) in failed_targets:return consts.AppState.idle
   else:return consts.AppState.wait
  cn.read_vcpu_struct_field.side_effect=read_struct_field
  with cn(app_id=app_id):
   with pytest.raises(SpiNNakerLoadingError) as excinfo:cn.load_application({'test.aplx':targets})
  assert '(0, 1, 4)' in str(excinfo.value)
 def test_send_signal_fails(self):
  'Test that we refuse to send diagnostic signals which need treating\n        specially.\n        ';cn=MachineController('localhost')
  with pytest.raises(ValueError):cn.send_signal(consts.AppDiagnosticSignal.AND)
 @pytest.mark.parametrize('app_id',[16,30])
 @pytest.mark.parametrize('signal',[consts.AppSignal.sync0,consts.AppSignal.timer,consts.AppSignal.start])
 def test_send_signal_one_target(self,app_id,signal):
  cn=MachineController('localhost');cn._send_scp=mock.Mock()
  with cn(app_id=app_id):cn.send_signal(signal)
  assert cn._send_scp.call_count==1;cargs=cn._send_scp.call_args[0];assert cargs[:3]==(0,0,0);cmd,arg1,arg2,arg3=cargs[3:8];assert cmd==SCPCommands.signal;assert arg1==consts.signal_types[signal];assert arg2&255==app_id;assert arg2&65280==65280;assert arg2&16711680==signal<<16;assert arg3==65535
 @pytest.mark.parametrize('app_id, count',[(16,3),(30,68)])
 @pytest.mark.parametrize('state',[consts.AppState.idle,consts.AppState.run])
 def test_count_cores_in_state(self,app_id,count,state):
  cn=MachineController('localhost');cn._send_scp=mock.Mock();cn._send_scp.return_value=mock.Mock(spec_set=SCPPacket);cn._send_scp.return_value.arg1=count
  with cn(app_id=app_id):assert cn.count_cores_in_state(state)==count
  assert cn._send_scp.call_count==1;cargs=cn._send_scp.call_args[0];assert cargs[:3]==(0,0,0);cmd,arg1,arg2,arg3=cargs[3:8];assert cmd==SCPCommands.signal;assert arg1==consts.diagnostic_signal_types[consts.AppDiagnosticSignal.count];assert arg2&255==app_id;assert arg2&65280==65280;assert arg2&983040==state<<16;assert arg2&3145728==consts.AppDiagnosticSignal.count<<20;assert arg2&62914560==1<<22;assert arg2&201326592==0;assert arg3==65535
 @pytest.mark.parametrize('x, y, app_id',[(1,2,32),(4,10,17)])
 @pytest.mark.parametrize('entries',[[RoutingTableEntry({Routes.east},4294901760,4294901760),RoutingTableEntry({Routes.west},4294705152,4294963200),RoutingTableEntry({Routes.north_east},4294705152,4294963200)]])
 @pytest.mark.parametrize('base_addr, rtr_base',[(1736441856,3)])
 def test_load_routing_table_entries(self,x,y,app_id,entries,base_addr,rtr_base):
  cn=MachineController('localhost');cn._send_scp=mock.Mock();cn._send_scp.return_value=SCPPacket(False,1,0,0,0,0,0,0,0,0,128,128,rtr_base,None,None,b'');temp_mem=tempfile.TemporaryFile();cn.write=mock.Mock();cn.write.side_effect=lambda addr,data,x,y:temp_mem.write(data);cn.read_struct_field=mock.Mock();cn.read_struct_field.return_value=base_addr
  with cn(x=x,y=y,app_id=app_id):cn.load_routing_table_entries(entries)
  cn._send_scp.assert_any_call(x,y,0,SCPCommands.alloc_free,app_id<<8|consts.AllocOperations.alloc_rtr,len(entries));cn.read_struct_field.assert_called_once_with('sv','sdram_sys',x,y);temp_mem.seek(0);rte_data=temp_mem.read();i=0
  while len(rte_data)>0:
   entry_data,rte_data=rte_data[:16],rte_data[16:];next,free,route,key,mask=struct.unpack('<2H 3I',entry_data);assert next==i;assert free==0;assert key==entries[i].key and mask==entries[i].mask;exp_route=0
   for r in entries[i].route:exp_route|=1<<r
   assert exp_route==route;i+=1
  cn._send_scp.assert_called_with(x,y,0,SCPCommands.router,len(entries)<<16|app_id<<8|consts.RouterOperations.load,base_addr,rtr_base)
 def test_load_routing_table_entries_fails(self):
  cn=MachineController('localhost');cn._send_scp=mock.Mock();cn._send_scp.return_value=SCPPacket(False,1,0,0,0,0,0,0,0,0,128,0,0,None,None,b'')
  with pytest.raises(SpiNNakerRouterError) as excinfo:cn.load_routing_table_entries([None]*100,0,4,32)
  assert '100' in str(excinfo.value);assert '(0, 4)' in str(excinfo.value)
 @pytest.mark.parametrize('routing_tables',[{(0,1):[RoutingTableEntry({Routes.core_1},16711680,4294901760)],(1,1):[RoutingTableEntry({Routes.east},16711680,4294901760)]}])
 def test_loading_routing_tables(self,routing_tables):
  cn=MachineController('localhost');cn.load_routing_table_entries=mock.Mock()
  with cn(app_id=69):cn.load_routing_tables(routing_tables)
  cn.load_routing_table_entries.assert_has_calls([mock.call(entries,x=x,y=y,app_id=69) for ((x,y),entries) in iteritems(routing_tables)])
 @pytest.mark.parametrize('x, y',[(0,1),(50,32)])
 @pytest.mark.parametrize('addr, data, expected',[(1728643072,b'\x00\x00B\x03\x01\x00\x00\x00UU\xff\xff\xff\xff\xff\xff'+b'\xff'*1023*16,[(RoutingTableEntry({Routes.east},4294923605,4294967295),66,3)]+[None]*1023),(1661534208,b'\xff'*16+b'\x00\x00B\x03\x01\x00\x00\x00UU\xff\xff\xff\xff\xff\xff'+b'\xff'*1022*16,[None]+[(RoutingTableEntry({Routes.east},4294923605,4294967295),66,3)]+[None]*1022),(1728315392,b'\xff'*1024*16,[None]*1024)])
 def test_get_routing_table_entries(self,x,y,addr,data,expected):
  cn=MachineController('localhost');cn.read_struct_field=mock.Mock();cn.read_struct_field.return_value=addr;cn.read=mock.Mock();cn.read.return_value=data
  with cn(x=x,y=y):assert cn.get_routing_table_entries()==expected
  cn.read_struct_field.assert_called_once_with('sv','rtr_copy',x,y);cn.read.assert_called_once_with(addr,1024*16,x,y)
 def test_get_p2p_routing_table(self):
  cn=MachineController('localhost');w,h=10,15
  def read_struct_field(struct,field,x,y):assert struct=='sv';assert field=='p2p_dims';assert x==0;assert y==0;return w<<8|h
  cn.read_struct_field=mock.Mock();cn.read_struct_field.side_effect=read_struct_field;p2p_table_len=256*256//8*4;reads=set()
  def read(addr,length,x,y):assert consts.SPINNAKER_RTR_P2P<=addr;assert addr<consts.SPINNAKER_RTR_P2P+p2p_table_len;assert length==(h+7)//8*4;assert x==0;assert y==0;reads.add(addr);return struct.pack('<I',sum(i<<3*i for i in range(8)))*(length//4)
  cn.read=mock.Mock();cn.read.side_effect=read;p2p_table=cn.get_p2p_routing_table(x=0,y=0);assert set(consts.SPINNAKER_RTR_P2P+x*256//8*4 for x in range(w))==reads;assert set(p2p_table)==set((x,y) for x in range(w) for y in range(h))
  for (x,y),entry in iteritems(p2p_table):word_offset=y%8;desired_entry=consts.P2PTableEntry(word_offset);assert entry==desired_entry
 @pytest.mark.parametrize('links',[set(),set([Links.north,Links.south]),set(Links)])
 def test_get_working_links(self,links):cn=MachineController('localhost');cn.read_struct_field=mock.Mock();cn.read_struct_field.return_value=sum(1<<l for l in links);assert cn.get_working_links(x=0,y=0)==links;assert cn.read_struct_field.called_once_with('sv','link_up',0,0,0)
 @pytest.mark.parametrize('num_cpus',[1,18])
 def test_get_num_working_cores(self,num_cpus):cn=MachineController('localhost');cn.read_struct_field=mock.Mock();cn.read_struct_field.return_value=num_cpus;assert cn.get_num_working_cores(x=0,y=0)==num_cpus;assert cn.read_struct_field.called_once_with('sv','num_cpus',0,0,0)
 def test_get_machine(self):
  cn=MachineController('localhost');sdram_heap=1617166336;sdram_sys=1736441856;sysram_heap=3841986816;vcpu_base=3842011136
  def read_struct_field(struct_name,field_name,x,y,p=0):return {('sv','sdram_heap'):sdram_heap,('sv','sdram_sys'):sdram_sys,('sv','sysram_heap'):sysram_heap,('sv','vcpu_base'):vcpu_base}[(struct_name,field_name)]
  cn.read_struct_field=mock.Mock();cn.read_struct_field.side_effect=read_struct_field;cn.get_p2p_routing_table=mock.Mock();cn.get_p2p_routing_table.return_value={(x,y):consts.P2PTableEntry.north if x<8 and y<8 and (x,y)!=(3,3) else consts.P2PTableEntry.none for x in range(256) for y in range(256)}
  def get_num_working_cores(x,y):return 18 if (x,y)!=(2,2) else 3
  cn.get_num_working_cores=mock.Mock();cn.get_num_working_cores.side_effect=get_num_working_cores
  def get_working_links(x,y):
   if (x,y)!=(4,4):return set(Links)
   else:return set(Links)-set([Links.north])
  cn.get_working_links=mock.Mock();cn.get_working_links.side_effect=get_working_links;m=cn.get_machine();assert isinstance(m,Machine);assert m.width==8;assert m.height==8;assert m.chip_resources=={Cores:18,SDRAM:sdram_sys-sdram_heap,SRAM:vcpu_base-sysram_heap};assert m.chip_resource_exceptions=={(2,2):{Cores:3,SDRAM:sdram_sys-sdram_heap,SRAM:vcpu_base-sysram_heap}};assert m.dead_chips==set([(3,3)]);assert m.dead_links==set([(4,4,Links.north)]);cn.read_struct_field.assert_has_calls([mock.call('sv','sdram_heap',0,0),mock.call('sv','sdram_sys',0,0),mock.call('sv','sysram_heap',0,0),mock.call('sv','vcpu_base',0,0)],any_order=True);cn.get_p2p_routing_table.assert_called_once_with(0,0);cn.get_num_working_cores.assert_has_calls([mock.call(x,y) for x in range(8) for y in range(8) if (x,y)!=(3,3)],any_order=True);cn.get_working_links.assert_has_calls([mock.call(x,y) for x in range(8) for y in range(8) if (x,y)!=(3,3)],any_order=True)
class TestMemoryIO(object):
 'Test the SDRAM file-like object.'
 @pytest.mark.parametrize('x, y',[(1,3),(3,0)])
 @pytest.mark.parametrize('start_address',[1610612736,1627389952])
 @pytest.mark.parametrize('lengths',[[100,200],[100],[300,128,32]])
 def test_read(self,mock_controller,x,y,start_address,lengths):
  sdram_file=MemoryIO(mock_controller,x,y,start_address,start_address+500);assert sdram_file.tell()==0;calls=[];offset=0
  for n_bytes in lengths:sdram_file.read(n_bytes);assert sdram_file.tell()==offset+n_bytes;assert sdram_file.address==start_address+offset+n_bytes;calls.append(mock.call(start_address+offset,n_bytes,x,y,0));offset=offset+n_bytes
  mock_controller.read.assert_has_calls(calls)
 @pytest.mark.parametrize('x, y',[(1,3),(3,0)])
 @pytest.mark.parametrize('start_address, length, offset',[(1610612736,100,25),(1627389952,4,0)])
 def test_read_no_parameter(self,mock_controller,x,y,start_address,length,offset):sdram_file=MemoryIO(mock_controller,x,y,start_address,start_address+length);sdram_file.seek(offset);sdram_file.read();mock_controller.read.assert_called_one_with(start_address+offset,length-offset,x,y,0)
 def test_read_beyond(self,mock_controller):sdram_file=MemoryIO(mock_controller,0,0,start_address=0,end_address=10);sdram_file.read(100);mock_controller.read.assert_called_with(0,10,0,0,0);assert sdram_file.read(1)==b'';assert mock_controller.read.call_count==1
 @pytest.mark.parametrize('x, y',[(4,2),(255,1)])
 @pytest.mark.parametrize('start_address',[1610612740,1627389955])
 @pytest.mark.parametrize('lengths',[[100,200],[100],[300,128,32]])
 def test_write(self,mock_controller,x,y,start_address,lengths):
  sdram_file=MemoryIO(mock_controller,x,y,start_address,start_address+500);assert sdram_file.tell()==0;calls=[];offset=0
  for i,n_bytes in enumerate(lengths):n_written=sdram_file.write(chr(i%256)*n_bytes);assert n_written==n_bytes;assert sdram_file.tell()==offset+n_bytes;assert sdram_file.address==start_address+offset+n_bytes;calls.append(mock.call(start_address+offset,chr(i%256)*n_bytes,x,y,0));offset=offset+n_bytes
  mock_controller.write.assert_has_calls(calls)
 def test_write_beyond(self,mock_controller):sdram_file=MemoryIO(mock_controller,0,0,start_address=0,end_address=10);assert sdram_file.write(b'\x00\x00'*12)==10;assert sdram_file.write(b'\x00')==0;assert mock_controller.write.call_count==1
 @pytest.mark.parametrize('start_address',[1610612740,1627389955])
 @pytest.mark.parametrize('seeks',[(100,-3,32,5,-7)])
 def test_seek_from_start(self,mock_controller,seeks,start_address):
  sdram_file=MemoryIO(mock_controller,0,0,start_address,start_address+200);assert sdram_file.tell()==0
  for seek in seeks:sdram_file.seek(seek);assert sdram_file.tell()==seek
 @pytest.mark.parametrize('start_address',[1610612740,1627389955])
 @pytest.mark.parametrize('seeks',[(100,-3,32,5,-7)])
 def test_seek_from_current(self,mock_controller,seeks,start_address):
  sdram_file=MemoryIO(mock_controller,0,0,start_address,start_address+200);assert sdram_file.tell()==0;cseek=0
  for seek in seeks:sdram_file.seek(seek,from_what=1);assert sdram_file.tell()==cseek+seek;cseek+=seek
 @pytest.mark.parametrize('start_address, length',[(1610612740,300),(1627389955,250)])
 @pytest.mark.parametrize('seeks',[(100,-3,32,5,-7)])
 def test_seek_from_end(self,mock_controller,seeks,start_address,length):
  sdram_file=MemoryIO(mock_controller,0,0,start_address,start_address+length);assert sdram_file.tell()==0
  for seek in seeks:sdram_file.seek(seek,from_what=2);assert sdram_file.tell()==length-seek
 def test_seek_from_invalid(self,mock_controller):
  sdram_file=MemoryIO(mock_controller,0,0,0,8);assert sdram_file.tell()==0
  with pytest.raises(ValueError):sdram_file.seek(1,from_what=3)
@pytest.mark.parametrize('entry, unpacked',[(b'\x00\x00B\x03\x01\x00\x00\x00UU\xff\xff\xff\xff\xff\xff',(RoutingTableEntry({Routes.east},4294923605,4294967295),66,3)),(b'\x00\x00\x02\x03\x03\x00\x00\x00PU\xff\xff\xf0\xff\xff\xff',(RoutingTableEntry({Routes.east,Routes.north_east},4294923600,4294967280),2,3)),(b'\x00\x00\x03\x02\x03\x00\x00\xffPU\xff\xff\xf0\xff\xff\xff',None)])
def test_unpack_routing_table_entry(entry,unpacked):assert unpack_routing_table_entry(entry)==unpacked
