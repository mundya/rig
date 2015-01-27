import mock

from rig.netlist import Net


class Vertex(object):
    """Represents an object that could be the source or sink of a net."""
    pass


class TestNet(object):
    def test_init_with_list(self):
        source = Vertex()
        sinks = [Vertex() for _ in range(3)]

        net = Net(source, sinks, 0.5)

        # Assert that the source object is the same but that the sinks list has
        # been copied.
        assert net.source is source
        assert net.sinks is not sinks
        assert net.sinks == sinks
        assert net.weight == 0.5

    def test_init_with_object(self):
        source = Vertex()
        sink = Vertex()

        net = Net(source, sink, 5)

        # Assert that the sinks is a list of the 1 sink we provided.
        assert net.source is source
        assert net.sinks == [sink]
        assert net.weight == 5

    def test_init_with_keyspace(self):
        source = Vertex()
        sinks = [Vertex() for _ in range(5)]
        ks = mock.Mock()

        net = Net(source, sinks, 1, keyspace=ks)
        assert net.keyspace == ks
