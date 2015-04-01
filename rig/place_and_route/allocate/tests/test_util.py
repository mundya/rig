'Generic correctness tests applicable to all allocation algorithms.'
from rig.place_and_route.allocate.util import slices_overlap,align
def test_slices_overlap():assert not slices_overlap(slice(0,1),slice(2,3));assert not slices_overlap(slice(0,2),slice(2,4));assert not slices_overlap(slice(2,3),slice(0,1));assert not slices_overlap(slice(2,4),slice(0,2));assert not slices_overlap(slice(0,0),slice(0,0));assert not slices_overlap(slice(0,0),slice(1,1));assert not slices_overlap(slice(0,0),slice(0,1));assert not slices_overlap(slice(1,1),slice(0,0));assert not slices_overlap(slice(0,1),slice(0,0));assert slices_overlap(slice(3,8),slice(3,8));assert slices_overlap(slice(0,2),slice(1,2));assert slices_overlap(slice(0,2),slice(1,3));assert slices_overlap(slice(0,2),slice(0,3));assert slices_overlap(slice(0,2),slice(0,2));assert slices_overlap(slice(1,2),slice(0,2));assert slices_overlap(slice(1,3),slice(0,2));assert slices_overlap(slice(0,3),slice(0,2));assert slices_overlap(slice(0,2),slice(0,2))
def test_align():
 for alignment in range(1,8):
  assert align(0,alignment)==0
  for target in [x*alignment for x in range(1,8)]:
   for offset in range(alignment):assert align(target-offset,alignment)==target
