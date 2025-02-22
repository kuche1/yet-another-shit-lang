
from parser_types import *

class FnSignature:

    def __init__(self, name:str, can_ret_err:bool, return_type:str, args:CCode|tuple[tuple[str,str], ...]) -> None:
        self.name = name
        self.can_ret_err = can_ret_err
        self.return_type = return_type
        self.args = args

    def __repr__(self) -> str:
        err_type = FTS_ERR if self.can_ret_err else FTS_NO_ERR

        if isinstance(self.args, CCode):
            args = f'({self.args})'
        else:
            args = ''
            for name, typ in self.args:
                args += f'{name}:{typ}, '
            if args.endswith(', '):
                args = args[:-2]
            args = f'[{args}]'

        return f'`fn {self.name}{err_type}{self.return_type} {args}`'

    def matches(self, other:'FnSignature') -> tuple[bool, str]:
        if self.name != other.name:
            return False, f'name: `{self.name}` != `{other.name}`'
        
        if self.can_ret_err != other.can_ret_err:
            return False, 'difference in ability to return an error'

        if self.return_type != other.return_type:
            return False, f'return type: {self.return_type} != {other.return_type}'

        # if `args` is CCode just give up and pretend they're the same
        if isinstance(self.args, CCode) or (isinstance(other.args, CCode)):
            pass
        else:
            if self.args != other.args:
                return False, f'arguments: {self.args} != {other.args}' # TODO!!! make this pretty and make a fnc for turning args like that into str
        
        return True, ''

DUMMY_FN_SIGNATURE = FnSignature('<DUMMY>', False, 'int', CCode('(void)'))

class FnSignatures:

    def __init__(self) -> None:
        self.fns:list[FnSignature] = []

    def get_signature(self, name:str) -> tuple[bool, FnSignature]: # TODO!!!! make different classes for FnName VarName and shit like that and put them in file `parser_types.py`
        for fn in self.fns:
            if fn.name == name:
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