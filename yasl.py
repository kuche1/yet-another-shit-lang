#! /usr/bin/env python3

# TODO add something like `obj@add` and that would be syntax sugar for `obj_add_$int$(obj, a)` where `int` is infered by the type of `a`
# TODO add some checks for `pop_type` and `pop_ctype` (actually im not sure this one needs any checks)
# TODO add the ability to make vars mutable, and if they are mutable pass them as reference (we would also need to track all variables so that when that variable is used we would know to automatically dereference it)
#       perhaps we could declare them as int&a or something like that
# TODO make the err msgs colorful, for example the different prototype err could higlight the exact reason, in if the reterr missmatches the : and ! could be in red

# TODO fix all the `!` todos and a coupld of the regular ones
# TODO ? write function body inplace instead of returning a billion times
# TODO implement normal + -

# from typing import NewType
from typing import NoReturn
from typing import Literal
from typing import Any
import subprocess
import shutil
import sys
import os

from fn_signature import *
from parser_types import *
from constants import *

HERE = os.path.dirname(os.path.realpath(__file__))
FOLDER_TMP = os.path.join(HERE, 'tmp')
FILE_INPUT = os.path.join(HERE, 'test.yasl')
FILE_TMP_OUTPUT_UGLY = os.path.join(FOLDER_TMP, 'code_ugly.c')
FILE_TMP_OUTPUT = os.path.join(FOLDER_TMP, 'code.c')
FILE_EXECUTABLE = os.path.join(FOLDER_TMP, 'executable')

###
### fncs
###

def term(args:list[str]) -> None:
    subprocess.run(args, check=True)

###
### class src
###

