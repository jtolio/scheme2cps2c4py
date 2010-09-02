#!/usr/bin/env python

from parse_tree import Exp, Variable, Literal, Application, Begin, If, Lambda, \
        SetBang

def rename(exp, name_cache={}, data={"counter": 0}):
    if type(exp) == Variable:
        if exp.three_d and exp.name[:len("gensym")] != "gensym":
            return exp
        if not name_cache.has_key((exp.name, exp.three_d)):
            data["counter"] += 1
            name_cache[(exp.name, exp.three_d)] = "x%d" % data["counter"]
        return Variable(name_cache[(exp.name, exp.three_d)], False)
    if type(exp) == Literal: return exp
    if type(exp) == Application:
        return Application(rename(exp.function), *map(rename, exp.args))
    if type(exp) == Begin:
        return Begin(map(rename, exp.instructions))
    if type(exp) == If:
        return If(rename(exp.test), rename(exp.true), rename(exp.false))
    if type(exp) == Lambda:
        return Lambda(map(rename, exp.args), rename(exp.instruction), exp.name)
    if type(exp) == SetBang:
        return SetBang(rename(exp.var), rename(exp.val))

def merge_two_dicts(dict1, dict2):
    for key in dict2:
        assert not dict1.has_key(key)
        dict1[key] = dict2[key]
    return dict1

def find_lambdas(exp):
    if type(exp) in (Variable, Literal): return {}
    if type(exp) == Application:
        lambdas = find_lambdas(exp.function)
        for arg in exp.args:
            lambdas = merge_two_dicts(lambdas, find_lambdas(arg))
        return lambdas
    if type(exp) == Begin:
        lambdas = {}
        for inst in exp.instructions:
            lambdas = merge_two_dicts(lambdas, find_lambdas(inst))
        return lambdas
    if type(exp) == If:
        return merge_two_dicts(find_lambdas(exp.test),
                merge_two_dicts(find_lambdas(exp.true),
                        find_lambdas(exp.false)))
    if type(exp) == SetBang:
        return merge_two_dicts(find_lambdas(exp.var), find_lambdas(exp.val))
    assert type(exp) == Lambda
    lambdas = {exp.name: exp}
    for arg in exp.args:
        lambdas = merge_two_dicts(lambdas, find_lambdas(arg))
    return merge_two_dicts(lambdas, find_lambdas(exp.instruction))
