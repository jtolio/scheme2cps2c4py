#!/usr/bin/env python

from util import LazyList, Token, ParserError, LogicError
import re
from cStringIO import StringIO

WHITESPACE = re.compile(r'^[\n\r \t]$')

def read_list(lst):
    items = []
    while not lst.eof() and lst.head() not in (")", "]"):
        item, lst = read(lst)
        if item is not None: items.append(item)
    return items, lst

def read(lst):
    # skip whitespace
    while True:
        if lst.eof(): break
        if not WHITESPACE.match(lst.head()): break
        lst = lst.tail()

    # anything to read?
    if lst.eof() or lst.head() in (")", "]"): return None, lst

    # lists
    for start_char, end_char in (("(", ")"), ("[", "]")):
        if lst.head() == start_char:
            item, lst = read_list(lst.tail())
            if lst.head() != end_char:
                raise ParserError, "Line %d: Missing %s" % (lst.lineno(),
                        end_char)
            return item, lst.tail()

    # single line comments
    if lst.head() == ";":
        while True:
            lst = lst.tail()
            if lst.eof(): return None, lst
            if lst.head() == "\n": return None, lst.tail()

    # nested comments
    if lst.head() == "#" and lst.tail().head() == "!":
        depth = 1
        lst = lst.tail()
        while True:
            lst = lst.tail()
            if lst.eof():
                raise ParserError, "Line %d: Missing !#" % lst.lineno()
            if lst.head() == "#" and lst.tail().head() == "!":
                depth += 1
                lst = lst.tail()
                continue
            if lst.head() == "!" and lst.tail().head() == "#":
                depth -= 1
                lst = lst.tail()
                if depth == 0: return None, lst.tail()
                continue

    # integers
    if ((lst.head() == "-" and lst.tail().head().isdigit()) or
            lst.head().isdigit()):
        val = lst.head()
        while True:
            lst = lst.tail()
            if not lst.head().isdigit(): break
            val += lst.head()
        return Token("integer", int(val)), lst

    # strings
    if lst.head() == '"':
        val = ""
        while True:
            lst = lst.tail()
            if lst.eof():
                raise ParserError, "Line %d: Missing \"" % lst.lineno()
            if lst.head() == '"': break
            if lst.head() == "\\" and not lst.tail().eof():
                lst = lst.tail()
                if lst.head() == "n": val += "\n"
                elif lst.head() == '"': val += '"'
                elif lst.head() == "\\": val += "\\"
                else:
                    raise ParserError, ("Line %d: Invalid escape sequence: "
                            "\\%s" % (lst.lineno(), lst.head()))
                continue
            val += lst.head()
        return Token("string", val), lst.tail()

    # booleans
    if lst.head() == "#" and lst.tail().head().lower() in ("f", "t"):
        return Token("boolean", lst.tail().head().lower() != "f"), \
                lst.tail().tail()

    # quotes
    if lst.head() == "'":
        item, lst = read(lst.tail())
        return [Token("symbol", "quote"), item], lst

    # symbols
    # symbols are non-whitespace characters that don't start comments and don't
    # have parentheses. further, an arbitrary character can be inserted into a
    # symbol by doing #\<char>
    val = ""
    while True:
        if lst.eof(): break
        if lst.head() in ("(", ")", ";", "[", "]"): break
        if lst.head() == "#" and lst.tail().head() == "!": break
        if WHITESPACE.match(lst.head()): break
        if lst.head() == "#" and lst.tail().head() == "\\":
            lst = lst.tail().tail()
            if lst.eof():
                raise ParserError, "Line %d: Missing character" % lst.lineno()
        val += lst.head()
        lst = lst.tail()
    if not val: raise LogicError, "no symbol?"
    return Token("symbol", val), lst

def parse(input):
    if not hasattr(input, "read"): input = StringIO(input)
    sexps, lst = read_list(LazyList(input))
    if not lst.eof(): raise LogicError, "didn't parse whole file?"
    return sexps

def serialize(node):
    if type(node) == Token: return str(node)
    assert type(node) == list
    return "(%s)" % " ".join(map(serialize, node))
