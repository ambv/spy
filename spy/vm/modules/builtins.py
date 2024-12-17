"""
Second half of the `builtins` module.

The first half is in vm/b.py. See its docstring for more details.
"""

from typing import TYPE_CHECKING, Any
from spy.vm.builtin import builtin_func
from spy.vm.primitive import W_F64, W_I32, W_Bool, W_Dynamic, W_Void
from spy.vm.object import W_Object, W_Type
from spy.vm.str import W_Str
from spy.vm.function import W_FuncType
from spy.vm.b import BUILTINS, B

if TYPE_CHECKING:
    from spy.vm.vm import SPyVM

PY_PRINT = print  # type: ignore

@BUILTINS.builtin_func(color='blue')
def w_STATIC_TYPE(vm: 'SPyVM', w_expr: W_Object) -> W_Type:
    msg = ("STATIC_TYPE should never be called at runtime. "
           "It's special-cased by ASTFrame")
    raise NotImplementedError(msg)

@BUILTINS.builtin_func
def w_abs(vm: 'SPyVM', w_x: W_I32) -> W_I32:
    x = vm.unwrap_i32(w_x)
    res = vm.ll.call('spy_builtins$abs', x)
    return vm.wrap(res) # type: ignore

@BUILTINS.builtin_func
def w_print(vm: 'SPyVM', w_x: W_Dynamic) -> W_Void:
    """
    Super minimal implementation of print().

    It takes just one argument.
    """
    if isinstance(w_x, (W_I32, W_F64, W_Bool, W_Str, W_Void)):
        PY_PRINT(vm.unwrap(w_x))
    else:
        PY_PRINT(w_x)
    return B.w_None


@BUILTINS.builtin_func
def w_print_i32(vm: 'SPyVM', w_x: W_I32) -> W_Void:
    PY_PRINT(vm.unwrap(w_x))
    return B.w_None

@BUILTINS.builtin_func
def w_print_f64(vm: 'SPyVM', w_x: W_F64) -> W_Void:
    PY_PRINT(vm.unwrap(w_x))
    return B.w_None

@BUILTINS.builtin_func
def w_print_bool(vm: 'SPyVM', w_x: W_Bool) -> W_Void:
    PY_PRINT(vm.unwrap(w_x))
    return B.w_None

@BUILTINS.builtin_func
def w_print_void(vm: 'SPyVM', w_x: W_Void) -> W_Void:
    PY_PRINT(vm.unwrap(w_x))
    return B.w_None

@BUILTINS.builtin_func
def w_print_str(vm: 'SPyVM', w_x: W_Str) -> W_Void:
    PY_PRINT(vm.unwrap(w_x))
    return B.w_None


# this should belong to function.py, but we cannot put it there because of
# circular import issues
@builtin_func('builtins')
def w_functype_eq(vm: 'SPyVM', w_ft1: W_FuncType, w_ft2: W_FuncType) -> W_Bool:
    return vm.wrap(w_ft1 == w_ft2)
