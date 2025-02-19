#! /usr/bin/env python3

from typing import Literal
from typing import cast
import subprocess
import typing
import sys
import os

HERE = os.path.dirname(os.path.realpath(__file__))
FOLDER_TMP = os.path.join(HERE, 'tmp')
FILE_INPUT = os.path.join(HERE, 'test.yasl')
FILE_TMP_OUTPUT = os.path.join(FOLDER_TMP, 'code.c')
FILE_EXECUTABLE = os.path.join(FOLDER_TMP, 'executable')

NEWLINE = '\n'
WHITESPACE = [' ', '\t', NEWLINE]

FN_ARG_BEGIN = '['
FN_ARG_END = ']'

FN_BODY_BEGIN = '{'
FN_BODY_END = '}'

VAR_TYPE_SEP = ':'

TUPLE_BEGIN = FN_ARG_BEGIN
TUPLE_END = FN_ARG_END

VAR_NAME_SEPARATORS = WHITESPACE + [FN_ARG_BEGIN, FN_ARG_END] + [VAR_TYPE_SEP] + [TUPLE_BEGIN, TUPLE_END]

ST_BEG_RET = 'ret'
ST_BEG_VAL = 'val'
ST_BEG_VAR = 'var'
ST_BEG_INC = 'inc'
ST_BEG_DEC = 'dec'
ST_BEG_CAST = 'cast'
STATEMENT_BEGINNINGS = [ST_BEG_RET, ST_BEG_VAL, ST_BEG_VAR, ST_BEG_INC, ST_BEG_DEC, ST_BEG_CAST]

MT_FN_DEF = 'fn'
MT_FN_DEC = 'fn@'
METATYPES = [MT_FN_DEF, MT_FN_DEC]

MACRO_BODY_BEGIN = '('
MACRO_BODY_END = ')'
# right now those CAN be part of a variable name
# I'm intentionally keeping this here, just to see what happens

# c code

CCode = typing.NewType("CCode", str)

CC_SPACE = CCode(' ')
CC_SEMICOLON_NEWLINE = CCode(';\n')
CC_ASSIGN = CCode(' = ')
CC_OB = CCode('(')
CC_CB = CCode(')')

# fnc

def term(args:list[str]) -> None:
    subprocess.run(args, check=True)

def ccodecat(*arg:CCode) -> CCode:
    return CCode(''.join(arg))

def argtuple_to_ccallargs(args:tuple[str, ...]) -> CCode:
    ret = ''

    for arg_name in args:
        c_arg_name = varname_to_ccode(arg_name)
        ret += f'{c_arg_name}, '

    if ret.endswith(', '):
        ret = ret[:-2]

    return cast(CCode, ret)

def argtuple_to_cdeclargs(args:tuple[tuple[str, str], ...]) -> CCode:
    ret = ''

    if len(args) == 0:
        ret += 'void'
    else:
        for arg_name, arg_type in args:
            arg_name = varname_to_ccode(arg_name)
            arg_type = type_to_ccode(arg_type)
            ret += f'{arg_type} {arg_name}, '
        if ret.endswith(', '):
            ret = ret[:-2]

    return cast(CCode, ret)

def varname_to_ccode(name:str) -> CCode:
    # TODO! we're using this in more places than we should - in the future this is going to fuck strings over
    # maybe we could omit the `$` to make the code a bit more readable and compliant
    name = name.replace('-', '$M$')
    name = name.replace('+', '$P$')
    name = name.replace('(', '$OB$')
    name = name.replace(')', '$CB$')
    return cast(CCode, name)

def value_to_ccode(value:str) -> CCode:
    # TODO what about strings ?
    return varname_to_ccode(value)

def type_to_ccode(typ:str) -> CCode:
    return cast(CCode, typ)

def ctuple_to_ccallargs(args:tuple[CCode, ...]) -> CCode:
    ret = CCode('')
    for arg in args:
        if len(ret):
            ret = ccodecat(ret, CCode(', '), arg)
        else:
            ret = arg
    return ret

# class

