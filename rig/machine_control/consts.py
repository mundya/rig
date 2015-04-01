'Constants used in the SCP protocol.\n'
import enum
from rig.utils.enum_doc import int_enum_doc
BOOT_PORT=54321
'Port used to boot a SpiNNaker machine.'
SCP_PORT=17893
'Port used for SDP communication.'
SDP_HEADER_LENGTH=8
'The number of bytes making up the header of an SDP packet.'
SCP_SVER_RECEIVE_LENGTH_MAX=512
'The smallest power of two large enough to handle that SVER will\nproduce (256 + 8 bytes).\n'
SPINNAKER_RTR_BASE=3774873600
'Base address of router hardware registers.'
SPINNAKER_RTR_P2P=SPINNAKER_RTR_BASE+65536
'Base address of P2P routing table.'
BMP_POWER_ON_TIMEOUT=5.
'Additional timeout for BMP power-on commands to reply.'
BMP_ADC_MAX=1<<12
"The range of values the BMP's 12-bit ADCs can measure."
BMP_V_SCALE_2_5=2.5/BMP_ADC_MAX
'Multiplier to convert from ADC value to volts for lines less than 2.5 V.'
BMP_V_SCALE_3_3=3.75/BMP_ADC_MAX
'Multiplier to convert from ADC value to volts for 3.3 V lines.'
BMP_V_SCALE_12=15./BMP_ADC_MAX
'Multiplier to convert from ADC value to volts for 12 V lines.'
BMP_TEMP_SCALE=1./256.
'Multiplier to convert from temperature probe values to degrees Celsius.'
BMP_MISSING_TEMP=-32768
'Temperature value returned when a probe is not connected.'
BMP_MISSING_FAN=-1
'Fan speed value returned when a fan is absent.'
RTR_ENTRIES=1024
'Number of routing table entries in each routing table.\n'
RTE_PACK_STRING='<2H 3I'
'Packing string used with routing table entries, values are (next, free,\nroute, key, mask).\n'
@int_enum_doc
class SCPCommands(enum.IntEnum):'Command codes used in SCP packets.';sver=0;'Get the software version';read=2;write=3;link_read=17;link_write=18;nearest_neighbour_packet=20;signal=22;flood_fill_data=23;led=25;iptag=26;alloc_free=28;router=29;bmp_info=48;power=57
@int_enum_doc
class DataType(enum.IntEnum):'Used to specify the size of data being read to/from a SpiNNaker machine\n    over SCP.\n    ';byte=0;short=1;word=2
@int_enum_doc
class LEDAction(enum.IntEnum):
 'Indicate the action that should be applied to a given LED.';on=3;off=2;toggle=1
 @classmethod
 def from_bool(cls,action):
  'Maps from a bool or None to toggle.'
  if action is None:return cls.toggle
  elif action:return cls.on
  else:return cls.off
@int_enum_doc
class IPTagCommands(enum.IntEnum):'Indicate the action that should be performed to the given IPTag.';set=1;get=2;clear=3
@int_enum_doc
class AllocOperations(enum.IntEnum):'Used to allocate or free regions of SDRAM and routing table entries.';alloc_sdram=0;free_sdram_by_ptr=1;free_sdram_by_tag=2;alloc_rtr=3;free_rtr_by_pos=4;free_rtr_by_app=5
@int_enum_doc
class RouterOperations(enum.IntEnum):'Operations that may be performed to the router.';init=0;clear=1;load=2;fixed_route_set_get=3
@int_enum_doc
class NNCommands(enum.IntEnum):'Nearest Neighbour operations.';flood_fill_start=6;flood_fill_end=15
@int_enum_doc
class NNConstants(enum.IntEnum):'Constants for use with nearest neighbour commands.';forward=63;retry=24
@int_enum_doc
class AppFlags(enum.IntEnum):'Flags for application loading.';wait=1
@int_enum_doc
class AppState(enum.IntEnum):'States that an application may be in.';dead=0;power_down=1;runtime_exception=2;watchdog=3;init=4;wait=5;c_main=6;run=7;pause=10;exit=11;idle=15;sync0=8;sync1=9
@int_enum_doc
class RuntimeException(enum.IntEnum):'Runtime exceptions as reported by SARK.';none=0;reset=1;undefined_instruction=2;svc=3;prefetch_abort=4;data_abort=5;unhandled_irq=6;unhandled_fiq=7;unconfigured_vic=8;abort=9;malloc_failure=10;division_by_zero=11;event_startup_failure=12;software_error=13;iobuf_failure=14;bad_enable=15;null_pointer=16;pkt_startup_failure=17;timer_startup_failure=18;api_startup_failure=19
@int_enum_doc
class AppSignal(enum.IntEnum):'Signals that may be transmitted to applications.';init=0;power_down=1;stop=2;start=3;pause=6;cont=7;exit=8;timer=9;sync0=4;sync1=5;usr0=10;usr1=11;usr2=12;usr3=13
@int_enum_doc
class AppDiagnosticSignal(enum.IntEnum):'Signals which interrogate the state of a machine.\n\n    Note that a value is returned when any of these signals is sent.\n    ';OR=0;AND=1;count=2
@int_enum_doc
class MessageType(enum.IntEnum):'Internally used to specify the type of a message.';multicast=0;peer_to_peer=1;nearest_neighbour=2
signal_types={AppSignal.init:MessageType.nearest_neighbour,AppSignal.power_down:MessageType.nearest_neighbour,AppSignal.start:MessageType.nearest_neighbour,AppSignal.stop:MessageType.nearest_neighbour,AppSignal.exit:MessageType.nearest_neighbour,AppSignal.sync0:MessageType.multicast,AppSignal.sync1:MessageType.multicast,AppSignal.pause:MessageType.multicast,AppSignal.cont:MessageType.multicast,AppSignal.timer:MessageType.multicast,AppSignal.usr0:MessageType.multicast,AppSignal.usr1:MessageType.multicast,AppSignal.usr2:MessageType.multicast,AppSignal.usr3:MessageType.multicast}
'Mapping from an :py:class:`.AppSignal` to the :py:class:`.MessageType`\nused to transmit it.\n'
diagnostic_signal_types={AppDiagnosticSignal.AND:MessageType.peer_to_peer,AppDiagnosticSignal.OR:MessageType.peer_to_peer,AppDiagnosticSignal.count:MessageType.peer_to_peer}
'Mapping from an :py:class:`.AppDiagnosticSignal` to the\n:py:class:`.MessageType` used to transmit it.\n'
@int_enum_doc
class P2PTableEntry(enum.IntEnum):'Routing table entry in the point-to-point SpiNNaker routing table.';east=0;north_east=1;north=2;west=3;south_west=4;south=5;none=6;monitor=7
@int_enum_doc
class BMPInfoType(enum.IntEnum):'Type of information to return from a bmp_info SCP command.';serial=0;can_status=2;adc=3;ip_addr=4
