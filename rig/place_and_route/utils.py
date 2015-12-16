"""Utilities functions which assist in the generation of commonly required data
structures from the products of placement, allocation and routing.
"""

from collections import defaultdict, deque, namedtuple, OrderedDict

from six import iteritems, itervalues

from rig.place_and_route.machine import Machine, Cores, SDRAM, SRAM

from rig.routing_table import RoutingTableEntry

from rig.place_and_route.routing_tree import RoutingTree

from rig.place_and_route.constraints import ReserveResourceConstraint

from rig.machine_control.consts import AppState


def build_machine(system_info,
                  core_resource=Cores,
                  sdram_resource=SDRAM,
                  sram_resource=SRAM):
    """Build a :py:class:`~rig.place_and_route.Machine` object from a
    :py:class:`~rig.machine_control.machine_controller.SystemInfo` object.

    .. note::
        Links are tested by sending a 'PEEK' command down the link which
        checks to see if the remote device responds correctly. If the link
        is dead, no response will be received and the link will be assumed
        dead. Since peripherals do not generally respond to 'PEEK'
        commands, working links attached to peripherals will also be marked
        as dead.

    .. note::
        The returned object does not report how much memory is free, nor
        how many cores are idle but rather the total number of working cores
        and the size of the heap. See :py:func:`.build_resource_constraints`
        for a function which can generate a set of
        :py:class:`~rig.place_and_route.constraints` which prevent the use of
        already in-use cores and memory.

    .. note::
        This method replaces the deprecated
        :py:meth:`rig.machine_control.MachineController.get_machine` method.
        Its functionality may be recreated using
        :py:meth:`rig.machine_control.MachineController.get_system_info` along
        with this function like so::

            >> sys_info = mc.get_system_info()
            >> machine = build_machine(sys_info)

    Parameters
    ----------
    system_info : :py:class:`rig.machine_control.machine_controller.SystemInfo`
        The resource availability information for a SpiNNaker machine,
        typically produced by
        :py:meth:`rig.machine_control.MachineController.get_system_info`.
    core_resource : resource (default: :py:class:`rig.place_and_route.Cores`)
        The resource type to use to represent the number of working cores on a
        chip, including the monitor, those already in use and all idle cores.
    sdram_resource : resource (default: :py:class:`rig.place_and_route.SDRAM`)
        The resource type to use to represent SDRAM on a chip. This resource
        will be set to the number of bytes in the largest free block in the
        SDRAM heap. This gives a conservative estimate of the amount of free
        SDRAM on the chip which will be an underestimate in the presence of
        memory fragmentation.
    sram_resource : resource (default: :py:class:`rig.place_and_route.SRAM`)
        The resource type to use to represent SRAM (a.k.a. system RAM) on a
        chip. This resource will be set to the number of bytes in the largest
        free block in the SRAM heap. This gives a conservative estimate of the
        amount of free SRAM on the chip which will be an underestimate in the
        presence of memory fragmentation.

    Returns
    -------
    :py:class:`rig.place_and_route.Machine`
        A :py:class:`~rig.place_and_route.Machine` object representing the
        resources available within a SpiNNaker machine in the form used by the
        place-and-route infrastructure.
    """
    try:
        max_cores = max(c.num_cores for c in itervalues(system_info))
    except ValueError:
        max_cores = 0

    try:
        max_sdram = max(c.largest_free_sdram_block
                        for c in itervalues(system_info))
    except ValueError:
        max_sdram = 0

    try:
        max_sram = max(c.largest_free_sram_block
                       for c in itervalues(system_info))
    except ValueError:
        max_sram = 0

    return Machine(width=system_info.width,
                   height=system_info.height,
                   chip_resources={
                       core_resource: max_cores,
                       sdram_resource: max_sdram,
                       sram_resource: max_sram,
                   },
                   chip_resource_exceptions={
                       chip: {
                           core_resource: info.num_cores,
                           sdram_resource: info.largest_free_sdram_block,
                           sram_resource: info.largest_free_sram_block,
                       }
                       for chip, info in iteritems(system_info)
                       if (info.num_cores != max_cores
                           or info.largest_free_sdram_block != max_sdram
                           or info.largest_free_sram_block != max_sram)
                   },
                   dead_chips=set(system_info.dead_chips()),
                   dead_links=set(system_info.dead_links()))


