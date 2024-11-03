"""
This is just to make it easier to import all the various W_* classes
"""

from spy.vm.primitive import W_Void
from spy.vm.function import W_Func, W_FuncType, W_ASTFunc, W_BuiltinFunc
from spy.vm.builtin import builtin_func
from spy.vm.module import W_Module
from spy.vm.object import (W_Bool, W_F64, W_I32, W_Object, W_Type, W_Dynamic, spytype)
from spy.vm.str import W_Str
from spy.vm.list import W_List
from spy.vm.opimpl import W_OpImpl
