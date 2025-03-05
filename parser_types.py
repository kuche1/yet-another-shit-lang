
from typing import Generator
from typing import NoReturn
from typing import Callable
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

    def to_TypeTuple(self) -> 'TypeTuple':
        return TypeTuple(any_=True)

    def empty(self) -> bool:
        return len(self.val) == 0

    def del_if_endswith(self, end:'CCode') -> None:
        if self.val.endswith(end.val):
            self.val = self.val[:-len(end.val)]

    def del_if_startswith(self, start:'CCode') -> None:
        if self.val.startswith(start.val):
            self.val = self.val[len(start.val):]

CC_SPACE = CCode(' ')
CC_SEMICOLON_NL = CCode(';\n')
CC_ASSIGN = CCode(' = ')
CC_OB = CCode('(')
CC_CB = CCode(')')
CC_COMMA_SPACE = CCode(', ')
CC_WARNUNUSEDRESULT_SPACE = CCode('__attribute__((warn_unused_result)) ')
CC_CBO = CCode('{')
CC_CBC = CCode('}')
CC_NL = CCode('\n')


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
        if self.matches(TYPE_COMPTIME_STR):
            return CCode('char*')
        return VarName(self.typ).to_ccode()

    def matches(self, other:Self) -> bool:
        if self.typ == 'any' or other.typ == 'any':
            return True

        return self.typ == other.typ

TYPE_COMPTIME_STR = Type('comptime_str')
TYPE_CSTR = Type('char*')
TYPE_ANY = Type('any') # special placeholder type that needs to go later
# TYPE_CSTR = Type('char*') # TODO better idea to use this I think

######
###### type tuple
######

class TypeTuple(BaseParserThingClass):

    def __init__(self, any_:bool=False) -> None:
        self.any = any_
        self.vals:list[Type] = []

    def to_str(self) -> str:
        ret = ''
        for typ in self.vals:
            ret += f', {typ.to_str()}'
        if ret.startswith(', '):
            ret = ret[2:]
        return ret

    def matches(self, other:Self) -> bool:
        if self.any or other.any:
            return True

        if len(self.vals) != len(other.vals):
            return False
        
        for s_val, o_val in zip(self.vals, other.vals, strict=True):
            if not s_val.matches(o_val):
                return False
        
        return True
    
    def add_another(self, val:Type) -> None:
        assert not self.any
        self.vals.append(val)

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
    
    def to_TypeTuple(self) -> 'TypeTuple':
        ret = TypeTuple()
        for _name, typ in self.args:
            ret.add_another(typ)
        return ret
    
    def generator(self) -> Generator[tuple[VarName,Type]]:
        # for arg in self.args:
        #   yield arg
        # pylint is telling me to use this instead
        yield from self.args

    # 1st ret is err, 2nd ret is reason
    def add_another(self, arg:tuple[VarName,Type]) -> tuple[bool, str]:
        arg_name, _arg_type = arg

        for name, _typ in self.args:
            if name.matches(arg_name):
                return True, f'argument {arg_name.to_str()} already specified'

        self.args.append(arg)
        return False, ''

######
###### var
######

class Var(BaseParserThingClass):

    # TODO!!!! actually, i think its about time that we got rid of `name_or_value`
    def __init__(self, name_or_value:str, typ:Type):
        self.name_or_value = name_or_value # TODO!!! `name_or_value` is stupid and makes everything more complex, it only exists because string can be their own thing and are not put into variables
        self.typ = typ

    def to_str(self) -> str:
        return f'{self.name_or_value}{VAR_TYPE_SEP}{self.typ.to_str()}'

    def to_ccode(self) -> CCode:
        if self.typ.to_str() == TYPE_COMPTIME_STR.to_str(): # kinda hacky but we can't use `matches`
            return CCode('"' + self.name_or_value[1:-1] + '"')
        return VarName(self.name_or_value).to_ccode() # needed so that we can have shit like `(` in the variable name
    
    def get_type(self) -> Type:
        return self.typ

######
###### fn call
######

