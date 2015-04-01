'Tests for BitFields.\n\nPlease note that for historical reasons, in this file instances of\n:py:class:`rig.bitfield.BitField` are commonly named `ks`, standing for `Key\nSpace` (or variants thereof).\n'
import pytest
from rig.bitfield import BitField
def test_bitfield_add_field():
 ks=BitField(64)
 with pytest.raises(ValueError):ks.add_field('out_of_range',start_at=64)
 with pytest.raises(ValueError):ks.add_field('out_of_range',start_at=128)
 with pytest.raises(ValueError):ks.add_field('out_of_range',length=2,start_at=63)
 with pytest.raises(ValueError):ks.add_field('out_of_range',length=2,start_at=128)
 with pytest.raises(ValueError):ks.add_field('zero_length',length=0,start_at=0)
 ks.add_field('obstruction',length=8,start_at=8)
 with pytest.raises(ValueError):ks.add_field('obstructed',length=8,start_at=8)
 with pytest.raises(ValueError):ks.add_field('obstructed',length=16,start_at=0)
 with pytest.raises(ValueError):ks.add_field('obstructed',length=12,start_at=0)
 with pytest.raises(ValueError):ks.add_field('obstructed',length=16,start_at=8)
 with pytest.raises(ValueError):ks.add_field('obstructed',length=12,start_at=12)
 with pytest.raises(ValueError):ks.add_field('obstructed',length=4,start_at=10)
 with pytest.raises(ValueError):ks.add_field('obstruction',length=1,start_at=0)
def test_bitfield_masks():
 ks=BitField(64);ks.add_field('bottom',length=32,start_at=0,tags='Bottom All');ks.add_field('top',length=8,start_at=56,tags='Top All');assert ks.get_mask()==0xff000000ffffffff;assert ks.get_mask(field='bottom')==4294967295;assert ks.get_mask(field='top')==0xff00000000000000;assert ks.get_mask(tag='All')==0xff000000ffffffff;assert ks.get_mask(tag='Bottom')==4294967295;assert ks.get_mask(tag='Top')==0xff00000000000000
 with pytest.raises(AssertionError):assert ks.get_mask(tag='All',field='top')==0xff000000ffffffff
def test_bitfield_keys():
 ks=BitField(32);ks.add_field('a',length=8,start_at=0,tags='A All');ks.add_field('b',length=8,start_at=8,tags='B All');ks.add_field('c',length=8,start_at=16,tags='C All')
 with pytest.raises(AttributeError):ks.d
 with pytest.raises(ValueError):ks(d=123)
 with pytest.raises(ValueError):ks.get_value()
 with pytest.raises(ValueError):ks.get_value(tag='All')
 with pytest.raises(ValueError):ks.get_value(field='a')
 with pytest.raises(ValueError):ks.get_value(tag='A')
 with pytest.raises(ValueError):ks.get_value(field='b')
 with pytest.raises(ValueError):ks.get_value(tag='B')
 with pytest.raises(ValueError):ks.get_value(field='c')
 with pytest.raises(ValueError):ks.get_value(tag='C')
 assert ks.a is None;assert ks.b is None;assert ks.c is None
 with pytest.raises(ValueError):ks_a=ks(a=256)
 with pytest.raises(ValueError):ks_a=ks(a=-1)
 ks_a=ks(a=170);assert ks_a.a==170;assert ks_a.b is None;assert ks_a.c is None;assert ks_a.get_value(field='a')==170;assert ks_a.get_value(tag='A')==170
 with pytest.raises(ValueError):ks_a.get_value()
 with pytest.raises(ValueError):ks_a.get_value(tag='All')
 with pytest.raises(ValueError):ks_a.get_value(field='b')
 with pytest.raises(ValueError):ks_a.get_value(tag='B')
 with pytest.raises(ValueError):ks_a.get_value(field='c')
 with pytest.raises(ValueError):ks_a.get_value(tag='C')
 with pytest.raises(ValueError):ks_a(a=0)
 with pytest.raises(ValueError):ks_a(a=170)
 ks_abc=ks_a(b=187,c=204);assert ks_abc.a==170;assert ks_abc.b==187;assert ks_abc.c==204;assert ks_abc.get_value()==13417386;assert ks_abc.get_value(field='a')==170;assert ks_abc.get_value(field='b')==47872;assert ks_abc.get_value(field='c')==13369344;assert ks_abc.get_value(tag='All')==13417386;assert ks_abc.get_value(tag='A')==170;assert ks_abc.get_value(tag='B')==47872;assert ks_abc.get_value(tag='C')==13369344;ks_a0=ks(a=0);assert ks_a0.get_value(field='a')==0;ks_a1=ks(a=1);assert ks_a1.get_value(field='a')==1;ks_aFF=ks(a=255);assert ks_aFF.get_value(field='a')==255
