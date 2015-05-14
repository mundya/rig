"""A blocking implementation of the SCP protocol.
"""
import collections
import functools
import math
import six
import socket
import struct
import time
from . import consts
from .packets import SCPPacket


class scpcall(collections.namedtuple("_scpcall", "x, y, p, cmd, arg1, arg2, "
                                                 "arg3, data,  callback, "
                                                 "timeout")):
    """Utility for specifying SCP packets which will be sent using
    :py:meth:`~.SCPConnection.send_scp_burst` and their callbacks.

    ..note::
        The parameters are similar to the parameters for
        :py:class:`~.SCPConnection.send_scp` but for the addition of `callback`
        between `expected_args` and `timeout`.

    Attributes
    ----------
    x : int
    y : int
    p : int
    cmd : int
    arg1 : int
    arg2 : int
    arg3 : int
    data : bytes
    callback : function
        Function which will be called with the packet that acknowledges the
        transmission of this packet.
    timeout : float
        Additional timeout in seconds to wait for a reply on top of the
        default specified upon instantiation.
    """
    def __new__(cls, x, y, p, cmd, arg1=0, arg2=0, arg3=0, data=b'',
                callback=lambda p: None, timeout=0.0):
        return super(scpcall, cls).__new__(
            cls, x, y, p, cmd, arg1, arg2, arg3, data, callback, timeout
        )


