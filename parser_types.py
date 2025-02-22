
from typing import NoReturn
from typing import Self

from constants import *

# TODO add: VarName VarFnType FnCanRetErr ArgsType and stuff like that

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

    def to_str(self) -> str:
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

######
###### base class
######

class BaseParserThingClass:

    def __repr__(self) -> NoReturn:
        assert False, f'trying to call __repr__ on {type(self)}'
    
    def __eq__(self, other:object) -> NoReturn:
        assert False, f'trying to call __eq__ on {type(self)}'

######
###### var name
######

class VarName(BaseParserThingClass):

    def __init__(self, name:str):
        self.name = name

    def to_str(self) -> str:
        return f'{self.name}'

    def matches(self, other:Self) -> bool:
        return self.name == other.name
    def matches_str(self, other:str) -> bool:
        return self.name == other
    
    def to_FnName(self) -> 'FnName':
        return FnName(self.name)
    
    def to_Type(self) -> 'Type':
        return Type(self.name)
    
    def to_ccode(self) -> CCode:
        # ? maybe we could omit the `$` to make the code a bit more readable and compliant
        name = self.name
        name = name.replace('-', '$M$')
        name = name.replace('+', '$P$')
        name = name.replace('(', '$OB$')
        name = name.replace(')', '$CB$')
        return CCode(name)

######
###### fn name
######

class FnName(BaseParserThingClass):

    def __init__(self, name:str):
        self.name = name

    def to_str(self) -> str:
        return f'{self.name}'

    def to_ccode(self) -> CCode:
        return VarName(self.name).to_ccode()

    def matches(self, other:Self) -> bool:
        return self.name == other.name

######
###### type
######

class Type(BaseParserThingClass):

    def __init__(self, typ:str):
        self.typ = typ

    def to_str(self) -> str:
        return f'{self.typ}'

    def to_ccode(self) -> CCode:
        return VarName(self.typ).to_ccode()

    def matches(self, other:Self) -> bool:
        if self.typ == 'any' or other.typ == 'any':
            return True

        return self.typ == other.typ

TYPE_STR = Type('str')
TYPE_ANY = Type('any') # special placeholder type that needs to go later

######
###### fn decl args
######

class FnDeclArgs(BaseParserThingClass):

    def __init__(self) -> None:
        self.args:list[tuple[VarName,Type]] = []

    def to_str(self) -> str:
        ret = ''

        for name, typ in self.args:
            ret += f'{name.to_str()}:{typ.to_str()}, '

        if ret.endswith(', '):
            ret = ret[:-2]

        ret = f'{FN_ARG_BEGIN}{ret}{FN_ARG_END}'

        return ret

    def to_ccode(self) -> CCode:
        ret = CCode('(')

        if len(self.args) == 0:
            ret += CCode('void')
        else:
            for arg_name, arg_type in self.args:
                ret += arg_type.to_ccode()
                ret += CC_SPACE
                ret += arg_name.to_ccode()
                ret += CC_COMMA_SPACE
            ret.del_if_endswith(CC_COMMA_SPACE)

        ret += CCode(')')
        return ret

    # 1st ret is err, 2nd ret is reason
    def add_another(self, arg:tuple[VarName,Type]) -> tuple[bool, str]:
        arg_name, arg_type = arg

        for name, typ in self.args:
            if name.matches(arg_name):
                return True, f'argument {arg_name.to_str()} already specified'

        self.args.append(arg)
        return False, ''

# TODO!!!! delete if it seems that this is useless
# ######
# ###### tuple
# ######

# class Tuple(BaseParserThingClass):

#     def __init__(self) -> None:
#         self.value:list[Value] = []

######
###### var
######

class Var(BaseParserThingClass):

    def __init__(self, name_or_value:str, typ:Type):
        self.name_or_value = name_or_value
        self.typ = typ

    def to_str(self) -> str:
        return f'{self.name_or_value}{VAR_TYPE_SEP}{self.typ.to_str()}'

    def to_ccode(self) -> CCode:
        if self.typ.to_str() == TYPE_STR.to_str(): # kinda hacky but we can't use `matches`
            return CCode('"' + self.name_or_value[1:-1] + '"')
        else:
            return VarName(self.name_or_value).to_ccode() # needed so that we can have shit like `(` in the variable name

######
###### fn call
######

class FnCall(BaseParserThingClass):

    def __init__(self, name:FnName, args:'ValueTuple'):
        self.name = name
        self.args = args

    def to_str(self) -> str:
        return f'{self.name.to_str()}{self.args.to_str()}'

    def to_ccode(self) -> CCode:
        ret = self.name.to_ccode()
        ret += self.args.to_ccode()
        return ret

######
###### value
######

class Value(BaseParserThingClass):

    def __init__(self, value:Var|FnCall):
        self.value = value
    
    def to_str(self) -> str:
        return self.value.to_str()
    
    def to_ccode(self) -> CCode:
        return self.value.to_ccode()

######
###### value tuple
######

class ValueTuple(BaseParserThingClass): # TODO!!!! and use this everywhere instead of using ', '.join() manually every time

    def __init__(self) -> None:
        self.value:list[Value] = []
    
    def to_str(self) -> str:
        ret = TUPLE_BEGIN

        for item in self.value:
            ret += f'{item.to_str()}, '
        
        if ret.endswith(', '):
            ret = ret[:-2]

        ret += TUPLE_END

        return ret
    
    def to_ccode(self) -> CCode:
        ret = CCode('')

        ret += CC_OB

        for item in self.value:
            ret += item.to_ccode()
            ret += CC_COMMA_SPACE

        ret.del_if_endswith(CC_COMMA_SPACE)

        ret += CC_CB

        return ret

    def add_another(self, item:Value) -> None:
        self.value.append(item)

######
###### string check
######

def is_str(obj:str) -> bool:
    if isinstance(obj, str):
        if obj.startswith(STRING):
            assert obj.endswith(STRING)
            assert len(obj) >= 2
            assert obj[1:-1].count(STRING) == 0
            assert obj[1:-1].count('"') == 0
            return True
        return False
    else:
        assert False