class Src:

    def __init__(self, file_in:str, file_out:str) -> None:
        self.file_in = file_in

        with open(file_in, 'r') as f:
            self.src = f.read()
        
        self.file_out = open(file_out, 'w')
        
        self.line_number = 1

        self.declared_functions:FnSignatures = FnSignatures()
        self.defined_functions:FnSignatures = FnSignatures()

    def __del__(self) -> None:
        self.file_out.close()

    def __enter__(self) -> 'Src':
        return self

    def __exit__(self, exc_type:Any, exc_val:Any, exc_tb:Any) -> None:
        self.file_out.close()

    def no_more_code(self) -> bool:
        return len(self.src) == 0
    
    def write_ccode(self, code:CCode) -> None:
        self.file_out.write(code.val)
    
    def warn(self, warn_msg:str) -> None:
        print(f'WARNING: file `{self.file_in}`: line {self.line_number}: {warn_msg}', file=sys.stderr)

    def err(self, err_msg:str) -> NoReturn:
        print(f'ERROR: file `{self.file_in}`: line {self.line_number}: {err_msg}', file=sys.stderr)
        sys.exit(1)
    
    def register_function_declaration(self, fn:FnSignature) -> None:
        found, sig = self.declared_functions.get_signature(fn.name)
        if found:
            match, fail_reason = fn.matches(sig)
            if match:
                self.warn(f'function declaration of {fn} already registered')
            else:
                self.err(f'function already declared as different type: {fail_reason}: old declaration {sig}, new declaration {fn}')
        else:
            self.declared_functions.register(fn)

    def register_function_definition(self, fn:FnSignature) -> None:
        found, sig = self.declared_functions.get_signature(fn.name)
        if found:
            match, fail_reason = fn.matches(sig)
            if not match:
                self.err(f'function declaration and definition missmatch: {fail_reason}: function declaration is {sig}, function definition is {fn}')
        else:
            self.declared_functions.register(fn)

        found, sig = self.defined_functions.get_signature(fn.name)
        if found:
            self.err(f'function {fn} already defined')
        else:
            self.defined_functions.register(fn)
    
    def function_name_in_register(self, fn:FnName) -> bool:
        found, _sig = self.declared_functions.get_signature(fn)
        return found

    # pop: whitespace

    def pop_whitespace(self) -> None:

        while True:
            if len(self.src) == 0:
                break

            ch = self.src[0]

            if ch in WHITESPACE:
                self.src = self.src[1:]
                self.line_number += ch.count(NEWLINE)
                continue

            if ch == '/':
                if len(self.src) >= 2:
                    if self.src[1] == '/':
                        next_newline = self.src.find(NEWLINE)
                        if next_newline == -1:
                            next_newline = len(self.src)
                        else:
                            self.line_number += 1
                        self.src = self.src[next_newline+1:]
                        continue

            break

    # pop: type separator

    def pop_var_type_sep(self, var_name:VarName) -> None:
        sep = self.pop_var_name_orr(orr=VAR_TYPE_SEP)
        self.unpop_var_name(sep)
        if sep is not True:
            self.err(f'variable `{var_name.to_str()}`: expected a type seperator `{VAR_TYPE_SEP}`, instead got `{sep}`')
    
    def pop_fn_type_sep(self, name:FnName) -> bool:

        for fts in FUNCTION_TYPE_SEPARATORS:

            sep = self.popif_var_name(orr=fts)
            self.unpop_var_name(sep)

            if sep is True:
                if fts == FTS_NO_ERR:
                    return False
                if fts == FTS_ERR:
                    return True
                assert False

        if sep is None:
            info = '<end of file>'
        else:
            assert sep is not True # make mypy happy
            info = sep.to_str()

        self.err(f'function {name.to_str()}: expected one of the function type seperators {FUNCTION_TYPE_SEPARATORS}, instead got `{info}`')

    # pop: type

    def pop_type(self) -> Type:
        ret = self.popif_var_name(orr=None)
        if ret is None:
            self.err('a type needs to be specified')
        assert ret is not True
        return ret.to_Type()

    def pop_c_type(self, name:VarName) -> CCode:
        data:CCode = CCode('')

        while not self.no_more_code():
            ch = self.src[0]
            self.src = self.src[1:]

            if ch in WHITESPACE:
                break
        
            data += CCode(ch)
                
        if data.empty():
            self.err(f'a C type needs to be specified for `{name.to_str()}`')

        return data

    # pop: var name

    def popif_var_name(self, orr:None|str) -> None|Literal[True]|VarName:
        self.pop_whitespace()

        data = ''

        while not self.no_more_code():
            ch = self.src[0]
            self.src = self.src[1:]

            if data + ch == orr:
                return True

            if ch in SEPARATORS:
                self.src = ch + self.src
                break

            data += ch

        if len(data) == 0:
            return None

        return VarName(data)

    def pop_var_name_orr(self, *, orr:None|str) -> Literal[True]|VarName:
        name = self.popif_var_name(orr=orr)
        
        if name is None:
            msg = 'expected valid variable name'
            if orr is not None:
                msg += f' or `{orr}`'
            self.err(msg)
        
        if name is True:
            return True

        return name

    # TODO this name is missleading, it's not really just "variable name", see where its used
    def pop_var_name(self) -> VarName:
        name = self.pop_var_name_orr(orr=None)
        assert name is not True
        return name
    
    # the input of this needs to be the same as the output of `pop_var_name`
    def unpop_var_name(self, name:None|Literal[True]|VarName) -> None:
        if not isinstance(name, VarName):
            return
        self.src = name.to_str() + ' ' + self.src

    # pop: var name and type

    def pop_var_name_and_type_orr(self, *, orr:None|str=None) -> Literal[True]|tuple[VarName, Type]:
        name = self.pop_var_name_orr(orr=orr)
        if name is True:
            return True

        self.pop_var_type_sep(name)

        typ = self.pop_type()

        return name, typ

    def pop_var_name_and_type(self) -> tuple[VarName, Type]:
        nametype_orr = self.pop_var_name_and_type_orr()
        assert nametype_orr is not True
        return nametype_orr

    # pop: var metatype

    def pop_var_metatype(self) -> VarName:
        ret = self.pop_var_name()
        return ret

    # pop: value

    def pop_value_orr(self, *, orr:None|str) -> Literal[True]|CCode:
        # TODO not taking care of `"`
        # TODO not taking care of \X

        self.pop_whitespace()

        in_string = False

        value = ''

        while not self.no_more_code():
            ch = self.src[0]
            self.src = self.src[1:]

            if value + ch == orr:
                return True

            if in_string:
                value += ch
                if ch == STRING:
                    in_string = False
                    break
                continue

            # not in string

            if ch == STRING:
                in_string = True
                assert len(value) == 0
                value += ch
                continue

            if ch in SEPARATORS:
                self.src = ch + self.src
                break

            value += ch

        assert not in_string # should be unreachable

        # `value` could be a value in itself or a function call

        # TODO!! we should also be checking if such a function exists
        # TODO!! we should be checking if the function can return an error, and if it can we should raise a compiletime error that the value was used before it was checked
        fncargs = self.popif_tuple()
        if fncargs is None:
            return value_to_ccode(value)

        # is a function call
        c_fn_name = FnName(value).to_ccode() # TODO if we are to implement anonymous functions this needs to change
        c_fn_args = ctuple_to_ccallargs(fncargs)
        ret = CCode('')
        ret += c_fn_name
        ret += CC_OB
        ret += c_fn_args
        ret += CC_CB
        return ret

    def pop_value(self) -> CCode:
        ret = self.pop_value_orr(orr=None)
        assert ret is not True # make mypy happy
        return ret

    # pop: tuple

    def popif_tuple(self) -> None|tuple[CCode, ...]:
        # TODO we're not taking care of string
        # TODO actually, anything with space doesnt work (like `(void * ) a` or `a + b`)

        self.pop_whitespace()

        if self.no_more_code():
            return None

        if self.src[0] != TUPLE_BEGIN:
            return None
    
        self.src = self.src[1:]

        the_tuple:list[CCode] = []
        while True:
            item = self.pop_value_orr(orr=TUPLE_END)
            if item is True:
                break
            the_tuple.append(item)
        return tuple(the_tuple)

    def pop_tuple(self, err:str) -> tuple[CCode, ...]:
        data = self.popif_tuple()
        if data is None:
            self.err(f'{err}: expected a tuple beginning `{TUPLE_BEGIN}`')
        return data

    # pop: code block

    def pop_statement_beginning(self, *, orr:None|str=None) -> Literal[True]|VarName:
        return self.pop_var_name_orr(orr=orr)

    # 1st return value is err, 2nd is what we got instead
    def pop_code_block_begin(self) -> tuple[bool,str]:
        fn_body_begin = self.popif_var_name(orr=CODE_BLOCK_BEGIN)
        self.unpop_var_name(fn_body_begin)

        if fn_body_begin is True:
            return False, ''
        
        if fn_body_begin is None:
            return True, '<end of input reached>'

        return True, fn_body_begin.to_str()

    def pop_code_block_element(self) -> None|CCode:
        while True:
            statement_begin = self.pop_statement_beginning(orr=CODE_BLOCK_END)

            # fn body end

            if statement_begin is True:
                return None
            
            # ret

            if statement_begin.matches_str(ST_BEG_RET):
                ret = CCode('return ')
                ret += self.pop_value() # TODO! fucking annotate `pop_var_name` and all those shits with YCodeValue or YCodeVarname or some shit like that
                ret += CC_SEMICOLON_NEWLINE
                return ret
            
            # val/var

            if statement_begin.matches_str(ST_BEG_VAL) or statement_begin.matches_str(ST_BEG_VAR):
                var_name, var_type = self.pop_var_name_and_type()

                c_var_name = var_name.to_ccode()

                c_var_type = var_type.to_ccode()

                c_var_value = self.pop_value()

                const_prefix = CCode('const ') if statement_begin.matches_str(ST_BEG_VAL) else CCode('') # TODO you can't make gcc raise a warning if a variable was declared without const but was not modified, so we need to do something about this in the future

                ret = CCode('')
                ret += const_prefix
                ret += c_var_type
                ret += CC_SPACE
                ret += c_var_name
                ret += CC_ASSIGN
                ret += c_var_value
                ret += CC_SEMICOLON_NEWLINE
                return ret

            # variable increase/decrease

            if statement_begin.matches_str(ST_BEG_INC) or statement_begin.matches_str(ST_BEG_DEC):
                vn = self.pop_var_name()

                c_var_name = vn.to_ccode()
                c_value = self.pop_value()
                c_change = CCode('+=') if statement_begin.matches_str(ST_BEG_INC) else CCode('-=')

                ret = CCode('')
                ret += c_var_name
                ret += c_change
                ret += c_value
                ret += CC_SEMICOLON_NEWLINE
                return ret
            
            # cast

            if statement_begin.matches_str(ST_BEG_CAST):
                var = self.pop_var_name()
                c_var = var.to_ccode()

                self.pop_var_type_sep(var)

                new_c_type = self.pop_c_type(var)

                cast_from = self.pop_value()

                ret = CCode('')
                ret += new_c_type # TODO and what if it needs to be a constant ?
                ret += c_var
                ret += CC_ASSIGN
                ret += CC_OB
                ret += new_c_type
                ret += CC_CB
                ret += cast_from
                ret += CC_SEMICOLON_NEWLINE
                return ret
            
            # if

            if statement_begin.matches_str(ST_BEG_IF):
                cond = self.pop_value()

                err, code = self.pop_code_block()
                if err:
                    self.err(f'`{ST_BEG_IF}` statement: could not get code block `{CODE_BLOCK_BEGIN}`, instead got `{code}`')
                assert isinstance(code, CCode) # make mypy happy

                ret = CCode('if(')
                ret += cond
                ret += CC_CB
                ret += CC_CBO
                ret += code
                ret += CC_CBC
                ret += CC_NEWLINE
                return ret

            # fn call

            fn_name = statement_begin.to_FnName()

            if self.function_name_in_register(fn_name):
                # TODO!!! then check the full fnc signature
                # TODO!!! put an assert if the fnc can return an error, maybe take advantage of the c syntax `(val1ignored, val2ignored, val3actualvalue)`
                # TODO!!! also, make this CCode fnc call code into its own function so that we can use it in that other place (the value popper or the tuple popper or whatever)

                c_fn_name = fn_name.to_ccode()

                fn_call_args_ctuple = self.pop_fn_call_args(fn_name)
                c_fn_args = ctuple_to_ccallargs(fn_call_args_ctuple)

                ret = CCode('')
                ret += c_fn_name
                ret += CC_OB
                ret += c_fn_args
                ret += CC_CB
                ret += CC_SEMICOLON_NEWLINE
                return ret
            
            # invalid

            self.err(f'a valid statement beginning needs to be provided; those inclide {STATEMENT_BEGINNINGS}; this could also be a function call (could not find function `{statement_begin}`)')

    def pop_code_block(self) -> tuple[Literal[True],str] | tuple[Literal[False],CCode]:
        err, instead_got = self.pop_code_block_begin()
        if err:
            return True, instead_got

        data:CCode = CCode('')
        while True:
            body_element:None|CCode = self.pop_code_block_element()
            if body_element is None:
                break

            data += body_element

        return False, data

    # pop: fn_name can_return_error return_type

    def pop_fn_name(self) -> FnName:
        var_name = self.pop_var_name()
        return var_name.to_FnName()

    def pop_fn_name_and_canreterr_and_rettype(self) -> tuple[FnName, bool, Type]:
        name = self.pop_fn_name()
        canreterr = self.pop_fn_type_sep(name)
        typ = self.pop_type()
        return name, canreterr, typ

    # pop: fn arg

    # returns False if error
    def popif_fn_arg_begin(self) -> bool:
        fn_arg_begin = self.popif_var_name(orr=FN_ARG_BEGIN)
        self.unpop_var_name(fn_arg_begin)

        return fn_arg_begin is True

    def pop_fn_arg_begin(self) -> None:
        assert self.popif_fn_arg_begin() is True

    def pop_fn_def_arg_or_end(self) -> Literal[True] | tuple[VarName,Type]:
        name_and_type = self.pop_var_name_and_type_orr(orr=FN_ARG_END)
        if name_and_type is True:
            return True

        return name_and_type

    def popif_fn_def_args(self) -> None | tuple[tuple[VarName,Type], ...]:
        if not self.popif_fn_arg_begin():
            return None

        args:list[tuple[VarName,Type]] = []
        while True:
            arg = self.pop_fn_def_arg_or_end()
            if arg is True:
                break
            args.append(arg)

        return tuple(args)

    def pop_fn_def_args(self) -> tuple[tuple[VarName,Type], ...]:
        ret = self.popif_fn_def_args()
        assert ret is not None
        return ret

    def pop_fn_dec_args(self) -> CCode:
        args = self.popif_fn_def_args()
        if args is not None:
            return argtuple_to_cdeclargs(args)

        body = self.popif_macro_body()
        if body is not None:
            return body
        
        self.err('could not get function declaration args, tried both definition args and macro args')

    def pop_fn_call_args(self, fn_name:FnName) -> tuple[CCode, ...]:
        return self.pop_tuple(f'could not get function `{fn_name.to_str()}`\'s call args')

    # pop: fn body

    def pop_fn_body(self, fn_name:FnName) -> CCode:
        err, data = self.pop_code_block()
        if err:
            self.err(f'function {fn_name.to_str()}: could not find function body `{CODE_BLOCK_BEGIN}`, instead got `{data}`')
        assert isinstance(data, CCode) # make mypy happy
        return data

    # pop: macro

    def popif_macro_body(self) -> None|CCode:
        self.pop_whitespace()

        if self.no_more_code():
            return None
        
        if self.src[0] != MACRO_BODY_BEGIN:
            return None

        self.src = self.src[1:]

        end = self.src.find(MACRO_BODY_END)
        if end == -1:
            self.err(f'could not find macro end `{MACRO_BODY_END}`')
        
        macro = self.src[:end]
        self.src = self.src[end+1:]

        assert MACRO_BODY_BEGIN not in macro

        return CCode(macro)

