import numpy as np
import pytest
from rig.type_casts import float_to_fix,fix_to_float,NumpyFloatToFixConverter
import struct
class TestFloatToFix(object):
 'Test converting from a float to a fixed point.\n    '
 @pytest.mark.parametrize('signed, n_bits, n_frac',[(True,32,32),(False,32,33),(False,-1,3),(False,32,-1)])
 def test_invalid_parameters(self,signed,n_bits,n_frac):
  with pytest.raises(ValueError):float_to_fix(signed,n_bits,n_frac)
 @pytest.mark.parametrize('value, n_bits, n_frac, output',[(.5,8,4,8),(.5,8,5,16),(.5,8,6,32),(.5,8,7,64),(.5,8,8,128),(.25,8,4,4),(.75,8,4,12),(1.75,8,4,28),(-1.75,8,4,0)])
 def test_no_saturate_unsigned(self,value,n_bits,n_frac,output):assert float_to_fix(False,n_bits,n_frac)(value)==output
 @pytest.mark.parametrize('value, n_bits, n_frac, output',[(.5,8,4,8),(.5,8,5,16),(.5,8,6,32),(.5,8,7,64),(.25,8,4,4),(.75,8,4,12),(-.5,8,4,248),(-.5,8,5,240),(-.5,8,6,224),(-.5,8,7,192),(-.25,8,4,252),(-.75,8,4,244),(-.25,8,1,0),(1.75,8,4,28),(-1.75,8,4,228),(-2.75,8,4,212),(-1.,8,4,240),(-7.9375,8,4,129),(-8,8,4,128),(-16,8,4,128),(-1.,8,3,248),(-1.,8,2,252),(-1.,8,1,254),(-1.,16,1,65534),(-1.,16,2,65532)])
 def test_no_saturate_signed(self,value,n_bits,n_frac,output):assert float_to_fix(True,n_bits,n_frac)(value)==output
 @pytest.mark.parametrize('value, n_bits, n_frac, output',[(2**4,8,4,255),(2**4-1+sum(2**(-n) for n in range(1,6)),8,4,255)])
 def test_saturate_unsigned(self,value,n_bits,n_frac,output):assert float_to_fix(False,n_bits,n_frac)(value)==output
class TestFixToFloat(object):
 @pytest.mark.parametrize('signed, n_bits, n_frac',[(True,32,32),(False,32,33),(False,-1,3),(False,32,-1)])
 def test_invalid_parameters(self,signed,n_bits,n_frac):
  with pytest.raises(ValueError):fix_to_float(signed,n_bits,n_frac)
 @pytest.mark.parametrize('bits, signed, n_bits, n_frac, value',[(255,False,8,0,255.),(255,True,8,0,-127.),(255,False,8,1,127.5),(255,True,8,1,-63.5)])
 def test_fix_to_float(self,bits,signed,n_bits,n_frac,value):assert value==fix_to_float(signed,n_bits,n_frac)(bits)
class TestNumpyFloatToFixConverter(object):
 @pytest.mark.parametrize('signed, n_bits, n_frac',[(True,32,32),(False,32,33),(False,32,-1),(False,-1,1),(False,31,30)])
 def test_init_fails(self,signed,n_bits,n_frac):
  with pytest.raises(ValueError):NumpyFloatToFixConverter(signed,n_bits,n_frac)
 @pytest.mark.parametrize('signed, n_bits, dtype, n_bytes',[(False,8,np.uint8,1),(True,8,np.int8,1),(False,16,np.uint16,2),(True,16,np.int16,2),(False,32,np.uint32,4),(True,32,np.int32,4),(False,64,np.uint64,8),(True,64,np.int64,8)])
 def test_dtypes(self,signed,n_bits,dtype,n_bytes):'Check that the correcy dtype is returned.';fpf=NumpyFloatToFixConverter(signed,n_bits,0);assert fpf.dtype==dtype;assert fpf.bytes_per_element==n_bytes
 @pytest.mark.parametrize('n_bits, n_frac, values, dtype',[(8,4,[.5,.25,.125,.0625],np.uint8),(8,3,[.5,.25,.125,.0625],np.uint8),(8,2,[.5,.25,.125,.0625],np.uint8),(8,1,[.5,.25,.125,.0625],np.uint8),(8,0,[.5,.25,.125,.0625],np.uint8),(8,8,[.5,.25,.125,.0625],np.uint8),(16,12,[.5,.25,.125,.0625],np.uint16),(32,15,[.5,.25,.125,.0625],np.uint32)])
 def test_unsigned_no_saturate(self,n_bits,n_frac,values,dtype):fpf=NumpyFloatToFixConverter(False,n_bits,n_frac);vals=fpf(np.array(values));ftf=float_to_fix(False,n_bits,n_frac);assert np.all(vals==np.array([ftf(v) for v in values]));assert vals.dtype==dtype
 @pytest.mark.parametrize('n_bits, n_frac, values, dtype',[(8,4,[.5,.25,.125,.0625,-.5],np.int8),(8,3,[.5,.25,.125,.0625,-.25],np.int8),(8,2,[.5,.25,.125,.0625,-.33],np.int8),(8,1,[.5,.25,.125,.0625,-.25],np.int8),(8,0,[.5,.25,.125,.0625,-.23],np.int8),(16,12,[.5,.25,.125,.0625,-.45],np.int16),(32,15,[.5,.25,.125,.0625,-.77],np.int32)])
 def test_signed_no_saturate(self,n_bits,n_frac,values,dtype):fpf=NumpyFloatToFixConverter(True,n_bits,n_frac);vals=fpf(np.array(values));c={8:'B',16:'H',32:'I'}[n_bits];ftf=float_to_fix(True,n_bits,n_frac);assert vals.dtype==dtype;assert bytes(vals.data)==struct.pack('{}{}'.format(len(values),c),*[ftf(v) for v in values])
 @pytest.mark.parametrize('signed',[True,False])
 @pytest.mark.parametrize('n_bits, n_frac',[(8,0),(8,4),(16,5),(32,27)])
 def test_saturate(self,signed,n_bits,n_frac):values=[2.**(n_bits-n_frac-(1 if signed else 0)),2.**(n_bits-n_frac-(1 if signed else 0))-1];fpf=NumpyFloatToFixConverter(signed,n_bits,n_frac);vals=fpf(np.array(values));c={8:'B',16:'H',32:'I'}[n_bits];ftf=float_to_fix(signed,n_bits,n_frac);assert bytes(vals.data)==struct.pack('{}{}'.format(len(values),c),*[ftf(v) for v in values])