class SCPConnection(object):
    """Implements the SCP protocol for communicating with a SpiNNaker chip.
    """
    error_codes = {}

    def __init__(self, spinnaker_host, port=consts.SCP_PORT,
                 n_tries=5, timeout=0.5):
        """Create a new communicator to handle control of the SpiNNaker chip
        with the supplied hostname.

        Parameters
        ----------
        spinnaker_host : str
            A IP address or hostname of the SpiNNaker chip to control.
        port : int
            Port number to send to.
        n_tries : int
            The maximum number of tries to communicate with the chip before
            failing.
        timeout : float
            The timeout to use on the socket.
        """
        self.default_timeout = timeout

        # Create a socket to communicate with the SpiNNaker machine
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(self.default_timeout)
        self.sock.connect((spinnaker_host, port))

        # Store the number of tries that will be allowed
        self.n_tries = n_tries

        # Sequence values
        self.seq = seqs()

    @classmethod
    def _register_error(cls, cmd_rc):
        """Register an Exception class as belonging to a certain CMD_RC value.
        """
        def err_(err):
            cls.error_codes[cmd_rc] = err
            return err
        return err_

    def send_scp(self, buffer_size, x, y, p, cmd, arg1=0, arg2=0, arg3=0,
                 data=b'', expected_args=3, timeout=0.0):
        """Transmit a packet to the SpiNNaker machine and block until an
        acknowledgement is received.

        Parameters
        ----------
        buffer_size : int
            Number of bytes held in an SCP buffer by SARK, determines how many
            bytes will be expected in a socket.
        x : int
        y : int
        p : int
        cmd : int
        arg1 : int
        arg2 : int
        arg3 : int
        data : bytestring
        expected_args : int
            The number of arguments (0-3) that are expected in the returned
            packet.
        timeout : float
            Additional timeout in seconds to wait for a reply on top of the
            default specified upon instantiation.

        Returns
        -------
        :py:class:`~rig.machine_control.packets.SCPPacket`
            The packet that was received in acknowledgement of the transmitted
            packet.
        """
        # This is implemented as a single burst packet sent using the bursty
        # interface.  This significantly reduces code duplication.
        # Construct a callable to retain the returned packet for us
        class Callback(object):
            def __init__(self):
                self.packet = None

            def __call__(self, packet):
                self.packet = SCPPacket.from_bytestring(
                    packet, n_args=expected_args
                )

        # Create the packet to send
        callback = Callback()
        packets = [
            scpcall(x, y, p, cmd, arg1, arg2, arg3, data, callback, timeout)
        ]

        # Send the burst
        self.send_scp_burst(buffer_size, 1, packets)

        # Return the received packet
        assert callback.packet is not None
        return callback.packet

    def send_scp_burst(self, buffer_size, window_size,
                       parameters_and_callbacks):
        """Send a burst of SCP packets and call a callback for each returned
        packet.

        Parameters
        ----------
        buffer_size : int
            Number of bytes held in an SCP buffer by SARK, determines how many
            bytes will be expected in a socket.
        window_size : int
            Number of packets which can be awaiting replies from the SpiNNaker
            board.
        parameters_and_callbacks: iterable of :py:class:`.scpcall`
            Iterable of :py:class:`.scpcall` elements.  These elements can
            specify a callback which will be called with the returned packet.
        """
        parameters_and_callbacks = iter(parameters_and_callbacks)

        # Non-blocking and then the following is a busy loop.
        self.sock.setblocking(False)

        # Calculate the receive length, this should be the smallest power of
        # two greater than the required size
        max_length = buffer_size + consts.SDP_HEADER_LENGTH
        receive_length = int(2**math.ceil(math.log(max_length, 2)))

        class TransmittedPacket(object):
            """A packet which has been transmitted and still awaits a response.
            """
            __slots__ = ["callback", "packet", "n_tries",
                         "time_sent", "extra_timeout"]

            def __init__(self, callback, packet, extra_timeout):
                self.callback = callback
                self.packet = packet
                self.extra_timeout = extra_timeout
                self.n_tries = 1
                self.time_sent = time.time()

        queued_packets = True
        outstanding_packets = {}

        # While there are packets in the queue or packets for which we are
        # still awaiting returns then continue to loop.
        while queued_packets or outstanding_packets:
            # If there are fewer outstanding packets than the window can take
            # and we still might have packets left to send then transmit a
            # packet and add it to the list of outstanding packets.
            if len(outstanding_packets) < window_size and queued_packets:
                try:
                    args = next(parameters_and_callbacks)
                except StopIteration:
                    queued_packets = False

                if queued_packets:
                    # If we extracted a new packet to send then create a new
                    # outstanding packet and transmit it.
                    seq = next(self.seq)
                    while seq in outstanding_packets:
                        # The seq should rarely be already taken, it normally
                        # means that one packet is taking such a long time to
                        # send that the sequence has wrapped around.  It's not
                        # a problem provided that we don't reuse the number.
                        seq = next(self.seq)

                    # Construct the packet that we'll be sending
                    packet = SCPPacket(
                        reply_expected=True, tag=0xff, dest_port=0,
                        dest_cpu=args.p, src_port=7, src_cpu=31,
                        dest_x=args.x, dest_y=args.y, src_x=0, src_y=0,
                        cmd_rc=args.cmd, seq=seq,
                        arg1=args.arg1, arg2=args.arg2, arg3=args.arg3,
                        data=args.data
                    )

                    # Create a reference to this packet so that we know we're
                    # expecting a response for it and can retransmit it if
                    # necessary.
                    outstanding_packets[seq] = TransmittedPacket(
                        args.callback, packet.bytestring, args.timeout)

                    # Actually send the packet
                    self.sock.send(outstanding_packets[seq].packet)

            # Listen on the socket for an acknowledgement packet, there not be
            # one.
            try:
                ack = self.sock.recv(receive_length)
            except IOError:
                # There wasn't a returned packet, we may spend quite some time
                # here.
                ack = None

            # Process the received packet (if there is one)
            if ack is not None:
                # Extract the sequence number from the bytestring, iff possible
                rc, seq = struct.unpack_from("<2H", ack,
                                             consts.SDP_HEADER_LENGTH + 2)

                # If the code is an error then we respond immediately
                if rc in self.error_codes:
                    raise self.error_codes[rc]

                # Look up the sequence index of packet in the list of
                # outstanding packets.  We may have already processed a
                # response for this packet (indicating that the response was
                # delayed and we retransmitted the initial message) in which
                # case we can silently ignore the returned packet.
                # XXX: There is a danger that a response was so delayed that we
                # already reused the seq number... this is probably
                # sufficiently unlikely that there is no problem.
                outstanding = outstanding_packets.pop(seq, None)
                if outstanding is not None:
                    outstanding.callback(ack)

            # Look through all the remaining outstanding packets, if any of
            # them have timed out then we retransmit them.
            current_time = time.time()
            for seq, outstanding in six.iteritems(outstanding_packets):
                if (current_time - outstanding.time_sent >
                        self.default_timeout + outstanding.extra_timeout):
                    # This packet has timed out, if we have sent it more than
                    # the given number of times then raise a timeout error for
                    # it.
                    if outstanding.n_tries >= self.n_tries:
                        raise TimeoutError(self.n_tries)

                    # Otherwise we retransmit it
                    self.sock.send(outstanding.packet)
                    outstanding.n_tries += 1
                    outstanding.time_sent = current_time

    def read(self, buffer_size, window_size, x, y, p, address, length_bytes):
        """Read a bytestring from an address in memory.

        ..note::
            This method is included here to maintain API compatibility with an
            `alternative implementation of SCP
            <https://github.com/project-rig/rig-scp>`_.

        Parameters
        ----------
        buffer_size : int
            Number of bytes held in an SCP buffer by SARK, determines how many
            bytes will be expected in a socket and how many bytes of data will
            be read back in each packet.
        window_size : int
        x : int
        y : int
        p : int
        address : int
            The address at which to start reading the data.
        length_bytes : int
            The number of bytes to read from memory. Large reads are
            transparently broken into multiple SCP read commands.

        Returns
        -------
        :py:class:`bytes`
            The data is read back from memory as a bytestring.
        """
        # Prepare the buffer to receive the incoming data
        data = bytearray(length_bytes)
        mem = memoryview(data)

        # Create a callback which will write the data from a packet into a
        # memoryview.
        def callback(mem, data):
            mem[:] = data[6 + consts.SDP_HEADER_LENGTH:]

        # Create a generator that will generate request packets and store data
        # until all data has been returned
        def packets(length_bytes, data):
            offset = 0
            while length_bytes > 0:
                # Get the next block of data
                block_size = min((length_bytes, buffer_size))
                read_address = address + offset
                dtype = consts.address_length_dtype[(read_address % 4,
                                                     block_size % 4)]

                # Create the call spec and yield
                yield scpcall(
                    x, y, p, consts.SCPCommands.read, read_address,
                    block_size, dtype,
                    callback=functools.partial(callback,
                                               mem[offset:offset + block_size])
                )

                # Update the number of bytes remaining and the offset
                offset += block_size
                length_bytes -= block_size

        # Run the event loop and then return the retrieved data
        self.send_scp_burst(buffer_size, window_size,
                            packets(length_bytes, data))
        return bytes(data)

    def write(self, buffer_size, window_size, x, y, p, address, data):
        """Write a bytestring to an address in memory.

        ..note::
            This method is included here to maintain API compatibility with an
            `alternative implementation of SCP
            <https://github.com/project-rig/rig-scp>`_.

        Parameters
        ----------
        buffer_size : int
            Number of bytes held in an SCP buffer by SARK, determines how many
            bytes will be expected in a socket and how many bytes will be
            written in each packet.
        window_size : int
        x : int
        y : int
        p : int
        address : int
            The address at which to start writing the data. Addresses are given
            within the address space of a SpiNNaker core. See the SpiNNaker
            datasheet for more information.
        data : :py:class:`bytes`
            Data to write into memory. Writes are automatically broken into a
            sequence of SCP write commands.
        """
        # While there is still data perform a write: get the block to write
        # this time around, determine the data type, perform the write and
        # increment the address
        def packets(address, data):
            end = len(data)
            pos = 0
            while pos < end:
                block = data[pos:pos + buffer_size]
                block_size = len(block)

                dtype = consts.address_length_dtype[(address % 4,
                                                     block_size % 4)]

                yield scpcall(x, y, p, consts.SCPCommands.write, address,
                              block_size, dtype, block)

                address += block_size
                pos += block_size

        # Run the event loop and then return the retrieved data
        self.send_scp_burst(buffer_size, window_size, packets(address, data))


def seqs(mask=0xffff):
    i = 0
    while True:
        yield i
        i = (i + 1) & mask


class SCPError(IOError):
    """Base Error for SCP return codes."""
    pass


class TimeoutError(SCPError):
    """Raised when an SCP is not acknowledged within the given period of time.
    """
    pass


@SCPConnection._register_error(0x81)
class BadPacketLengthError(SCPError):
    """Raised when an SCP packet is an incorrect length."""
    pass


@SCPConnection._register_error(0x83)
class InvalidCommandError(SCPError):
    """Raised when an SCP packet contains an invalid command code."""
    pass


@SCPConnection._register_error(0x84)
class InvalidArgsError(SCPError):
    """Raised when an SCP packet has an invalid argument."""
    pass


@SCPConnection._register_error(0x87)
class NoRouteError(SCPError):
    """Raised when there is no route to the requested core."""