class Src:

    def __init__(self, file_in:str, file_out:str) -> None:
        self.file_in = file_in

        with open(file_in, 'r') as f:
            self.src = f.read()
        
        self.file_out = open(file_out, 'w')
        
        self.line_number = 1

        self.declared_functions:list[str] = [] # TODO ideally we would also check the types
        self.called_functions:list[str] = []

    def no_more_code(self) -> bool:
        return len(self.src) == 0
    
    def write_ccode(self, code:CCode) -> None:
        self.file_out.write(code)
    
    def err(self, err_msg:str) -> None:
        print(f'ERROR: file `{self.file_in}`: line {self.line_number}: {err_msg}', file=sys.stderr)
        sys.exit(1)
    
    def register_function_declaration(self, fn_name:str) -> None:
        if fn_name in self.declared_functions:
            self.err(f'function `{fn_name}` already declared')
        self.declared_functions.append(fn_name)
    
    def register_function_call(self, fn_name:str) -> None:
        if fn_name not in self.called_functions: # or maybe just use a set
            self.called_functions.append(fn_name)
    
    def function_in_register(self, fn_name:str) -> bool:
        return fn_name in self.declared_functions
    
    def end_of_compilation_checks(self) -> None:
        for fn_called in self.called_functions:
            if fn_called not in self.declared_functions:
                self.err(f'function `{fn_called}` called but never defined')
        self.file_out.close()

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

    # pop: syntax characters

    def pop_var_type_sep(self, name:str) -> None:
        if self.pop_var_name(orr=VAR_TYPE_SEP) != VAR_TYPE_SEP:
            self.err(f'expected a variable type seperator `{VAR_TYPE_SEP}` after `{name}`')

    # pop: var name

    def popif_var_name(self, orr:None|str) -> None|str:
        self.pop_whitespace()

        data = ''

        while True:
            if len(self.src) == 0:
                break

            ch = self.src[0]
            self.src = self.src[1:]

            if data + ch == orr:
                data += ch
                break

            if ch in VAR_NAME_SEPARATORS:
                self.src = ch + self.src
                break

            data += ch

        if len(data) == 0:
            return None

        return data

    # TODO this name is missleading, it's not really just "variable name", see where its used
    def pop_var_name(self, *, orr:None|str=None) -> str:
        name = self.popif_var_name(orr=orr)
        if name is None:
            msg = 'expected valid variable name'
            if orr is not None:
                msg += f' or `{orr}`'
            self.err(msg)

        assert isinstance(name, str) # make mypy happy
        return name
    
    def unpop_var_name(self, name:str) -> None:
        self.src = name + ' ' + self.src

    # pop: var name and type

    def pop_var_name_and_type_orr(self, *, orr:None|str=None) -> str|tuple[str, str]:
        name = self.pop_var_name(orr=orr)
        if name == orr:
            return orr

        self.pop_var_type_sep(name)

        typ = self.pop_var_name()

        return name, typ

    def pop_var_name_and_type(self) -> tuple[str, str]:
        nametype_orr = self.pop_var_name_and_type_orr()
        assert not isinstance(nametype_orr, str)
        return nametype_orr

    # pop: var metatype

    def pop_var_metatype(self) -> str:
        return self.pop_var_name()

    # pop: value

    def pop_value_orr(self, *, orr:None|str) -> Literal[True]|CCode:
        value_or_fnccall:str = self.pop_var_name(orr=orr)
        if value_or_fnccall == orr:
            return True

        fncargs = self.popif_tuple()
        if fncargs is None:
            # return the value
            return value_to_ccode(value_or_fnccall)
        
        # is a function call
        c_fn_name = varname_to_ccode(value_or_fnccall)
        c_fn_args = ctuple_to_ccallargs(fncargs)
        ret = ccodecat(c_fn_name, CC_OB, c_fn_args, CC_CB)
        print(f'dbg: pop_value_orr: {ret=}')
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

        assert data is not None # make mypy happy
        return data

    # pop: fn name

    def pop_fn_name(self, *, orr:None|str=None) -> str:
        ret = self.pop_var_name(orr=orr)
        return ret

    def pop_fn_name_and_returntype(self) -> tuple[str, str]:
        return self.pop_var_name_and_type()

    # pop: fn arg

    # returns True if error
    def popif_fn_arg_begin(self) -> bool:
        fn_arg_begin = self.pop_var_name(orr=FN_ARG_BEGIN)
        ret = fn_arg_begin != FN_ARG_BEGIN
        if ret:
            self.unpop_var_name(fn_arg_begin)
        return ret

    def pop_fn_arg_begin(self) -> None:
        assert self.popif_fn_arg_begin() is False

    def pop_fn_def_arg_or_end(self) -> None|tuple[str,str]:
        name_and_type = self.pop_var_name_and_type_orr(orr=FN_ARG_END)
        if name_and_type == FN_ARG_END:
            return None

        assert isinstance(name_and_type, tuple)
        # make mypy happy
        
        return name_and_type

    def popif_fn_def_args(self) -> None|tuple[tuple[str,str], ...]:
        if self.popif_fn_arg_begin():
            return None

        args = []
        while True:
            arg = self.pop_fn_def_arg_or_end()
            if arg is None:
                break
            args.append(arg)

        return tuple(args)

    def pop_fn_def_args(self) -> tuple[tuple[str,str], ...]:
        self.pop_fn_arg_begin()

        args = []
        while True:
            arg = self.pop_fn_def_arg_or_end()
            if arg is None:
                break
            args.append(arg)

        return tuple(args)

    def pop_fn_dec_args(self) -> CCode:
        args = self.popif_fn_def_args()
        if args is not None:
            return argtuple_to_cdeclargs(args)

        return self.pop_macro_body()

    def pop_fn_call_args(self, fn_name:str) -> tuple[str, ...]:
        return self.pop_tuple(f'could not get function `{fn_name}`\'s call args')

    # pop: fn body

    def pop_statement_beginning(self, *, orr:None|str=None) -> str:
        return self.pop_fn_name(orr=orr)

    def pop_fn_body_begin(self) -> None:
        fn_body_begin = self.pop_var_name(orr=FN_BODY_BEGIN)
        assert fn_body_begin == FN_BODY_BEGIN

    def pop_fn_body_element(self) -> None|CCode:
        while True:
            statement_begin = self.pop_statement_beginning(orr=FN_BODY_END)

            # fn body end

            if statement_begin == FN_BODY_END:
                return None
            
            # ret

            if statement_begin == ST_BEG_RET:
                val_to_return = self.pop_var_name()
                val_to_return = varname_to_ccode(val_to_return)
                return CCode(f'return {val_to_return};')
            
            # val/var

            if statement_begin in [ST_BEG_VAL, ST_BEG_VAR]:
                var_name, var_type = self.pop_var_name_and_type()

                var_name = varname_to_ccode(var_name)

                var_type = type_to_ccode(var_type)

                var_value = self.pop_value()

                const_prefix = 'const ' if statement_begin == ST_BEG_VAL else '' # TODO you can't make gcc raise a warning if a variable was declared without const but was not modified, so we need to do something about this in the future
                const_prefix = CCode(const_prefix)

                return ccodecat(
                    const_prefix, var_type, CC_SPACE, var_name,
                    CC_ASSIGN,
                    var_value, CC_SEMICOLON_NEWLINE)

            # variable increase/decrease

            if statement_begin in [ST_BEG_INC, ST_BEG_DEC]:
                var_name = self.pop_var_name()
                var_name = varname_to_ccode(var_name)

                value = self.pop_value()

                change = '+=' if statement_begin == ST_BEG_INC else '-='
                change = CCode(change)

                return ccodecat(
                    var_name,
                    CC_SPACE, change, CC_SPACE,
                    value, CC_SEMICOLON_NEWLINE)
            
            # cast

            if statement_begin == ST_BEG_CAST:
                var = self.pop_var_name()
                var = varname_to_ccode(var)

                self.pop_var_type_sep(var)

                new_c_type = self.pop_c_type()

                cast_from = self.pop_value()

                return ccodecat(
                    new_c_type, CC_SPACE, var, # TODO and what if it needs to be a constant ?
                    CC_ASSIGN,
                    CC_OB, new_c_type, CC_CB, CC_SPACE, cast_from, CC_SEMICOLON_NEWLINE)

            # fn call

            if self.function_in_register(statement_begin):
                self.register_function_call(statement_begin) # TODO! this might becode useless very soon

                c_fn_name = varname_to_ccode(statement_begin)

                fn_call_args = self.pop_fn_call_args(statement_begin)
                c_fn_args = argtuple_to_ccallargs(fn_call_args)

                return ccodecat(c_fn_name, CC_OB, c_fn_args, CC_CB, CC_SEMICOLON_NEWLINE)
            
            # invalid

            self.err(f'a valid statement beginning needs to be provided; those inclide {STATEMENT_BEGINNINGS}; this could also be a function call (could not find function `{statement_begin}`)')

    def pop_fn_body(self) -> CCode:
        self.pop_fn_body_begin()

        data:CCode = CCode('')
        while True:
            body_element_or_end:None|CCode = self.pop_fn_body_element()
            if body_element_or_end is None:
                break

            if body_element_or_end == 'const int fib$OB$2$CB$ = add$M$int$OB$fib$OB$0$CB$, fib$OB$1$CB$$CB$;\n':
                print('~~~ ', end='')
            print(f'dbg: pop_fn_body: {body_element_or_end=}')
            body_element:CCode = body_element_or_end

            data = ccodecat(data, body_element)

        return data

    # pop: macro

    def pop_macro_body(self) -> CCode:
        self.pop_whitespace()

        if self.no_more_code():
            self.err(f'reached end of source code before macro beginning `{MACRO_BODY_BEGIN}` could be found')
        
        if self.src[0] != MACRO_BODY_BEGIN:
            self.err(f'a macro beginning `{MACRO_BODY_BEGIN}` needs to follow, instead got `{self.src[0]}`')

        self.src = self.src[1:]

        end = self.src.find(MACRO_BODY_END)
        if end == -1:
            self.err(f'could not find macro end `{MACRO_BODY_END}`')
        
        macro = self.src[:end]
        self.src = self.src[end+1:]

        assert MACRO_BODY_BEGIN not in macro

        return CCode(macro)

    # pop: c related

    def pop_c_type(self) -> CCode:
        data:CCode = CCode('')

        while not self.no_more_code():
            ch = self.src[0]
            self.src = self.src[1:]

            if ch in WHITESPACE:
                break
        
            data = ccodecat(data, CCode(ch))
                
        assert len(data)

        return data


