import collections
import mock
from mock import call
import pytest
import struct
import time

from ..consts import SCPCommands, DataType
from ..packets import SCPPacket
from ..scp_connection import scpcall, SCPConnection
from .. import scp_connection


class SendReceive(object):
    def __init__(self, return_packet=None):
        self.last_seen = None
        self.return_packet = return_packet

    def send(self, packet, *args):
        self.last_seen = packet[:]

    def recv(self, *args, **kwargs):
        return self.return_packet(self.last_seen)


@pytest.fixture
def mock_conn():
    """Create an SCP connection with a mocked out socket.
    """
    # Create an SCPConnection pointed at localhost
    # Mock out the socket
    conn = SCPConnection("localhost", timeout=0.01)
    conn.sock = mock.Mock(spec_set=conn.sock)

    return conn


def test_scpcall():
    """scpcall is a utility for specifying SCP packets and callbacks"""
    call = scpcall(0, 1, 2, 3)
    assert call.x == 0
    assert call.y == 1
    assert call.p == 2
    assert call.cmd == 3
    assert call.arg1 == call.arg2 == call.arg3 == 0
    assert call.data == b''
    assert call.expected_args == 3
    assert isinstance(call.callback, collections.Callable)

    assert call.positional == (call.x, call.y, call.p, call.cmd,
                               call.arg1, call.arg2, call.arg3, call.data,
                               call.expected_args)


@pytest.mark.parametrize("bufsize, recv_size", [(232, 512), (256, 512),
                                                (248, 512), (504, 512),
                                                (514, 1024)])
def test_success(mock_conn, bufsize, recv_size):
    """Test successfully transmitting and receiving, where the seq of the first
    returned packet is wrong.
    """
    # Generate the return packet
    class ReturnPacket(object):
        def __init__(self):
            self.d = False

        def __call__(self, last):
            if not self.d:
                self.d = True

                # Change the sequence value
                pkg = SCPPacket.from_bytestring(last)
                pkg.seq += 1
                return pkg.bytestring
            else:
                return last

    sr = SendReceive(ReturnPacket())

    # Set up the mock connections
    mock_conn.sock.send.side_effect = sr.send
    mock_conn.sock.recv.side_effect = sr.recv

    # Send and receive
    recvd = mock_conn.send_scp(bufsize, 1, 2, 3, 4, 5, 6, 7, b'\x08')
    assert isinstance(recvd, SCPPacket)

    # Check that the transmitted packet was sane, and that only two packets
    # were transmitted (because the first was acknowledged with an incorrect
    # sequence number).  Also assert that there were only 2 calls to recv and
    # that they were of the correct size.
    assert mock_conn.sock.send.call_count == 2
    mock_conn.sock.recv.assert_has_calls([call(recv_size)] * 2)
    transmitted = SCPPacket.from_bytestring(sr.last_seen)
    assert transmitted.dest_x == recvd.dest_x == 1
    assert transmitted.dest_y == recvd.dest_y == 2
    assert transmitted.dest_cpu == recvd.dest_cpu == 3
    assert transmitted.cmd_rc == recvd.cmd_rc == 4
    assert transmitted.arg1 == recvd.arg1 == 5
    assert transmitted.arg2 == recvd.arg2 == 6
    assert transmitted.arg3 == recvd.arg3 == 7
    assert transmitted.data == recvd.data == b'\x08'


@pytest.mark.parametrize("n_tries", [5, 2])
def test_retries(mock_conn, n_tries):
    mock_conn.sock.recv.side_effect = IOError
    mock_conn.n_tries = n_tries

    # Send an SCP command and check that an error is raised
    with pytest.raises(scp_connection.TimeoutError):
        mock_conn.send_scp(256, 0, 0, 0, 0)

    # Check that n attempts were made
    assert mock_conn.sock.send.call_count == n_tries


@pytest.mark.parametrize(
    "rc, error",
    [(0x81, scp_connection.BadPacketLengthError),
     (0x83, scp_connection.InvalidCommandError),
     (0x84, scp_connection.InvalidArgsError),
     (0x87, scp_connection.NoRouteError)])
def test_errors(mock_conn, rc, error):
    """Test that errors are raised when error RCs are returned."""
    def return_packet(last):
        packet = SCPPacket.from_bytestring(last)
        packet.cmd_rc = rc
        return packet.bytestring

    sr = SendReceive(return_packet)
    mock_conn.sock.send.side_effect = sr.send
    mock_conn.sock.recv.side_effect = sr.recv

    # Send an SCP command and check that the correct error is raised
    with pytest.raises(error):
        mock_conn.send_scp(256, 0, 0, 0, 0)

    assert mock_conn.sock.send.call_count == 1
    assert mock_conn.sock.recv.call_count == 1


