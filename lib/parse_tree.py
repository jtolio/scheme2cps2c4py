#!/usr/bin/env python

# so, i'm dumb. my parse tree up to this point sucks, so I'm going to rewrite it
# in this module

from util import Token, LogicError, c_format
from desugar import KEYWORDS
from primitives import PRIMITIVE_NAMES

class Exp(object): pass

class Variable(Exp):
    def __init__(self, name, three_d):
        assert type(name) in (str, unicode)
        assert type(three_d) == bool
        self.name, self.three_d = name, three_d
    def __repr__(self):
        return "Variable(%r, %r)" % (self.name, self.three_d)
    def __str__(self): return self.name
    def isTrivial(self): return True
    def __hash__(self): return hash((self.name, self.three_d))
    def __cmp__(self, other):
        if type(self) != type(other):
            return cmp(type(self), type(other))
        return cmp((self.name, self.three_d), (other.name, other.three_d))
    def freeVariables(self):
        if (self.name in PRIMITIVE_NAMES or self.name == "halt") and \
                self.three_d:
            return set()
        return set([self])
    allVariables = freeVariables
    def mutableVariables(self): return set()

class Literal(Exp):
    def __init__(self, type_, value):
        assert type(type_) in (str, unicode)
        assert type_ in ("symbol", "string", "integer", "boolean")
        if type_ == "string":
            assert type(value) in (str, unicode)
        elif type_ == "symbol":
            assert isinstance(value, Exp)
        elif type_ == "integer":
            assert type(value) in (int, long)
        elif type_ == "boolean":
            assert type(value) == bool
        self.type, self.value = type_, value
    def __repr__(self):
        return "Literal(%r, %r)" % (self.type, self.value)
    def __str__(self):
        if self.type == "boolean":
            if not self.value: return "#f"
            return "#t"
        if self.type == "integer": return repr(self.value)
        if self.type == "symbol": return str(self.value)
        if self.type == "string": return c_format(self.value)
        raise LogicError, "?"
    def isTrivial(self): return True
    def freeVariables(self): return set()
    allVariables = freeVariables
    mutableVariables = freeVariables

class Application(Exp):
    def __init__(self, function, *args):
        assert isinstance(function, Exp)
        for arg in args:
            assert isinstance(arg, Exp)
        self.function, self.args = function, args
    def __repr__(self):
        return "Application(%r, %s)" % (self.function,
                ", ".join([repr(x) for x in self.args]))
    def __str__(self):
        return "(%s)" % " ".join([str(self.function)] +
                [str(x) for x in self.args])
    def special(self):
        return (type(self.function) == Variable and self.function.three_d and
                self.function.name in PRIMITIVE_NAMES)
    def isTrivial(self):
        if self.special():
            return not self.function.three_d or self.function.name != "call/cc"
        return False
    def freeVariables(self):
        free = self.function.freeVariables()
        for arg in self.args:
            free = free.union(arg.freeVariables())
        return free
    def allVariables(self):
        all = self.function.allVariables()
        for arg in self.args:
            all = all.union(arg.allVariables())
        return all
    def mutableVariables(self):
        mutable = self.function.mutableVariables()
        for arg in self.args:
            mutable = mutable.union(arg.mutableVariables())
        return mutable

class Begin(Exp):
    def __init__(self, instructions):
        for instruction in instructions:
            assert isinstance(instruction, Exp)
        self.instructions = instructions
    def __repr__(self):
        return "Begin(%r)" % self.instructions
    def __str__(self):
        return "(%s)" % " ".join(["begin"] +
                [str(x) for x in self.instructions])
    def isTrivial(self): return False
    def freeVariables(self):
        free = set()
        for instruction in self.instructions:
            free = free.union(instruction.freeVariables())
        return free
    def allVariables(self):
        all = set()
        for instruction in self.instructions:
            all = all.union(instruction.allVariables())
        return all
    def mutableVariables(self):
        mutable = set()
        for instruction in self.instructions:
            mutable = mutable.union(instruction.mutableVariables())
        return mutable