def test_bitfield_tags():
 ks=BitField(6);ks.add_field('a',length=1,start_at=0);ks.add_field('b',length=1,start_at=1,tags='B');ks.add_field('c',length=1,start_at=2,tags='C C_');ks.add_field('d',length=1,start_at=3,tags=['D']);ks.add_field('e',length=1,start_at=4,tags=['E','E_']);ks_def=ks(a=1,b=1,c=1,d=1,e=1);assert ks_def.get_mask()==31;assert ks_def.get_mask('B')==2;assert ks_def.get_mask('C')==4;assert ks_def.get_mask('C_')==4;assert ks_def.get_mask('D')==8;assert ks_def.get_mask('E')==16;assert ks_def.get_mask('E_')==16;assert ks_def.get_value()==31;assert ks_def.get_value('B')==2;assert ks_def.get_value('C')==4;assert ks_def.get_value('C_')==4;assert ks_def.get_value('D')==8;assert ks_def.get_value('E')==16;assert ks_def.get_value('E_')==16
 with pytest.raises(ValueError):ks.get_mask('Non-existant')
 with pytest.raises(ValueError):ks.get_value('Non-existant')
 ks_a0=ks(a=0);ks_a0.add_field('a0',length=1,start_at=5,tags='A0');ks_a1=ks(a=1);ks_a1.add_field('a1',length=1,start_at=5,tags='A1');assert ks.get_mask('A0')==1;assert ks.get_mask('A1')==1;assert ks_a0.get_mask('A0')==33;assert ks_a0(a0=1).get_value('A0')==32;assert ks.get_mask('A1')==1;assert ks_a1.get_mask('A1')==33;assert ks_a1(a1=1).get_value('A1')==33;assert ks.get_mask('A0')==1
def test_bitfield_hierachy():
 ks=BitField(8);ks.add_field('always',length=1,start_at=7);ks.add_field('split',length=1,start_at=6);ks_s0=ks(split=0);ks_s0.add_field('s0_btm',length=3,start_at=0);ks_s0.add_field('s0_top',length=3,start_at=3);ks_s1=ks(split=1);ks_s1.add_field('s1_btm',length=2,start_at=0);ks_s1.add_field('s1_top',length=2,start_at=2);ks_s1s=ks_s1(s1_btm=0,s1_top=0);ks_s1s.add_field('split2',length=2,start_at=4)
 with pytest.raises(AttributeError):ks.s0_top
 with pytest.raises(AttributeError):ks.s0_btm
 with pytest.raises(AttributeError):ks.s1_top
 with pytest.raises(AttributeError):ks.s1_btm
 with pytest.raises(AttributeError):ks.split2
 ks_s0_defined=ks(always=1,split=0,s0_btm=3,s0_top=5);assert ks_s0_defined.always==1;assert ks_s0_defined.split==0;assert ks_s0_defined.s0_btm==3;assert ks_s0_defined.s0_top==5;assert ks_s0_defined.get_value()==171;assert ks_s0_defined.get_mask()==255;ks(s0_btm=3,s0_top=5,always=1,split=0)
 with pytest.raises(AttributeError):ks_s0_defined.s1_btm
 with pytest.raises(AttributeError):ks_s0_defined.s1_top
 with pytest.raises(AttributeError):ks_s0_defined.split2
 ks_s1_selected=ks(split=1);assert ks_s1_selected.split==1;assert ks_s1_selected.always is None;assert ks_s1_selected.s1_btm is None;assert ks_s1_selected.s1_top is None
 with pytest.raises(AttributeError):ks_s1_selected.s0_btm
 with pytest.raises(AttributeError):ks_s1_selected.s0_top
 with pytest.raises(AttributeError):ks_s1_selected.split2
 ks_s1s_selected=ks(always=1,split=1,s1_btm=0,s1_top=0,split2=3);assert ks_s1s_selected.always==1;assert ks_s1s_selected.split==1;assert ks_s1s_selected.s1_btm==0;assert ks_s1s_selected.s1_top==0;assert ks_s1s_selected.split2==3
 with pytest.raises(AttributeError):ks(s0_btm=3,s0_top=5)
 ks_obst=BitField(32);ks_obst.add_field('split');ks_obst_s1=ks_obst(split=1);ks_obst_s1.add_field('obstruction',start_at=0)
 with pytest.raises(ValueError):ks_obst.add_field('obstructed',start_at=0)
 ks_obst.add_field('obstructed');ks_obst.assign_fields();assert ks_obst.get_mask(field='obstructed')==2
