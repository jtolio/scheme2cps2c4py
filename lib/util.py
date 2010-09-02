#!/usr/bin/env python

class Error_(Exception): pass
class ParserError(Error_): pass
class LogicError(Error_): pass

class LazyList(object):
    """This class turns a Python stream into a lazy list of characters"""

    def __init__(self, stream, starting_lineno = 0):
        """Args:
            stream: a stream object that can read a byte at a time
        """
        self._stream, self._char, self._tail = stream, None, None
        self._lineno = starting_lineno

    def eof(self):
        """Returns if this node in the Lazy List designates end of file
        Args: None
        Returns: boolean
        """
        if self._char is None:
            self._char = self._stream.read(1)
        return not self._char

    def head(self):
        """Returns the character at this node of the list
        Args: None
        Returns: length-1 string
        """
        if self.eof(): return ""
        return self._char

    def tail(self):
        """Returns a LazyList of the remainder of the input
        Args: None
        Returns: A LazyList
        """
        if self.eof(): return self
        if self._tail is None:
            new_lineno = self._lineno
            if self._char == "\n": new_lineno += 1
            self._tail = LazyList(self._stream, new_lineno)
        return self._tail

    def __str__(self):
        """Converts the input into a Python string"""
        if self.eof(): return ""
        return self.head() + str(self.tail())

    def lineno(self):
        """Returns the line number of the current character"""
        return self._lineno

class Token(object):
    def __init__(self, type, value):
        assert type in ("symbol", "string", "integer", "boolean", "3d-symbol")
        self.type, self.value = type, value
    def __repr__(self):
        return "Token(%r, %r)" % (self.type, self.value)
    def __str__(self):
        if self.type == "symbol": return self.value
        elif self.type == "string": return c_format(self.value)
        elif self.type == "integer": return repr(self.value)
        elif self.type == "boolean":
            if not self.value: return "#f"
            return "#t"
        elif self.type == "3d-symbol": return self.value
        else: raise LogicError, "Unknown type: %s" % self.type
    def isSymbol(self, symbol):
        return self.type == "symbol" and self.value == symbol
    def __hash__(self):
        return hash((self.type, self.value))
    def __cmp__(self, other):
        if type(self) != type(other):
            return cmp(type(self), type(other))
        return cmp((self.type, self.value), (other.type, other.value))

def Sym(value):
    return Token("symbol", value)

def TD(value):
    return Token("3d-symbol", value)

def c_format(string):
    for pair in (('\\', r'\\'),
                 ('\n', r'\n'),
                 ('\r', r'\r'),
                 ('"',  r'\"'),
                 ('\t', r'\t')):
        string = string.replace(*pair)
    return '"%s"' % string
