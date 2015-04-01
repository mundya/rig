'Boot constructs for a SpiNNaker machine.\n\n.. warning::\n    Implementation is reconstructed from a Perl implementation which forms a\n    significant part of the documentation for this process.\n'
from . import struct_file,consts
import enum
import pkg_resources
import socket
import struct
import time
from rig.utils.enum_doc import int_enum_doc
DTCM_SIZE=32*1024
BOOT_BYTE_SIZE=1024
BOOT_WORD_SIZE=BOOT_BYTE_SIZE//4
BOOT_MAX_BLOCKS=DTCM_SIZE//BOOT_BYTE_SIZE
BOOT_DATA_OFFSET=3*128
BOOT_DATA_LENGTH=128
spin1_boot_options={'width':2,'height':2,'hardware_version':0,'led_config':483588}
'Boot options for :py:func:`.boot` for SpiNN-1 boards.'
spin2_boot_options={'width':2,'height':2,'hardware_version':2,'led_config':24835}
'Boot options for :py:func:`.boot` for SpiNN-2 boards.'
spin3_boot_options={'width':2,'height':2,'hardware_version':3,'led_config':1282}
'Boot options for :py:func:`.boot` for SpiNN-3 boards.'
spin4_boot_options={'width':8,'height':8,'hardware_version':4,'led_config':1}
'Boot options for :py:func:`.boot` for standalone SpiNN-4 boards.'
spin5_boot_options={'width':8,'height':8,'hardware_version':5,'led_config':1}
'Boot options for :py:func:`.boot` for standalone SpiNN-5 boards.'
def boot(hostname,width,height,boot_port=consts.BOOT_PORT,cpu_frequency=200,hardware_version=0,led_config=1,boot_data=None,structs=None,boot_delay=.05,post_boot_delay=5.):
 'Boot a SpiNNaker machine of the given size.\n\n    Parameters\n    ----------\n    hostname : str\n        Hostname or IP address of the SpiNNaker chip to boot [as chip (0, 0)].\n    width : int\n        Width of the machine (0 < w < 256)\n    height : int\n        Height of the machine (0 < h < 256)\n    cpu_frequency : int\n        CPU clock-frequency.  **Note**: The default (200 MHz) is known\n        safe.\n    hardware_version : int\n        Version number of the SpiNNaker boards used in the system (e.g. SpiNN-5\n        boards would be 5). At the time of writing this value is ignored and\n        can be safely set to the default value of 0.\n    led_config : int\n        Defines LED pin numbers for the SpiNNaker boards used in the system.\n        The four least significant bits (3:0) give the number of LEDs. The next\n        four bits give the pin number of the first LED, the next four the pin\n        number of the second LED, and so forth. At the time of writing, all\n        SpiNNaker board versions have their first LED attached to pin 0 and\n        thus the default value of 0x00000001 is safe.\n    boot_data : bytes or None\n        Data to boot the machine with\n    structs : dict or None\n        The structs to use to supply boot parameters to the machine or None to\n        use the default struct.\n    boot_delay : float\n        Number of seconds to pause between sending boot data packets.\n    post_boot_delay : float\n        Time in seconds to sleep after the boot has finished. This delay is\n        important since after boot it takes some time for P2P routing tables to\n        be built by SARK (order 5 seconds). Before these tables have been\n        assembled, many useful commands will not function.\n\n    Notes\n    -----\n    The constants `rig.machine_control.boot.spinX_boot_options` can be used to\n    specify boot parameters, for example::\n\n        boot("board1", **spin3_boot_options)\n\n    Will boot the Spin3 board connected with hostname "board1".\n\n    Returns\n    -------\n    {struct_name: :py:class:`~rig.machine_control.struct_file.Struct`}\n        Layout of structs in memory.\n    '
 if boot_data is None:boot_data=pkg_resources.resource_string('rig','boot/scamp.boot')
 if structs is None:struct_data=pkg_resources.resource_string('rig','boot/sark.struct');structs=struct_file.read_struct_file(struct_data)
 sv=structs[b'sv'];sv.update_default_values(p2p_dims=width<<8|height,hw_ver=hardware_version,cpu_clk=cpu_frequency,led0=led_config,unix_time=int(time.time()),boot_sig=int(time.time()),root_chip=1);struct_packed=sv.pack();assert len(struct_packed)>=128;buf=bytearray(boot_data);buf[BOOT_DATA_OFFSET:BOOT_DATA_OFFSET+BOOT_DATA_LENGTH]=struct_packed[:BOOT_DATA_LENGTH];assert len(buf)<DTCM_SIZE;boot_data=bytes(buf);sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.connect((hostname,boot_port));n_blocks=(len(buf)+BOOT_BYTE_SIZE-1)//BOOT_BYTE_SIZE;assert n_blocks<=BOOT_MAX_BLOCKS;boot_packet(sock,BootCommand.start,arg3=n_blocks-1);time.sleep(boot_delay);block=0
 while len(boot_data)>0:data,boot_data=boot_data[:BOOT_BYTE_SIZE],boot_data[BOOT_BYTE_SIZE:];a1=BOOT_WORD_SIZE-1<<8|block;boot_packet(sock,BootCommand.send_block,a1,data=data);time.sleep(boot_delay);block+=1
 boot_packet(sock,BootCommand.end,1);sock.close();time.sleep(post_boot_delay);return structs
def boot_packet(sock,cmd,arg1=0,arg2=0,arg3=0,data=b''):
 'Create and transmit a packet to boot the machine.\n\n    Parameters\n    ----------\n    sock : :py:class:`~socket.socket`\n        Connected socket to use to transmit the packet.\n    cmd : int\n    arg1 : int\n    arg2 : int\n    arg3 : int\n    data : :py:class:`bytes`\n        Optional data to include in the packet.\n    ';PROTOCOL_VERSION=1;header=struct.pack('!H4I',PROTOCOL_VERSION,cmd,arg1,arg2,arg3);assert len(data)%4==0;fdata=b''
 while len(data)>0:word,data=data[:4],data[4:];fdata+=struct.pack('!I',struct.unpack('<I',word)[0])
 sock.send(header+fdata)
@int_enum_doc
class BootCommand(enum.IntEnum):'Boot packet command numbers';start=1;'Boot data begin.\n\n    Parameters\n    ----------\n    arg1 : unused\n    arg2 : unused\n    arg3 : int\n        Number of boot data blocks to be sent - 1.\n    ';send_block=3;'Send a block of boot data.\n\n    Parameters\n    ----------\n    arg1 : unused\n        32-bit value with:\n\n        * Bits 7:0 containing the block number being sent.\n        * Bits 31:8 The number of 32-bit words in the block being sent - 1.\n    arg2 : unused\n    arg3 : unused\n    ';end=5;"End of boot data.\n\n    Parameters\n    ----------\n    arg1 : int\n        The value '1'.\n    arg2 : unused\n    arg3 : unused\n    "
