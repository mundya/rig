"""A blocking implementation of the SCP protocol.
"""
import collections
import functools
import six
import socket
import struct
import time
from . import consts, packets


class scpcall(collections.namedtuple("_scpcall", "x, y, p, cmd, arg1, arg2, "
                                                 "arg3, data, expected_args, "
                                                 "callback")):
    """Utility for constructing SCP packets."""
    def __new__(cls, x, y, p, cmd, arg1=0, arg2=0, arg3=0, data=b'',
                expected_args=3, callback=lambda p: None):
        return super(scpcall, cls).__new__(cls, x, y, p, cmd, arg1, arg2, arg3,
                                           data, expected_args, callback)

    @property
    def positional(self):
        """Get positional arguments as a list."""
        return (self.x, self.y, self.p, self.cmd,
                self.arg1, self.arg2, self.arg3, self.data,
                self.expected_args)


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
        self.sock.settimeout(self.default_timeout + timeout)

        # Construct the packet that will be sent
        seq = next(self.seq)
        packet = packets.SCPPacket(
            reply_expected=True, tag=0xff, dest_port=0, dest_cpu=p,
            src_port=7, src_cpu=31, dest_x=x, dest_y=y, src_x=0, src_y=0,
            cmd_rc=cmd, seq=seq, arg1=arg1, arg2=arg2, arg3=arg3,
            data=data
        )

        # Determine how many bytes to listen to on the socket, this should
        # be the smallest power of two greater than the required size (for
        # efficiency reasons).
        max_length = buffer_size + consts.SDP_HEADER_LENGTH
        receive_length = 1 << 9  # 512 bytes is a reasonable minimum
        while receive_length < max_length:
            receive_length <<= 1

        # Repeat until a reply is received or we run out of tries.
        n_tries = 0
        while n_tries < self.n_tries:
            # Transit the packet
            self.sock.send(packet.bytestring)
            n_tries += 1

            try:
                # Try to receive the returned acknowledgement
                ack = self.sock.recv(receive_length)
            except IOError:
                # There was nothing to receive from the socket
                continue

            # Convert the possible returned packet into an SCP packet. If
            # the sequence number matches the expected sequence number then
            # the acknowledgement has been received.
            scp = packets.SCPPacket.from_bytestring(ack, n_args=expected_args)

            # Check that the CMD_RC isn't an error
            if scp.cmd_rc in self.error_codes:
                raise self.error_codes[scp.cmd_rc](
                    "Packet with arguments: cmd={}, arg1={}, arg2={}, "
                    "arg3={}; sent to core ({},{},{}) was bad.".format(
                        cmd, arg1, arg2, arg3, x, y, p
                    )
                )

            if scp.seq == seq:
                # The packet is the acknowledgement.
                return scp

        # The packet we transmitted wasn't acknowledged.
        raise TimeoutError(
            "Exceeded {} tries when trying to transmit packet.".format(
                self.n_tries)
        )

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
        # Non-blocking and then the following is a busy loop.
        self.sock.setblocking(False)

        # Calculate the receive length, this should be the smallest power of
        # two greater than the required size
        max_length = buffer_size + consts.SDP_HEADER_LENGTH
        receive_length = 1 << 9  # 512 bytes is a reasonable minimum
        while receive_length < max_length:
            receive_length <<= 1

        class TransmittedPacket(object):
            """A packet which has been transmitted and still awaits a response.
            """
            __slots__ = ["callback", "packet", "expected_args", "n_tries",
                         "time_sent"]

            def __init__(self, callback, packet, expected_args):
                self.callback = callback
                self.packet = packet
                self.expected_args = expected_args
                self.n_tries = 1
                self.time_sent = time.time()

        queued_packets = True
        outstanding_packets = {}

        # While there are packets in the queue or packets for which we are
        # still awaiting returns then continue to loop.
        while queued_packets or outstanding_packets:
            # If there are fewer outstanding packets than the window can take
            # then transmit a packet and add it to the list of outstanding
            # packets.
            if len(outstanding_packets) < window_size and queued_packets:
                try:
                    args = next(parameters_and_callbacks)
                except StopIteration:
                    queued_packets = False

                if queued_packets:
                    # If we extracted a new packet to extend create the
                    # outstanding packet and transmit it.
                    seq = next(self.seq)
                    packet = packets.SCPPacket(
                        reply_expected=True, tag=0xff, dest_port=0,
                        dest_cpu=args.p, src_port=7, src_cpu=31,
                        dest_x=args.x, dest_y=args.y, src_x=0, src_y=0,
                        cmd_rc=args.cmd, seq=seq,
                        arg1=args.arg1, arg2=args.arg2, arg3=args.arg3,
                        data=args.data
                    )
                    outstanding = TransmittedPacket(
                        args.callback, packet.bytestring, args.expected_args)
                    outstanding_packets[seq] = outstanding
                    self.sock.send(b"\x00\x00" + packet.bytestring)

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
                seq_bytes = ack[2 + consts.SDP_HEADER_LENGTH + 2:
                                2 + consts.SDP_HEADER_LENGTH + 2 + 2]
                seq, = struct.unpack("<H", seq_bytes)
                ack_packet = packets.SCPPacket.from_bytestring(ack[2:])
                assert ack_packet.seq == seq

                # Look up the sequence index of packet in the list of
                # outstanding packets.  We may have already processed a
                # response for this packet (indicating that the response was
                # delayed and we retransmitted the initial message) in which
                # case we can silently ignore the returned packet.
                outstanding = outstanding_packets.pop(seq, None)
                if outstanding is not None:
                    ack_packet = packets.SCPPacket.from_bytestring(
                        ack[2:], n_args=outstanding.expected_args)
                    outstanding.callback(ack_packet)

            # Look through all the remaining outstanding packets, if any of
            # them have timed out then we retransmit them.
            current_time = time.time()
            for seq, outstanding in six.iteritems(outstanding_packets):
                if current_time - outstanding.time_sent > self.default_timeout:
                    # This packet has timed out, if we have sent it more than
                    # the given number of times then raise a timeout error for
                    # it.
                    if outstanding.n_tries >= self.n_tries:
                        raise TimeoutError(self.n_tries)

                    # Otherwise we retransmit it
                    self.sock.send(b"\x00\x00" + outstanding.packet)
                    outstanding.n_tries += 1
                    outstanding.time_sent = current_time

    def read(self, buffer_size, window_size, x, y, p, address, length_bytes):
        """Read a bytestring from an address in memory.

        Parameters
        ----------
        buffer_size : int
            Number of bytes held in an SCP buffer by SARK, determines how many
            bytes will be expected in a socket.
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
        def callback(mem, block_data):
            mem[:] = block_data.data

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
                    block_size, dtype, expected_args=0,
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

        Parameters
        ----------
        buffer_size : int
            Number of bytes held in an SCP buffer by SARK, determines how many
            bytes will be expected in a socket.
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


def seqs(mask=0xf):
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
