import pytest

from rig.routing_table import (
    RoutingTableEntry, Routes, table_is_subset_of, MinimisationFailedError
)
from rig.routing_table.ordered_covering import (
    get_generality, get_all_merges, get_insertion_index, Merge, refine_merge,
    minimise
)


@pytest.mark.parametrize(
    "key, mask, generality", (
        (0x0, 0x0, 32),
        (0x1, 0x1, 31),
        (0xffffffff, 0xffffffff, 0),
        (0x7fffffff, 0x80000000, 0)
    )
)
def test_get_generality(key, mask, generality):
    assert get_generality(key, mask) == generality


def test_get_all_merges():
    table = [
        RoutingTableEntry(0, 0, 0),
        RoutingTableEntry(0, 0, 0),
        RoutingTableEntry(1, 0, 0),
        RoutingTableEntry(0, 0, 0),
        RoutingTableEntry(1, 0, 0),
        RoutingTableEntry(2, 0, 0),
    ]
    expected_merges = [{0, 1, 3}, {2, 4}]

    # Get merges from the table
    merges = list(get_all_merges(table))

    assert len(expected_merges) == len(merges)
    for merge, expected in zip(merges, expected_merges):
        assert merge.routing_table is table
        assert merge.entries == expected


def test_get_insertion_index():
    # Construct a routing table containing only generality 31 entries
    table = [RoutingTableEntry(None, 0b00, 0b10),
             RoutingTableEntry(None, 0b10, 0b10),
             RoutingTableEntry(None, 0b00, 0b01),
             RoutingTableEntry(None, 0b01, 0b01)]

    # Check that the insertion position for any generality 30 expression is 0.
    assert get_insertion_index(table, 30) == 0

    # Add a generality 30 expression and then check where generality 31
    # expressions would go (they should go to the end of the table)
    table.insert(0, RoutingTableEntry(None, 0b00, 0b11))
    assert get_insertion_index(table, 32) == len(table)

    # Check that generality 32 expressions should go to the end of the table
    assert get_insertion_index(table, 32) == len(table)
    table.append(RoutingTableEntry(None, 0x0, 0x0))

    # Check that generality 31 expressions should be inserted before this
    assert get_insertion_index(table, 31) == len(table) - 1


class TestMerge(object):
    def test_apply(self):
        """Test applying a merge to a routing table."""
        table = [RoutingTableEntry(None, 0b00, 0b10),
                 RoutingTableEntry(None, 0b10, 0b10),
                 RoutingTableEntry(None, 0b00, 0b01),
                 RoutingTableEntry(None, 0b01, 0b01)]

        # Merge the first two entries together, check the correct entry is
        # inserted in the correct part of the table and that the alias
        # dictionary is filled in.
        merge = Merge(table, {0, 1})
        new_table, new_aliases = merge.apply(dict())
        assert new_table == [RoutingTableEntry(None, 0b00, 0b01),
                             RoutingTableEntry(None, 0b01, 0b01),
                             RoutingTableEntry(None, 0b00, 0b00)]
        assert new_aliases == {(0b00, 0b00): {(0b00, 0b10), (0b10, 0b10)}}

        # Merge the last two entries together, check that correct entry is
        # inserted into the table.
        merge = Merge(table, {2, 3})
        new_table, new_aliases = merge.apply(dict())
        assert new_table == [RoutingTableEntry(None, 0b00, 0b10),
                             RoutingTableEntry(None, 0b10, 0b10),
                             RoutingTableEntry(None, 0b00, 0b00)]
        assert new_aliases == {(0b00, 0b00): {(0b00, 0b01), (0b01, 0b01)}}

        # Merge the last two entries together, check that correct entry is
        # inserted into the table. Also check that the aliases dictionary is
        # updated correctly.
        merge = Merge(table, {2, 3})
        aliases = {
            (0b00, 0b10): {(0xcafecafe, 0xffffffff)},
            (0b01, 0b01): {(0x0000ffff, 0xffffffff)},
        }
        new_table, new_aliases = merge.apply(aliases)
        assert new_table == [RoutingTableEntry(None, 0b00, 0b10),
                             RoutingTableEntry(None, 0b10, 0b10),
                             RoutingTableEntry(None, 0b00, 0b00)]
        assert new_aliases == {
            (0b00, 0b10): {(0xcafecafe, 0xffffffff)},
            (0b00, 0b00): {(0b00, 0b01), (0x0000ffff, 0xffffffff)},
        }


