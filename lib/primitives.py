#!/usr/bin/env python

from util import Sym, TD

DISPLAY = [Sym("define"), [Sym("display"), Sym("object")], [TD("display"),
        Sym("object")]]
NEWLINE = [Sym("define"), [Sym("newline")], [TD("newline")]]
ADDITION = [Sym("define"), [Sym("+"), Sym("x"), Sym("y")], [TD("+"), Sym("x"),
        Sym("y")]]
MULTIPLICATION = [Sym("define"), [Sym("*"), Sym("x"), Sym("y")], [TD("*"),
        Sym("x"), Sym("y")]]
SUBTRACTION = [Sym("define"), [Sym("-"), Sym("x"), Sym("y")], [TD("-"),
        Sym("x"), Sym("y")]]
DIVISION = [Sym("define"), [Sym("/"), Sym("x"), Sym("y")], [TD("/"), Sym("x"),
        Sym("y")]]
EQUALITY = [Sym("define"), [Sym("="), Sym("x"), Sym("y")], [TD("="), Sym("x"),
        Sym("y")]]
LESSTHAN = [Sym("define"), [Sym("<"), Sym("x"), Sym("y")], [TD("<"), Sym("x"),
        Sym("y")]]
CALLCC = [Sym("define"), [Sym("call/cc"), Sym("func")], [TD("call/cc"),
        Sym("func")]]

PRIMITIVES = [
              DISPLAY,
              NEWLINE,
              ADDITION,
              MULTIPLICATION,
              SUBTRACTION,
              DIVISION,
              EQUALITY,
              LESSTHAN,
              CALLCC,
              ]

PRIMITIVE_NAMES = set(["display", "newline", "+", "*", "-", "/", "=", "<",
        "call/cc"])

def wrap(sexps, include_primitives=True):
    rv = [Sym("begin")]
    if include_primitives: rv += PRIMITIVES
    return rv + sexps