def test_auto_length():
 ks_never=BitField(8);ks_never.add_field('never',start_at=0);ks_never.assign_fields();assert ks_never.get_mask()==1
 with pytest.raises(ValueError):ks_never.add_field('obstructed',start_at=0)
 ks_once=BitField(8);ks_once.add_field('once',start_at=0);once_fifteen=ks_once(once=15)
 with pytest.raises(ValueError):ks_once.get_mask()
 with pytest.raises(ValueError):once_fifteen.get_value()
 ks_once.assign_fields();assert once_fifteen.get_value()==15;assert once_fifteen.get_mask()==15;assert ks_never(never=0).never==0;assert ks_never(never=1).never==1
 with pytest.raises(ValueError):ks_never(never=2)
 ks=BitField(64);ks.add_field('auto_length',start_at=32)
 for val in [0,1,3735928559,4660]:ks_val=ks(auto_length=val);assert ks_val.auto_length==val
 ks.assign_fields();assert ks.get_mask()==0xffffffff00000000
 with pytest.raises(ValueError):ks(auto_length=4294967296)
 ks_long=BitField(16);ks_long.add_field('too_long',start_at=0);ks_long(too_long=65536)
 with pytest.raises(ValueError):ks_long.assign_fields()
 with pytest.raises(ValueError):ks_long.get_mask()
 ks_h=BitField(16);ks_h.add_field('split',start_at=8);ks_h_s0=ks_h(split=0);ks_h_s0.add_field('s0',start_at=0);ks_h_s2=ks_h(split=2);ks_h_s2.add_field('s2',start_at=0);ks_h_s0_val=ks_h(split=0,s0=16);ks_h_s0_val.assign_fields();assert ks_h_s0_val.get_mask()==799;assert ks_h_s0_val.get_value()==16
 with pytest.raises(ValueError):ks_h(split=0,s0=63)
 with pytest.raises(ValueError):ks_h(split=4)
 with pytest.raises(ValueError):ks_h(split=2,s2=63)
