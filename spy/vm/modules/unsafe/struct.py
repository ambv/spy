from typing import TYPE_CHECKING, Any, Optional, Type, ClassVar
from dataclasses import dataclass
import fixedint
from spy.fqn import FQN
from spy.vm.primitive import W_I32, W_Void
from spy.vm.b import B
from spy.vm.object import W_Object, W_Type
from spy.vm.builtin import builtin_func
from spy.vm.opimpl import W_OpImpl, W_OpArg
from . import UNSAFE
if TYPE_CHECKING:
    from spy.vm.vm import SPyVM
    from spy.vm.opimpl import W_OpImpl, W_OpArg

FIELDS_T = dict[str, W_Type]
OFFSETS_T = dict[str, int]

class W_StructType(W_Type):
    fields: FIELDS_T
    offsets: OFFSETS_T
    size: int

    def __init__(self, fqn: FQN, pyclass: Type[W_Object],
                 fields: FIELDS_T) -> None:
        super().__init__(fqn, pyclass)
        self.fields = fields
        self.offsets, self.size = calc_layout(fields)

    def __repr__(self) -> str:
        return f"<spy type struct '{self.fqn}'>"

    def is_struct(self, vm: 'SPyVM') -> bool:
        return True


def calc_layout(fields: FIELDS_T) -> tuple[OFFSETS_T, int]:
    from spy.vm.modules.unsafe.misc import sizeof
    offset = 0
    offsets = {}
    for field, w_type in fields.items():
        field_size = sizeof(w_type)
        # compute alignment
        offset = (offset + (field_size - 1)) & ~(field_size - 1)
        offsets[field] = offset
        offset += field_size
    size = offset
    return offsets, size


# XXX note that we don't call @spytype, because it's annoying to pass a custom
# metaclass. But it's fine for now because we don't need/want many
# functionalities: in particolar, we don't want to *instantiate* a struct: we
# just want to have a w_type to describe the fields, to pass to gc_alloc
class W_Struct(W_Object):
    pass


def make_struct_type(vm: 'SPyVM', fqn: FQN, fields: FIELDS_T) -> W_Type:
    class W_MyStruct(W_Struct):
        pass

    name = fqn.symbol_name
    W_MyStruct.__name__ = W_MyStruct.__qualname__ = f'W_{name}'
    w_struct_type = W_StructType(fqn, W_MyStruct, fields)
    W_MyStruct._w = w_struct_type # poor's man @spytype
    return w_struct_type