class If(Exp):
    def __init__(self, test, true, false):
        for thing in (test, true, false):
            assert isinstance(thing, Exp)
        self.test, self.true, self.false = test, true, false
    def __repr__(self):
        return "If(%r, %r, %r)" % (self.test, self.true, self.false)
    def __str__(self):
        return "(if %s %s %s)" % (self.test, self.true, self.false)
    def isTrivial(self): return False
    def freeVariables(self):
        return self.test.freeVariables().union(self.true.freeVariables())\
                .union(self.false.freeVariables())
    def allVariables(self):
        return self.test.allVariables().union(self.true.allVariables())\
                .union(self.false.allVariables())
    def mutableVariables(self):
        return self.test.mutableVariables().union(self.true.mutableVariables())\
                .union(self.false.mutableVariables())

class Lambda(Exp):
    counter = 0
    def __init__(self, args, instruction, name=None):
        for arg in args:
            assert type(arg) == Variable
        assert isinstance(instruction, Exp)
        self.args, self.instruction = args, instruction
        Lambda.counter += 1
        if name is not None:
            self.name = name
        else:
            self.name = "l%d" % Lambda.counter
        argset = set()
        for arg in args:
            if arg in argset:
                raise ParserError, "'lambda' got two identically named " \
                        "arguments"
            argset.add(arg)
        self._free_cache = [set(), False]
    def __repr__(self):
        return "Lambda(%r, %r)" % (self.args, self.instruction)
    def __str__(self):
        return "(lambda (%s) %s)" % (" ".join([str(x) for x in self.args]),
                self.instruction)
    def isTrivial(self): return True
    def freeVariables(self):
        if not self._free_cache[1]:
            bound = set()
            for arg in self.args:
                bound = bound.union(arg.freeVariables())
            self._free_cache = [self.instruction.freeVariables() - bound, True]
        return self._free_cache[0]
    def allVariables(self):
        bound = set()
        for arg in self.args:
            bound = bound.union(arg.allVariables())
        return self.instruction.allVariables().union(bound)
    def mutableVariables(self):
        bound = set()
        for arg in self.args:
            bound = bound.union(arg.mutableVariables())
        return self.instruction.mutableVariables().union(bound)

class SetBang(Exp):
    def __init__(self, var, val):
        assert type(var) == Variable
        assert isinstance(val, Exp)
        self.var, self.val = var, val
    def __repr__(self):
        return "SetBang(%r, %r)" % (self.var, self.val)
    def __str__(self):
        return "(set! %s %s)" % (self.var, self.val)
    def isTrivial(self): return False
    def freeVariables(self):
        return self.var.freeVariables().union(self.val.freeVariables())
    def allVariables(self):
        return self.var.allVariables().union(self.val.allVariables())
    def mutableVariables(self):
        return self.var.mutableVariables().union(self.val.mutableVariables())\
                .union(set([self.var]))

class List(Exp):
    def __init__(self, things):
        for thing in things:
            assert type(thing) in (List, Literal, Variable)
        self.things = things
    def __repr__(self):
        return "List(%r)" % self.things
    def __str__(self):
        return "(%s)" % " ".join((str(x) for x in self.things))

def quote(node):
    if type(node) == Token:
        if node.type == "symbol": return Variable(node.value, False)
        assert node.type != "3d-symbol"
        return Literal(node.type, node.value)
    assert type(node) == list
    return List(map(quote, node))

def structure(node):
    """turns the old parse tree into a new one"""
    if type(node) == Token:
        if node.type in ("symbol", "3d-symbol"):
            return Variable(node.value, node.type == "3d-symbol")
        return Literal(node.type, node.value)
    assert type(node) == list
    if not node:
        raise ParserError, "Application missing method!"
    if type(node[0]) == list:
        return Application(structure(node[0]), *map(structure, node[1:]))
    assert type(node[0]) == Token
    if node[0].isSymbol("quote"):
        return Literal("symbol", quote(node))
    if node[0].isSymbol("begin"):
        return Begin(map(structure, node[1:]))
    if node[0].isSymbol("if"):
        assert len(node) == 4
        return If(structure(node[1]), structure(node[2]), structure(node[3]))
    if node[0].isSymbol("lambda"):
        assert len(node) == 3
        assert type(node[1]) == list
        return Lambda(map(structure, node[1]), structure(node[2]))
    if node[0].isSymbol("set!"):
        assert len(node) == 3
        return SetBang(structure(node[1]), structure(node[2]))
    if node[0].type == "symbol":
        if node[0].value in KEYWORDS:
            raise LogicError, "unhandled keyword '%s'" % node[0].value
    return Application(structure(node[0]), *map(structure, node[1:]))