def test_auto_start_at():
 ks=BitField(32);ks.add_field('a',length=4);ks.add_field('b',length=4);ks.add_field('c',length=4)
 with pytest.raises(ValueError):ks.get_mask()
 with pytest.raises(ValueError):ks(a=0).get_value(field='a')
 ks.assign_fields();assert ks.get_mask(field='c')==3840;assert ks.get_mask(field='b')==240;assert ks.get_mask(field='a')==15;assert ks.get_mask()==4095;ks.add_field('full_obstruction',length=4,start_at=12);ks.add_field('d',length=4);ks.assign_fields();assert ks.get_mask(field='d')==983040;ks.add_field('partial_obstruction',length=4,start_at=22);ks.add_field('e',length=4);ks.add_field('f',length=2);ks.assign_fields();assert ks.get_mask(field='e')==1006632960;assert ks.get_mask(field='f')==3145728;ks.add_field('last_straw',length=4)
 with pytest.raises(ValueError):ks.assign_fields()
 ks_h=BitField(32);ks_h.add_field('split',length=4);ks_h.add_field('always_before',length=4);ks_h_s0=ks_h(split=0);ks_h_s0.add_field('s0',length=4);ks_h_s1=ks_h(split=1);ks_h_s1.add_field('s1',length=8);ks_h(split=0).assign_fields();assert ks_h(split=0).get_mask(field='split')==15;assert ks_h(split=0).get_mask(field='always_before')==240;assert ks_h(split=0).get_mask(field='s0')==3840;assert ks_h(split=0).get_mask()==4095
 with pytest.raises(ValueError):ks_h_s0.add_field('obstructed',start_at=8)
 assert ks_h(split=1).get_mask(field='split')==15;assert ks_h(split=1).get_mask(field='always_before')==240;assert ks_h(split=1).get_mask(field='s1')==65280;assert ks_h(split=1).get_mask()==65535
 with pytest.raises(ValueError):ks_h_s1.add_field('obstructed',length=4,start_at=8)
def test_full_auto():ks=BitField(32);ks.add_field('a');ks.add_field('b');ks(a=255,b=4095);ks.assign_fields();assert ks.get_mask(field='a')==255;assert ks.get_mask(field='b')==1048320;assert ks.get_mask()==1048575;ks_h=BitField(32);ks_h.add_field('s');ks_h(s=0).add_field('s0');ks_h(s=0,s0=0).add_field('s00');ks_h(s=0,s0=1).add_field('s01');ks_h(s=1).add_field('s1');ks_h(s=1,s1=0).add_field('s10');ks_h(s=1,s1=1).add_field('s11');ks_h.assign_fields();assert ks_h.get_mask(field='s')==1;assert ks_h(s=0).get_mask(field='s0')==2;assert ks_h(s=1).get_mask(field='s1')==2;assert ks_h(s=0,s0=0).get_mask(field='s00')==4;assert ks_h(s=0,s0=1).get_mask(field='s01')==4;assert ks_h(s=1,s1=0).get_mask(field='s10')==4;assert ks_h(s=1,s1=1).get_mask(field='s11')==4
def test_eq():ks1=BitField(32);ks2=BitField(32);assert ks1!=ks2;ks1.add_field('test',length=2,start_at=1);ks2.add_field('test',length=2,start_at=1);assert ks1!=ks2;ks1_val=ks1(test=1);ks2_val=ks2(test=1);assert ks1_val!=ks2_val;ks1.add_field('test1',length=10,start_at=20);ks2.add_field('test2',length=20,start_at=10);assert ks1!=ks2;ks1_val2=ks1(test1=10);ks2_val2=ks2(test2=20);assert ks1_val2!=ks2_val2;ks=BitField(32);assert ks==ks;ks.add_field('test');ks.add_field('split');ks_s0=ks(split=0);ks_s0.add_field('s0');ks_s1=ks(split=1);ks_s1.add_field('s1');assert ks==ks;ks_val0=ks(test=0,split=1,s1=2);ks_val1=ks(test=0)(split=1,s1=2);ks_val2=ks(test=0,split=1)(s1=2);ks_val3=ks(test=0)(split=1)(s1=2);assert ks_val0==ks_val1==ks_val2==ks_val3;assert ks!=ks_val0;ks_val_diff=ks(test=123);assert ks_val_diff!=ks_val0
def test_repr():ks=BitField(128);ks.add_field('always');ks.add_field('split');ks_s0=ks(split=0);ks_s0.add_field('s0');ks_s1=ks(split=1);ks_s1.add_field('s1');assert '128' in repr(ks);assert 'BitField' in repr(ks);assert "'always'" in repr(ks);assert "'split'" in repr(ks);assert '12345' in repr(ks(always=12345));assert "'s0'" not in repr(ks);assert "'s1'" not in repr(ks);assert "'s0'" in repr(ks_s0);assert "'s1'" not in repr(ks_s0);assert "'s0'" not in repr(ks_s1);assert "'s1'" in repr(ks_s1)