class FnCall(BaseParserThingClass):

    # TODO!! I hate the fact taht we have to pass warn an err
    def __init__(self, name:FnName, args:'ValueTuple', ret_type:Type, original_signature:'FnSignature', warn:Callable[[str],None], err:Callable[[str],NoReturn]):

        if original_signature.get_can_ret_err():
            warn(f'calling function `{name.to_str()}` that can return error') # TODO!! make the compiler take care of this instead of just printing a warning

        # TODO check return type ?

        decl_args = original_signature.get_arg_types()
        call_args = args.to_TypeTuple()

        if not decl_args.matches(call_args):
            err(f'declaration args do not match call args for function `{name.to_str()}`: `{decl_args.to_str()}` and `{call_args.to_str()}`')

        self.name = name
        self.args = args
        self.ret_type = ret_type

    def to_str(self) -> str:
        return f'{self.name.to_str()}{self.args.to_str()}'

    def to_ccode(self) -> CCode:
        ret = self.name.to_ccode()
        ret += self.args.to_ccode()
        return ret
    
    def get_ret_type(self) -> Type:
        return self.ret_type

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
    
    def to_Type(self) -> Type:
        if isinstance(self.value, FnCall):
            return self.value.get_ret_type()
        if isinstance(self.value, Var):
            return self.value.get_type()
        assert False

######
###### value tuple
######

class ValueTuple(BaseParserThingClass):

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
    
    def to_TypeTuple(self) -> TypeTuple:
        ret = TypeTuple()
        for val in self.value:
            ret.add_another(val.to_Type())
        return ret

    def add_another(self, item:Value) -> None:
        self.value.append(item)

######
###### SPECIAL: fn signature
######

class FnSignature:

    def __init__(self, name:FnName, can_ret_err:bool, return_type:Type, args:CCode|FnDeclArgs) -> None:
        self.name = name
        self.can_ret_err = can_ret_err
        self.return_type = return_type
        self.args = args

    def __repr__(self) -> str:
        err_type = FTS_ERR if self.can_ret_err else FTS_NO_ERR
        return f'`fn {self.name.to_str()}{err_type}{self.return_type.to_str()} {self.args.to_str()}`'

    def __eq__(self, other:object) -> NoReturn:
        assert False, 'trying to call __eq__ on FnSignature'
    def matches(self, other:Self) -> tuple[bool, str]:
        if not self.name.matches(other.name):
            return False, f'name missmatch `{self.name.to_str()}` and `{other.name.to_str()}`'

        if self.can_ret_err != other.can_ret_err:
            return False, 'difference in ability to return an error'

        if not self.return_type.matches(other.return_type):
            return False, f'return type missmatch `{self.return_type.to_str()}` and `{other.return_type.to_str()}`'

        # if `args` is CCode just give up and pretend they're the same
        if isinstance(self.args, CCode) or (isinstance(other.args, CCode)):
            pass
        else:
            if self.args != other.args:
                return False, f'arguments: {self.args} != {other.args}'
        
        return True, ''
    
    def get_can_ret_err(self) -> bool:
        return self.can_ret_err
    
    def get_arg_types(self) -> TypeTuple:
        return self.args.to_TypeTuple()
    
    def get_ret_type(self) -> Type:
        return self.return_type

DUMMY_FN_SIGNATURE = FnSignature(FnName('dummy'), False, Type('int'), CCode('(void)'))

class FnSignatures:

    def __init__(self) -> None:
        self.fns:list[FnSignature] = []

    def get_signature(self, name:FnName) -> tuple[bool, FnSignature]:
        for fn in self.fns:
            if name.matches(fn.name):
                return True, fn
        return False, DUMMY_FN_SIGNATURE

    def register(self, fn:FnSignature) -> None:
        found, _sig = self.get_signature(fn.name)
        assert not found
        self.fns.append(fn)

######
###### SPECIAL: string check
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
    
    assert False

def is_num(obj:str|VarName) -> bool:
    if isinstance(obj, str):
        val_str = obj
    elif isinstance(obj, VarName):
        val_str = obj.to_str()
    else:
        assert False, f'unhandled type {type(obj)}'

    try:
        float(val_str)
    except ValueError:
        return False
    else:
        return True
