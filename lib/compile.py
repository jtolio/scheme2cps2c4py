#!/usr/bin/env python

from sexp_io import parse, serialize
from desugar import desugar
from cps_transform import cps_transform, curry
from primitives import wrap, PRIMITIVE_NAMES
from parse_tree import structure, Variable, If, Begin, Application, Lambda, \
        Literal, SetBang
from lift import rename, find_lambdas
from util import ParserError, LogicError, c_format
from cStringIO import StringIO
from constants import HEADER, STARTMAIN, ENDMAIN, CALLFUNC, GRANDCENTRAL, \
        ENABLE_GC
import gflags

FLAGS = gflags.FLAGS
gflags.DEFINE_boolean("curry", False, "If True, curries all functions.")
gflags.DEFINE_enum("output", "c", ["c", "cps"], "The output type.")
gflags.DEFINE_integer("recursion_limit", 1000000, "The recursion limit to set "
        "for the Python interpreter.")
gflags.DEFINE_boolean("gc", True, "If False (or --nogc), disables usage of "
        "Boehm GC")

def check_unbound(program):
    assert len(program.freeVariables()) == 0
    return program

def parse_program(input, check_bound=True):
    tree = structure(desugar(wrap(parse(input))))
    if FLAGS.curry: tree = curry(tree)
    return check_unbound(rename(cps_transform(tree)))

def write_primitive(thing, helper):
    assert type(thing) == Application and thing.special()
    if thing.function.name == "display":
        assert len(thing.args) == 1
        return "prim_display(%s)" % (helper(thing.args[0]))
    if thing.function.name == "newline":
        assert len(thing.args) == 0
        return "prim_newline()"
    if thing.function.name == "+":
        assert len(thing.args) == 2
        return "prim_addition(%s, %s)" % (
                helper(thing.args[0]), helper(thing.args[1]))
    if thing.function.name == "*":
        assert len(thing.args) == 2
        return "prim_multiplication(%s, %s)" % (
                helper(thing.args[0]), helper(thing.args[1]))
    if thing.function.name == "-":
        assert len(thing.args) == 2
        return "prim_subtraction(%s, %s)" % (
                helper(thing.args[0]), helper(thing.args[1]))
    if thing.function.name == "/":
        assert len(thing.args) == 2
        return "prim_division(%s, %s)" % (
                helper(thing.args[0]), helper(thing.args[1]))
    if thing.function.name == "=":
        assert len(thing.args) == 2
        return "prim_equality(%s, %s)" % (
                helper(thing.args[0]), helper(thing.args[1]))
    if thing.function.name == "<":
        assert len(thing.args) == 2
        return "prim_lessthan(%s, %s)" % (
                helper(thing.args[0]), helper(thing.args[1]))
    raise LogicError, "unknown primitive!"

def write(thing, name, mutable_vars):
    helper = lambda x: write(x, name, mutable_vars)
    if type(thing) == Variable:
        if thing.three_d:
            assert thing.name == "halt"
            return "MakeClosure(&&done, 0)"
        if thing in mutable_vars:
            return "(*(((struct env_%s*)env)->%s).cell.addr)" % (name,
                    thing.name)
        return "(((struct env_%s*)env)->%s)" % (name, thing.name)
    if type(thing) == Literal:
        if thing.type == "symbol":
            return "MakeSymbol(%s)" % c_format(str(thing))
        if thing.type == "integer":
            return "MakeInteger(%s)" % thing
        if thing.type == "boolean":
            if thing.value:
                return "MakeBoolean(1)"
            return "MakeBoolean(0)"
        if thing.type == "string":
            return "MakeString(%s)" % thing
        raise LogicError, "shouldn't have gotten here"
    if type(thing) == Application:
        if thing.special():
            return write_primitive(thing, helper)
        assert type(thing.function) in (Lambda, Variable)
        assignments = ["(dest = %s)" % helper(thing.function)]
        for i, arg in enumerate(thing.args):
            assert type(arg) in (Lambda, Variable, Literal, Application)
            if type(arg) == Application: assert arg.special()
            assignments.append("(args[%d] = %s)" % (i, helper(arg)))
        return "(%s)" % ", ".join(assignments)
    if type(thing) == Begin:
        assert len(thing.instructions) == 2
        assert type(thing.instructions[0]) == SetBang
        return "((%s = %s), %s)" % (helper(thing.instructions[0].var),
                helper(thing.instructions[0].val),
                helper(thing.instructions[1]))
        raise Exception, "incomplete"
    if type(thing) == If:
        return "(isTrue(%s) ? (%s) : (%s))" % (helper(thing.test),
                helper(thing.true), helper(thing.false))
    if type(thing) == Lambda:
        return "MakeClosure(&&%s, alloc_env_%s(%s))" % (thing.name, thing.name,
                ", ".join(write(arg, name, set())
                for arg in thing.freeVariables()))
    raise LogicError, "shouldn't have gotten here"

def compile(input):
    program = parse_program(input)
    assert type(program) in (If, Begin, Application)
    lambdas = find_lambdas(program)
    all_vars = program.allVariables()
    mutable_vars = program.mutableVariables()
    immutable_vars = all_vars - mutable_vars

    out = StringIO()
    out.write(HEADER)

    max_args = 0
    for name in lambdas:
        if len(lambdas[name].args) > max_args:
            max_args = len(lambdas[name].args)

        out.write("struct env_%s {\n" % name)
        for arg in list(lambdas[name].args)+list(lambdas[name].freeVariables()):
            assert type(arg) == Variable
            assert not arg.three_d
            out.write("\tunion Value %s;\n" % arg.name)
        out.write("};\n\n")

        out.write("struct env_%s* alloc_env_%s(%s) {\n" % (
                name, name, ", ".join((
                "union Value %s" % arg.name
                for arg in lambdas[name].freeVariables()))))
        out.write("\tstruct env_%s* t = GC_MALLOC(sizeof(struct env_%s));\n" %
                (name, name))
        for arg in lambdas[name].freeVariables():
            out.write("\tt->%s = %s;\n" % (arg.name, arg.name))
        out.write("\treturn t;\n}\n\n")

    out.write(STARTMAIN)
    out.write("\tunion Value args[%d];\n" % max_args)

    out.write("\t%s;\n" % write(program, "NULL", mutable_vars))

    out.write(GRANDCENTRAL)

    for name in lambdas:
        out.write("%s:\n" % name)
        for i, arg in enumerate(lambdas[name].args):
            if arg in mutable_vars:
                out.write("\t((struct env_%s*)env)->%s = MakeCell(args[%d]);\n"
                        % (name, arg.name, i))
            else:
                out.write("\t((struct env_%s*)env)->%s = args[%d];\n" % (name,
                        arg.name, i))
        out.write("\t%s;\n" % write(lambdas[name].instruction, name,
                mutable_vars))
        out.write(CALLFUNC)

    out.write(ENDMAIN)
    out.reset()
    return out.read()

def main():
    import sys
    args = FLAGS(sys.argv)
    sys.setrecursionlimit(FLAGS.recursion_limit)
    if FLAGS.output == "c":
        if FLAGS.gc: print ENABLE_GC
        print compile(sys.stdin)
    elif FLAGS.output == "cps":
        print "(define (halt x) x)"
        print parse_program(sys.stdin)
    else:
        raise Exception, "Unknown output type requested!"

if __name__ == "__main__": main()
