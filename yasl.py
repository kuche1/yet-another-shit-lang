#! /usr/bin/env python3

import subprocess
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

# fnc

def term(args:list[str]) -> None:
    subprocess.run(args, check=True)

def argtuple_to_ccallargs(args:tuple[str, ...]) -> str:
    ret = ''

    for arg_name in args:
        c_arg_name = varname_to_cvarname(arg_name)
        ret += f'{c_arg_name}, '

    if ret.endswith(', '):
        ret = ret[:-2]

    return ret

def argtuple_to_cdeclargs(args:tuple[tuple[str, str], ...]) -> str:
    if len(args) == 0:
        return 'void'

    ret = ''
    for arg_name, arg_type in args:
        arg_name = varname_to_cvarname(arg_name)
        ret += f'{arg_type} {arg_name}, '
    if ret.endswith(', '):
        ret = ret[:-2]
    return ret

def varname_to_cvarname(name:str) -> str:
    # TODO! we're using this in more places than we should - in the future this is going to fuck strings over
    # maybe we could omit the `$` to make the code a bit more readable and compliant
    name = name.replace('-', '$M$')
    name = name.replace('+', '$P$')
    name = name.replace('(', '$OB$')
    name = name.replace(')', '$CB$')
    return name

# class

class Src:

    def __init__(self, file:str) -> None:
        self.file = file

        with open(file, 'r') as f:
            self.src = f.read()
        
        self.line_number = 1

        self.declared_functions:list[str] = [] # TODO ideally we would also check the types
        self.called_functions:list[str] = []

    def no_more_code(self) -> bool:
        return len(self.src) == 0
    
    def err(self, err_msg:str) -> None:
        print(f'ERROR: file `{self.file}`: line {self.line_number}: {err_msg}', file=sys.stderr)
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

    def popif_var_name(self, orr:None|str=None) -> None|str:
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

    # pop: var value

    def pop_var_value_orr(self, orr:None|str) -> str:
        value_or_fnccall = self.pop_var_name(orr=orr)
        if value_or_fnccall == orr:
            return value_or_fnccall

        fncargs = self.popif_tuple()
        if fncargs is None:
            # return the value
            return value_or_fnccall
        
        # is a function call
        c_fn_name = varname_to_cvarname(value_or_fnccall)
        c_fn_args = argtuple_to_ccallargs(fncargs)
        return f'{c_fn_name}({c_fn_args})'

    def pop_var_value(self) -> str:
        return self.pop_var_value_orr(None)

    # pop: var metatype

    def pop_var_metatype(self) -> str:
        return self.pop_var_name()

    # pop: tuple

    def popif_tuple(self) -> None|tuple[str, ...]:
        # TODO we're not taking care of string
        # TODO actually, anything with space doesnt work (like `(void * ) a` or `a + b`)

        self.pop_whitespace()

        if self.no_more_code():
            return None

        if self.src[0] != TUPLE_BEGIN:
            return None
    
        self.src = self.src[1:]

        the_tuple = []
        while True:
            item = self.pop_var_value_orr(orr=TUPLE_END)
            if item == TUPLE_END:
                break
            the_tuple.append(item)
        return tuple(the_tuple)

    def pop_tuple(self, err:str) -> tuple[str, ...]:
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

    def pop_fn_dec_args(self) -> str:
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

    def pop_fn_body_element(self) -> str:
        while True:
            statement_begin = self.pop_statement_beginning(orr=FN_BODY_END)

            # fn body end

            if statement_begin == FN_BODY_END:
                return statement_begin
            
            # ret

            if statement_begin == ST_BEG_RET:
                val_to_return = self.pop_var_name()
                val_to_return = varname_to_cvarname(val_to_return)
                return f'return {val_to_return};'
            
            # val or var

            if statement_begin in [ST_BEG_VAL, ST_BEG_VAR]:
                var_name, var_type = self.pop_var_name_and_type()
                var_name = varname_to_cvarname(var_name)
                var_value = self.pop_var_value()
                const_prefix = 'const ' if statement_begin == ST_BEG_VAL else '' # TODO you can't make gcc raise a warning if a variable was declared without const but was not modified, so we need to do something about this in the future
                return f'{const_prefix}{var_type} {var_name} = {var_value};\n'

            # variable increase

            if statement_begin == ST_BEG_INC:
                var_name = self.pop_var_name()
                var_name = varname_to_cvarname(var_name)
                inc_value = self.pop_var_name()
                return f'{var_name} += {inc_value};\n'

            # variable decrease

            if statement_begin == ST_BEG_DEC:
                var_name = self.pop_var_name()
                var_name = varname_to_cvarname(var_name)
                dec_value = self.pop_var_name()
                return f'{var_name} -= {dec_value};\n'
            
            # cast

            if statement_begin == ST_BEG_CAST:
                var = self.pop_var_name()
                self.pop_var_type_sep(var)
                new_c_type = self.pop_c_type()
                cast_from = self.pop_var_value()
                return f'{new_c_type} {var} = ({new_c_type}) {cast_from};\n' # TODO and what if it needs to be a constant ?

            # fn call

            if self.function_in_register(statement_begin):
                self.register_function_call(statement_begin) # TODO! this might becode useless very soon
                c_fn_name = varname_to_cvarname(statement_begin)
                fn_call_args = self.pop_fn_call_args(statement_begin)
                c_fn_args = argtuple_to_ccallargs(fn_call_args)
                return f'{c_fn_name}({c_fn_args});\n'
            
            # invalid

            self.err(f'a valid statement beginning needs to be provided; those inclide {STATEMENT_BEGINNINGS}; this could also be a function call (could not find function `{statement_begin}`)')

    def pop_fn_body(self) -> str:
        self.pop_fn_body_begin()

        data = ''
        while True:
            body_element = self.pop_fn_body_element()
            if body_element == FN_BODY_END:
                break

            data += body_element

        return data

    # pop: macro

    def pop_macro_body(self) -> str:
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
        print(f'{macro=}')

        print(f'before {self.src[:20]=}')
        self.src = self.src[end+1:]
        print(f'after  {self.src[:20]=}')

        assert MACRO_BODY_BEGIN not in macro

        return macro

    # pop: c related

    def pop_c_type(self) -> str:
        data = ''
        while not self.no_more_code():
            ch = self.src[0]
            self.src = self.src[1:]

            if ch in WHITESPACE:
                break
        
            data += ch
                
        assert len(data)

        return data


