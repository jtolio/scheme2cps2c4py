#!/usr/bin/env python

from util import Token, ParserError, Sym

KEYWORDS = set(["if", "set!", "lambda", "begin", "cond", "else", "let",
        "letrec", "quote", "and", "or", "define"])

def eliminate_keywords(node):
    if type(node) == Token: return node
    if not node:
        raise ParserError, "Application missing method!"
    if type(node[0]) != Token or node[0].type != "symbol":
        return map(eliminate_keywords, node)
    if node[0].isSymbol("if"):
        if len(node) == 3:
            return handle_conditional(node[1], node[2], Token("boolean", False))
        elif len(node) == 4:
            return handle_conditional(node[1], node[2], node[3])
        else: raise ParserError, "Wrong number of parameters to 'if'"
    if node[0].isSymbol("set!"):
        if len(node) != 3:
            raise ParserError, "Wrong number of parameters to 'set!'"
        if type(node[1]) != Token or node[1].type != "symbol":
            raise ParserError, "First parameter to 'set!' expected to be a " \
                    "variable"
        return [node[0], node[1], eliminate_keywords(node[2])]
    if node[0].isSymbol("lambda"):
        if len(node) < 3:
            raise ParserError, "lambda expects a list of arguments and a body"
        if type(node[1]) != list:
            raise ParserError, "First parameter to 'lambda' expected to be a " \
                    "list of arguments"
        var_names = set()
        for arg in node[1]:
            if type(arg) != Token or arg.type != "symbol":
                raise ParserError, "First parameter to 'lambda' expected to " \
                        "be a list of arguments"
            if arg.value in KEYWORDS:
                raise ParserError, "'lambda' got an argument that is a " \
                        "reserved word"
            if arg.value in var_names:
                raise ParserError, "'lambda' got two identically named " \
                        "arguments"
            var_names.add(arg.value)
        if len(node) > 3:
            return [node[0], node[1]] + [eliminate_keywords([Sym("begin")] +
                    node[2:])]
        return [node[0], node[1], eliminate_keywords(node[2])]
    if node[0].isSymbol("begin"):
        return handle_begin(node[1:])
    if node[0].isSymbol("cond"):
        return eliminate_keywords(rewrite_cond(node[1:]))
    if node[0].isSymbol("let"):
        return eliminate_keywords(rewrite_let(node[1:]))
    if node[0].isSymbol("letrec"):
        return eliminate_keywords(rewrite_letrec(node[1:]))
    if node[0].isSymbol("quote"):
        return node
    if node[0].isSymbol("and") or node[0].isSymbol("or"):
        raise ParserError, "'and' and 'or' are only supported as part of an " \
                "if expression"
    return map(eliminate_keywords, node)

def rewrite_cond(args):
    if not args: return Token("boolean", False)
    if type(args[0]) != list:
        raise ParserError, "Parameters to 'cond' are expected to be lists"
    if not args[0]:
        raise ParserError, "Parameters to 'cond' are expected to be non-empty "\
                "lists"
    if type(args[0][0]) == Token and args[0][0].isSymbol("else"):
        if len(args) != 1:
            raise ParserError, "'else' is supposed to be the last conditional "\
                    "in 'cond'"
        if len(args[0]) != 2:
            raise ParserError, "'else' expects one value in 'cond'"
        return args[0][1]
    rv = [Sym("if"), args[0][0]]
    if len(args[0]) > 1:
        if type(args[0][1]) == Token and args[0][1].isSymbol("=>"):
            if len(args[0]) != 3:
                raise ParserError, "'=>' format in cond expects (<exp> => " \
                        "<exp>)"
            rv.append(args[0][2])
        elif len(args[0]) == 2:
            rv.append(args[0][1])
        else:
            rv.append([Sym("begin")] + args[0][1:])
    else:
        rv.append(Token("boolean", False))
    return rv + [rewrite_cond(args[1:])]

def check_let(node, name):
    if len(node) < 2:
        raise ParserError, "'%s' expects a binding list and a body" % name
    if type(node[0]) != list:
        raise ParserError, "'%s' expects a binding list as the first " \
                "parameter" % name

def check_binding(binding):
    if type(binding) != list or len(binding) != 2:
        raise ParserError, "bindings are supposed to be lists of length 2"
    if type(binding[0]) != Token or binding[0].type != "symbol":
        raise ParserError, "left side of binding is supposed to be a " \
                "variable"

def rewrite_let(node):
    check_let(node, "let")
    if not node[0]: return [Sym("begin")] + node[1:]
    args, vals = [], []
    for binding in node[0]:
        check_binding(binding)
        args.append(binding[0])
        vals.append(binding[1])
    return [[Sym("lambda"), args] + node[1:]] + vals

def rewrite_letrec(node):
    check_let(node, 'letrec')
    if not node[0]: return [Sym("begin")] + node[1:]
    args, defines = [], []
    for binding in node[0]:
        check_binding(binding)
        args.append(binding[0])
        defines.append([Sym("set!"), binding[0], binding[1]])
    return [[Sym("lambda"), args] + defines + node[1:]] + \
            [Token("boolean", False) for a in args]

def handle_define(define):
    if type(define[0]) == Token and define[0].type == "symbol":
        return define[0], eliminate_keywords(define[1])
    if type(define[0]) != list:
        raise ParserError, "'define' expects a list or a variable as the " \
                "first parameter"
    if not define[0]:
        raise ParserError, "'define' used for function definition " \
                "requires a function name"
    for thing in define[0]:
        if type(thing) != Token or thing.type != "symbol":
            raise ParserError, "'define' requires a list of symbols"
    name, args, body = define[0][0], define[0][1:], define[1:]
    return name, eliminate_keywords([Sym("lambda"), args] + body)

def handle_begin(node):
    if len(node) == 1: return eliminate_keywords(node[0])
    body, argdefines = [], {}
    found_body = False
    for thing in node:
        if type(thing) != list or not thing or type(thing[0]) != Token or \
                not thing[0].isSymbol("define"):
            found_body = True
            body.append(thing)
            continue
        if found_body:
            raise ParserError, "defines must come before expressions!"
        arg, val = handle_define(thing[1:])
        argdefines[arg] = [Sym("set!"), arg, val]
    if not argdefines:
        return [Sym("begin")] + map(eliminate_keywords, body)
    args = argdefines.keys()
    return eliminate_keywords([[Sym("lambda"), args] +
            [argdefines[key] for key in args] + body] +
            [Token("boolean", False) for a in args])

def handle_conditional(cond, true, false):
    if type(cond) != list or not cond or type(cond[0]) != Token or not (
            cond[0].isSymbol("and") or cond[0].isSymbol("or")):
        return [Sym("if")] + map(eliminate_keywords, [cond, true, false])
    if cond[0].isSymbol("and"):
        if len(cond) == 1: return eliminate_keywords(true)
        return eliminate_keywords([Sym("if"), cond[1], [Sym("if"), [Sym("and")]
                + cond[2:], true, false], false])
    if cond[0].isSymbol("or"):
        if len(cond) == 1: return eliminate_keywords(false)
        return eliminate_keywords([Sym("if"), cond[1], true, [Sym("if"),
                [Sym("or")] + cond[2:], true, false]])
    raise LogicError, "I don't understand how this error could happen"

desugar = eliminate_keywords
