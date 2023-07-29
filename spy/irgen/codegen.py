import spy.ast
from spy.irgen.typechecker import TypeChecker
from spy.irgen.symtable import SymTable
from spy.errors import SPyCompileError
from spy.vm.vm import SPyVM
from spy.vm.object import W_Object
from spy.vm.codeobject import W_CodeObject, OpCode
from spy.vm.function import W_FunctionType
from spy.util import magic_dispatch


class CodeGen:
    """
    Compile the body of spy.ast.FuncDef into a W_CodeObject
    """
    vm: SPyVM
    t: TypeChecker
    funcdef: spy.ast.FuncDef
    scope: SymTable
    w_code: W_CodeObject

    def __init__(self,
                 vm: SPyVM,
                 t: TypeChecker,
                 funcdef: spy.ast.FuncDef) -> None:
        self.vm = vm
        self.t = t
        self.funcdef = funcdef
        w_functype, scope = t.get_funcdef_info(funcdef)
        self.scope = scope
        self.w_code = W_CodeObject(self.funcdef.name, w_functype=w_functype)
        self.add_local_variables()

    def add_local_variables(self) -> None:
        for sym in self.scope.symbols.values():
            if sym.name == '@return':
                continue
            self.w_code.declare_local(sym.name, sym.w_type)

    def make_w_code(self) -> W_CodeObject:
        for stmt in self.funcdef.body:
            self.exec_stmt(stmt)
        #
        # if we arrive here, we have reached the end of the function. Let's
        # emit an implicit return (if the return type is void) or an abort (in
        # all other cases)
        if self.w_code.w_functype.w_restype is self.vm.builtins.w_void:
            self.emit('load_const', self.vm.builtins.w_None)
            self.emit('return')
        else:
            self.emit('abort', 'reached the end of the function without a `return`')
        return self.w_code

    def is_const(self, expr: spy.ast.Expr) -> bool:
        """
        Check whether the given expr is a compile time const. We consider consts:
          - spy.ast.Constant
          - spy.ast.Name which refers to a 'const'
        """
        if isinstance(expr, spy.ast.Constant):
            return True
        elif isinstance(expr, spy.ast.Name):
            varname = expr.id
            sym = self.scope.lookup(varname)
            assert sym is not None
            return sym.qualifier == 'const'
        return False

    def emit(self, name: str, *args: object) -> tuple[int, OpCode]:
        """
        Emit an OpCode into the w_code body.

        Return a tuple (label, op) where label is the index of op inside the
        body.
        """
        label = self.get_label()
        op = OpCode(name, *args)
        self.w_code.body.append(op)
        return label, op

    def get_label(self) -> int:
        """
        Return the position in the resulting w_code body which corresponds to the
        NEXT opcode which will be emitted.
        """
        return len(self.w_code.body)

    def exec_stmt(self, stmt: spy.ast.Stmt) -> None:
        """
        Compile a statement.

        Pop all the operands from the stack, don't push any result.
        """
        magic_dispatch(self, 'do_exec', stmt)

    def eval_expr(self, expr: spy.ast.Expr) -> None:
        """
        Compile an expression.

        Pop all the operands from the stack, push the result on the stack.
        """
        magic_dispatch(self, 'do_eval', expr)

    # ====== statements ======

    def do_exec_Return(self, ret: spy.ast.Return) -> None:
        assert ret.value is not None
        self.eval_expr(ret.value)
        self.emit('return')

    def do_exec_StmtExpr(self, stmt: spy.ast.StmtExpr) -> None:
        self.eval_expr(stmt.value)
        self.emit('pop_and_discard')

    def do_exec_VarDef(self, vardef: spy.ast.VarDef) -> None:
        # sanity check, the var must be in the local scope
        assert vardef.name in self.scope.symbols
        assert vardef.value is not None
        self.eval_expr(vardef.value)
        self.emit('store_local', vardef.name)

    def do_exec_Assign(self, assign: spy.ast.Assign) -> None:
        sym = self.scope.lookup(assign.target)
        assert sym # there MUST be a symbol somewhere, else the typechecker is broken
        self.eval_expr(assign.value)
        if sym.scope is self.scope:
            self.emit('store_local', assign.target) # local variable
        elif sym.scope is self.t.global_scope:
            self.emit('store_global', assign.target) # local variable
        else:
            assert False, 'TODO' # non-local variables

    def do_exec_If(self, if_node: spy.ast.If) -> None:
        if if_node.else_body:
            self._do_exec_If_then_else(if_node)
        else:
            self._do_exec_If_then(if_node)

    def _do_exec_If_then(self, if_node: spy.ast.If) -> None:
        """
             mark_if_then IF, END
             <eval cond>
        IF:  br_if_not END
             <then body>
        END: <rest of the program>

        """
        _, op_mark = self.emit('mark_if_then', ...)
        self.eval_expr(if_node.test) # <eval cond>
        IF, br_if_not = self.emit('br_if_not', ...)
        # <then body>
        for stmt in if_node.then_body:
            self.exec_stmt(stmt)
        #
        END = self.get_label()
        br_if_not.set_args(END)
        op_mark.set_args(IF, END)

    def _do_exec_If_then_else(self, if_node: spy.ast.If) -> None:
        """
              mark_if_then_else IF, ELSE, END
              <eval cond>
        IF:   br_if_not ELSE
              <then body>
              br END
        ELSE: <else body>
        END:  <rest of the program>
        """
        _, op_mark = self.emit('mark_if_then_else', ...)
        self.eval_expr(if_node.test) # <eval cond>
        IF, br_if_not = self.emit('br_if_not', ...)
        # <then body>
        for stmt in if_node.then_body:
            self.exec_stmt(stmt)
        #
        _, br = self.emit('br', ...)
        # <else body>
        ELSE = self.get_label()
        for stmt in if_node.else_body:
            self.exec_stmt(stmt)
        #
        END = self.get_label()
        br_if_not.set_args(ELSE)
        br.set_args(END)
        op_mark.set_args(IF, ELSE, END)

    def do_exec_While(self, while_node: spy.ast.While) -> None:
        """
               mark_while IF, LOOP
        START: <eval cond>
        IF:    br_if_not END
               <body>
        LOOP:  br START
        END:   <rest of the program>
        """
        _, op_mark = self.emit('mark_while', ...)
        START = self.get_label()
        self.eval_expr(while_node.test)
        #
        IF, br_if_not = self.emit('br_if_not', ...)
        for stmt in while_node.body:
            self.exec_stmt(stmt)
        #
        LOOP, _ = self.emit('br', START)
        END = self.get_label()
        br_if_not.set_args(END)
        op_mark.set_args(IF, LOOP)

    # ====== expressions ======

    def do_eval_Constant(self, const: spy.ast.Constant) -> None:
        w_const = self.t.get_w_const(const)
        self.emit('load_const', w_const)

    def do_eval_Name(self, expr: spy.ast.Name) -> None:
        varname = expr.id
        sym = self.scope.lookup(varname)
        assert sym is not None
        if sym.scope is self.scope:
            # local variable
            self.emit('load_local', varname)
        elif sym.scope is self.t.global_scope:
            # global var
            self.emit('load_global', varname)
        else:
            # non-local variable
            assert False, 'XXX todo'

    def do_eval_BinOp(self, binop: spy.ast.BinOp) -> None:
        w_i32 = self.vm.builtins.w_i32
        w_str = self.vm.builtins.w_str
        w_ltype = self.t.get_expr_type(binop.left)
        w_rtype = self.t.get_expr_type(binop.right)
        if w_ltype is w_i32 and w_rtype is w_i32:
            self.eval_expr(binop.left)
            self.eval_expr(binop.right)
            if binop.op == '+':
                self.emit('i32_add')
                return
            elif binop.op == '*':
                self.emit('i32_mul')
                return
        elif w_ltype is w_str and w_rtype is w_str and binop.op == '+':
            self.eval_expr(binop.left)
            self.eval_expr(binop.right)
            self.emit('call_primitive', 'str_add')
            return
        #
        raise NotImplementedError(
            f'{binop.op} op between {w_ltype.name} and {w_rtype.name}')

    do_eval_Add = do_eval_BinOp
    do_eval_Mul = do_eval_BinOp

    def do_eval_CompareOp(self, cmpop: spy.ast.CompareOp) -> None:
        w_i32 = self.vm.builtins.w_i32
        w_ltype = self.t.get_expr_type(cmpop.left)
        w_rtype = self.t.get_expr_type(cmpop.right)
        if w_ltype is w_i32 and w_rtype is w_i32:
            self.eval_expr(cmpop.left)
            self.eval_expr(cmpop.right)
            if   cmpop.op == '==': self.emit('i32_eq');  return
            elif cmpop.op == '!=': self.emit('i32_neq'); return
            elif cmpop.op == '<':  self.emit('i32_lt');  return
            elif cmpop.op == '<=': self.emit('i32_lte'); return
            elif cmpop.op == '>':  self.emit('i32_gt');  return
            elif cmpop.op == '>=': self.emit('i32_gte'); return
        #
        raise NotImplementedError(
            f'{cmpop.op} op between {w_ltype.name} and {w_rtype.name}')

    do_eval_Eq = do_eval_CompareOp
    do_eval_NotEq = do_eval_CompareOp
    do_eval_Lt = do_eval_CompareOp
    do_eval_LtE = do_eval_CompareOp
    do_eval_Gt = do_eval_CompareOp
    do_eval_GtE = do_eval_CompareOp

    def do_eval_Call(self, call: spy.ast.Call) -> None:
        if not self.is_const(call.func):
            # XXX there is no test for this at the moment because we don't
            # have higher order functions, so it's impossible to reach this
            # branch
            err = SPyCompileError('indirect calls not supported')
            raise err
        assert isinstance(call.func, spy.ast.Name)
        funcname = call.func.id
        for expr in call.args:
            self.eval_expr(expr)
        self.emit('call_global', funcname, len(call.args))
