import pytest
import struct
from mock import Mock
from rig.machine_control import BMPController
from rig.machine_control.bmp_controller import BMPInfo
from rig.machine_control.packets import SCPPacket
from rig.machine_control.consts import SCPCommands,LEDAction,BMPInfoType,BMP_V_SCALE_2_5,BMP_V_SCALE_3_3,BMP_V_SCALE_12,BMP_TEMP_SCALE,BMP_MISSING_TEMP,BMP_MISSING_FAN
from rig.machine_control import consts
@pytest.fixture(scope='module')
def live_controller(bmp_ip):return BMPController(bmp_ip)
@pytest.fixture(scope='module')
def sver_response():return BMPInfo(code_block=1,frame_id=2,can_id=3,board_id=4,version=123/1e2,buffer_size=512,build_date=1234,version_string='Hello, World!')
@pytest.fixture(scope='module',params=['127.0.0.1',{(0,0,0):'127.0.0.1'}])
def bc_mock_sver(request,sver_response):arg1=sver_response.code_block<<24|sver_response.frame_id<<16|sver_response.can_id<<8|sver_response.board_id;version=int(sver_response.version*100);arg2=version<<16|sver_response.buffer_size;arg3=sver_response.build_date;bc=BMPController(request.param);bc._send_scp=Mock();bc._send_scp.return_value=Mock(spec_set=SCPPacket);bc._send_scp.return_value.arg1=arg1;bc._send_scp.return_value.arg2=arg2;bc._send_scp.return_value.arg3=arg3;bc._send_scp.return_value.data=sver_response.version_string.encode('utf-8');return bc
@pytest.mark.order_id('bmp_hw_test')
@pytest.mark.incremental
class TestBMPControllerLive(object):
 'Test the BMP controller against real hardware.'
 def test_scp_data_length(self,live_controller):assert live_controller.scp_data_length>=256
 def test_get_software_version(self,live_controller):sver=live_controller.get_software_version(0,0,0);assert sver.version>=1.3;assert 'BMP' in sver.version_string
 @pytest.mark.order_id('bmp_power_cycle')
 @pytest.mark.no_boot
 def test_power_cycle(self,live_controller):live_controller.set_power(False,board=0);live_controller.set_power(True,board=[0])
 def test_set_led(self,live_controller):live_controller.set_led(range(8),None);live_controller.set_led(range(8),None);live_controller.set_led(7,True);live_controller.set_led(7,False)
 @pytest.mark.order_after('bmp_power_cycle')
 def test_read_write_fpga_reg(self,live_controller):
  PKEY_ADDR=262152
  for fpga_num in range(3):live_controller.write_fpga_reg(fpga_num,PKEY_ADDR,3203334144|fpga_num)
  for fpga_num in range(3):assert live_controller.read_fpga_reg(fpga_num,PKEY_ADDR)==3203334144|fpga_num
 @pytest.mark.order_after('bmp_power_cycle')
 def test_read_adc(self,live_controller):adc=live_controller.read_adc();assert 1.1<adc.voltage_1_2a<1.3 or -.1<adc.voltage_1_2a<.1;assert 1.1<adc.voltage_1_2b<1.3 or -.1<adc.voltage_1_2b<.1;assert 1.1<adc.voltage_1_2c<1.3 or -.1<adc.voltage_1_2c<.1;assert 1.7<adc.voltage_1_8<1.9 or -.1<adc.voltage_1_8<.1;assert 3.2<adc.voltage_3_3<3.4 or -.1<adc.voltage_3_3<.1;assert 10.<adc.voltage_supply<14.;assert 5.<adc.temp_top<1e2;assert 5.<adc.temp_btm<1e2;assert adc.temp_ext_0 is None or 5.<adc.temp_ext_0<1e2;assert adc.temp_ext_1 is None or 5.<adc.temp_ext_1<1e2;assert adc.fan_0 is None or 0.<adc.fan_0<1e4;assert adc.fan_1 is None or 0.<adc.fan_1<1e4