###
### main
###

def main() -> None:

    os.makedirs(FOLDER_TMP, exist_ok=True)

    with Src(FILE_INPUT, FILE_TMP_OUTPUT_UGLY) as src:

        # f_out.write('#include <stdio.h>\n')
        # f_out.write('\n')

        while True:

            src.pop_whitespace()

            if src.no_more_code():
                break

            metatype = src.pop_var_metatype()

            if metatype.matches_str(MT_FN_DEF):

                # name and return type

                fn_name, fn_can_ret_err, fn_ret_type = src.pop_fn_name_and_canreterr_and_rettype()

                if fn_can_ret_err:
                    src.write_ccode(CC_WARNUNUSEDRESULT_SPACE) # `-Wunused-result` doesn't do the trick
                src.write_ccode(fn_ret_type.to_ccode())
                src.write_ccode(CC_SPACE)
                src.write_ccode(fn_name.to_ccode())

                # args

                src.write_ccode(CC_OB)
                args = src.pop_fn_def_args()
                src.write_ccode(argtuple_to_cdeclargs(args))
                src.write_ccode(CC_CB)

                # register

                fn_sig = FnSignature(fn_name, fn_can_ret_err, fn_ret_type, args)
                src.register_function_definition(fn_sig)

                # body

                src.write_ccode(CCode('\n{\n'))
                body = src.pop_fn_body(fn_name)
                src.write_ccode(body)
                src.write_ccode(CCode('\n}\n'))

            elif metatype.matches_str(MT_FN_DEC):

                fn_name, fn_can_ret_err, ret_type = src.pop_fn_name_and_canreterr_and_rettype()

                c_fn_name = fn_name.to_ccode()

                c_ret_type = ret_type.to_ccode()

                fn_args = src.pop_fn_dec_args()
                # TODO!! the fact that this always returns CCode makes the error messages much less understandable

                fn_sig = FnSignature(fn_name, fn_can_ret_err, ret_type, fn_args)
                src.register_function_declaration(fn_sig)

                if fn_can_ret_err:
                    src.write_ccode(CC_WARNUNUSEDRESULT_SPACE)
                src.write_ccode(c_ret_type)
                src.write_ccode(CC_SPACE)
                src.write_ccode(c_fn_name)
                src.write_ccode(CC_OB)
                src.write_ccode(fn_args) # we could have used `()` but unfortunately this doesnt work for stdlib fncs (line printf)
                src.write_ccode(CC_CB)
                src.write_ccode(CC_SEMICOLON_NEWLINE)

            else:
                
                src.err(f'unknown metatype `{metatype}`; valid metatypes are {METATYPES}')

    shutil.copyfile(FILE_TMP_OUTPUT_UGLY, FILE_TMP_OUTPUT)
    # term(['clang-format', '-i', FILE_TMP_OUTPUT]) # uses 2 spaces
    term(['astyle', FILE_TMP_OUTPUT]) # ok
    # term(['uncrustify', FILE_TMP_OUTPUT]) # requires a config file

    term(['gcc', '-Werror', '-Wextra', '-Wall', '-pedantic', '-Wfatal-errors', '-Wshadow', '-fwrapv', '-o', FILE_EXECUTABLE, FILE_TMP_OUTPUT])

    term([FILE_EXECUTABLE])

main()
