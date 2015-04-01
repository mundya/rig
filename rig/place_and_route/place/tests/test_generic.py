'Generic correctness tests applicable to all placement algorithms.'
import pytest
from six import iteritems
from rig.netlist import Net
from rig.machine import Machine,Cores
from rig.place_and_route.exceptions import InsufficientResourceError
from rig.place_and_route.exceptions import InvalidConstraintError
from rig.place_and_route.constraints import LocationConstraint,ReserveResourceConstraint
from rig.place_and_route import place as default_place
from rig.place_and_route.place.hilbert import place as hilbert_place
ALGORITHMS_UNDER_TEST=[(default_place,{}),(hilbert_place,{})]
@pytest.mark.parametrize('algorithm,kwargs',ALGORITHMS_UNDER_TEST)
def test_null_placement(algorithm,kwargs):'Test algorithms correctly handle placements with no vertices to\n    place.\n    ';machine=Machine(2,2);assert algorithm({},[],machine,[],**kwargs)=={};machine=Machine(0,0);assert algorithm({},[],machine,[],**kwargs)=={}
@pytest.mark.parametrize('algorithm,kwargs',ALGORITHMS_UNDER_TEST)
def test_impossible(algorithm,kwargs):
 "Test that algorithms fail to place things which simply can't fit.";machine=Machine(0,0)
 with pytest.raises(InsufficientResourceError):algorithm({object():{Cores:1}},[],machine,[],**kwargs)
 machine=Machine(2,2,dead_chips=set((x,y) for x in range(2) for y in range(2)))
 with pytest.raises(InsufficientResourceError):algorithm({object():{Cores:1}},[],machine,[],**kwargs)
 machine=Machine(2,2,chip_resources={Cores:1})
 with pytest.raises(InsufficientResourceError):algorithm({object():{Cores:2}},[],machine,[],**kwargs)
 machine=Machine(2,2,chip_resources={Cores:1},chip_resource_exceptions={(0,0):{Cores:2}},dead_chips=set([(0,0)]))
 with pytest.raises(InsufficientResourceError):algorithm({object():{Cores:2}},[],machine,[],**kwargs)
@pytest.mark.parametrize('algorithm,kwargs',ALGORITHMS_UNDER_TEST)
def test_trivial(algorithm,kwargs):
 'Test that algorithms succeed in placing trivial cases.\n\n    Note that these tests are intended to be so easy that it will just weed out\n    fundamental failures of placement algorithms. Note that in general,\n    however, it is perfectly acceptable for problems to exist which not all\n    placers can handle.\n    ';machine=Machine(1,1);vertex=object();assert algorithm({vertex:{Cores:1}},[],machine,[],**kwargs)=={vertex:(0,0)};machine=Machine(10,10);vertex=object();placement=algorithm({vertex:{Cores:1}},[],machine,[],**kwargs);assert vertex in placement;assert placement[vertex] in machine;machine=Machine(1,1,chip_resources={Cores:8});vertices=[object() for _ in range(8)];assert algorithm({v:{Cores:1} for v in vertices},[],machine,[],**kwargs)=={v:(0,0) for v in vertices};machine=Machine(1,1,chip_resources={Cores:8});vertices=[object() for _ in range(8)];nets=[Net(vertices[0],vertices[1:])];assert algorithm({v:{Cores:1} for v in vertices},nets,machine,[],**kwargs)=={v:(0,0) for v in vertices};machine=Machine(10,10,chip_resources={Cores:1});vertices=[object() for _ in range(8)];placement=algorithm({v:{Cores:1} for v in vertices},[],machine,[],**kwargs);used_chips=set()
 for v in vertices:assert v in placement;assert placement[v] in machine;assert placement[v] not in used_chips;used_chips.add(v)
 machine=Machine(10,10,chip_resources={Cores:1});vertices=[object() for _ in range(8)];nets=[Net(vertices[0],vertices[1:])];placement=algorithm({v:{Cores:1} for v in vertices},nets,machine,[],**kwargs);used_chips=set()
 for v in vertices:assert v in placement;assert placement[v] in machine;assert placement[v] not in used_chips;used_chips.add(v)
 machine=Machine(10,10,chip_resources={Cores:1});vertices=[object() for _ in range(8)];nets=[Net(vertices[0],vertices[1:4]),Net(vertices[4],vertices[5:])];placement=algorithm({v:{Cores:1} for v in vertices},nets,machine,[],**kwargs);used_chips=set()
 for v in vertices:assert v in placement;assert placement[v] in machine;assert placement[v] not in used_chips;used_chips.add(v)
