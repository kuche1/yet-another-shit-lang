
from typing import NoReturn
from typing import Self

from parser_types import *

class FnSignature:

    def __init__(self, name:FnName, can_ret_err:bool, return_type:Type, args:CCode|tuple[tuple[VarName,Type], ...]) -> None:
        self.name = name
        self.can_ret_err = can_ret_err
        self.return_type = return_type
        self.args = args

    def __repr__(self) -> str:
        err_type = FTS_ERR if self.can_ret_err else FTS_NO_ERR

        if isinstance(self.args, CCode):
            args = f'({self.args.to_str()})'
        else:
            args = ''
            for name, typ in self.args:
                args += f'{name}:{typ}, '
            if args.endswith(', '):
                args = args[:-2]
            args = f'[{args}]'

        return f'`fn {self.name.to_str()}{err_type}{self.return_type.to_str()} {args}`'

    def __eq__(self, other:object) -> NoReturn:
        assert False, f'trying to call __eq__ on FnSignature'
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
                return False, f'arguments: {self.args} != {other.args}' # TODO!!! make this pretty and make a fnc for turning args like that into str
        
        return True, ''

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

# only export what is specified here (also applies to `from X import *`)
__all__ = [
    'FnSignature',
    'FnSignatures',
]
