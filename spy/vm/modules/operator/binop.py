from typing import TYPE_CHECKING
from spy.vm.b import B
from spy.vm.object import W_Dynamic, W_Type
from spy.vm.opimpl import W_OpImpl, W_OpArg
from . import OP
from .multimethod import MultiMethodTable
if TYPE_CHECKING:
    from spy.vm.vm import SPyVM

MM = MultiMethodTable()

# i32 ops
MM.register('+',  'i32', 'i32', OP.w_i32_add)
MM.register('-',  'i32', 'i32', OP.w_i32_sub)
MM.register('*',  'i32', 'i32', OP.w_i32_mul)
MM.register('/',  'i32', 'i32', OP.w_i32_div)
MM.register('==', 'i32', 'i32', OP.w_i32_eq)
MM.register('!=', 'i32', 'i32', OP.w_i32_ne)
MM.register('<' , 'i32', 'i32', OP.w_i32_lt)
MM.register('<=', 'i32', 'i32', OP.w_i32_le)
MM.register('>' , 'i32', 'i32', OP.w_i32_gt)
MM.register('>=', 'i32', 'i32', OP.w_i32_ge)

# f64 ops
MM.register('+',  'f64', 'f64', OP.w_f64_add)
MM.register('-',  'f64', 'f64', OP.w_f64_sub)
MM.register('*',  'f64', 'f64', OP.w_f64_mul)
MM.register('/',  'f64', 'f64', OP.w_f64_div)
MM.register('==', 'f64', 'f64', OP.w_f64_eq)
MM.register('!=', 'f64', 'f64', OP.w_f64_ne)
MM.register('<' , 'f64', 'f64', OP.w_f64_lt)
MM.register('<=', 'f64', 'f64', OP.w_f64_le)
MM.register('>' , 'f64', 'f64', OP.w_f64_gt)
MM.register('>=', 'f64', 'f64', OP.w_f64_ge)

# mixed i32/f64 ops: this is still small enough that we can write it manually,
# but we should consider the idea of generating this table automatically. This
# will become especially relevant when we add more integer types.
MM.register('+',  'f64', 'i32', OP.w_f64_add)
MM.register('+',  'i32', 'f64', OP.w_f64_add)
MM.register('-',  'f64', 'i32', OP.w_f64_sub)
MM.register('-',  'i32', 'f64', OP.w_f64_sub)
MM.register('*',  'f64', 'i32', OP.w_f64_mul)
MM.register('*',  'i32', 'f64', OP.w_f64_mul)
MM.register('/',  'f64', 'i32', OP.w_f64_div)
MM.register('/',  'i32', 'f64', OP.w_f64_div)
MM.register('==', 'f64', 'i32', OP.w_f64_eq)
MM.register('==', 'i32', 'f64', OP.w_f64_eq)
MM.register('!=', 'f64', 'i32', OP.w_f64_ne)
MM.register('!=', 'i32', 'f64', OP.w_f64_ne)
MM.register('<' , 'f64', 'i32', OP.w_f64_lt)
MM.register('<' , 'i32', 'f64', OP.w_f64_lt)
MM.register('<=', 'f64', 'i32', OP.w_f64_le)
MM.register('<=', 'i32', 'f64', OP.w_f64_le)
MM.register('>' , 'f64', 'i32', OP.w_f64_gt)
MM.register('>' , 'i32', 'f64', OP.w_f64_gt)
MM.register('>=', 'f64', 'i32', OP.w_f64_ge)
MM.register('>=', 'i32', 'f64', OP.w_f64_ge)

# str ops
MM.register('+',  'str', 'str', OP.w_str_add)
MM.register('*',  'str', 'i32', OP.w_str_mul)
MM.register('==', 'str', 'str', OP.w_str_eq)
MM.register('!=', 'str', 'str', OP.w_str_ne)

# dynamic ops
MM.register_partial('+',  'dynamic', OP.w_dynamic_add)
MM.register_partial('*',  'dynamic', OP.w_dynamic_mul)
MM.register_partial('==', 'dynamic', OP.w_dynamic_eq)
MM.register_partial('!=', 'dynamic', OP.w_dynamic_ne)
MM.register_partial('<',  'dynamic', OP.w_dynamic_lt)
MM.register_partial('<=', 'dynamic', OP.w_dynamic_le)
MM.register_partial('>',  'dynamic', OP.w_dynamic_gt)
MM.register_partial('>=', 'dynamic', OP.w_dynamic_ge)


@OP.builtin_func(color='blue')
def w_ADD(vm: 'SPyVM', wop_l: W_OpArg, wop_r: W_OpArg) -> W_OpImpl:
    return MM.lookup(vm, '+', wop_l, wop_r)

@OP.builtin_func(color='blue')
def w_SUB(vm: 'SPyVM', wop_l: W_OpArg, wop_r: W_OpArg) -> W_OpImpl:
    return MM.lookup(vm, '-', wop_l, wop_r)

@OP.builtin_func(color='blue')
def w_MUL(vm: 'SPyVM', wop_l: W_OpArg, wop_r: W_OpArg) -> W_OpImpl:
    return MM.lookup(vm, '*', wop_l, wop_r)

