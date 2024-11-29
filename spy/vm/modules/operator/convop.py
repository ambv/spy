from typing import TYPE_CHECKING, Annotated, Optional
from spy.errors import SPyTypeError
from spy.vm.b import B
from spy.vm.modules.jsffi import JSFFI
from spy.vm.modules.operator import OP
from spy.vm.object import W_Type, W_Object
from spy.vm.function import W_Func, W_FuncType
from spy.vm.opimpl import W_OpArg, W_OpImpl
from spy.vm.primitive import W_I32, W_F64, W_Bool, W_Dynamic
from spy.vm.builtin import builtin_func
from . import OP
from .multimethod import MultiMethodTable
if TYPE_CHECKING:
    from spy.vm.vm import SPyVM

MM = MultiMethodTable()

@OP.builtin_func(color='blue')
def w_CONVERT(vm: 'SPyVM', w_exp: W_Type, wop_x: W_OpArg) -> W_Func:
    """
    Return a w_func which can convert the given OpArg to the desired type.

    If the types are not compatible, raise SPyTypeError. In this case,
    the caller can catch the error, add extra info and re-raise.
    """
    w_opimpl = get_opimpl(vm, w_exp, wop_x)
    if not w_opimpl.is_null():
        return w_opimpl._w_func # XXX: maybe we should return a W_OpImpl?

    # mismatched types
    err = SPyTypeError('mismatched types')
    got = wop_x.w_static_type.fqn.human_name
    exp = w_exp.fqn.human_name
    err.add('error', f'expected `{exp}`, got `{got}`', loc=wop_x.loc)
    raise err


def get_opimpl(vm: 'SPyVM', w_exp: W_Type, wop_x: W_OpArg) -> W_OpImpl:
    # this condition is checked by CONVERT_maybe. If we want this function to
    # become more generally usable, we might want to return an identity func
    # here.
    w_got = wop_x.w_static_type
    assert not vm.issubclass(w_got, w_exp)

    if vm.issubclass(w_exp, w_got):
        # this handles two separate cases:
        #   - upcasts, e.g. object->i32: in this case we just do a typecheck
        #   - dynamic->*: in this case we SHOULD do actual conversions, but at
        #                 the moment we don't so we conflate the two cases
        #                 into one
        w_from_dynamic_T = vm.call(OP.w_from_dynamic, [w_exp])
        return W_OpImpl(w_from_dynamic_T)

    w_opimpl = MM.lookup('convert', w_got, w_exp)
    if not w_opimpl.is_null():
        return w_opimpl

    from_pyclass = w_got.pyclass
    to_pyclass = w_exp.pyclass
    if from_pyclass.has_meth_overriden('op_CONVERT_TO'):
        return from_pyclass.op_CONVERT_TO(vm, w_exp, wop_x)
    elif to_pyclass.has_meth_overriden('op_CONVERT_FROM'):
        return to_pyclass.op_CONVERT_FROM(vm, w_got, wop_x)

    return W_OpImpl.NULL


def CONVERT_maybe(
        vm: 'SPyVM', w_exp: W_Type, wop_x: W_OpArg,
) -> Optional[W_Func]:
    """
    Same as w_CONVERT, but return None if the types are already compatible.
    """
    w_got = wop_x.w_static_type
    if vm.issubclass(w_got, w_exp):
        # nothing to do
        return None
    return vm.call(OP.w_CONVERT, [w_exp, wop_x])

@OP.builtin_func
def w_i32_to_f64(vm: 'SPyVM', w_x: W_I32) -> W_F64:
    val = vm.unwrap_i32(w_x)
    return vm.wrap(float(val))

@OP.builtin_func
def w_i32_to_bool(vm: 'SPyVM', w_x: W_I32) -> W_Bool:
    val = vm.unwrap_i32(w_x)
    return vm.wrap(bool(val))


@OP.builtin_func(color='blue')
def w_from_dynamic(vm: 'SPyVM', w_T: W_Type) -> W_Dynamic:
    """
    Generic function to convert `dynamic` to arbitrary types:
        a: dynamic = ...
        b: i32 = from_dynamic[i32](a)
    """
    T = Annotated[W_Object, w_T]

    # operator::from_dynamic[i32]
    @builtin_func('operator', 'from_dynamic', [w_T.fqn])
    def w_from_dynamic_T(vm: 'SPyVM', w_obj: W_Dynamic) -> T:
        # XXX, we can probably generate better errors
        #
        # XXX, we should probably try to *convert* w_obj to w_T, instead of
        # just typechecking. E.g.:
        #     a: dynamic = 42
        #     b: f64 = from_dynamic[f64](a)  # this should work
        vm.typecheck(w_obj, w_T)
        return w_obj

    vm.add_global(w_from_dynamic_T.fqn, w_from_dynamic_T)
    return w_from_dynamic_T

MM.register('convert', 'i32', 'f64', OP.w_i32_to_f64)
MM.register('convert', 'i32', 'bool', OP.w_i32_to_bool)