# main

def main() -> None:

    os.makedirs(FOLDER_TMP, exist_ok=True)

    src = Src(FILE_INPUT, FILE_TMP_OUTPUT)

    # f_out.write('#include <stdio.h>\n')
    # f_out.write('\n')

    while True:

        src.pop_whitespace()

        if src.no_more_code():
            break

        metatype = src.pop_var_metatype()

        if metatype == MT_FN_DEF:

            # name and return type

            fn_name, ret_type = src.pop_fn_name_and_returntype()
            src.register_function_declaration(fn_name)

            src.write_ccode(cast(CCode, '__attribute__((warn_unused_result)) ')) # `-Wunused-result` doesn't do the trick
            src.write_ccode(type_to_ccode(ret_type))
            src.write_ccode(cast(CCode, ' '))
            src.write_ccode(varname_to_ccode(fn_name))

            # args

            src.write_ccode(cast(CCode, '('))
            args = src.pop_fn_def_args()
            src.write_ccode(argtuple_to_cdeclargs(args))
            src.write_ccode(cast(CCode, ')'))

            # body

            src.write_ccode(cast(CCode, '\n{\n'))
            body = src.pop_fn_body()
            src.write_ccode(body)
            src.write_ccode(cast(CCode, '\n}\n'))

        elif metatype == MT_FN_DEC:

            fn_name, ret_type = src.pop_fn_name_and_returntype()
            src.register_function_declaration(fn_name)

            fn_name = varname_to_ccode(fn_name)

            ret_type = type_to_ccode(ret_type)

            fn_args = src.pop_fn_dec_args()

            # TODO missing __attribute__((warn_unused_result))
            # removed for now until I make a proper error handling system
            src.write_ccode(ret_type)
            src.write_ccode(CC_SPACE)
            src.write_ccode(fn_name)
            src.write_ccode(CC_OB)
            src.write_ccode(fn_args) # we could have used `()` but unfortunately this doesnt work for stdlib fncs (line printf)
            src.write_ccode(CC_CB)
            src.write_ccode(CC_SEMICOLON_NEWLINE)

        else:
            
            src.err(f'unknown metatype `{metatype}`; valid metatypes are {METATYPES}')

    src.end_of_compilation_checks()

    term(['gcc', '-Werror', '-Wextra', '-Wall', '-pedantic', '-Wfatal-errors', '-Wshadow', '-fwrapv', '-o', FILE_EXECUTABLE, FILE_TMP_OUTPUT])

    term([FILE_EXECUTABLE])

main()