def test_refines_out_aliased_entries():
    """Test that entries which would be aliased out by being moved below
    other entries are removed from the merge.
    """
    # NOTE: TABLE IS NOT ORTHOGONAL!
    table = [
        RoutingTableEntry(0, 0b1101, 0b1111),  # 1101
        RoutingTableEntry(0, 0b1011, 0b1111),  # 1011
        RoutingTableEntry(0, 0b1001, 0b1111),  # 1001
        RoutingTableEntry(1, 0b1001, 0b1001),  # 1XX1
    ]
    merge = Merge(table, {0, 1, 2})  # Merge the first three entries

    # Ultimately no merge should be possible
    assert refine_merge(merge, dict(), 0).goodness <= 0


def test_aborts_merge_due_to_down_aliasing():
    """Check that a merge is properly aborted if performing the merge would
    lead an entry lower down the table to be aliased out.
    """
    table = [
        RoutingTableEntry(0, 0b001, 0b111),  # 001
        RoutingTableEntry(0, 0b010, 0b111),  # 010
        RoutingTableEntry(1, 0b000, 0b000),  # XXX
    ]
    merge = Merge(table, {0, 1})

    assert refine_merge(merge, {(0x0, 0x0): {(0b011, 0b111)}}, 0).goodness <= 0


def test_reduces_merge_due_to_down_aliasing():
    """Check that a merge is reduced if performing the merge would lead an
    entry lower down the table to be aliased out.
    """
    table = [
        RoutingTableEntry(0, 0b000, 0b111),  # 000
        RoutingTableEntry(0, 0b001, 0b111),  # 001
        RoutingTableEntry(0, 0b010, 0b111),  # 010
        RoutingTableEntry(1, 0b000, 0b000),  # XXX
    ]
    merge = Merge(table, {0, 1, 2})

    merge = refine_merge(merge, {(0x0, 0x0): {(0b011, 0b111)}}, 0)
    assert (merge == Merge(table, {0, 1}) or
            merge == Merge(table, {0, 2}))


def test_reduces_merge_due_to_down_aliasing_multiple_bits():
    """Check that a merge is reduced if performing the merge would lead an
    entry lower down the table to be aliased out.
    """
    table = [
        RoutingTableEntry(0, 0b1000, 0b1111),  # 1000
        RoutingTableEntry(0, 0b1001, 0b1111),  # 1001
        RoutingTableEntry(0, 0b1011, 0b1111),  # 1011
        RoutingTableEntry(0, 0b1100, 0b1110),  # 110X
        RoutingTableEntry(1, 0b0000, 0b0000),  # XXXX
    ]
    merge = Merge(table, {0, 1, 2, 3})  # Merge produces 1XXX

    new_merge = refine_merge(
        merge, {(0x0, 0x0): {(0b0011, 0b0011),  # XX11
                             (0b1000, 0b1001),  # 1XX0
                             }},
        min_goodness=0
    )

    # Ultimately no merge should be possible
    assert new_merge.goodness <= 0


def test_refine_merge_fails_due_to_unchangeable_bit():
    """Check that a merge is reduced if performing the merge would lead an
    entry lower down the table to be aliased out.

    The first two entries can never be merged::

        0001 -> N
        001X -> N
        XXX1 -> S
        XX1X -> S
        XXXX -> S

    Because there is no way of splitting the merge up to avoid aliasing the
    last entry.
    """
    table = [
        RoutingTableEntry({Routes.north}, 0b0001, 0b1111),
        RoutingTableEntry({Routes.north}, 0b0010, 0b1110),
        RoutingTableEntry({Routes.south}, 0b0001, 0b0001),
        RoutingTableEntry({Routes.south}, 0b0010, 0b0010),
        RoutingTableEntry({Routes.south}, 0b0000, 0b0000),
    ]
    merge = Merge(table, {0, 1})  # Merge produces 00XX

    # Ultimately no merge should be possible
    new_merge = refine_merge(merge, dict(), 0)
    assert new_merge.goodness <= 0