def _get_minimal_core_reservations(core_resource, cores, chip=None):
    """Yield a minimal set of
    :py:class:`~rig.place_and_route.constraints.ReserveResourceConstraint`
    objects which reserve the specified set of cores.

    Parameters
    ----------
    core_resource : resource type
        The type of resource representing cores.
    cores : [int, ...]
        The core numbers to reserve *in ascending order*.
    chip : None or (x, y)
        Which chip the constraints should be applied to or None for a global
        constraint.

    Yields
    ------
    :py:class:`~rig.place_and_route.constraints.ReserveResourceConstraint`
    """
    reservation = None

    # Cores is in ascending order
    for core in cores:
        if reservation is None:
            reservation = slice(core, core + 1)
        elif reservation.stop == core:
            reservation = slice(reservation.start, core + 1)
        else:
            yield ReserveResourceConstraint(
                core_resource, reservation, chip)
            reservation = slice(core, core + 1)

    if reservation is not None:
        yield ReserveResourceConstraint(core_resource, reservation, chip)


def build_core_constraints(system_info, core_resource=Cores):
    """Return a set of place-and-route
    :py:class:`~rig.place_and_route.constraints.ReserveResourceConstraint`
    which reserve any cores that that are already in use.

    The returned list of
    :py:class:`~rig.place_and_route.constraints.ReserveResourceConstraint`\ s
    reserves all cores not in an Idle state (i.e. not a monitor and not already
    running an application).

    .. note::

        Historically, every application was required to add a
        :py:class:~rig.place_and_route.constraints.ReserveResourceConstraint to
        reserve the monitor processor on each chip. This method improves upon
        this approach by automatically generating constraints which reserve not
        just the monitor core but also any other cores which are already in
        use.

    Parameters
    ----------
    system_info : :py:class:`rig.machine_control.machine_controller.SystemInfo`
        The resource availability information for a SpiNNaker machine,
        typically produced by
        :py:meth:`rig.machine_control.MachineController.get_system_info`.
    core_resource : resource (Default: :py:data:`~rig.place_and_route.Cores`)
        The resource identifier used for cores.

    Returns
    -------
    [:py:class:`rig.place_and_route.constraints.ReserveResourceConstraint`, \
            ...]
        A set of place-and-route constraints which reserves all non-idle cores.
        The resource type given in the ``core_resource`` argument will be
        reserved accordingly.
    """
    constraints = []

    # Find the set of cores which are universally reserved
    globally_reserved = None
    for chip_info in itervalues(system_info):
        reserved = sum(1 << c for c, state in enumerate(chip_info.core_states)
                       if state != AppState.idle)
        if globally_reserved is None:
            globally_reserved = reserved
        else:
            globally_reserved &= reserved

    if globally_reserved is None:
        globally_reserved = 0

    constraints.extend(_get_minimal_core_reservations(
        core_resource,
        [core for core in range(18) if (1 << core) & globally_reserved]))

    # Create chip-specific resource reservations for any special cases
    for chip, chip_info in iteritems(system_info):
        constraints.extend(_get_minimal_core_reservations(
            core_resource,
            [core for core, state in enumerate(chip_info.core_states)
             if state != AppState.idle
                and not globally_reserved & (1 << core)],
            chip))

    return constraints


def build_application_map(vertices_applications, placements, allocations,
                          core_resource=Cores):
    """Build a mapping from application to a list of cores where the
    application is used.

    This utility function assumes that each vertex is associated with a
    specific application.

    Parameters
    ----------
    vertices_applications : {vertex: application, ...}
        Applications are represented by the path of their APLX file.
    placements : {vertex: (x, y), ...}
    allocations : {vertex: {resource: slice, ...}, ...}
        One of these resources should match the `core_resource` argument.
    core_resource : object
        The resource identifier which represents cores.

    Returns
    -------
    {application: {(x, y) : set([c, ...]), ...}, ...}
        For each application, for each used chip a set of core numbers onto
        which the application should be loaded.
    """
    application_map = defaultdict(lambda: defaultdict(set))

    for vertex, application in iteritems(vertices_applications):
        chip_cores = application_map[application][placements[vertex]]
        core_slice = allocations[vertex].get(core_resource, slice(0, 0))
        chip_cores.update(range(core_slice.start, core_slice.stop))

    return application_map


