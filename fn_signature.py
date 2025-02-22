
from ccode import *

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

class FnSignatures:

    def __init__(self) -> None:
        self.fns:list[FnSignature] = []

    def name_found(self, name:str) -> bool:
        for sig in self.fns:
            if name == sig.name:
                return True
        return False
    
    def signature_matches(self, fn:FnSignature) -> tuple[bool, str, FnSignature]:
        for sig in self.fns:
            if fn.name == sig.name:
                matches, fail_reason = fn.matches(sig)
                return matches, fail_reason, sig
        assert False

    def register(self, fn:FnSignature) -> None:
        assert not self.name_found(fn.name)
        self.fns.append(fn)