class TestMinimise(object):
    def test_simple(self):
        """Test that a very simple routing table can be minimised, only one
        merge should be made and there are no conflicts.

        Table::

            0000 -> N, NE
            0001 -> N, NE
            001X -> S

        Can be minimised to::

            001X -> S
            000X -> N, NE
        """
        # Original table
        RTE = RoutingTableEntry
        table = [
            RTE({Routes.north, Routes.north_east}, 0b0000, 0b1111),
            RTE({Routes.north, Routes.north_east}, 0b0001, 0b1111),
            RTE({Routes.south}, 0b0010, 0b1110),
        ]

        # Expected table
        expected_table = [
            RTE({Routes.south}, 0b0010, 0b1110),
            RTE({Routes.north, Routes.north_east}, 0b0000, 0b1110),
        ]

        assert table_is_subset_of(table, expected_table), "Test is broken"

        # Minimise and check the result
        assert minimise(table, target_length=None) == expected_table

    def test_stop_if_table_sufficiently_small(self):
        """Test that nothing happens if the table is already sufficiently
        small.
        """
        RTE = RoutingTableEntry
        table = [
            RTE({Routes.north, Routes.north_east}, 0b0000, 0b1111),
            RTE({Routes.north, Routes.north_east}, 0b0001, 0b1111),
            RTE({Routes.south}, 0b0010, 0b1110),
        ]

        # Minimise and check the result
        assert minimise(table, target_length=3) == table

    def test_fail_if_table_cannot_be_made_sufficiently_small(self):
        """Test that nothing happens if the table is already sufficiently
        small.
        """
        RTE = RoutingTableEntry
        table = [
            RTE({Routes.north, Routes.south}, 0b0000, 0b1111),
            RTE({Routes.north, Routes.north_east}, 0b0001, 0b1111),
            RTE({Routes.south}, 0b0010, 0b1110),
        ]

        # Minimise and check the result
        with pytest.raises(MinimisationFailedError) as exc:
            minimise(table, target_length=2)
        assert "3" in str(exc)

    def test_complex_a(self):
        """Attempt to minimise the following table:

            0000 -> N NE
            0001 -> E
            0101 -> SW
            1000 -> N NE
            1001 -> E
            1110 -> SW
            1100 -> N NE
            0100 -> S SW

        The result (worked out by hand) should be:

            0100 -> S SW
            X001 -> E
            XX00 -> N NE
            X1XX -> SW
        """
        RTE = RoutingTableEntry
        table = [
            RTE({Routes.north, Routes.north_east}, 0b0000, 0b1111),
            RTE({Routes.east}, 0b0001, 0b1111),
            RTE({Routes.south_west}, 0b0101, 0b1111),
            RTE({Routes.north, Routes.north_east}, 0b1000, 0b1111),
            RTE({Routes.east}, 0b1001, 0b1111),
            RTE({Routes.south_west}, 0b1110, 0b1111),
            RTE({Routes.north, Routes.north_east}, 0b1100, 0b1111),
            RTE({Routes.south, Routes.south_west}, 0b0100, 0b1111),
        ]

        expected_table = [
            RTE({Routes.south, Routes.south_west}, 0b0100, 0b1111),
            RTE({Routes.east}, 0b0001, 0b0111),
            RTE({Routes.north, Routes.north_east}, 0b0000, 0b0011),
            RTE({Routes.south_west}, 0b0100, 0b0100),
        ]

        assert table_is_subset_of(table, expected_table), "Test is broken"

        # Get the minimised table
        assert minimise(table, target_length=None) == expected_table

    def test_complex_b(self):
        """Attempt to minimise the following table:

            0000 -> N NE
            0001 -> E
            0101 -> SW
            1000 -> N NE
            1001 -> E
            1110 -> SW
            1100 -> N NE
            0X00 -> S SW

        The result (worked out by hand) should be:

            0000 -> N NE
            0X00 -> S SW
            1X00 -> N NE
            X001 -> E
            X1XX -> SW
        """
        RTE = RoutingTableEntry
        table = [
            RTE({Routes.north, Routes.north_east}, 0b0000, 0b1111),
            RTE({Routes.east}, 0b0001, 0b1111),
            RTE({Routes.south_west}, 0b0101, 0b1111),
            RTE({Routes.north, Routes.north_east}, 0b1000, 0b1111),
            RTE({Routes.east}, 0b1001, 0b1111),
            RTE({Routes.south_west}, 0b1110, 0b1111),
            RTE({Routes.north, Routes.north_east}, 0b1100, 0b1111),
            RTE({Routes.south, Routes.south_west}, 0b0000, 0b1011),
        ]

        expected_table = [
            RTE({Routes.north, Routes.north_east}, 0b0000, 0b1111),
            RTE({Routes.south, Routes.south_west}, 0b0000, 0b1011),
            RTE({Routes.north, Routes.north_east}, 0b1000, 0b1011),
            RTE({Routes.east}, 0b0001, 0b0111),
            RTE({Routes.south_west}, 0b0100, 0b0100),
        ]

        assert table_is_subset_of(table, expected_table), "Test is broken"

        # Get the minimised table
        assert minimise(table, target_length=None) == expected_table
