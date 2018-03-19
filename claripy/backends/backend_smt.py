import logging

from pysmt.shortcuts import Symbol, String, StrConcat, Equals, NotEquals, \
                            StrSubstr, Int, StrLength, StrReplace, \
                            Bool, BV
                            
from pysmt.typing import STRING

l = logging.getLogger("claripy.backends.backend_smt")

from . import BackendError, Backend


class BackendSMT(Backend):
    def __init__(self):
        Backend.__init__(self)

        self._assertions_stack = []

        self._op_expr['StringV'] = self.StringV
        self._op_expr['StringS'] = self.StringS
        self._op_expr['BoolV'] = self.BoolV
        self._op_expr['BVV'] = self.BVV

        self._op_raw['__eq__'] = self._op_eq
        self._op_raw['__ne__'] = self._op_ne
        self._op_raw['StrConcat'] = self._op_raw_str_concat
        self._op_raw['Substr'] = self._op_raw_str_substr
        self._op_raw['StrLen'] = self._op_raw_str_strlen
        self._op_raw['StrReplace'] = self._op_raw_str_replace
        # self._op_raw['__sub__'] = self._op_sub
        # self._op_raw['__mul__'] = self._op_mul
        # self._op_raw['__or__'] = self._op_or
        # self._op_raw['__xor__'] = self._op_xor
        # self._op_raw['__and__'] = self._op_and

        # self._cache_objects = False

    def StringV(self, ast):
        # TODO: check correct format
        # self._op_expr['StringV'] = self.StringV
        #       if format not correct throw exception BackError()
        content, _ = ast.args
        return String(content)

    def StringS(self, ast):
        # TODO: check correct format
        #       if format not correct throw exception BackError()
        name, _ = ast.args
        assertion = Symbol(name, STRING) 
        self._assertions_stack.append(assertion)
        return assertion

    def BoolV(self, ast):
        return Bool(ast.is_true())

    def BVV(self, ast):
        val, size = ast.args
        return BV(val, size)

    def _op_raw_str_concat(self, *args):
        return StrConcat(args)

    def _op_raw_str_substr(self, *args):
        i, j, symb = args
        return StrSubstr(symb, Int(i), Int(j))

    def _op_raw_str_strlen(self, *args):
        return StrLength(args[0])

    def _op_raw_str_replace(self, *args):
        initial_str, pattern_to_replace, replacement_pattern = args
        return StrReplace(initial_str, pattern_to_replace, replacement_pattern)

    def _op_eq(self, *args):
        expr_left, expr_rigth = args
        # We emulate the integer through a bitvector but
        # since a constraint with the form (assert (= (str.len Symb_str) bit_vect))
        # is not valid we need to tranform the concrete vqalue of the bitvector in an integer
        #
        # TODO: implement logic for integer
        if expr_left.is_str_op() and expr_rigth.is_bv_constant():
            return Equals(expr_left, Int(expr_rigth.bv_signed_value()))
        elif expr_left.is_bv_constant() and expr_rigth.is_str_op():
            return Equals(expr_rigth, Int(expr_left.bv_signed_value())) 
        return Equals(expr_left, expr_rigth)

    def _op_ne(self, *args):
        expr_left, expr_rigth = args
        return NotEquals(expr_left, expr_rigth)

    # @staticmethod
    # def _op_sub(*args):
    #     return reduce(operator.__sub__, args)
    # @staticmethod
    # def _op_mul(*args):
    #     return reduce(operator.__mul__, args)
    # @staticmethod
    # def _op_or(*args):
    #     return reduce(operator.__or__, args)
    # @staticmethod
    # def _op_xor(*args):
    #     return reduce(operator.__xor__, args)
    # @staticmethod
    # def _op_and(*args):
    #     return reduce(operator.__and__, args)

    # def _If(self, b, t, f): #pylint:disable=no-self-use,unused-argument
    #     if not isinstance(b, bool):
    #         raise BackendError("BackendConcrete can't handle non-bool condition in If.")
    #     else:
    #         return t if b else f

    # def _size(self, e):
    #     if isinstance(e, (bool, numbers.Number)):
    #         return None
    #     elif isinstance(e, bv.BVV):
    #         return e.size()
    #     elif isinstance(e, fp.FPV):
    #         return e.sort.length
    #     else:
    #         raise BackendError("can't get size of type %s" % type(e))

    # def _name(self, e): #pylint:disable=unused-argument,no-self-use
    #     return None

    def _satisfiable(self, extra_constraints=(), solver=None, model_callback=None):
        '''
        Returns a SMT script that declare all the symbols and constraint and checks
        their satisfiability (check-sat)
        '''
        smt_script = self._dump_assertion_stack()
        # TODO: manage extra constraint in a sane manner
        # for constr in extra_constraints:
        #     smt_script += "\n(assert %s)" % constr.to_smtlib()
        smt_script += '(check-sat)\n'
        self._assertions_stack = []
        return smt_script

    def _add(self, constraint):
        self._assertions_stack.append(constraint)

    # def _identical(self, a, b):
    #     if type(a) is bv.BVV and type(b) is bv.BVV and a.size() != b.size():
    #         return False
    #     else:
    #         return a == b

    # def _convert(self, a):
    #     if isinstance(a, (numbers.Number, bv.BVV, fp.FPV, fp.RM, fp.FSort, strings.StringV)):
    #         return a
    #     raise BackendError("can't handle AST of type %s" % type(a))

    # def _simplify(self, e):
    #     return e

    # def _abstract(self, e): #pylint:disable=no-self-use
    #     if isinstance(e, bv.BVV):
    #         return BVV(e.value, e.size())
    #     elif isinstance(e, bool):
    #         return BoolV(e)
    #     elif isinstance(e, fp.FPV):
    #         return FPV(e.value, e.sort)
    #     else:
    #         raise BackendError("Couldn't abstract object of type {}".format(type(e)))

    # def _cardinality(self, b):
    #     # if we got here, it's a cardinality of 1
    #     return 1

    # #
    # # Evaluation functions
    # #

    # @staticmethod
    # def _to_primitive(expr):
    #     if isinstance(expr, bv.BVV):
    #         return expr.value
    #     if isinstance(expr, fp.FPV):
    #         return expr.value
    #     if isinstance(expr, bool):
    #         return expr
    #     if isinstance(expr, numbers.Number):
    #         return expr

    # def _eval(self, expr, n, extra_constraints=(), solver=None, model_callback=None):
    #     if not all(extra_constraints):
    #         raise UnsatError('concrete False constraint in extra_constraints')

    #     return (self._to_primitive(expr),)

    # def _batch_eval(self, exprs, n, extra_constraints=(), solver=None, model_callback=None):
    #     if not all(extra_constraints):
    #         raise UnsatError('concrete False constraint in extra_constraints')

    #     return [ tuple(self._to_primitive(ex) for ex in exprs) ]

    # def _max(self, expr, extra_constraints=(), solver=None, model_callback=None):
    #     if not all(extra_constraints):
    #         raise UnsatError('concrete False constraint in extra_constraints')
    #     return self._to_primitive(expr)

    # def _min(self, expr, extra_constraints=(), solver=None, model_callback=None):
    #     if not all(extra_constraints):
    #         raise UnsatError('concrete False constraint in extra_constraints')
    #     return self._to_primitive(expr)

    # def _solution(self, expr, v, extra_constraints=(), solver=None, model_callback=None):
    #     if not all(extra_constraints):
    #         raise UnsatError('concrete False constraint in extra_constraints')
    #     return self.convert(expr) == v

    # #pylint:disable=singleton-comparison
    # def _is_true(self, e, extra_constraints=(), solver=None, model_callback=None):
    #     return e == True
    # def _is_false(self, e, extra_constraints=(), solver=None, model_callback=None):
    #     return e == False
    # def _has_true(self, e, extra_constraints=(), solver=None, model_callback=None):
    #     return e == True
    # def _has_false(self, e, extra_constraints=(), solver=None, model_callback=None):
    #     return e == False

from ..operations import backend_operations, backend_fp_operations
from .. import bv, fp, strings
from ..errors import UnsatError
