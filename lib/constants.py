#!/usr/bin/env python

ENABLE_GC = "#define DO_GC"

HEADER = """\
#include <stdlib.h>
#include <stdio.h>

#ifdef DO_GC
#include <gc/gc.h>
#else
#define GC_MALLOC(size) malloc(size)
#define GC_MALLOC_ATOMIC(size) malloc(size)
#define GC_INIT() {}
#endif

enum Tag { INTEGER, BOOLEAN, STRING, SYMBOL, CLOSURE, CELL, ENV };

union Value;

struct Integer {
    enum Tag t;
    int value;
};

struct Boolean {
    enum Tag t;
    char value;
};

struct String {
    enum Tag t;
    char* value;
};

struct Symbol {
    enum Tag t;
    char* value;
};

struct Closure {
    enum Tag t;
    void* func;
    void* env;
};

struct Cell {
    enum Tag t;
    union Value* addr;
};

struct Env {
    enum Tag t;
    void* env;
};

union Value {
    enum Tag t;
    struct Integer integer;
    struct Boolean boolean;
    struct String string;
    struct Symbol symbol;
    struct Closure closure;
    struct Cell cell;
};

static union Value MakeInteger(int n) {
    static union Value v;
    v.t = INTEGER;
    v.integer.value = n;
    return v;
}

static union Value MakeBoolean(char val) {
    static union Value v;
    v.t = BOOLEAN;
    v.boolean.value = val;
    return v;
}

static union Value MakeString(char* val) {
    static union Value v;
    v.t = STRING;
    v.string.value = val;
    return v;
}

static union Value MakeSymbol(char* val) {
    static union Value v;
    v.t = SYMBOL;
    v.symbol.value = val;
    return v;
}

static union Value MakeClosure(void* func, void* env) {
    static union Value v;
    v.t = CLOSURE;
    v.closure.func = func;
    v.closure.env = env;
    return v;
}

static union Value MakeCell(union Value initialValue) {
    union Value v;
    v.t = CELL;
    v.cell.addr = GC_MALLOC(sizeof(union Value));
    *(v.cell.addr) = initialValue;
    return v;
}

static char isTrue(union Value v) {
    return (v.t != BOOLEAN || v.boolean.value);
}

static union Value prim_display(union Value a) {
    switch(a.t) {
        case INTEGER:
            printf("%d", a.integer.value); break;
        case BOOLEAN:
            if(a.boolean.value) printf("#t");
            else printf("#f");
            break;
        case STRING:
            printf("%s", a.string.value); break;
        case SYMBOL:
            printf("%s", a.symbol.value); break;
        case CLOSURE:
            printf("<anonymous-function>"); break;
        default:
            printf("unknown type!\\n");
            exit(-1);
    }
    return MakeBoolean(0);
}

static union Value prim_newline() {
    printf("\\n");
    return MakeBoolean(0);
}

static union Value prim_addition(union Value a, union Value b) {
    if(a.t != INTEGER || b.t != INTEGER) {
        printf("expects two integers!\\n");
        exit(-1);
    }
    return MakeInteger(a.integer.value + b.integer.value);
}

static union Value prim_multiplication(union Value a, union Value b) {
    if(a.t != INTEGER || b.t != INTEGER) {
        printf("expects two integers!\\n");
        exit(-1);
    }
    return MakeInteger(a.integer.value * b.integer.value);
}

static union Value prim_subtraction(union Value a, union Value b) {
    if(a.t != INTEGER || b.t != INTEGER) {
        printf("expects two integers!\\n");
        exit(-1);
    }
    return MakeInteger(a.integer.value - b.integer.value);
}

static union Value prim_division(union Value a, union Value b) {
    if(a.t != INTEGER || b.t != INTEGER) {
        printf("expects two integers!\\n");
        exit(-1);
    }
    return MakeInteger(a.integer.value / b.integer.value);
}

static union Value prim_equality(union Value a, union Value b) {
    if(a.t != INTEGER || b.t != INTEGER) {
        printf("expects two integers!\\n");
        exit(-1);
    }
    return MakeBoolean(a.integer.value == b.integer.value);
}

static union Value prim_lessthan(union Value a, union Value b) {
    if(a.t != INTEGER || b.t != INTEGER) {
        printf("expects two integers!\\n");
        exit(-1);
    }
    return MakeBoolean(a.integer.value < b.integer.value);
}

"""

STARTMAIN = """\
int main(int argc, char **argv) {
    void* env = NULL;
    union Value dest;
    dest.t = BOOLEAN;

    GC_INIT();

"""

GRANDCENTRAL = """\
grandcentral:
    if(dest.t != CLOSURE) {
        printf("cannot call a non-function!\\n");
        exit(-1);
    }
    env = dest.closure.env;
    goto *dest.closure.func;
"""

CALLFUNC = """\
    goto grandcentral;
"""

ENDMAIN = """\
done:
    return 0;
};
"""
