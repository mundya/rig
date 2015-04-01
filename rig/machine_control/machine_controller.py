'A high level interface for controlling a SpiNNaker system.'
import collections
import os
import six
from six import iteritems
import socket
import struct
import time
import pkg_resources
from . import struct_file
from .consts import SCPCommands,DataType,NNCommands,NNConstants,AppFlags,LEDAction
from . import boot,consts,regions
from .scp_connection import SCPConnection
from rig import routing_table
from rig.machine import Cores,SDRAM,SRAM,Links,Machine
from rig.utils.contexts import ContextMixin,Required
class MachineController(ContextMixin):
 'A high-level interface for controlling a SpiNNaker system.\n\n    This class is essentially a wrapper around key functions provided by the\n    SCP protocol which aims to straight-forwardly handle many of the difficult\n    details and corner cases to ensure easy, efficient and reliable\n    communication with a machine.\n\n    Key features at a glance:\n\n    * Machine booting\n    * Probing for available resources\n    * (Efficient & reliable) loading of applications\n    * Application monitoring and control\n    * Allocation and loading of routing tables\n    * Allocation and loading of memory\n    * An optional file-like interface to memory blocks\n    * Setting up IPTags\n    * Easy-to-use blocking API\n\n    Coming soon:\n\n    * (Additional) \'advanced\' non-blocking, parallel I/O interface\n    * (Automagically) handling multiple connections simultaneously\n\n    This class features a context system which allows commonly required\n    arguments to be specified for a whole block of code using a \'with\'\n    statement, for example::\n\n        cm = MachineController("spinnaker")\n\n        # Commands should refer to chip (2, 3)\n        with cm(x=2, y=3):\n            three_kb_of_joy = cm.sdram_alloc(3*1024)\n            cm.write(three_kb_of_joy, b"joy" * 1024)\n            core_one_status = cm.get_processor_status(1)\n\n    '
 def __init__(self,initial_host,scp_port=consts.SCP_PORT,boot_port=consts.BOOT_PORT,n_tries=5,timeout=.5,structs=None,initial_context={'app_id':66}):
  'Create a new controller for a SpiNNaker machine.\n\n        Parameters\n        ----------\n        initial_host : string\n            Hostname or IP address of the SpiNNaker chip to connect to. If the\n            board has not yet been booted, this will become chip (0, 0).\n        scp_port : int\n            Port number for SCP connections.\n        boot_port : int\n            Port number for booting the board.\n        n_tries : int\n            Number of SDP packet retransmission attempts.\n        timeout : float\n            Timeout in seconds before an SCP response is assumed lost and the\n            request is retransmitted.\n        structs : dict or None\n            A dictionary of struct data defining the memory locations of\n            important values in SARK as produced by\n            :py:class:`rig.machine_control.struct_file.read_struct_file`. If\n            None, the default struct file will be used.\n        initial_context : `{argument: value}`\n            Default argument values to pass to methods in this class. By\n            default this just specifies a default App-ID.\n        ';ContextMixin.__init__(self,initial_context);self.initial_host=initial_host;self.scp_port=scp_port;self.boot_port=boot_port;self.n_tries=n_tries;self.timeout=timeout;self._nn_id=0;self._scp_data_length=None;self.structs=structs
  if self.structs is None:struct_data=pkg_resources.resource_string('rig','boot/sark.struct');self.structs=struct_file.read_struct_file(struct_data)
  self.connections=[SCPConnection(initial_host,scp_port,n_tries,timeout)]
 def __call__(self,**context_args):'For use with `with`: set default argument values.\n\n        E.g::\n\n            with controller(x=3, y=4):\n                # All commands in this block now communicate with chip (3, 4)\n        ';return self.get_new_context(**context_args)
 @property
 def scp_data_length(self):
  'The maximum SCP data field length supported by the machine\n        (bytes).\n        '
  if self._scp_data_length is None:data=self.get_software_version(0,0);self._scp_data_length=data.buffer_size
  return self._scp_data_length
 @ContextMixin.use_named_contextual_arguments(x=Required,y=Required,p=Required)
 def send_scp(self,*args,**kwargs):'Transmit an SCP Packet and return the response.\n\n        This function is a thin wrapper around\n        :py:meth:`~rig.machine_control.scp_connection.SCPConnection`.\n\n        Future versions of this command will automatically choose the most\n        appropriate connection to use for machines with more than one Ethernet\n        connection.\n\n        Parameters\n        ----------\n        x : int\n        y : int\n        p : int\n        *args\n        **kwargs\n        ';x=kwargs.pop('x');y=kwargs.pop('y');p=kwargs.pop('p');return self._send_scp(x,y,p,*args,**kwargs)
 def _send_scp(self,x,y,p,*args,**kwargs):
  'Determine the best connection to use to send an SCP packet and use\n        it to transmit.\n\n        This internal version of the method is identical to send_scp except it\n        has positional arguments for x, y and p.\n\n        See the arguments for\n        :py:meth:`~rig.machine_control.scp_connection.SCPConnection` for\n        details.\n        '
  if self._scp_data_length is None:length=consts.SCP_SVER_RECEIVE_LENGTH_MAX
  else:length=self._scp_data_length
  return self.connections[0].send_scp(length,x,y,p,*args,**kwargs)
 def boot(self,width,height,**boot_kwargs):"Boot a SpiNNaker machine of the given size.\n\n        The system will be booted from the chip whose hostname was given as the\n        argument to the MachineController.\n\n        This method is a thin wrapper around\n        :py:func:`rig.machine_control.boot.boot`.\n\n        After booting, the structs in this MachineController will be set to\n        those used to boot the machine.\n\n        .. warning::\n            This function does not check that the system has been booted\n            successfully. This can be checked by ensuring that\n            :py:meth:`.MachineController.get_software_version` returns a\n            sensible value.\n\n        .. warning::\n            If the system has already been booted, this command will not cause\n            the system to 'reboot' using the supplied firmware.\n\n        .. warning::\n            Booting the system over the open internet is likely to fail due to\n            the port number being blocked by most ISPs and UDP not being\n            reliable. A proxy such as `spinnaker_proxy\n            <https://github.com/project-rig/spinnaker_proxy>`_ may be useful in\n            this situation.\n\n        Parameters\n        ----------\n        width : int\n            Width of the machine (0 < w < 256)\n        height : int\n            Height of the machine (0 < h < 256)\n\n        Notes\n        -----\n        The constants `rig.machine_control.boot.spinX_boot_options` can be used\n        to specify boot parameters, for example::\n\n            controller.boot(**spin3_boot_options)\n\n        This is neccessary on boards such as SpiNN-3 boards if the more than\n        LED 0 are required by an application since by default, only LED 0 is\n        enabled.\n        ";boot_kwargs.setdefault('boot_port',self.boot_port);self.structs=boot.boot(self.initial_host,width=width,height=height,**boot_kwargs);assert len(self.structs)>0
 @ContextMixin.use_contextual_arguments
 def get_software_version(self,x=Required,y=Required,processor=0):'Get the software version for a given SpiNNaker core.\n\n        Returns\n        -------\n        :py:class:`.CoreInfo`\n            Information about the software running on a core.\n        ';sver=self._send_scp(x,y,processor,SCPCommands.sver);p2p=sver.arg1>>16;p2p_address=p2p>>8,p2p&255;pcpu=sver.arg1>>8&255;vcpu=sver.arg1&255;version=(sver.arg2>>16)/1e2;buffer_size=sver.arg2&65535;return CoreInfo(p2p_address,pcpu,vcpu,version,buffer_size,sver.arg3,sver.data.decode('utf-8'))
 @ContextMixin.use_contextual_arguments
 def write(self,address,data,x=Required,y=Required,p=0):
  'Write a bytestring to an address in memory.\n\n        It is strongly encouraged to only read and write to blocks of memory\n        allocated using :py:meth:`.sdram_alloc`. Additionally,\n        :py:meth:`.sdram_alloc_as_filelike` can be used to safely wrap\n        read/write access to memory with a file-like interface and prevent\n        accidental access to areas outside the allocated block.\n\n        Parameters\n        ----------\n        address : int\n            The address at which to start writing the data. Addresses are given\n            within the address space of a SpiNNaker core. See the SpiNNaker\n            datasheet for more information.\n        data : :py:class:`bytes`\n            Data to write into memory. Writes are automatically broken into a\n            sequence of SCP write commands.\n        ';end=len(data);pos=0
  while pos<end:block=data[pos:pos+self.scp_data_length];block_size=len(block);dtype=address_length_dtype[(address%4,block_size%4)];self._write(x,y,p,address,block,dtype);address+=block_size;pos+=block_size
 def _write(self,x,y,p,address,data,data_type=DataType.byte):"Write an SCP command's worth of data to an address in memory.\n\n        It is better to use :py:func:`~.write` which wraps this method and\n        allows writing bytestrings of arbitrary length.\n\n        Parameters\n        ----------\n        address : int\n            The address at which to start writing the data.\n        data : :py:class:`bytes`\n            Data to write into memory.  Must be <= the amount accepted by the\n            receiving core.\n        data_type : :py:class:`~rig.machine_control.consts.DataType`\n            The size of the data to write into memory.\n        ";length_bytes=len(data);self._send_scp(x,y,p,SCPCommands.write,address,length_bytes,int(data_type),data,expected_args=0)
 @ContextMixin.use_contextual_arguments
 def read(self,address,length_bytes,x=Required,y=Required,p=0):
  'Read a bytestring from an address in memory.\n\n        Parameters\n        ----------\n        address : int\n            The address at which to start reading the data.\n        length_bytes : int\n            The number of bytes to read from memory. Large reads are\n            transparently broken into multiple SCP read commands.\n\n        Returns\n        -------\n        :py:class:`bytes`\n            The data is read back from memory as a bytestring.\n        ';data=bytearray(b'\x00'*length_bytes);pos=0
  while pos<length_bytes:reads=min(self.scp_data_length,length_bytes-pos);dtype=address_length_dtype[(address%4,reads%4)];data[pos:pos+reads]=self._read(x,y,p,address,reads,dtype);address+=reads;pos+=reads
  return bytes(data)
 def _read(self,x,y,p,address,length_bytes,data_type=DataType.byte):"Read an SCP command's worth of data from an address in memory.\n\n        It is better to use :py:func:`~.read` which wraps this method and\n        allows reading bytestrings of arbitrary length.\n\n        Parameters\n        ----------\n        address : int\n            The address at which to start reading the data.\n        length_bytes : int\n            The number of bytes to read from memory, must be <=\n            :py:attr:`.scp_data_length`\n        data_type : DataType\n            The size of the data to write into memory.\n\n        Returns\n        -------\n        :py:class:`bytes`\n            The data is read back from memory as a bytestring.\n        ";read_scp=self._send_scp(x,y,p,SCPCommands.read,address,length_bytes,int(data_type),expected_args=0);return read_scp.data
 @ContextMixin.use_contextual_arguments
 def read_struct_field(self,struct_name,field_name,x=Required,y=Required,p=0):
  'Read the value out of a struct maintained by SARK.\n\n        This method is particularly useful for reading fields from the ``sv``\n        struct which, for example, holds information about system status. See\n        ``sark.h`` for details.\n\n        Parameters\n        ----------\n        struct_name : string\n            Name of the struct to read from, e.g., `"sv"`\n        field_name : string\n            Name of the field to read, e.g., `"eth_addr"`\n\n        Returns\n        -------\n        value\n            The value returned is unpacked given the struct specification.\n\n            Currently arrays are returned as tuples, e.g.::\n\n                # Returns a 20-tuple.\n                cn.read_struct_field("sv", "status_map")\n\n                # Fails\n                cn.read_struct_field("sv", "status_map[1]")\n        ';field=self.structs[six.b(struct_name)][six.b(field_name)];address=self.structs[six.b(struct_name)].base+field.offset;pack_chars=b'<'+field.length*field.pack_chars;length=struct.calcsize(pack_chars);data=self.read(address,length,x,y,p);unpacked=struct.unpack(pack_chars,data)
  if field.length==1:return unpacked[0]
  else:return unpacked
 @ContextMixin.use_contextual_arguments
 def read_vcpu_struct_field(self,field_name,x=Required,y=Required,p=Required):
  'Read a value out of the VCPU struct for a specific core.\n\n        Similar to :py:meth:`.read_struct_field` except this method accesses\n        the individual VCPU struct for to each core and contains application\n        runtime status.\n\n        Parameters\n        ----------\n        field_name : string\n            Name of the field to read from the struct (e.g. `"cpu_state"`)\n\n        Returns\n        -------\n        value\n            A value of the type contained in the specified struct field.\n        ';vcpu_struct=self.structs[b'vcpu'];field=vcpu_struct[six.b(field_name)];address=self.read_struct_field('sv','vcpu_base',x,y)+vcpu_struct.size*p+field.offset;pack_chars=b'<'+field.pack_chars;length=struct.calcsize(pack_chars);data=self.read(address,length,x,y);unpacked=struct.unpack(pack_chars,data)
  if field.length==1:return unpacked[0]
  else:
   if b's' in pack_chars:return unpacked[0].strip(b'\x00').decode('utf-8')
   return unpacked
 @ContextMixin.use_contextual_arguments
 def get_processor_status(self,p=Required,x=Required,y=Required):
  'Get the status of a given core and the application executing on it.\n\n        Returns\n        -------\n        :py:class:`.ProcessorStatus`\n            Representation of the current state of the processor.\n        ';address=self.read_struct_field('sv','vcpu_base',x,y)+self.structs[b'vcpu'].size*p;data=self.read(address,self.structs[b'vcpu'].size,x,y);state={name.decode('utf-8'):struct.unpack(f.pack_chars,data[f.offset:f.offset+struct.calcsize(f.pack_chars)])[0] for (name,f) in iteritems(self.structs[b'vcpu'].fields)};state['registers']=[state.pop('r{}'.format(i)) for i in range(8)];state['user_vars']=[state.pop('user{}'.format(i)) for i in range(4)];state['app_name']=state['app_name'].strip(b'\x00').decode('utf-8');state['cpu_state']=consts.AppState(state['cpu_state']);state['rt_code']=consts.RuntimeException(state['rt_code'])
  for newname,oldname in [('iobuf_address','iobuf'),('program_state_register','psr'),('stack_pointer','sp'),('link_register','lr')]:state[newname]=state.pop(oldname)
  state.pop('__PAD');return ProcessorStatus(**state)
 @ContextMixin.use_contextual_arguments
 def iptag_set(self,iptag,addr,port,x=Required,y=Required):'Set the value of an IPTag.\n\n        Forward SDP packets with the specified IP tag sent by a SpiNNaker\n        application to a given external IP address.\n\n        Parameters\n        ----------\n        iptag : int\n            Index of the IPTag to set\n        addr : string\n            IP address or hostname that the IPTag should point at.\n        port : int\n            UDP port that the IPTag should direct packets to.\n        ';ip_addr=struct.pack('!4B',*map(int,socket.gethostbyname(addr).split('.')));self._send_scp(x,y,0,SCPCommands.iptag,int(consts.IPTagCommands.set)<<16|iptag,port,struct.unpack('<I',ip_addr)[0])
 @ContextMixin.use_contextual_arguments
 def iptag_get(self,iptag,x=Required,y=Required):'Get the value of an IPTag.\n\n        Parameters\n        ----------\n        iptag : int\n            Index of the IPTag to get\n\n        Returns\n        -------\n        :py:class:`.IPTag`\n            The IPTag returned from SpiNNaker.\n        ';ack=self._send_scp(x,y,0,SCPCommands.iptag,int(consts.IPTagCommands.get)<<16|iptag,1,expected_args=0);return IPTag.from_bytestring(ack.data)
 @ContextMixin.use_contextual_arguments
 def iptag_clear(self,iptag,x=Required,y=Required):'Clear an IPTag.\n\n        Parameters\n        ----------\n        iptag : int\n            Index of the IPTag to clear.\n        ';self._send_scp(x,y,0,SCPCommands.iptag,int(consts.IPTagCommands.clear)<<16|iptag)
 @ContextMixin.use_contextual_arguments
 def set_led(self,led,action=None,x=Required,y=Required):
  'Set or toggle the state of an LED.\n\n        .. note::\n            By default, SARK takes control of LED 0 and so changes to this LED\n            will not typically last long enough to be useful.\n\n        Parameters\n        ----------\n        led : int or iterable\n            Number of the LED or an iterable of LEDs to set the state of (0-3)\n        action : bool or None\n            State to set the LED to. True for on, False for off, None to\n            toggle (default).\n        '
  if isinstance(led,int):leds=[led]
  else:leds=led
  arg1=sum(LEDAction.from_bool(action)<<led*2 for led in leds);self._send_scp(x,y,0,SCPCommands.led,arg1=arg1,expected_args=0)
 @ContextMixin.use_contextual_arguments
 def sdram_alloc(self,size,tag=0,x=Required,y=Required,app_id=Required):
  'Allocate a region of SDRAM for an application.\n\n        Requests SARK to allocate a block of SDRAM for an application. This\n        allocation will be freed when the application is stopped.\n\n        Parameters\n        ----------\n        size : int\n            Number of bytes to attempt to allocate in SDRAM.\n        tag : int\n            8-bit (chip-wide) tag that can be looked up by a SpiNNaker\n            application to discover the address of the allocated block.  If `0`\n            then no tag is applied.\n\n        Returns\n        -------\n        int\n            Address of the start of the region.\n\n        Raises\n        ------\n        SpiNNakerMemoryError\n            If the memory cannot be allocated, the tag is already taken or it\n            is invalid.\n        ';assert 0<=tag<256;arg1=app_id<<8|consts.AllocOperations.alloc_sdram;rv=self._send_scp(x,y,0,SCPCommands.alloc_free,arg1,size,tag)
  if rv.arg1==0:raise SpiNNakerMemoryError(size,x,y)
  return rv.arg1
 @ContextMixin.use_contextual_arguments
 def sdram_alloc_as_filelike(self,size,tag=0,x=Required,y=Required,app_id=Required):'Like :py:meth:`.sdram_alloc` but returns a file-like object which\n        allows safe reading and writing to the block that is allocated.\n\n        Returns\n        -------\n        :py:class:`.MemoryIO`\n            File-like object which allows accessing the newly allocated region\n            of memory.\n\n        Raises\n        ------\n        SpiNNakerMemoryError\n            If the memory cannot be allocated, or the tag is already taken or\n            invalid.\n        ';start_address=self.sdram_alloc(size,tag,x,y,app_id);return MemoryIO(self,x,y,start_address,start_address+size)
 def _get_next_nn_id(self):'Get the next nearest neighbour ID.';self._nn_id=self._nn_id+1 if self._nn_id<126 else 1;return self._nn_id*2
 def _send_ffs(self,pid,region,n_blocks,fr):'Send a flood-fill start packet.';sfr=fr|1<<31;self._send_scp(0,0,0,SCPCommands.nearest_neighbour_packet,NNCommands.flood_fill_start<<24|pid<<16|n_blocks<<8,region,sfr)
 def _send_ffd(self,pid,aplx_data,address):
  'Send flood-fill data packets.';block=0;pos=0;aplx_size=len(aplx_data)
  while pos<aplx_size:data=aplx_data[pos:pos+self.scp_data_length];data_size=len(data);size=data_size//4-1;arg1=NNConstants.forward<<24|NNConstants.retry<<16|pid;arg2=block<<16|size<<8;self._send_scp(0,0,0,SCPCommands.flood_fill_data,arg1,arg2,address,data);block+=1;address+=data_size;pos+=data_size
 def _send_ffe(self,pid,app_id,app_flags,cores,fr):'Send a flood-fill end packet.';arg1=NNCommands.flood_fill_end<<24|pid;arg2=app_id<<24|app_flags<<18|cores&16383;self._send_scp(0,0,0,SCPCommands.nearest_neighbour_packet,arg1,arg2,fr)
 @ContextMixin.use_named_contextual_arguments(app_id=Required,wait=True)
 def flood_fill_aplx(self,*args,**kwargs):
  'Unreliably flood-fill APLX to a set of application cores.\n\n        .. note::\n            Most users should use the :py:meth:`.load_application` wrapper\n            around this method which guarantees successful loading.\n\n        This method can be called in either of the following ways::\n\n            flood_fill_aplx("/path/to/app.aplx", {(x, y): {core, ...}, ...})\n            flood_fill_aplx({"/path/to/app.aplx": {(x, y): {core, ...}, ...},\n                             ...})\n\n        Note that the latter format is the same format produced by\n        :py:func:`~rig.place_and_route.util.build_application_map`.\n\n        .. warning::\n            The loading process is likely, but not guaranteed, to succeed.\n            This is because the flood-fill packets used during loading are not\n            guaranteed to arrive. The effect of this is one of the following:\n\n            * Some regions may be included/excluded incorrectly.\n            * Some chips will not receive the complete application binary and\n              will silently not execute the binary.\n\n            As a result, the user is responsible for checking that each core\n            was successfully loaded with the correct binary. At present, the\n            two recommended approaches to this are:\n\n            * The user should check that the correct number of application\n              binaries reach their initial barrier (SYNC0), when this facility\n              is used. This is not fool-proof but will flag up all but\n              situations where exactly the right number, but the wrong\n              selection of cores were loaded. (At the time of writing, this\n              situation is not possible but will become a concern in future\n              versions of SC&MP.\n            * The user can check the process list of each chip to ensure the\n              application was loaded into the correct set of cores.\n\n        Parameters\n        ----------\n        app_id : int\n        wait : bool (Default: True)\n            Should the application await the AppSignal.start signal after it\n            has been loaded?\n        ';application_map={}
  if len(args)==1:application_map=args[0]
  elif len(args)==2:application_map={args[0]:args[1]}
  else:raise TypeError('flood_fill_aplx: accepts either 1 or 2 positional arguments: a map of filenames to targets OR a single filename and itstargets')
  app_id=kwargs.pop('app_id');flags=0
  if kwargs.pop('wait'):flags|=AppFlags.wait
  fr=NNConstants.forward<<8|NNConstants.retry
  for aplx,targets in iteritems(application_map):
   fills=regions.compress_flood_fill_regions(targets)
   with open(aplx,'rb+') as f:aplx_data=f.read()
   n_blocks=(len(aplx_data)+self.scp_data_length-1)//self.scp_data_length
   for region,cores in fills:pid=self._get_next_nn_id();self._send_ffs(pid,region,n_blocks,fr);base_address=self.read_struct_field('sv','sdram_sys',0,0);self._send_ffd(pid,aplx_data,base_address);self._send_ffe(pid,app_id,flags,cores,fr)
 @ContextMixin.use_named_contextual_arguments(app_id=Required,n_tries=2,wait=False,app_start_delay=.1)
 def load_application(self,*args,**kwargs):
  'Load an application to a set of application cores.\n\n        This method guarantees that once it returns, all required cores will\n        have been loaded. If this is not possible after a small number of\n        attempts, an exception will be raised.\n\n        This method can be called in either of the following ways::\n\n            load_application("/path/to/app.aplx", {(x, y): {core, ...}, ...})\n            load_application({"/path/to/app.aplx": {(x, y): {core, ...}, ...},\n                              ...})\n\n        Note that the latter format is the same format produced by\n        :py:func:`~rig.place_and_route.util.build_application_map`.\n\n        Parameters\n        ----------\n        app_id : int\n        wait : bool\n            Leave the application in a wait state after successfully loading\n            it.\n        n_tries : int\n            Number attempts to make to load the application.\n        app_start_delay : float\n            Time to pause (in seconds) after loading to ensure that the\n            application successfully reaches the wait state before checking for\n            success.\n        ';app_id=kwargs.pop('app_id');wait=kwargs.pop('wait');n_tries=kwargs.pop('n_tries');app_start_delay=kwargs.pop('app_start_delay');application_map={}
  if len(args)==1:application_map=args[0]
  elif len(args)==2:application_map={args[0]:args[1]}
  else:raise TypeError('load_application: accepts either 1 or 2 positional arguments:a map of filenames to targets OR a single filename and itstargets')
  unloaded=application_map;tries=0
  while unloaded!={} and tries<=n_tries:
   tries+=1;self.flood_fill_aplx(unloaded,app_id=app_id,wait=True);time.sleep(app_start_delay);new_unloadeds=dict()
   for app_name,targets in iteritems(unloaded):
    unloaded_targets={}
    for (x,y),cores in iteritems(targets):
     unloaded_cores=set()
     for p in cores:
      state=consts.AppState(self.read_vcpu_struct_field('cpu_state',x,y,p))
      if state is not consts.AppState.wait:unloaded_cores.add(p)
     if len(unloaded_cores)>0:unloaded_targets[(x,y)]=unloaded_cores
    if len(unloaded_targets)>0:new_unloadeds[app_name]=unloaded_targets
   unloaded=new_unloadeds
  if unloaded!={}:raise SpiNNakerLoadingError(unloaded)
  if not wait:self.send_signal(consts.AppSignal.start,app_id)
 @ContextMixin.use_contextual_arguments
 def send_signal(self,signal,app_id=Required):
  "Transmit a signal to applications.\n\n        .. warning::\n            In current implementations of SARK, signals are highly likely to\n            arrive but this is not guaranteed (especially when the system's\n            network is heavily utilised). Users should treat this mechanism\n            with caution.\n\n        Parameters\n        ----------\n        signal : :py:class:`~rig.machine_control.consts.AppSignal`\n            Signal to transmit.\n        "
  if signal not in consts.AppSignal:raise ValueError('send_signal: Cannot transmit signal of type {}'.format(signal))
  arg1=consts.signal_types[signal];arg2=signal<<16|65280|app_id;arg3=65535;self._send_scp(0,0,0,SCPCommands.signal,arg1,arg2,arg3)
 @ContextMixin.use_contextual_arguments
 def count_cores_in_state(self,state,app_id=Required):"Count the number of cores in a given state.\n\n        .. warning::\n            In current implementations of SARK, signals (which are used to\n            determine the state of cores) are highly likely to arrive but this\n            is not guaranteed (especially when the system's network is heavily\n            utilised). Users should treat this mechanism with caution.\n\n        Parameters\n        ----------\n        state : :py:class:`~rig.machine_control.consts.AppState`\n            Count the number of cores currently in this state.\n        ";region=65535;level=region>>16&3;mask=region&65535;arg1=consts.diagnostic_signal_types[consts.AppDiagnosticSignal.count];arg2=level<<26|1<<22|consts.AppDiagnosticSignal.count<<20|state<<16|255<<8|app_id;arg3=mask;return self._send_scp(0,0,0,SCPCommands.signal,arg1,arg2,arg3).arg1
 @ContextMixin.use_contextual_arguments
 def load_routing_tables(self,routing_tables,app_id=Required):
  'Allocate space for an load multicast routing tables.\n\n        The routing table entries will be removed automatically when the\n        associated application is stopped.\n\n        Parameters\n        ----------\n        routing_tables : {(x, y):                           [:py:class:`~rig.routing_table.RoutingTableEntry`                           (...), ...], ...}\n            Map of chip co-ordinates to routing table entries, as produced, for\n            example by\n            :py:func:`~rig.place_and_route.util.build_routing_tables`.\n\n        Raises\n        ------\n        SpiNNakerRouterError\n            If it is not possible to allocate sufficient routing table entries.\n        '
  for (x,y),table in iteritems(routing_tables):self.load_routing_table_entries(table,x=x,y=y,app_id=app_id)
 @ContextMixin.use_contextual_arguments
 def load_routing_table_entries(self,entries,x=Required,y=Required,app_id=Required):
  'Allocate space for and load multicast routing table entries into the\n        router of a SpiNNaker chip.\n\n        .. note::\n            This method only loads routing table entries for a single chip.\n            Most users should use :py:meth:`.load_routing_tables` which loads\n            routing tables to multiple chips.\n\n        Parameters\n        ----------\n        entries : [:py:class:`~rig.routing_table.RoutingTableEntry`(...), ...]\n            List of :py:class:`rig.routing_table.RoutingTableEntry`\\ s.\n\n        Raises\n        ------\n        SpiNNakerRouterError\n            If it is not possible to allocate sufficient routing table entries.\n        ';count=len(entries);rv=self._send_scp(x,y,0,SCPCommands.alloc_free,app_id<<8|consts.AllocOperations.alloc_rtr,count);rtr_base=rv.arg1
  if rtr_base==0:raise SpiNNakerRouterError(count,x,y)
  buf=self.read_struct_field('sv','sdram_sys',x,y);data=b''
  for i,entry in enumerate(entries):
   route=0
   for r in entry.route:route|=1<<r
   data+=struct.pack(consts.RTE_PACK_STRING,i,0,route,entry.key,entry.mask)
  self.write(buf,data,x,y);self._send_scp(x,y,0,SCPCommands.router,count<<16|app_id<<8|consts.RouterOperations.load,buf,rtr_base)
 @ContextMixin.use_contextual_arguments
 def get_routing_table_entries(self,x=Required,y=Required):
  'Dump the multicast routing table of a given chip.\n\n        Returns\n        -------\n        [(:py:class:`~rig.routing_table.RoutingTableEntry`, app_id, core)           or None, ...]\n            Ordered list of routing table entries with app_ids and\n            core numbers.\n        ';rtr_addr=self.read_struct_field('sv','rtr_copy',x,y);read_size=struct.calcsize(consts.RTE_PACK_STRING);rtr_data=self.read(rtr_addr,consts.RTR_ENTRIES*read_size,x,y);table=list()
  while len(rtr_data)>0:entry,rtr_data=rtr_data[:read_size],rtr_data[read_size:];table.append(unpack_routing_table_entry(entry))
  return table
 @ContextMixin.use_contextual_arguments
 def get_p2p_routing_table(self,x=Required,y=Required):
  "Dump the contents of a chip's P2P routing table.\n\n        This method can be indirectly used to get a list of functioning chips.\n\n        .. note::\n            This method only returns the entries for chips within the bounds of\n            the system. E.g. if booted with 8x8 only entries for these 8x8\n            chips will be returned.\n\n        Returns\n        -------\n        {(x, y): :py:class:`~rig.machine_control.consts.P2PTableEntry`, ...}\n        ";table={};p2p_dims=self.read_struct_field('sv','p2p_dims',x,y);width=p2p_dims>>8&255;height=p2p_dims>>0&255;col_words=(height+7)//8*4
  for col in range(width):
   raw_table_col=self.read(consts.SPINNAKER_RTR_P2P+256*col//8*4,col_words,x,y);row=0
   while row<height:
    raw_word,raw_table_col=raw_table_col[:4],raw_table_col[4:];word,=struct.unpack('<I',raw_word)
    for entry in range(min(8,height-row)):table[(col,row)]=consts.P2PTableEntry(word>>3*entry&7);row+=1
  return table
 @ContextMixin.use_contextual_arguments
 def get_working_links(self,x=Required,y=Required):'Return the set of links reported as working.\n\n        The returned set lists only links over-which nearest neighbour\n        peek/poke commands could be sent. This means that links connected to\n        peripherals may falsely be omitted.\n\n        Returns\n        -------\n        set([:py:class:`rig.machine.Links`, ...])\n        ';link_up=self.read_struct_field('sv','link_up',x,y);return set(link for link in Links if link_up&1<<link)
 @ContextMixin.use_contextual_arguments
 def get_num_working_cores(self,x=Required,y=Required):'Return the number of working cores, including the monitor.';return self.read_struct_field('sv','num_cpus',x,y)
 def get_machine(self,default_num_cores=18):
  'Probe the machine to discover which cores and links are working.\n\n        .. note::\n            Links are reported as dead when the device at the other end of the\n            link does not respond to SpiNNaker nearest neighbour packets. This\n            may thus mistakenly report links attached to peripherals as dead.\n\n        .. note::\n            The probing process does not report how much memory is free, nor\n            how many processors are idle but rather the total available.\n\n        .. note::\n            The size of the SDRAM and SysRAM heaps is assumed to be the same\n            for all chips and is only checked on chip (0, 0).\n\n        Parameters\n        ----------\n        default_num_cores : int\n            The number of cores generally available on a SpiNNaker chip\n            (including the monitor).\n\n        Returns\n        -------\n        :py:class:`~rig.machine.Machine`\n            This Machine will include all cores reported as working by the\n            system software with the following resources defined:\n\n            :py:data:`~rig.machine.Cores`\n                Number of cores working on each chip (including the monitor\n                core).\n            :py:data:`~rig.machine.SDRAM`\n                The size of the SDRAM heap.\n            :py:data:`~rig.machine.SRAM`\n                The size of the SysRAM heap.\n        ';p2p_tables=self.get_p2p_routing_table(0,0);max_x=max(x for ((x,y),r) in iteritems(p2p_tables) if r!=consts.P2PTableEntry.none);max_y=max(y for ((x,y),r) in iteritems(p2p_tables) if r!=consts.P2PTableEntry.none);sdram_start=self.read_struct_field('sv','sdram_heap',0,0);sdram_end=self.read_struct_field('sv','sdram_sys',0,0);sysram_start=self.read_struct_field('sv','sysram_heap',0,0);sysram_end=self.read_struct_field('sv','vcpu_base',0,0);chip_resources={Cores:default_num_cores,SDRAM:sdram_end-sdram_start,SRAM:sysram_end-sysram_start};dead_chips=set();dead_links=set();chip_resource_exceptions={}
  for (x,y),p2p_route in iteritems(p2p_tables):
   if x<=max_x and y<=max_y:
    if p2p_route==consts.P2PTableEntry.none:dead_chips.add((x,y))
    else:
     num_working_cores=self.get_num_working_cores(x,y);working_links=self.get_working_links(x,y)
     if num_working_cores<default_num_cores:resource_exception=chip_resources.copy();resource_exception[Cores]=min(default_num_cores,num_working_cores);chip_resource_exceptions[(x,y)]=resource_exception
     for link in set(Links)-working_links:dead_links.add((x,y,link))
  return Machine(max_x+1,max_y+1,chip_resources,chip_resource_exceptions,dead_chips,dead_links)
class CoreInfo(collections.namedtuple('CoreInfo','position physical_cpu virt_cpu version buffer_size build_date version_string')):'Information returned about a core by sver.\n\n    Parameters\n    ----------\n    position : (x, y)\n        Logical location of the chip in the system.\n    physical_cpu : int\n        The physical ID of the core. (Not useful to most users).\n    virt_cpu : int\n        The virtual ID of the core. This is the number used by all high-level\n        software APIs.\n    version : float\n        Software version number. (Major version is integral part, minor version\n        is fractional part).\n    buffer_size : int\n        Maximum supported size (in bytes) of the data portion of an SCP packet.\n    build_date : int\n        The time at which the software was compiled as a unix timestamp. May be\n        zero if not set.\n    version_string : string\n        Human readable, textual version information split in to two fields by a\n        "/". In the first field is the kernal (e.g. SC&MP or SARK) and the\n        second the hardware platform (e.g. SpiNNaker).\n    '
class ProcessorStatus(collections.namedtuple('ProcessorStatus','registers program_state_register stack_pointer link_register rt_code cpu_flags cpu_state mbox_ap_msg mbox_mp_msg mbox_ap_cmd mbox_mp_cmd sw_count sw_file sw_line time app_name iobuf_address app_id user_vars')):'Information returned about the status of a processor.\n\n    Parameters\n    ----------\n    registers : list\n        Register values dumped during a runtime exception. (All zero by\n        default.)\n    program_status_register : int\n        CPSR register (dumped during a runtime exception and zero by default).\n    stack_pointer : int\n        Stack pointer (dumped during a runtime exception and zero by default).\n    link_register : int\n        Link register (dumped during a runtime exception and zero by default).\n    rt_code : :py:class:`~rig.machine_control.consts.RuntimeException`\n        Code for any run-time exception which may have occurred.\n    cpu_flags : int\n    cpu_state : :py:class:`~rig.machine_control.consts.AppState`\n        Current state of the processor.\n    mbox_ap_msg : int\n    mbox_mp_msg : int\n    mbox_ap_cmd : int\n    mbox_mp_cmd : int\n    sw_count : int\n        Saturating count of software errors.  (Calls to `sw_err`).\n    sw_file : int\n        Pointer to a string containing the file name in which the last software\n        error occurred.\n    sw_line : int\n        Line number of the last software error.\n    time : int\n        Time application was loaded.\n    app_name : string\n        Name of the application loaded to the processor core.\n    iobuf_address : int\n        Address of the output buffer used by the processor.\n    app_id : int\n        ID of the application currently running on the processor.\n    user_vars : list\n        List of 4 integer values that may be set by the user.\n    '
class IPTag(collections.namedtuple('IPTag','addr mac port timeout flags count rx_port spin_addr spin_port')):
 'An IPTag as read from a SpiNNaker machine.\n\n    Parameters\n    ----------\n    addr : str\n        IP address SDP packets are forwarded to\n    mac : int\n    port : int\n        Port number to forward SDP packets to\n    timeout : int\n    count : int\n    rx_port : int\n    spinn_addr : int\n    spinn_port : int\n    '
 @classmethod
 def from_bytestring(cls,bytestring):ip,mac,port,timeout,flags,count,rx_port,spin_addr,spin_port=struct.unpack('<4s 6s 3H I 2H B',bytestring[:25]);ip_addr='.'.join(str(x) for x in struct.unpack('4B',ip));return cls(ip_addr,mac,port,timeout,flags,count,rx_port,spin_addr,spin_port)
address_length_dtype={(i,j):DataType.word if i==j==0 else DataType.short if i%2==j%2==0 else DataType.byte for i in range(4) for j in range(4)}
class SpiNNakerMemoryError(Exception):
 'Raised when it is not possible to allocate memory on a SpiNNaker\n    chip.\n    '
 def __init__(self,size,x,y):self.size=size;self.chip=x,y
 __str__=lambda self:'Failed to allocate {} bytes of SDRAM on chip ({}, {})'.format(self.size,self.chip[0],self.chip[1])
class SpiNNakerRouterError(Exception):
 'Raised when it is not possible to allocated routing table entries on a\n    SpiNNaker chip.\n    '
 def __init__(self,count,x,y):self.count=count;self.chip=x,y
 __str__=lambda self:'Failed to allocate {} routing table entries on chip ({}, {})'.format(self.count,self.chip[0],self.chip[1])
class SpiNNakerLoadingError(Exception):
 'Raised when it has not been possible to load applications to cores.'
 def __init__(self,application_map):self.app_map=application_map
 def __str__(self):
  cores=[]
  for app,targets in iteritems(self.app_map):
   for (x,y),ps in iteritems(targets):
    for p in ps:cores.append('({}, {}, {})'.format(x,y,p))
  return 'Failed to load applications to cores {}'.format(', '.join(cores))
class MemoryIO(object):
 'A file-like view into a subspace of the memory-space of a chip.'
 def __init__(self,machine_controller,x,y,start_address,end_address):'Create a file-like view onto a subset of the memory-space of a chip.\n\n        Parameters\n        ----------\n        machine_controller : :py:class:`~.MachineController`\n            A communicator to handle transmitting and receiving packets from\n            the SpiNNaker machine.\n        x : int\n            x co-ordinate of the chip.\n        y : int\n            y co-ordinate of the chip.\n        start_address : int\n            Starting address in memory.\n        end_address : int\n            End address in memory.\n        ';self._x=x;self._y=y;self._machine_controller=machine_controller;self._start_address=start_address;self._end_address=end_address;self._offset=0
 def read(self,n_bytes=-1):
  'Read a number of bytes from the memory.\n\n        .. note::\n            Reads beyond the specified memory range will be truncated.\n\n        Parameters\n        ----------\n        n_bytes : int\n            A number of bytes to read.  If the number of bytes is negative or\n            omitted then read all data until the end of memory region.\n\n        Returns\n        -------\n        :py:class:`bytes`\n            Data read from SpiNNaker as a bytestring.\n        '
  if n_bytes<0:n_bytes=self._end_address-self.address
  if self.address+n_bytes>self._end_address:
   n_bytes=min(n_bytes,self._end_address-self.address)
   if n_bytes<=0:return b''
  data=self._machine_controller.read(self.address,n_bytes,self._x,self._y,0);self._offset+=n_bytes;return data
 def write(self,bytes):
  'Write data to the memory.\n\n        .. note::\n            Writes beyond the specified memory range will be truncated.\n\n        Parameters\n        ----------\n        bytes : :py:class:`bytes`\n            Data to write to the memory as a bytestring.\n\n        Returns\n        -------\n        int\n            Number of bytes written.\n        '
  if self.address+len(bytes)>self._end_address:
   n_bytes=min(len(bytes),self._end_address-self.address)
   if n_bytes<=0:return 0
   bytes=bytes[:n_bytes]
  self._machine_controller.write(self.address,bytes,self._x,self._y,0);self._offset+=len(bytes);return len(bytes)
 def tell(self):'Get the current offset in the memory region.\n\n        Returns\n        -------\n        int\n            Current offset (starting at 0).\n        ';return self._offset
 @property
 def address(self):'Get the current hardware memory address (indexed from 0x00000000).\n        ';return self._offset+self._start_address
 def seek(self,n_bytes,from_what=os.SEEK_SET):
  'Seek to a new position in the memory region.\n\n        Parameters\n        ----------\n        n_bytes : int\n            Number of bytes to seek.\n        from_what : int\n            As in the Python standard: `0` seeks from the start of the memory\n            region, `1` seeks from the current position and `2` seeks from the\n            end of the memory region. For example::\n\n                mem.seek(-1, 2)  # Goes to the last byte in the region\n                mem.seek(-5, 1)  # Goes 5 bytes before that point\n                mem.seek(0)      # Returns to the start of the region\n\n            Note that `os.SEEK_END`, `os.SEEK_CUR` and `os.SEEK_SET` are also\n            valid arguments.\n        '
  if from_what==0:self._offset=n_bytes
  elif from_what==1:self._offset+=n_bytes
  elif from_what==2:self._offset=self._end_address-self._start_address-n_bytes
  else:raise ValueError('from_what: can only take values 0 (from start), 1 (from current) or 2 (from end) not {}'.format(from_what))
def unpack_routing_table_entry(packed):
 'Unpack a routing table entry read from a SpiNNaker machine.\n\n    Parameters\n    ----------\n    packet : :py:class:`bytes`\n        Bytes containing a packed routing table.\n\n    Returns\n    -------\n    (:py:class:`~rig.routing_table.RoutingTableEntry`, app_id, core) or None\n        Tuple containing the routing entry, the app_id associated with the\n        entry and the core number associated with the entry; or None if the\n        routing table entry is flagged as unused.\n    ';_,free,route,key,mask=struct.unpack(consts.RTE_PACK_STRING,packed)
 if route&4278190080==4278190080:return None
 routes={r for r in routing_table.Routes if route>>r&1};rte=routing_table.RoutingTableEntry(routes,key,mask);app_id=free&255;core=free>>8&15;return rte,app_id,core