# main

def main() -> None:

    os.makedirs(FOLDER_TMP, exist_ok=True)

    src = Src(FILE_INPUT)

    with open(FILE_TMP_OUTPUT, 'w') as f_out:

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
                fn_name = varname_to_cvarname(fn_name)

                f_out.write(f'__attribute__((warn_unused_result)) {ret_type} {fn_name}')
                # `-Wunused-result` doesn't do the trick

                # args

                f_out.write('(')

                args = src.pop_fn_def_args()

                f_out.write(argtuple_to_cdeclargs(args))

                f_out.write(')')

                # body

                f_out.write('\n{\n')
                body = src.pop_fn_body()
                f_out.write(body)
                f_out.write('\n}\n')

            elif metatype == MT_FN_DEC:

                fn_name, ret_type = src.pop_fn_name_and_returntype()
                src.register_function_declaration(fn_name)
                fn_name = varname_to_cvarname(fn_name)

                fn_args = src.pop_fn_dec_args()

                # TODO missing __attribute__((warn_unused_result))
                # removed for now until I make a proper error handling system
                f_out.write(f'{ret_type} {fn_name}({fn_args});\n')
                # we could have used `()` but unfortunately this doesnt work for stdlib fncs (line printf)

            else:
                
                src.err(f'unknown metatype `{metatype}`; valid metatypes are {METATYPES}')

    src.end_of_compilation_checks()

    term(['gcc', '-Werror', '-Wextra', '-Wall', '-pedantic', '-Wfatal-errors', '-Wshadow', '-fwrapv', '-o', FILE_EXECUTABLE, FILE_TMP_OUTPUT])

    term([FILE_EXECUTABLE])

main()
