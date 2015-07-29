import logging
l = logging.getLogger("claripy.backends.backend_concrete")

import z3
zTrue = z3.BoolVal(True)
zFalse = z3.BoolVal(False)

from ..backend import BackendError
from .model_backend import ModelBackend

class BackendConcrete(ModelBackend):
    def __init__(self):
        ModelBackend.__init__(self)
        self._make_raw_ops(set(backend_operations) - { 'BitVec' }, op_module=bv)
        self._make_raw_ops(backend_fp_operations, op_module=fp)
        self._op_raw_result['BitVec'] = self.BitVec

    def BitVec(self, name, size, result=None): #pylint:disable=W0613,R0201
        if result is None:
            l.debug("BackendConcrete can only handle BitVec when we are given a model")
            raise BackendError("BackendConcrete can only handle BitVec when we are given a model")
        if name not in result.model:
            l.debug("BackendConcrete needs variable %s in the model", name)
            raise BackendError("BackendConcrete needs variable %s in the model" % name)
        else:
            return result.model[name]

    def _size(self, e, result=None):
        if type(e) in { bool, long, int }:
            return None
        elif type(e) in { BVV }:
            return e.size()
        elif isinstance(e, FPV):
            return e.sort.length
        else:
            raise BackendError("can't get size of type %s" % type(e))

    def _name(self, e, result=None): #pylint:disable=unused-argument,no-self-use
        return None

    def _identical(self, a, b, result=None):
        if type(a) is BVV and type(b) is BVV and a.size() != b.size():
            return False
        else:
            return a == b

    def _convert(self, a, result=None):
        if type(a) in { int, long, float, bool, str, BVV, FPV, RM, FSort }:
            return a

        if not hasattr(a, '__module__') or a.__module__ != 'z3':
            raise BackendError("BackendConcrete got an unsupported type %s" % a.__class__)

        z3_backend = self._claripy.backend_of_type(BackendZ3)
        if z3_backend is None:
            raise BackendError("can't convert z3 expressions when z3 is not in use")

        try:
            if hasattr(z3_backend, '_lock'):
                z3_backend._lock.acquire()

            if hasattr(a, 'as_long'): return bv.BVV(a.as_long(), a.size())
            elif isinstance(a, z3.FPRef):
                # TODO: don't replicate this code in backend_z3.py
                # this is really imprecise
                fp_mantissa = float(a.significand())
                fp_exp = float(a.exponent())
                value = fp_mantissa * (2 ** fp_exp)

                ebits = a.ebits()
                sbits = a.sbits()
                sort = FSort.from_params(ebits, sbits)

                return FPV(value, sort)
            elif isinstance(a, z3.BoolRef) and a.eq(zTrue): return True
            elif isinstance(a, z3.BoolRef) and a.eq(zFalse): return False
            elif result is not None and a.num_args() == 0:
                name = a.decl().name()
                if name in result.model:
                    return result.model[name]
                else:
                    l.debug("returning 0 for %s (not in model)", name)
                    return bv.BVV(0, a.size())
            else:
                #import ipdb; ipdb.set_trace()
                #l.warning("TODO: support more complex non-symbolic expressions, maybe?")
                raise BackendError("TODO: support more complex non-symbolic expressions, maybe?")
        finally:
            if hasattr(z3_backend, '_lock'):
                z3_backend._lock.release()

    def _simplify(self, e):
        return e

    def abstract(self, e):
        if isinstance(e, BVV):
            return BVI(self._claripy, e, length=e.size())
        elif isinstance(e, bool):
            return BoolI(self._claripy, e)
        elif isinstance(e, FPV):
            return FPI(self._claripy, e)
        else:
            raise BackendError("Couldn't abstract object of type {}".format(type(e)))

    #
    # Evaluation functions
    #

    def _eval(self, expr, n, result=None):
        return [ self.convert(expr, result=result if n == 1 else None) ]
    def _max(self, expr, result=None):
        return self.convert(expr, result=result)
    def _min(self, expr, result=None):
        return self.convert(expr, result=result)
    def _solution(self, expr, v, result=None):
        return self.convert(expr, result=result) == v

from ..bv import BVV
from ..fp import FPV, RM, FSort
from ..operations import backend_operations, backend_fp_operations
from .. import bv, fp
from .backend_z3 import BackendZ3
from ..ast import BVI, FPI, BoolI
