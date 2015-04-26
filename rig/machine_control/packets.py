"""Representations of SDP and SCP Packets."""
import struct

# SDP header flags
FLAG_REPLY = 0x87
FLAG_NO_REPLY = 0x07


class SDPPacket(object):
    """An SDP Packet"""
    __slots__ = ["reply_expected", "tag", "dest_port", "dest_cpu", "src_port",
                 "src_cpu", "dest_x", "dest_y", "src_x", "src_y", "data"]

    def __init__(self, reply_expected, tag, dest_port, dest_cpu, src_port,
                 src_cpu, dest_x, dest_y, src_x, src_y, data):
        """Create a new SDPPacket.

        Parameters
        ----------
        reply_expected : bool
            True if a reply is expected, otherwise False.
        tag : int
            An integer representing the IPTag that should be used to transmit
            the packer over an IPv4 network.
        """
        self.reply_expected = reply_expected
        self.tag = tag
        self.dest_port = dest_port
        self.dest_cpu = dest_cpu
        self.src_port = src_port
        self.src_cpu = src_cpu
        self.dest_x = dest_x
        self.dest_y = dest_y
        self.src_x = src_x
        self.src_y = src_y
        self.data = data

    @classmethod
    def unpack_packet(cls, bytestring):
        """Unpack the SDP header from a bytestring."""
        # Extract the header and the data from the packet
        header = bytestring[0:10]  # First 8+2 bytes
        data = bytestring[10:]  # Everything else

        # Unpack the header
        (flags, tag, dest_cpu_port, src_cpu_port, dest_p2p,
         src_p2p) = struct.unpack('<2x4B2H', header)

        dest_x = (dest_p2p & 0xff00) >> 8
        dest_y = (dest_p2p & 0x00ff)
        src_x = (src_p2p & 0xff00) >> 8
        src_y = (src_p2p & 0x00ff)

        # Neaten up the combined VCPU and port fields
        dest_cpu = dest_cpu_port & 0x1f
        dest_port = (dest_cpu_port >> 5) & 0x07
        src_cpu = src_cpu_port & 0x1f
        src_port = (src_cpu_port >> 5) & 0x07

        # Create a dictionary representing the packet.
        return dict(
            reply_expected=flags == FLAG_REPLY, tag=tag, dest_port=dest_port,
            dest_cpu=dest_cpu, src_port=src_port, src_cpu=src_cpu,
            dest_x=dest_x, dest_y=dest_y, src_x=src_x, src_y=src_y, data=data
        )

    @classmethod
    def from_bytestring(cls, bytestring):
        """Create a new SDPPacket from a bytestring.

        Returns
        -------
        SDPPacket
            An SDPPacket containing the data from the bytestring.
        """
        return cls(**cls.unpack_packet(bytestring))

    @property
    def packed_data(self):
        return self.data

    @property
    def bytestring(self):
        """Convert the packet into a bytestring."""
        # Convert x and y to p2p addresses
        dest_p2p = (self.dest_x << 8) | self.dest_y
        src_p2p = (self.src_x << 8) | self.src_y

        packed_dest_cpu_port = (((self.dest_port & 0x7) << 5) |
                                (self.dest_cpu & 0x1f))
        packed_src_cpu_port = (((self.src_port & 0x7) << 5) |
                               (self.src_cpu & 0x1f))

        # Construct the header
        header = struct.pack(
            '<2x4B2H', FLAG_REPLY if self.reply_expected else FLAG_NO_REPLY,
            self.tag, packed_dest_cpu_port, packed_src_cpu_port,
            dest_p2p, src_p2p
        )

        # Return the header and the packed data
        return header + self.packed_data


class SCPPacket(SDPPacket):
    """An SCP Packet"""
    __slots__ = ["cmd_rc", "seq", "arg1", "arg2", "arg3"]

    def __init__(self, reply_expected, tag, dest_port, dest_cpu, src_port,
                 src_cpu, dest_x, dest_y, src_x, src_y, cmd_rc, seq, arg1,
                 arg2, arg3, data):
        super(SCPPacket, self).__init__(
            reply_expected, tag, dest_port, dest_cpu, src_port,
            src_cpu, dest_x, dest_y, src_x, src_y, data)

        # Store additional data for the SCP packet
        self.cmd_rc = cmd_rc
        self.seq = seq
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3

    @classmethod
    def from_bytestring(cls, scp_packet, n_args=3):
        """Create a new SCPPacket from a bytestring.

        Parameters
        ----------
        scp_packet : bytestring
            Bytestring containing an SCP packet.
        n_args : int
            The number of arguments to unpack from the SCP data.
        """
        sdp_data = cls.unpack_packet(scp_packet)
        sdp_data.update(cls.unpack_scp_header(sdp_data["data"], n_args))
        return cls(**sdp_data)

    @classmethod
    def unpack_scp_header(cls, data, n_args=3):
        """Unpack the SCP header from a bytestring."""
        # Unpack the SCP header from the data
        (cmd_rc, seq) = struct.unpack('<2H', data[0:4])
        data = data[4:]

        # Unpack as much of the data as is present
        arg1 = arg2 = arg3 = None
        if n_args >= 1 and len(data) >= 4:
            arg1 = struct.unpack('<I', data[0:4])[0]
            data = data[4:]
        if n_args >= 2 and len(data) >= 4:
            arg2 = struct.unpack('<I', data[0:4])[0]
            data = data[4:]
        if n_args >= 3 and len(data) >= 4:
            arg3 = struct.unpack('<I', data[0:4])[0]
            data = data[4:]

        # Return the SCP header
        scp_header = {
            'cmd_rc': cmd_rc, 'seq': seq, 'arg1': arg1, 'arg2': arg2, 'arg3':
            arg3, 'data': data}
        return scp_header

    @property
    def packed_data(self):
        """Pack the data for the SCP packet."""
        scp_header = struct.pack("<2H", self.cmd_rc, self.seq)

        for arg in (self.arg1, self.arg2, self.arg3):
            if arg is not None:
                scp_header += struct.pack('<I', arg)

        # Return the SCP header and the rest of the data
        return scp_header + self.data