@pytest.mark.order_after('spinnaker_hw_test','bmp_hw_test')
@pytest.mark.no_boot
def test_power_down_on_finished(live_controller):'Power down the system after testing is complete.\n\n    The "order" marking on this test ensures that this test unit will run after\n    all SpiNNaker hardware tests are complete.\n    ';live_controller.set_power(False,board=0)
class TestBMPController(object):
 'Offline tests of the BMPController.'
 def test_single_hostname(self):bc=BMPController('127.0.0.1');assert set(bc.connections)==set([(0,0)]);assert bc.connections[(0,0)].sock.getsockname()[0]=='127.0.0.1'
 def test_connection_selection(self):
  bc=BMPController({});bc._scp_data_length=128;bc.connections={(0,0):Mock(),(0,0,1):Mock(),(0,1,1):Mock(),(1,2,3):Mock()};bc.send_scp(0,cabinet=0,frame=0,board=0);bc.connections[(0,0)].send_scp.assert_called_once_with(128,0,0,0,0);bc.connections[(0,0)].send_scp.reset_mock();bc.send_scp(2,cabinet=0,frame=0,board=2);bc.connections[(0,0)].send_scp.assert_called_once_with(128,0,0,2,2);bc.connections[(0,0)].send_scp.reset_mock();bc.send_scp(1,cabinet=0,frame=0,board=1);bc.connections[(0,0,1)].send_scp.assert_called_once_with(128,0,0,1,1);bc.connections[(0,0,1)].send_scp.reset_mock();bc.send_scp(3,cabinet=0,frame=1,board=1);bc.connections[(0,1,1)].send_scp.assert_called_once_with(128,0,0,1,3);bc.connections[(0,1,1)].send_scp.reset_mock()
  with bc(cabinet=1,frame=2,board=3):bc.send_scp(4)
  bc.connections[(1,2,3)].send_scp.assert_called_once_with(128,0,0,3,4);bc.connections[(1,2,3)].send_scp.reset_mock()
  with pytest.raises(Exception):bc.send_scp(5,cabinet=0,frame=1,board=0)
  with pytest.raises(Exception):bc.send_scp(6,cabinet=3,frame=2,board=1)
 def test_get_software_version(self,bc_mock_sver,sver_response):assert bc_mock_sver.get_software_version()==sver_response
 def test_scp_data_length(self,bc_mock_sver,sver_response):assert bc_mock_sver.scp_data_length==sver_response.buffer_size;assert bc_mock_sver.scp_data_length==sver_response.buffer_size
 def test_set_power(self):bc=BMPController('localhost');bc._send_scp=Mock();bc.set_power(False,0,0,2);arg1=0<<16|0;arg2=1<<2;bc._send_scp.assert_called_once_with(0,0,2,SCPCommands.power,arg1=arg1,arg2=arg2,timeout=0.,expected_args=0);bc._send_scp.reset_mock();bc.set_power(True,0,0,[1,2,4,8],delay=.1,post_power_on_delay=0.);arg1=100<<16|1;arg2=1<<1|1<<2|1<<4|1<<8;bc._send_scp.assert_called_once_with(0,0,1,SCPCommands.power,arg1=arg1,arg2=arg2,timeout=consts.BMP_POWER_ON_TIMEOUT,expected_args=0)
 @pytest.mark.parametrize('board,boards',[(0,[0]),(1,[1]),([2],[2]),([0,1,2],[0,1,2])])
 @pytest.mark.parametrize('action,led_action',[(True,LEDAction.on),(False,LEDAction.off),(None,LEDAction.toggle),(None,LEDAction.toggle)])
 @pytest.mark.parametrize('led,leds',[(0,[0]),(1,[1]),([2],[2]),([0,1,2],[0,1,2])])
 def test_led_controls(self,board,boards,action,led_action,led,leds):'Check setting/clearing/toggling an LED.\n\n        Outgoing:\n            cmd_rc : 25\n            arg1 : (on | off | toggle) << (led * 2)\n        ';bc=BMPController('localhost');bc._send_scp=Mock();bc.set_led(led,action,board=board);assert bc._send_scp.call_count==1;call,kwargs=bc._send_scp.call_args;assert call==(0,0,boards[0],SCPCommands.led);assert kwargs['arg1']==sum(led_action<<led*2 for led in leds);assert kwargs['arg2']==sum(1<<b for b in boards)
 @pytest.mark.parametrize('addr,real_addr',[(0,0),(1,0),(4,4)])
 @pytest.mark.parametrize('fpga_num',[0,1,2])
 def test_read_fpga_reg(self,addr,real_addr,fpga_num):bc=BMPController('localhost');bc._send_scp=Mock();bc._send_scp.return_value=Mock(spec_set=SCPPacket);bc._send_scp.return_value.data=struct.pack('<I',3735928559);assert bc.read_fpga_reg(fpga_num,addr)==3735928559;arg1=real_addr;arg2=4;arg3=fpga_num;bc._send_scp.assert_called_once_with(0,0,0,SCPCommands.link_read,arg1=arg1,arg2=arg2,arg3=arg3,expected_args=0)
 @pytest.mark.parametrize('addr,real_addr',[(0,0),(1,0),(4,4)])
 @pytest.mark.parametrize('fpga_num',[0,1,2])
 def test_write_fpga_reg(self,addr,real_addr,fpga_num):bc=BMPController('localhost');bc._send_scp=Mock();bc.write_fpga_reg(fpga_num,addr,3735928559);arg1=real_addr;arg2=4;arg3=fpga_num;bc._send_scp.assert_called_once_with(0,0,0,SCPCommands.link_write,arg1=arg1,arg2=arg2,arg3=arg3,data=struct.pack('<I',3735928559),expected_args=0)
 @pytest.mark.parametrize('t_ext0,t_ext0_raw',[(35.,int(35./BMP_TEMP_SCALE)),(None,BMP_MISSING_TEMP)])
 @pytest.mark.parametrize('t_ext1,t_ext1_raw',[(25.,int(25./BMP_TEMP_SCALE)),(None,BMP_MISSING_TEMP)])
 @pytest.mark.parametrize('fan_0,fan_0_raw',[(1000,1000),(None,BMP_MISSING_FAN)])
 @pytest.mark.parametrize('fan_1,fan_1_raw',[(1000,1000),(None,BMP_MISSING_FAN)])
 def test_read_adc(self,t_ext0,t_ext0_raw,t_ext1,t_ext1_raw,fan_0,fan_0_raw,fan_1,fan_1_raw):bc=BMPController('localhost');bc._send_scp=Mock();bc._send_scp.return_value=Mock(spec_set=SCPPacket);bc._send_scp.return_value.data=struct.pack('<8H4h4h4hII',0,int(1.1/BMP_V_SCALE_2_5),int(1.2/BMP_V_SCALE_2_5),int(1.3/BMP_V_SCALE_2_5),int(1.8/BMP_V_SCALE_2_5),0,int(3.3/BMP_V_SCALE_3_3),int(12./BMP_V_SCALE_12),int(40./BMP_TEMP_SCALE),int(30./BMP_TEMP_SCALE),0,0,t_ext0_raw,t_ext1_raw,0,0,fan_0_raw,fan_1_raw,0,0,0,0);adc=bc.read_adc();bc._send_scp.assert_called_once_with(0,0,0,SCPCommands.bmp_info,arg1=BMPInfoType.adc,expected_args=0);assert abs(adc.voltage_1_2a-1.3)<.01;assert abs(adc.voltage_1_2b-1.2)<.01;assert abs(adc.voltage_1_2c-1.1)<.01;assert abs(adc.voltage_1_8-1.8)<.01;assert abs(adc.voltage_3_3-3.3)<.01;assert abs(adc.voltage_supply-12.)<.01;assert abs(adc.temp_top-40.)<.01;assert abs(adc.temp_btm-30.)<.01;assert adc.temp_ext_0 is t_ext0 or abs(adc.temp_ext_0-t_ext0)<.01;assert adc.temp_ext_1 is t_ext1 or abs(adc.temp_ext_1-t_ext1)<.01;assert adc.fan_0 is fan_0 or abs(adc.fan_0-fan_0)<.01;assert adc.fan_1 is fan_1 or abs(adc.fan_1-fan_1)<.01
