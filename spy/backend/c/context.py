from dataclasses import dataclass
from spy.fqn import FQN
from spy.vm.vm import SPyVM
from spy.vm.b import B
from spy.vm.object import W_Type
from spy.vm.function import W_FuncType, W_Func
from spy.vm.modules.types import W_LiftedType
from spy.vm.modules.rawbuffer import RB
from spy.vm.modules.jsffi import JSFFI
from spy.vm.modules.unsafe.ptr import W_PtrType
from spy.vm.modules.unsafe.struct import W_StructType
from spy.textbuilder import TextBuilder

@dataclass
class C_Type:
    """
    Just a tiny wrapper around a string, but it helps to make things tidy.
    """
    name: str

    def __repr__(self) -> str:
        return f"<C type '{self.name}'>"

    def __str__(self) -> str:
        return self.name

@dataclass
class C_FuncParam:
    name: str
    c_type: C_Type


@dataclass
class C_Function:
    name: str
    params: list[C_FuncParam]
    c_restype: C_Type

    def __repr__(self) -> str:
        return f"<C func '{self.name}'>"

    def decl(self) -> str:
        if self.params == []:
            s_params = 'void'
        else:
            paramlist = [f'{p.c_type} {p.name}' for p in self.params]
            s_params = ', '.join(paramlist)
        #
        return f'{self.c_restype} {self.name}({s_params})'


class Context:
    """
    Global context of the C writer.

    Keep track of things like the mapping from W_* types to C types.
    """
    vm: SPyVM
    out_types_decl: TextBuilder
    out_ptrs_def: TextBuilder
    out_types_def: TextBuilder
    _d: dict[W_Type, C_Type]

    def __init__(self, vm: SPyVM) -> None:
        self.vm = vm
        # set by CModuleWriter.emit_module
        self.out_types_decl = None # type: ignore
        self.out_ptrs_def = None   # type: ignore
        self.out_types_def = None  # type: ignore
        self._d = {}
        self._d[B.w_void] = C_Type('void')
        self._d[B.w_i32] = C_Type('int32_t')
        self._d[B.w_f64] = C_Type('double')
        self._d[B.w_bool] = C_Type('bool')
        self._d[B.w_str] = C_Type('spy_Str *')
        self._d[RB.w_RawBuffer] = C_Type('spy_RawBuffer *')
        self._d[JSFFI.w_JsRef] = C_Type('JsRef')

    def w2c(self, w_type: W_Type) -> C_Type:
        if w_type in self._d:
            return self._d[w_type]
        elif isinstance(w_type, W_PtrType):
            return self.new_ptr_type(w_type)
        elif isinstance(w_type, W_StructType):
            return self.new_struct_type(w_type)
        elif isinstance(w_type, W_LiftedType):
            return self.new_lifted_type(w_type)
        elif w_type is B.w_type:
            return C_Type('void *') # XXXXXXXX
        raise NotImplementedError(f'Cannot translate type {w_type} to C')

    def c_restype_by_fqn(self, fqn: FQN) -> C_Type:
        w_func = self.vm.lookup_global(fqn)
        assert isinstance(w_func, W_Func)
        w_restype = w_func.w_functype.w_restype
        return self.w2c(w_restype)

    def c_function(self, name: str, w_functype: W_FuncType) -> C_Function:
        c_restype = self.w2c(w_functype.w_restype)
        c_params = [
            C_FuncParam(name=p.name, c_type=self.w2c(p.w_type))
            for p in w_functype.params
        ]
        return C_Function(name, c_params, c_restype)

    def new_ptr_type(self, w_ptrtype: W_PtrType) -> C_Type:
        c_ptrtype = C_Type(w_ptrtype.fqn.c_name)
        w_itemtype = w_ptrtype.w_itemtype
        c_itemtype = self.w2c(w_itemtype)
        self.out_types_decl.wb(f"""
        typedef struct {c_ptrtype} {{
            {c_itemtype} *p;
        #ifdef SPY_DEBUG
            size_t length;
        #endif
        }} {c_ptrtype};
        """)
        self.out_ptrs_def.wb(f"""
        SPY_PTR_FUNCTIONS({c_ptrtype}, {c_itemtype});
        #define {c_ptrtype}$NULL (({c_ptrtype}){{0}})
        """)
        self._d[w_ptrtype] = c_ptrtype
        return c_ptrtype

    def new_struct_type(self, w_st: W_StructType) -> C_Type:
        c_struct_type = C_Type(w_st.fqn.c_name)
        # forward declaration
        self._d[w_st] = c_struct_type
        self.out_types_decl.wl(f'typedef struct {c_struct_type} {c_struct_type};')

        # XXX this is VERY wrong: it assumes that the standard C layout
        # matches the layout computed by struct.calc_layout: as long as we use
        # only 32-bit types it should work, but eventually we need to do it
        # properly.
        #
        # Write the struct definition in a detached builder. This is necessary
        # because the call to w2c might trigger OTHER type definitions, so we
        # must ensure that we write the whole "struct { ... }" block
        # atomically.
        out = self.out_types_def.make_nested_builder(detached=True)
        out.wl("struct %s {" % c_struct_type)
        with out.indent():
            for field, w_fieldtype in w_st.fields.items():
                c_fieldtype = self.w2c(w_fieldtype)
                out.wl(f"{c_fieldtype} {field};")
        out.wl("};")
        out.wl("")
        self.out_types_def.attach_nested_builder(out)
        return c_struct_type

    def new_lifted_type(self, w_hltype: W_LiftedType) -> C_Type:
        c_hltype = C_Type(w_hltype.fqn.c_name)
        w_lltype = w_hltype.w_lltype
        c_lltype = self.w2c(w_lltype)
        self.out_types_decl.wb(f"""
        typedef struct {c_hltype} {{
            {c_lltype} ll;
        }} {c_hltype};
        """)
        LIFT = w_hltype.fqn.join('__lift__').c_name
        self.out_ptrs_def.wb(f"""
        SPY_TYPELIFT_FUNCTIONS({c_hltype}, {c_lltype});
        """)
        self._d[w_hltype] = c_hltype
        return c_hltype
