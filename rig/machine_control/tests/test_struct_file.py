import pytest
from rig.machine_control.struct_file import read_struct_file,read_conf_file,num,Struct,StructField
@pytest.mark.parametrize('s, val',[(b'10',10),(b'0x3a',58)])
def test_num(s,val):assert num(s)==val
no_size=b'\n# ------\nname = struct_1\nbase = 0x7fffe\n\nfield    C    0x00    %04x    0   # Comment\n\n# -------\nname = struct_2\n'
no_size_after=b'\n# ------\nname = struct_1\nbase = 0x7fffe\n\nfield    C    0x00    %04x    0   # Comment\n'
no_base=b'\n# ------\nname = struct_1\nsize = 256\n\nfield    C    0x00    %04x    0   # Comment\n\n# -------\nname = struct_2\n'
no_base_after=b'\n# ------\nname = struct_1\nsize = 256\n\nfield    C    0x00    %04x    0   # Comment\n'
neither_size_base=b'\n# ------\nname = struct_1\n\nfield    v    0x00    %04x    0   # Comment\n\n# -------\nname = struct_2\n'
@pytest.mark.parametrize('data, reason',[(no_size,'size'),(no_size_after,'size'),(no_base,'base'),(no_base_after,'base'),(neither_size_base,'size')])
def test_missing_sections(data,reason):
 with pytest.raises(ValueError) as excinfo:read_struct_file(data)
 assert reason in str(excinfo.value)
invalid_field=b'\neggs = spam\n'
@pytest.mark.parametrize('data, reason',[(invalid_field,'eggs')])
def test_invalid_field_name(data,reason):
 with pytest.raises(ValueError) as excinfo:read_struct_file(data)
 assert reason in str(excinfo.value)
invalid_syntax=b'name = test\nsize = 0x00\nbase = 0x00\n\nx 1 2 3\n'
@pytest.mark.parametrize('data',[invalid_syntax])
def test_invalid_syntax(data):
 with pytest.raises(ValueError) as excinfo:read_struct_file(data)
 assert 'syntax' in str(excinfo.value);assert 'line 4' in str(excinfo.value)
valid=b'\n# ----\nname = sv\nsize = 256\nbase = 0x345\n\n# Name   Perl struct pack   Offset    printf    default    comment\nspam     c                  0x00      %c        0          # Test\neggs     V                  0x0A      %d        4          # Test\n\n# ---\nname = sd\nsize = 128\nbase = 0\n\narthur[16]   A16                0x00      %f        0          # Test\n'
@pytest.mark.parametrize('data',[valid])
def test_valid_data(data):structs=read_struct_file(data);assert b'sv' in structs;sv=structs[b'sv'];assert sv.base==837;assert sv.size==256;assert b'sd' in structs;sd=structs[b'sd'];assert sd.base==0;assert sd.size==128;assert b'spam' in sv;spam=sv[b'spam'];assert spam.pack_chars==b'b';assert spam.offset==0;assert spam.printf==b'%c';assert spam.default==0;assert spam.length==1;assert b'eggs' in sv;eggs=sv[b'eggs'];assert eggs.pack_chars==b'I';assert eggs.offset==10;assert eggs.printf==b'%d';assert eggs.default==4;assert eggs.length==1;assert b'arthur' in sd;arthur=sd[b'arthur'];assert arthur.pack_chars==b'16s';assert arthur.offset==0;assert arthur.length==16
conf_file=b'\nspam    0xab\neggs    44\n'
bad_conf_file_a=b'\nfield_with_no_value\n'
bad_conf_file_b=b'\nfield_with_badly_formatted_value   oops\n'
@pytest.mark.parametrize('data',[conf_file])
def test_read_conf_file(data):conf=read_conf_file(data);assert len(conf)==2;assert conf[b'spam']==171;assert conf[b'eggs']==44
@pytest.mark.parametrize('data',[bad_conf_file_a,bad_conf_file_b])
def test_read_conf_file_fails(data):
 with pytest.raises(ValueError) as excinfo:read_conf_file(data)
 assert 'syntax error' in str(excinfo.value)
class TestStruct(object):
 def test_update_default_values(self):
  'Create a simple struct object, with one field.';s=Struct('test');s[b'field']=StructField('I',0,'%d',65535,1);assert s[b'field'].default==65535;s.update_default_values(field=43947);assert s[b'field'].default==43947
  with pytest.raises(KeyError) as excinfo:s.update_default_values(non_existent=255)
  assert 'non_existent' in str(excinfo.value)
 def test_pack(self):'Test packing a struct into bytes.';s=Struct('test',size=6);s['a']=StructField(b'I',0,'%d',2882390782,1);s['b']=StructField(b'H',4,'%d',41137,1);assert s.pack()==b'\xfe\xca\xcd\xab\xb1\xa0'
