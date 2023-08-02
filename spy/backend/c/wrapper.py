import struct
from typing import Any, Optional
import py.path
import wasmtime
from spy.llwasm import LLWasmInstance, LLWasmType
from spy.vm.object import W_Type
from spy.vm.str import W_str
from spy.vm.module import W_Module
from spy.vm.function import W_Function, W_FunctionType
from spy.vm.vm import SPyVM


class WasmModuleWrapper:
    vm: SPyVM
    w_mod: W_Module
    ll: LLWasmInstance

    def __init__(self, vm: SPyVM, w_mod: W_Module, f: py.path.local) -> None:
        self.vm = vm
        self.w_mod = w_mod
        self.ll = LLWasmInstance.from_file(f)

    def __repr__(self) -> str:
        return f"<WasmModuleWrapper 'self.ll.name'>"

    def __getattr__(self, name: str) -> Any:
        wasm_obj = self.ll.get_export(name)
        if isinstance(wasm_obj, wasmtime.Func):
            return self.read_function(name)
        elif isinstance(wasm_obj, wasmtime.Global):
            return self.read_global(name)
        else:
            t = type(wasm_obj)
            raise NotImplementedError(f'Unknown WASM object: {t}')

    def read_function(self, name: str) -> 'WasmFuncWrapper':
        w_func = self.w_mod.content.get(name)
        assert isinstance(w_func, W_Function)
        return WasmFuncWrapper(self.vm, name, w_func.w_functype, self.ll)

    def read_global(self, name: str) -> Any:
        w_type = self.w_mod.content.types_w[name]
        t: LLWasmType
        if w_type is self.vm.builtins.w_i32:
            t = 'int32_t'
        else:
            assert False, f'Unknown type: {w_type}'

        return self.ll.read_global(name, deref=t)


class WasmFuncWrapper:
    vm: SPyVM
    name: str
    w_functype: W_FunctionType
    ll: LLWasmInstance

    def __init__(self, vm: SPyVM, name:str, w_functype: W_FunctionType,
                 ll: LLWasmInstance) -> None:
        self.vm = vm
        self.name = name
        self.w_functype = w_functype
        self.ll = ll

    def py2wasm(self, pyval: Any, w_type: W_Type) -> Any:
        b = self.vm.builtins
        if w_type is b.w_i32:
            return pyval
        elif w_type is b.w_str:
            w_val = self.vm.wrap(pyval)
            assert isinstance(w_val, W_str)
            # XXX: when we introduce the GC, we need to think how to keep this alive
            return w_val.ptr
        else:
            assert False, f'Unsupported type: {w_type}'


    def from_py_args(self, py_args: Any) -> Any:
        a = len(py_args)
        b = len(self.w_functype.params)
        if a != b:
            raise TypeError(f'{self.name}: expected {b} arguments, got {a}')
        #
        wasm_args = []
        for py_arg, param in zip(py_args, self.w_functype.params):
            wasm_arg = self.py2wasm(py_arg, param.w_type)
            wasm_args.append(wasm_arg)
        return wasm_args

    def __call__(self, *py_args: Any) -> Any:
        wasm_args = self.from_py_args(py_args)
        #import pdb;pdb.set_trace()
        res = self.ll.call(self.name, *wasm_args)
        w_type = self.w_functype.w_restype
        b = self.vm.builtins
        if w_type is b.w_void:
            assert res is None
            return None
        elif w_type is b.w_i32:
            return res
        elif w_type is b.w_bool:
            return bool(res)
        elif w_type is b.w_str:
            # res is a  spy_Str*
            addr = res
            length = self.ll.mem.read_i32(addr)
            utf8 = self.ll.mem.read(addr + 4, length)
            return utf8.decode('utf-8')
        else:
            assert False, f"Don't know how to read {w_type} from WASM"