@pytest.mark.parametrize('algorithm,kwargs',ALGORITHMS_UNDER_TEST)
def test_location_constraint(algorithm,kwargs):
 'Test that the LocationConstraint is respected.';machine=Machine(1,1);vertex=object();constraints=[LocationConstraint(vertex,(0,0))];assert algorithm({vertex:{Cores:1}},[],machine,constraints,**kwargs)=={vertex:(0,0)};machine=Machine(10,10);vertex=object();constraints=[LocationConstraint(vertex,(5,5))];assert algorithm({vertex:{Cores:1}},[],machine,constraints,**kwargs)=={vertex:(5,5)};machine=Machine(5,5);manual_placement={object():(x,y) for x in range(5) for y in range(5)};constraints=[LocationConstraint(v,xy) for (v,xy) in iteritems(manual_placement)];assert algorithm({v:{Cores:1} for v in manual_placement},[],machine,constraints,**kwargs)==manual_placement;machine=Machine(2,1,chip_resources={Cores:1});constrained_vertex=object();free_vertex=object();constraints=[LocationConstraint(constrained_vertex,(0,0))];assert algorithm({constrained_vertex:{Cores:1},free_vertex:{Cores:1}},[],machine,constraints,**kwargs)=={constrained_vertex:(0,0),free_vertex:(1,0)};machine=Machine(2,2,dead_chips=set([(0,0)]));vertex=object();constraints=[LocationConstraint(vertex,(0,0))]
 with pytest.raises(InvalidConstraintError):algorithm({vertex:{Cores:1}},[],machine,constraints,**kwargs)
 machine=Machine(2,2);vertex=object();constraints=[LocationConstraint(vertex,(2,2))]
 with pytest.raises(InvalidConstraintError):algorithm({vertex:{Cores:1}},[],machine,constraints,**kwargs)
 machine=Machine(1,1,chip_resources={Cores:1});vertex=object();constraints=[LocationConstraint(vertex,(0,0))]
 with pytest.raises(InsufficientResourceError):algorithm({vertex:{Cores:2}},[],machine,constraints,**kwargs)
@pytest.mark.parametrize('algorithm,kwargs',ALGORITHMS_UNDER_TEST)
def test_reserve_resource_constraint(algorithm,kwargs):
 'Test that the ReserveResourceConstraint is respected.';machine=Machine(1,1,chip_resources={Cores:1});vertex=object();constraints=[ReserveResourceConstraint(Cores,slice(0,1))]
 with pytest.raises(InsufficientResourceError):algorithm({vertex:{Cores:1}},[],machine,constraints,**kwargs)
 machine=Machine(1,1,chip_resources={Cores:1});vertex=object();constraints=[ReserveResourceConstraint(Cores,slice(0,1),(0,0))]
 with pytest.raises(InsufficientResourceError):algorithm({vertex:{Cores:1}},[],machine,constraints,**kwargs)
 machine=Machine(1,1,chip_resources={Cores:1},chip_resource_exceptions={(0,0):{Cores:1}});vertex=object();constraints=[ReserveResourceConstraint(Cores,slice(0,1))]
 with pytest.raises(InsufficientResourceError):algorithm({vertex:{Cores:1}},[],machine,constraints,**kwargs)
 machine=Machine(2,2,chip_resources={Cores:2});vertices_resources={object():{Cores:1} for _ in range(4)};constraints=[ReserveResourceConstraint(Cores,slice(1,2))];placements=algorithm(vertices_resources,[],machine,constraints,**kwargs);used_chips=set()
 for vertex in vertices_resources:assert vertex in placements;assert placements[vertex] not in used_chips;used_chips.add(placements[vertex])
 assert len(placements)==4;assert len(used_chips)==4
