from typing import TYPE_CHECKING, no_type_check
import fixedint
from spy.vm.b import B
from spy.vm.primitive import W_I32, W_Dynamic
from spy.vm.w import W_Func, W_Type, W_Object
from spy.vm.builtin import builtin_func
from . import UNSAFE
from .ptr import W_Ptr, w_make_ptr_type, is_ptr_type
from .misc import sizeof

if TYPE_CHECKING:
    from spy.vm.vm import SPyVM

@UNSAFE.builtin_func(color='blue')
def w_gc_alloc(vm: 'SPyVM', w_T: W_Type) -> W_Dynamic:
    w_ptrtype = vm.call(w_make_ptr_type, [w_T])  # unsafe::ptr[i32]
    assert isinstance(w_ptrtype, W_Type)
    W_MyPtr = vm.unwrap(w_ptrtype)               # W_Ptr[W_I32]
    ITEMSIZE = sizeof(w_T)

    # this is a special builtin function, its C equivalent is automatically
    # generated by c.Context.new_ptr_type
    @no_type_check
    @builtin_func(w_ptrtype.fqn, 'gc_alloc')  # unsafe::ptr[i32]::gc_alloc
    def w_fn(vm: 'SPyVM', w_n: W_I32) -> W_MyPtr:
        n = vm.unwrap_i32(w_n)
        size = ITEMSIZE * n
        addr = vm.ll.call('spy_gc_alloc_mem', size)
        return W_MyPtr(addr, n)

    return w_fn


@UNSAFE.builtin_func(color='blue')
def w_mem_read(vm: 'SPyVM', w_T: W_Type) -> W_Dynamic:
    T = w_T.pyclass

    @no_type_check
    @builtin_func('unsafe', 'mem_read', [w_T.fqn])  # unsafe::mem_read[i32]
    def w_mem_read_T(vm: 'SPyVM', w_addr: W_I32) -> T:
        addr = vm.unwrap_i32(w_addr)
        if w_T is B.w_i32:
            return vm.wrap(vm.ll.mem.read_i32(addr))
        elif w_T is B.w_f64:
            return vm.wrap(vm.ll.mem.read_f64(addr))
        elif issubclass(w_T.pyclass, W_Ptr):
            v_addr, v_length = vm.ll.mem.read_ptr(addr)
            return w_T.pyclass(v_addr, v_length)
        else:
            assert False

    return w_mem_read_T


@UNSAFE.builtin_func(color='blue')
def w_mem_write(vm: 'SPyVM', w_T: W_Type) -> W_Dynamic:
    T = w_T.pyclass

    @no_type_check
    @builtin_func('unsafe', 'mem_write', [w_T.fqn])  # unsafe::mem_write[i32]
    def w_mem_write_T(vm: 'SPyVM', w_addr: W_I32, w_val: T) -> None:
        addr = vm.unwrap_i32(w_addr)
        if w_T is B.w_i32:
            v = vm.unwrap_i32(w_val)
            vm.ll.mem.write_i32(addr, v)
        elif w_T is B.w_f64:
            v = vm.unwrap_f64(w_val)
            vm.ll.mem.write_f64(addr, v)
        elif is_ptr_type(w_T):
            vm.ll.mem.write_ptr(addr, w_val.addr, w_val.length)
        else:
            assert False

    return w_mem_write_T