class TestBursts(object):
    """Tests for transmitting bursts of SCP packets."""
    @pytest.mark.parametrize("buffer_size, receive_length",
                             [(128, 512), (509, 1024)])
    def test_single_packet(self, mock_conn, buffer_size, receive_length):
        """Test correct operation for transmitting and receiving a single
        packet.
        """
        callback = mock.Mock(name="callback")

        def packets():
            # Yield a single packet, with a callback
            yield scpcall(3, 5, 0, 12, callback=callback)

        sent_packet = SCPPacket(
            True, 0xff, 0, 0, 7, 31, 3, 5, 0, 0, 12, 0, 0, 0, 0, b'')

        # Create a mock socket object which will reply with a valid packet the
        # second time it is called.
        class ReturnPacket(object):
            def __init__(self):
                self.packet = None
                self.called = False

            def __call__(self, packet):
                if not self.called:
                    self.called = True
                    raise IOError

                self.packet = SCPPacket.from_bytestring(packet)
                assert self.packet.dest_x == 3
                assert self.packet.dest_y == 5
                assert self.packet.dest_cpu == 0
                assert self.packet.cmd_rc == 12

                self.packet.cmd_rc = 0
                return self.packet.bytestring

        return_packet = ReturnPacket()
        sr = SendReceive(return_packet)
        mock_conn.sock.send.side_effect = sr.send
        mock_conn.sock.recv.side_effect = sr.recv

        # Send the bursty packet, assert that it was sent and received and that
        # the callback was called.
        mock_conn.send_scp_burst(buffer_size, 8, packets())

        mock_conn.sock.send.assert_called_once_with(
            b'\x00\x00' + sent_packet.bytestring)
        mock_conn.sock.recv.assert_has_calls([mock.call(receive_length)] * 2)

        assert callback.call_count == 1
        assert (callback.call_args[0][0].bytestring ==
                return_packet.packet.bytestring)

    def test_single_packet_times_out(self, mock_conn):
        """Test correct operation for transmitting a single packet which is
        never acknowledged.
        """
        def packets():
            # Yield a single packet
            yield scpcall(3, 5, 0, 12)

        # The socket will always return with an IOError, so the packet is never
        # acknowledged.
        mock_conn.sock.recv.side_effect = IOError

        # Send the bursty packet, assert that it was sent for as many times as
        # specified.
        start = time.time()
        with pytest.raises(scp_connection.TimeoutError):
            mock_conn.send_scp_burst(512, 8, packets())
        fail_time = time.time() - start

        # Failing to transmit should take some time
        assert fail_time >= mock_conn.n_tries * mock_conn.default_timeout

        # We shouldn't have transmitted the packet more than the number of
        # times we specified.
        assert mock_conn.sock.send.call_count == mock_conn.n_tries
        assert mock_conn.sock.recv.called

    @pytest.mark.parametrize("window_size, n_tries", [(10, 2), (8, 5)])
    def test_fills_window(self, mock_conn, window_size, n_tries):
        """Test that when no acknowledgement packets are sent the window fills
        up and all packets are tried multiple times.
        """
        def packets():
            # Yield 10 packets
            for x in range(10):
                yield scpcall(10, 5, 0, 12)

        # Set the number of retries
        mock_conn.n_tries = n_tries

        # The socket will always return with an IOError, so the packet is never
        # acknowledged.
        mock_conn.sock.recv.side_effect = IOError

        # Send the bursty packet, assert that it was sent for as many times as
        # specified.
        with pytest.raises(scp_connection.TimeoutError):
            mock_conn.send_scp_burst(512, window_size, packets())

        # We should have transmitted AT LEAST one packet per window item and AT
        # MOST window size * number of tries packets.
        assert (window_size < mock_conn.sock.send.call_count <=
                window_size * n_tries)


@pytest.mark.parametrize(
    "buffer_size, window_size, x, y, p", [(128, 1, 0, 0, 1), (256, 5, 1, 2, 3)]
)
@pytest.mark.parametrize(
    "n_bytes, data_type, start_address",
    [(1, DataType.byte, 0x60000000),   # Only reading a byte
     (3, DataType.byte, 0x60000000),   # Can only read bytes
     (2, DataType.byte, 0x60000001),   # Offset from short
     (4, DataType.byte, 0x60000001),   # Offset from word
     (2, DataType.short, 0x60000002),  # Reading a short
     (6, DataType.short, 0x60000002),  # Can read shorts
     (4, DataType.short, 0x60000002),  # Offset from word
     (4, DataType.word, 0x60000004),   # Reading a word
     (257, DataType.byte, 0x60000001),
     (511, DataType.byte, 0x60000001),
     (258, DataType.byte, 0x60000001),
     (256, DataType.byte, 0x60000001),
     (258, DataType.short, 0x60000002),
     (514, DataType.short, 0x60000002),
     (516, DataType.short, 0x60000002),
     (256, DataType.word, 0x60000004)
     ])
