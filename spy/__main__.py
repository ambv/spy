from typing import Annotated, Any, no_type_check
from pathlib import Path
import typer
import py.path
from spy.magic_py_parse import magic_py_parse
from spy.errors import SPyError
from spy.parser import Parser
from spy.compiler import Compiler
from spy.vm.vm import SPyVM

app = typer.Typer(pretty_exceptions_enable=False)

def boolopt(help: str, names: tuple[str, ...]=()) -> Any:
    return Annotated[bool, typer.Option(*names, help=help)]

def do_pyparse(filename: str) -> None:
    import ast as py_ast
    with open(filename) as f:
        src = f.read()
    mod = magic_py_parse(src)
    mod.pp()

@no_type_check
@app.command()
def main(filename: Path,
         pyparse: boolopt("dump the Python AST exit") = False,
         parse: boolopt("dump the SPy AST and exit") = False,
         cwrite: boolopt("create the .c file and exit") = False,
         g: boolopt("generate debug symbols", names=['-g']) = False,
         ) -> None:
    try:
        do_main(filename, pyparse, parse, cwrite, g)
    except SPyError as e:
        print(e.format(use_colors=True))

def do_main(filename: Path, pyparse: bool, parse: bool,
            cwrite: bool, debug_symbols: bool) -> None:
    if pyparse:
        do_pyparse(str(filename))
        return

    if parse:
        parser = Parser.from_filename(str(filename))
        mod = parser.parse()
        mod.pp()
        return

    modname = filename.stem
    builddir = filename.parent
    vm = SPyVM()
    vm.path.append(str(builddir))
    w_mod = vm.import_(modname)

    vm.redshift(modname)
    compiler = Compiler(vm, modname, py.path.local(builddir))
    if cwrite:
        compiler.cwrite()
    else:
        compiler.cbuild(debug_symbols=debug_symbols)

if __name__ == '__main__':
    app()
