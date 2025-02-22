
from constants import *

######
###### ccode
######

# CCode = typing.NewType("CCode", str)
# # even using this, mypy still allows passing `CCode` to functions requiring a `str` argument

# I really didn't want to do this but
# I couldn't find a way to get the compiler
# to act more strictly
class CCode:

    def __init__(self, val:str):
        self.val = val

    def __iadd__(self, other:'CCode') -> 'CCode':
        self.val += other.val
        return self
    
    def __repr__(self) -> str: # TODO as of 2025.02.22 we're still relying on this in the code, the affected code needs to use `as_str` instead
        assert False, 'calling __repr__ on CCode'
        return f'{self.val}'

    def as_str(self) -> str:
        return f'{self.val}'

    def empty(self) -> bool:
        return len(self.val) == 0

    def del_if_endswith(self, end:'CCode') -> None:
        if self.val.endswith(end.val):
            self.val = self.val[:-len(end.val)]

    def del_if_startswith(self, start:'CCode') -> None:
        if self.val.startswith(start.val):
            self.val = self.val[len(start.val):]

CC_SPACE = CCode(' ')
CC_SEMICOLON_NEWLINE = CCode(';\n')
CC_ASSIGN = CCode(' = ')
CC_OB = CCode('(')
CC_CB = CCode(')')
CC_COMMA_SPACE = CCode(', ')
CC_WARNUNUSEDRESULT_SPACE = CCode('__attribute__((warn_unused_result)) ')
CC_CBO = CCode('{')
CC_CBC = CCode('}')
CC_NEWLINE = CCode('\n')

# str to CCode converters

def argtuple_to_ccallargs(args:tuple[str, ...]) -> CCode:
    ret = CCode('')

    for val in args:
        ret += value_to_ccode(val)
        ret += CC_COMMA_SPACE

    ret.del_if_endswith(CC_COMMA_SPACE)

    return ret

def argtuple_to_cdeclargs(args:tuple[tuple[str, str], ...]) -> CCode:
    ret = CCode('')

    if len(args) == 0:
        ret += CCode('void')
    else:
        for arg_name, arg_type in args:
            ret += type_to_ccode(arg_type)
            ret += CC_SPACE
            ret += varname_to_ccode(arg_name)
            ret += CC_COMMA_SPACE
        ret.del_if_endswith(CC_COMMA_SPACE)

    return ret

def varname_to_ccode(name:str) -> CCode:
    # maybe we could omit the `$` to make the code a bit more readable and compliant
    name = name.replace('-', '$M$')
    name = name.replace('+', '$P$')
    name = name.replace('(', '$OB$')
    name = name.replace(')', '$CB$')
    return CCode(name)

def value_to_ccode(value:str) -> CCode:
    if value.startswith(STRING):
        assert value.endswith(STRING)
        assert len(value) >= 2
        assert value[1:-1].count(STRING) == 0
        assert value[1:-1].count('"') == 0
        return CCode('"' + value[1:-1] + '"')
    return varname_to_ccode(value)

def type_to_ccode(typ:str) -> CCode:
    return CCode(typ)

def ctuple_to_ccallargs(args:tuple[CCode, ...]) -> CCode:
    ret = CCode('')
    for arg in args:
        ret += CC_COMMA_SPACE
        ret += arg
    ret.del_if_startswith(CC_COMMA_SPACE)
    return ret

