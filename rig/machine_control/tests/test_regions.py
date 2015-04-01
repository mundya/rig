import pytest
from ..regions import get_region_for_chip,compress_flood_fill_regions,minimise_regions,RegionTree
@pytest.mark.parametrize('x, y, level, region',[(0,0,0,1),(0,0,1,65537),(0,0,2,131073),(0,0,3,196609),(64,72,0,32),(64,72,1,1078001665),(64,72,2,1078067456),(64,72,3,1078657025),(255,253,0,32768),(255,253,1,3233906688),(255,253,2,4042424320),(255,253,3,4244570240),(255,0,0,8),(255,0,1,3221291016),(255,0,2,4026662920),(255,0,3,4228055048)])
def test_get_region_for_chip(x,y,level,region):assert get_region_for_chip(x,y,level)==region
@pytest.mark.parametrize('chips, regions',[({(i,j) for i in range(4) for j in range(4)},{131073}),({(i+4,j) for i in range(4) for j in range(4)},{131074}),({(i,j+4) for i in range(4) for j in range(4)},{131088}),({(i,j) for i in range(4) for j in range(4)}|{(i+4,j) for i in range(4) for j in range(4)},{131075})])
def test_reduce_regions(chips,regions):'Test hierarchical reduction of regions.';assert set(minimise_regions(chips))==regions
def test_get_regions_and_cores_for_floodfill():'This test looks at trying to minimise the number of flood-fills required\n    to load an application.  The required chips are in two level-3 regions and\n    have different core requirements for each chip.\n    ';targets={(0,0):{1,2,4},(0,1):{1,2,4},(1,0):{2,3},(4,0):{1,2,4}};fills={(get_region_for_chip(0,0,3)|get_region_for_chip(0,1,3),1<<1|1<<2|1<<4),(get_region_for_chip(1,0,3),1<<2|1<<3),(get_region_for_chip(4,0,3),1<<1|1<<2|1<<4)};assert set(compress_flood_fill_regions(targets))==fills
class TestRegionTree(object):
 def test_add_coordinate_fails(self):
  t=RegionTree(level=3)
  with pytest.raises(ValueError):t.add_coordinate(16,0)
  with pytest.raises(ValueError):t.add_coordinate(0,16)
 def test_add_coordinate_normal(self):
  t=RegionTree();t.add_coordinate(8,0);assert t.subregions[0].subregions[0].subregions[2].locally_selected=={0};t.add_coordinate(0,8);assert t.subregions[0].subregions[0].subregions[8].locally_selected=={0};t.add_coordinate(255,255);assert t.subregions[15].subregions[15].subregions[15].locally_selected=={15};pr=t.subregions[0].subregions[0];pr.add_coordinate(0,0);sr=t.subregions[0].subregions[0].subregions[0]
  for i in range(4):
   for j in range(4):assert sr.add_coordinate(i,j)==(i==3 and j==3)
  assert pr.add_coordinate(3,3) is False;assert pr.locally_selected=={0};assert set(t.get_regions())=={131073,get_region_for_chip(255,255),get_region_for_chip(0,8),get_region_for_chip(8,0)}