@OP.builtin_func(color='blue')
def w_DIV(vm: 'SPyVM', wop_l: W_OpArg, wop_r: W_OpArg) -> W_OpImpl:
    return MM.lookup(vm, '/', wop_l, wop_r)

def can_use_reference_eq(vm: 'SPyVM', w_ltype: W_Type, w_rtype: W_Type) -> bool:
    """
    We can use 'is' to implement 'eq' if:
      1. the two types have a common ancestor
      2. the common ancestor must be a reference type
    """
    w_common = vm.union_type(w_ltype, w_rtype)
    return w_common is not B.w_object and w_common.is_reference_type(vm)

@OP.builtin_func(color='blue')
def w_EQ(vm: 'SPyVM', wop_l: W_OpArg, wop_r: W_OpArg) -> W_OpImpl:
    from spy.vm.typechecker import typecheck_opimpl
    w_ltype = wop_l.w_static_type
    w_rtype = wop_r.w_static_type
    if w_ltype.pyclass.has_meth_overriden('op_EQ'):
        w_opimpl = w_ltype.pyclass.op_EQ(vm, wop_l, wop_r)
        typecheck_opimpl(vm, w_opimpl, [wop_l, wop_r],
                         dispatch='multi',
                         errmsg='cannot do `{0}` == `{1}`')
        return w_opimpl
    elif can_use_reference_eq(vm, w_ltype, w_rtype):
        w_opimpl = W_OpImpl(OP.w_object_is)
        typecheck_opimpl(vm, w_opimpl, [wop_l, wop_r],
                         dispatch='multi',
                         errmsg='cannot do `{0}` == `{1}`')
        return w_opimpl
    else:
        return MM.lookup(vm, '==', wop_l, wop_r)

@OP.builtin_func(color='blue')
def w_NE(vm: 'SPyVM', wop_l: W_OpArg, wop_r: W_OpArg) -> W_OpImpl:
    from spy.vm.typechecker import typecheck_opimpl
    w_ltype = wop_l.w_static_type
    w_rtype = wop_r.w_static_type
    if w_ltype.pyclass.has_meth_overriden('op_NE'):
        w_opimpl = w_ltype.pyclass.op_NE(vm, wop_l, wop_r)
        typecheck_opimpl(vm, w_opimpl, [wop_l, wop_r],
                         dispatch='multi',
                         errmsg='cannot do `{0}` != `{1}`')
        return w_opimpl
    if can_use_reference_eq(vm, w_ltype, w_rtype):
        w_opimpl = W_OpImpl(OP.w_object_isnot)
        typecheck_opimpl(vm, w_opimpl, [wop_l, wop_r],
                         dispatch='multi',
                         errmsg='cannot do `{0}` != `{1}`')
        return w_opimpl
    return MM.lookup(vm, '!=', wop_l, wop_r)

@OP.builtin_func(color='blue')
def w_UNIVERSAL_EQ(vm: 'SPyVM', wop_l: W_OpArg, wop_r: W_OpArg) -> W_OpImpl:
    from spy.vm.typechecker import typecheck_opimpl
    # XXX this seems wrong: if we do universal_eq(i32, i32), we should get the
    # same as eq(i32, i32), not "w_object_universal_eq". In practice, it's not
    # a problem for now, because it's not exposed to the user, and we use it
    # only on W_Objects.
    w_opimpl = W_OpImpl(OP.w_object_universal_eq)
    typecheck_opimpl(vm, w_opimpl, [wop_l, wop_r],
                     dispatch='multi',
                     errmsg='cannot do `{0}` <universal_eq> `{1}`')
    return w_opimpl

@OP.builtin_func(color='blue')
def w_UNIVERSAL_NE(vm: 'SPyVM', wop_l: W_OpArg, wop_r: W_OpArg) -> W_OpImpl:
    from spy.vm.typechecker import typecheck_opimpl
    # XXX: see the commet in UNIVERSAL_EQ
    w_opimpl = W_OpImpl(OP.w_object_universal_ne)
    typecheck_opimpl(vm, w_opimpl, [wop_l, wop_r],
                     dispatch='multi',
                     errmsg='cannot do `{0}` <universal_ne> `{1}`')
    return w_opimpl

@OP.builtin_func(color='blue')
def w_LT(vm: 'SPyVM', wop_l: W_OpArg, wop_r: W_OpArg) -> W_OpImpl:
    return MM.lookup(vm, '<', wop_l, wop_r)

@OP.builtin_func(color='blue')
def w_LE(vm: 'SPyVM', wop_l: W_OpArg, wop_r: W_OpArg) -> W_OpImpl:
    return MM.lookup(vm, '<=', wop_l, wop_r)

@OP.builtin_func(color='blue')
def w_GT(vm: 'SPyVM', wop_l: W_OpArg, wop_r: W_OpArg) -> W_OpImpl:
    return MM.lookup(vm, '>', wop_l, wop_r)

@OP.builtin_func(color='blue')
def w_GE(vm: 'SPyVM', wop_l: W_OpArg, wop_r: W_OpArg) -> W_OpImpl:
    return MM.lookup(vm, '>=', wop_l, wop_r)