def build_routing_tables(routes, net_keys, omit_default_routes=True):
    """Convert a set of RoutingTrees into a per-chip set of routing tables.

    This command produces routing tables with entries optionally omitted when
    the route does not change direction (i.e. when default routing can be
    used).

    .. warning::
        A :py:exc:`rig.place_and_route.utils.MultisourceRouteError` will
        be raised if entries with identical keys and masks but with differing
        routes are generated. This is not a perfect test, entries which would
        otherwise collide are not spotted.

    .. warning::
        The routing trees provided are assumed to be correct and continuous
        (not missing any hops). If this is not the case, the output is
        undefined.

    .. note::
        If a routing tree has a terminating vertex whose route is set to None,
        that vertex is ignored.

    Parameters
    ----------
    routes : {net: :py:class:`~rig.place_and_route.routing_tree.RoutingTree`, \
              ...}
        The complete set of RoutingTrees representing all routes in the system.
        (Note: this is the same datastructure produced by routers in the `par`
        module.)
    net_keys : {net: (key, mask), ...}
        The key and mask associated with each net.
    omit_default_routes : bool
        Do not create routing entries for routes which do not change direction
        (i.e. use default routing).

    Returns
    -------
    {(x, y): [:py:class:`~rig.routing_table.RoutingTableEntry`, ...]
    """
    # Pairs of inbound and outbound routes.
    _InOutPair = namedtuple("_InOutPair", "ins, outs")

    # {(x, y): {(key, mask): _InOutPair}}
    route_sets = defaultdict(OrderedDict)

    for net, routing_tree in iteritems(routes):
        key, mask = net_keys[net]

        # A queue of (direction, node) to visit. The direction is the Links
        # entry which describes the direction in which we last moved to reach
        # the node (or None for the root).
        to_visit = deque([(None, routing_tree)])
        while to_visit:
            direction, node = to_visit.popleft()

            x, y = node.chip

            # Determine the set of directions we must travel to reach the
            # children
            out_directions = set()
            for child_direction, child in node.children:
                # Note that if the direction is unspecified, we simply
                # (silently) don't add a route for that child.
                if child_direction is not None:
                    out_directions.add(child_direction)

                # Search the next steps of the route too
                if isinstance(child, RoutingTree):
                    assert child_direction is not None
                    to_visit.append((child_direction, child))

            # Add a routing entry when the direction changes
            if (key, mask) in route_sets[(x, y)]:
                # If there is an existing route set raise an error if the out
                # directions are not equivalent.
                if route_sets[(x, y)][(key, mask)].outs != out_directions:
                    raise MultisourceRouteError(key, mask, (x, y))

                # Otherwise, add the input directions as this represents a
                # merge of the routes.
                route_sets[(x, y)][(key, mask)].ins.add(direction)
            else:
                # Otherwise create a new route set
                route_sets[(x, y)][(key, mask)] = _InOutPair(
                    set([direction]), set(out_directions)
                )

    # Construct the routing tables from the route sets
    routing_tables = defaultdict(list)
    for (x, y), routes in iteritems(route_sets):
        for (key, mask), route in iteritems(routes):
            # Remove default routes where possible
            if omit_default_routes and (len(route.ins) == 1 and
                                        route.outs == route.ins):
                # This route can be removed, so skip it.
                continue

            # Add the route
            routing_tables[(x, y)].append(
                RoutingTableEntry(route.outs, key, mask)
            )

    return routing_tables


class MultisourceRouteError(Exception):
    """Indicates that two nets with the same key and mask would cause packets
    to become duplicated.
    """
    def __init__(self, key, mask, coordinate):
        self.key = key
        self.mask = mask
        self.x, self.y = coordinate

    def __str__(self):
        return ("Two different nets with the same key ({0.key:#010x}) and "
                "mask ({0.mask:#010x}) fork differently at ({0.x}, {0.y})".
                format(self))
