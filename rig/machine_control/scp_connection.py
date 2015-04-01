'A blocking implementation of the SCP protocol.\n'
import socket
from . import consts,packets
class SCPConnection(object):
 'Implements the SCP protocol for communicating with a SpiNNaker chip.\n    ';error_codes={}
 def __init__(self,spinnaker_host,port=consts.SCP_PORT,n_tries=5,timeout=.5):'Create a new communicator to handle control of the SpiNNaker chip\n        with the supplied hostname.\n\n        Parameters\n        ----------\n        spinnaker_host : str\n            A IP address or hostname of the SpiNNaker chip to control.\n        port : int\n            Port number to send to.\n        n_tries : int\n            The maximum number of tries to communicate with the chip before\n            failing.\n        timeout : float\n            The timeout to use on the socket.\n        ';self.default_timeout=timeout;self.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);self.sock.settimeout(self.default_timeout);self.sock.connect((spinnaker_host,port));self.n_tries=n_tries;self._seq=0
 @classmethod
 def _register_error(cls,cmd_rc):
  'Register an Exception class as belonging to a certain CMD_RC value.\n        '
  def err_(err):cls.error_codes[cmd_rc]=err;return err
  return err_
 def send_scp(self,buffer_size,x,y,p,cmd,arg1=0,arg2=0,arg3=0,data=b'',expected_args=3,timeout=0.):
  'Transmit a packet to the SpiNNaker machine and block until an\n        acknowledgement is received.\n\n        Parameters\n        ----------\n        buffer_size : int\n            Number of bytes held in an SCP buffer by SARK, determines how many\n            bytes will be expected in a socket.\n        x : int\n        y : int\n        p : int\n        cmd : int\n        arg1 : int\n        arg2 : int\n        arg3 : int\n        data : bytestring\n        expected_args : int\n            The number of arguments (0-3) that are expected in the returned\n            packet.\n        timeout : float\n            Additional timeout in seconds to wait for a reply on top of the\n            default specified upon instantiation.\n\n        Returns\n        -------\n        :py:class:`~rig.machine_control.packets.SCPPacket`\n            The packet that was received in acknowledgement of the transmitted\n            packet.\n        ';self.sock.settimeout(self.default_timeout+timeout);packet=packets.SCPPacket(reply_expected=True,tag=255,dest_port=0,dest_cpu=p,src_port=7,src_cpu=31,dest_x=x,dest_y=y,src_x=0,src_y=0,cmd_rc=cmd,seq=self._seq,arg1=arg1,arg2=arg2,arg3=arg3,data=data);max_length=buffer_size+consts.SDP_HEADER_LENGTH;receive_length=1<<9
  while receive_length<max_length:receive_length<<=1
  n_tries=0
  while n_tries<self.n_tries:
   self.sock.send(b'\x00\x00'+packet.bytestring);n_tries+=1
   try:ack=self.sock.recv(receive_length)
   except IOError:continue
   scp=packets.SCPPacket.from_bytestring(ack[2:],n_args=expected_args)
   if scp.cmd_rc in self.error_codes:raise self.error_codes[scp.cmd_rc]('Packet with arguments: cmd={}, arg1={}, arg2={}, arg3={}; sent to core ({},{},{}) was bad.'.format(cmd,arg1,arg2,arg3,x,y,p))
   if scp.seq==self._seq:self._seq^=1;return scp
  raise TimeoutError('Exceeded {} tries when trying to transmit packet.'.format(self.n_tries))
class SCPError(IOError):'Base Error for SCP return codes.';pass
class TimeoutError(SCPError):'Raised when an SCP is not acknowledged within the given period of time.\n    ';pass
@SCPConnection._register_error(129)
class BadPacketLengthError(SCPError):'Raised when an SCP packet is an incorrect length.';pass
@SCPConnection._register_error(131)
class InvalidCommandError(SCPError):'Raised when an SCP packet contains an invalid command code.';pass
@SCPConnection._register_error(132)
class InvalidArgsError(SCPError):'Raised when an SCP packet has an invalid argument.';pass
@SCPConnection._register_error(135)
class NoRouteError(SCPError):'Raised when there is no route to the requested core.'