def test_read(buffer_size, window_size, x, y, p, n_bytes,
              data_type, start_address):
    mock_conn = SCPConnection("localhost")

    # Construct the expected calls, and hence the expected return packets
    offset = start_address
    offsets = []
    lens = []
    length_bytes = n_bytes
    while length_bytes > 0:
        offsets += [offset]
        lens += [min((buffer_size, length_bytes))]
        offset += lens[-1]
        length_bytes -= lens[-1]

    assert len(lens) == len(offsets), "Test is broken"

    with mock.patch.object(mock_conn, "send_scp_burst") as send_scp_burst:
        # Set send_scp_burst up to call all the callbacks with some specified
        # value.
        class CallCallbacks(object):
            read_data = b''

            def __call__(self, buffer_size, window_size, args):
                for i, arg in enumerate(args):
                    mock_packet = mock.Mock(spec_set=['data'])
                    mock_packet.data = struct.pack("B", i) * arg.arg2
                    self.read_data += mock_packet.data
                    arg.callback(mock_packet)

        ccs = CallCallbacks()
        send_scp_burst.side_effect = ccs

        # Read an amount of memory specified by the size.
        data = mock_conn.read(buffer_size, window_size, x, y, p,
                              start_address, n_bytes)
        assert data == ccs.read_data

    # send_burst_scp should have been called once, each element in the iterator
    # it is given should match the offsets and lengths we worked out
    # previously.
    assert send_scp_burst.call_count == 1
    assert send_scp_burst.call_args[0][0] == buffer_size
    assert send_scp_burst.call_args[0][1] == window_size
    pars_calls = send_scp_burst.call_args[0][2]

    for args, length, offset in zip(pars_calls, lens, offsets):
        assert args.x == x and args.y == y and args.p == p
        assert args.cmd == SCPCommands.read
        assert args.arg1 == offset
        assert args.arg2 == length
        assert args.arg3 == data_type
        assert args.expected_args == 0


@pytest.mark.parametrize(
    "buffer_size, window_size, x, y, p",
    [(128, 1, 0, 0, 1), (256, 5, 1, 2, 3)]
)
@pytest.mark.parametrize(
    "start_address,data,data_type",
    [(0x60000000, b'\x1a', DataType.byte),
     (0x60000001, b'\xab', DataType.byte),
     (0x60000001, b'\x00\x00', DataType.byte),
     (0x60000001, b'\x00\x00\x00\x00', DataType.byte),
     (0x60000000, b'\x00\x00', DataType.short),
     (0x60000002, b'\x00\x00\x00\x00', DataType.short),
     (0x60000004, b'\x00\x00\x00\x00', DataType.word),
     (0x60000001, 512*b'\x00\x00\x00\x00', DataType.byte),
     (0x60000002, 512*b'\x00\x00\x00\x00', DataType.short),
     (0x60000000, 512*b'\x00\x00\x00\x00', DataType.word),
     ])
def test_write(buffer_size, window_size, x, y, p,
               start_address, data, data_type):
    mock_conn = SCPConnection("localhost")

    # Write the data
    with mock.patch.object(mock_conn, "send_scp_burst") as send_scp_burst:
        mock_conn.write(buffer_size, window_size, x, y, p, start_address, data)

    # Check that the correct calls to send_scp were made
    segments = []
    address = start_address
    addresses = []
    while len(data) > 0:
        addresses.append(address)
        segments.append(data[0:buffer_size])

        data = data[buffer_size:]
        address += len(segments[-1])

    # send_burst_scp should have been called once, each element in the iterator
    # it is given should match the offsets and lengths we worked out
    # previously.
    assert send_scp_burst.call_count == 1
    assert send_scp_burst.call_args[0][0] == buffer_size
    assert send_scp_burst.call_args[0][1] == window_size
    pars_calls = send_scp_burst.call_args[0][2]

    for args, addr, data in zip(pars_calls, addresses, segments):
        assert args.x == x and args.y == y and args.p == p
        assert args.cmd == SCPCommands.write
        assert args.arg1 == addr
        assert args.arg2 == len(data)
        assert args.arg3 == data_type
        assert args.data == data
