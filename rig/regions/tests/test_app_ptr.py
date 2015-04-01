import mock
import pytest
import struct
from ..app_ptr import create_app_ptr_table
@pytest.mark.parametrize('magic_num, version, timer_period',[(2903706326,305402420,1000),(4294945450,4096,1234)])
def test_create_app_ptr_no_regions(magic_num,version,timer_period):'Creating an application pointer table with no regions should just write\n    out header.\n    ';assert create_app_ptr_table({},magic_num=magic_num,version=version,timer_period=timer_period)==struct.pack('3I',magic_num,version,timer_period)
def test_create_app_ptr():
 'Create a app_ptr table with entries of different sizes and with missing\n    regions.\n    ';r0=mock.Mock(name='region 0',spec_set=['sizeof']);r0.sizeof.return_value=3;r3=mock.Mock(name='region 3',spec_set=['sizeof']);r3.sizeof.return_value=75*4;r4=mock.Mock(name='region 4',spec_set=['sizeof']);r4.sizeof.return_value=2;r5=mock.Mock(name='region 5',spec_set=['sizeof']);r5.sizeof.return_value=1;regions={0:r0,3:r3,4:r4,5:r5};sl=mock.Mock(name='slice');table=create_app_ptr_table(regions,sl);assert len(table)==(3+6)*4;assert table[12:16]==struct.pack('<I',36);assert table[16:20]==b'\x00'*4 or table[16:20]==b'\xff'*4;assert table[20:24]==b'\x00'*4 or table[20:24]==b'\xff'*4;assert table[24:28]==struct.pack('<I',40);assert table[28:32]==struct.pack('<I',340);assert table[32:36]==struct.pack('<I',344)
 for r in (r0,r3,r4,r5):r.sizeof.assert_called_once_with(sl)
