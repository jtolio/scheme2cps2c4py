#!/usr/bin/env python

from parse_tree import Exp, Variable, Literal, Application, Begin, If, Lambda, \
        SetBang

def gensym(cache={}):
    if not cache.has_key("counter"):
        cache["counter"] = 0
    cache["counter"] += 1
    return Variable("gensym-%d" % cache["counter"], True)

def curry(exp):
    if type(exp) == Variable: return exp
    if type(exp) == Literal: return exp
    if type(exp) == Application:
        if exp.special():
            return Application(exp.function, *map(curry, exp.args))
        function = curry(exp.function)
        args = map(curry, exp.args)
        if not args: return Application(function, Literal("boolean", False))
        app = function
        for arg in args:
            app = Application(app, arg)
        return app
    if type(exp) == Begin:
        return Begin(map(curry, exp.instructions))
    if type(exp) == If:
        return If(curry(exp.test), curry(exp.true), curry(exp.false))
    if type(exp) == Lambda:
        if not exp.args:
            return Lambda([gensym()], curry(exp.instruction), exp.name)
        if len(exp.args) == 1:
            return Lambda(exp.args, curry(exp.instruction), exp.name)
        assert len(exp.args) > 1
        func = curry(exp.instruction)
        for arg in reversed(exp.args):
            func = Lambda([arg], func)
        return func
    if type(exp) == SetBang:
        return SetBang(exp.var, curry(exp.val))

def transmogrify(exp):
    if type(exp) == Variable and exp.three_d and exp.name == "call/cc":
        f, k1, x, k2 = gensym(), gensym(), gensym(), gensym()
        return Lambda([f, k1], Application(f, Lambda([x, k2],
                Application(k1, x)), k1))
    if type(exp) != Lambda: return exp
    var_c = gensym()
    return Lambda(exp.args + [var_c],
            cps_transform(exp.instruction, var_c), exp.name)

def cps_transform(node, continuation=None):
    if continuation is None: continuation = Variable("halt", True)
    if node.isTrivial():
        return Application(continuation, transmogrify(node))
    if type(node) == Application:
        vars = [gensym() for x in node.args]
        var_f = gensym()
        call = cps_transform(node.function, Lambda([var_f],
                Application(*([var_f] + vars + [continuation]))))
        for arg, var in zip(node.args, vars):
            call = cps_transform(arg, Lambda([var], call))
        return call
    if type(node) == Begin:
        assert len(node.instructions) > 0
        last_instruction = node.instructions[-1]
        last = cps_transform(last_instruction, continuation)
        if not node.instructions[:-1]:
            return last
        return cps_transform(Begin(node.instructions[:-1]), Lambda([gensym()],
                last))
    if type(node) == SetBang:
        var = gensym()
        return cps_transform(node.val, Lambda([var],
                Begin([SetBang(node.var, var),
                Application(continuation, Literal("boolean", False))])))
    if type(node) == If:
        var = gensym()
        return cps_transform(node.test, Lambda([var],
                If(var, cps_transform(node.true, continuation),
                        cps_transform(node.false, continuation))))
    raise LogicError, "huh?"
