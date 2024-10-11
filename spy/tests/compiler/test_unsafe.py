#-*- encoding: utf-8 -*-

import pytest
from spy.tests.support import CompilerTest, skip_backends, no_backend

class TestUnsafe(CompilerTest):

    def test_gc_alloc(self):
        mod = self.compile(
        """
        from unsafe import gc_alloc

        def foo() -> i32:
            # XXX: ideally we want gc_alloc[i32](1), but we can't for now
            ptr = gc_alloc(i32)(1)
            ptr[0] = 42
            return ptr[0]
        """)
        assert mod.foo() == 42
