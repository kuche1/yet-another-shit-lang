#! /usr/bin/env python3

import subprocess
import enum
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

# enum

class VarMetatype(enum.Enum):
    FN = 0
    VAR = 1
    VAL = 2

# generic fnc

def term(args:list[str]) -> None:
    subprocess.run(args, check=True)

# class

class Src:

    def __init__(self, file:str) -> None:
        self.file = file

        with open(file, 'r') as f:
            self.src = f.read()
        
        self.line_number = 1

        self.defined_functions:list[str] = []

    def no_more_code(self) -> bool:
        return len(self.src) == 0
    
    def err(self, err_msg:str) -> None:
        print(f'ERROR: file `{self.file}`: line {self.line_number}: {err_msg}', file=sys.stderr)
        sys.exit(1)
    
    def register_function_definition(self, fn_name:str) -> None:
        if fn_name in self.defined_functions:
            self.err(f'function `{fn_name}` already defined')
        self.defined_functions.append(fn_name)

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

        # this make the resulting C code less readable
        data = data.replace('-', '$MINUS$')
        data = data.replace('+', '$PLUS$')

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

    # pop: var name and type

    def pop_var_name_and_type_orr(self, *, orr:None|str=None) -> str|tuple[str, str]:
        name = self.pop_var_name(orr=orr)
        if name == orr:
            return orr
        
        assert self.pop_var_name(orr=VAR_TYPE_SEP) == VAR_TYPE_SEP
        
        typ = self.pop_var_name()

        return name, typ

    def pop_var_name_and_type(self) -> tuple[str, str]:
        nametype_orr = self.pop_var_name_and_type_orr()
        assert not isinstance(nametype_orr, str)
        return nametype_orr

    # pop: var metatype

    def pop_var_metatype(self) -> VarMetatype:
        metatype = self.pop_var_name()

        if metatype == 'fn':
            mt = VarMetatype.FN
        elif metatype == 'var':
            mt = VarMetatype.VAR
        elif metatype == 'val':
            mt = VarMetatype.VAL
        else:
            raise Exception(f'unknown var metatype `{metatype}`')

        return mt

    # pop: tuple

    def pop_tuple(self, err:str) -> tuple[str, ...]:
        # TODO we're not taking care of string
        # TODO actually, anything with space doesnt work (like `(void * ) a` or `a + b`)

        tuple_begin = self.pop_var_name(orr=TUPLE_BEGIN)
        if tuple_begin != TUPLE_BEGIN:
            self.err(f'{err}: expected a tuple beginning `{TUPLE_BEGIN}`')

        the_tuple = []
        while True:
            item = self.pop_var_name(orr=TUPLE_END)
            if item == TUPLE_END:
                break
            the_tuple.append(item)
        return tuple(the_tuple)

    # pop: fn name

    def pop_fn_name(self, *, orr:None|str=None) -> str:
        return self.pop_var_name(orr=orr)

    def pop_fn_name_and_returntype(self) -> tuple[str, str]:
        return self.pop_var_name_and_type()

    # pop: fn arg

    def pop_fn_arg_begin(self) -> None:
        fn_arg_begin = self.pop_var_name(orr=FN_ARG_BEGIN)
        assert fn_arg_begin == FN_ARG_BEGIN

    def pop_fn_def_arg_or_end(self) -> None|tuple[str,str]:
        name_and_type = self.pop_var_name_and_type_orr(orr=FN_ARG_END)
        if name_and_type == FN_ARG_END:
            return None

        assert isinstance(name_and_type, tuple)
        # make mypy happy
        
        return name_and_type

    def pop_fn_def_args(self) -> tuple[tuple[str,str], ...]:
        self.pop_fn_arg_begin()

        args = []
        while True:
            arg = self.pop_fn_def_arg_or_end()
            if arg is None:
                break
            args.append(arg)

        return tuple(args)

    def pop_fn_call_args(self, fn_name:str) -> tuple[str, ...]:
        return self.pop_tuple(f'could not get function `{fn_name}`\'s call args')

    # pop: fn body

    def pop_fn_body_begin(self) -> None:
        fn_body_begin = self.pop_var_name(orr=FN_BODY_BEGIN)
        assert fn_body_begin == FN_BODY_BEGIN

    def pop_fn_body_element(self) -> str:
        while True:
            fn_name = self.pop_fn_name(orr=FN_BODY_END)
            print(f'{fn_name=}')

            # fn body end

            if fn_name == FN_BODY_END:
                return fn_name
            
            # ret

            if fn_name == 'ret':
                val_to_return = self.pop_var_name()
                return f'return {val_to_return};'
            
            # val set

            if fn_name == 'val':
                val_name, val_type = self.pop_var_name_and_type()
                val_value = self.pop_var_name()
                return f'const {val_type} {val_name} = {val_value};\n'
            
            # var set

            if fn_name == 'var':
                # TODO you can't make gcc raise a warning if a variable was declared without const but was not modified, so we need to do something about this in the future
                var_name, var_type = self.pop_var_name_and_type()
                var_value = self.pop_var_name()
                return f'{var_type} {var_name} = {var_value};\n'

            # variable increase

            if fn_name == 'inc':
                var_name = self.pop_var_name()
                inc_value = self.pop_var_name()
                return f'{var_name} += {inc_value};\n'

            # variable decrease

            if fn_name == 'dec':
                var_name = self.pop_var_name()
                dec_value = self.pop_var_name()
                return f'{var_name} -= {dec_value};\n'

            # fn call

            # TODO we should that name with the existing functions, and in that case we should say that there needs to be either a valid function name or one of the operators checked for above in this fnc
            fn_call_args = self.pop_fn_call_args(fn_name)
            return f'{fn_name}({', '.join(fn_call_args)});\n'

    def pop_fn_body(self) -> str:
        self.pop_fn_body_begin()

        # TODO missing implementation

        data = ''
        while True:
            body_element = self.pop_fn_body_element()
            if body_element == FN_BODY_END:
                break

            data += body_element

        return data

# main

def main() -> None:

    os.makedirs(FOLDER_TMP, exist_ok=True)

    src = Src(FILE_INPUT)

    with open(FILE_TMP_OUTPUT, 'w') as f_out:

        f_out.write('#include <stdio.h>\n')
        f_out.write('\n')

        while True:

            src.pop_whitespace()

            if src.no_more_code():
                break

            metatype = src.pop_var_metatype()

            match metatype:

                case VarMetatype.FN:
                    print('yeee function')

                    # name and return type

                    fn_name, ret_type = src.pop_fn_name_and_returntype()

                    f_out.write(f'__attribute__((warn_unused_result)) {ret_type} {fn_name}')
                    # `-Wunused-result` doesn't do the trick

                    src.register_function_definition(fn_name)

                    # args

                    f_out.write('(')

                    args = src.pop_fn_def_args()

                    args_str = ''

                    if len(args) == 0:
                        args_str += 'void'
                    else:
                        for arg_name, arg_type in args:
                            args_str += f'{arg_type} {arg_name}, '

                        if args_str.endswith(', '):
                            args_str = args_str[:-2]

                    f_out.write(args_str)

                    f_out.write(')')

                    # body

                    f_out.write('\n{\n')
                    body = src.pop_fn_body()
                    f_out.write(body)
                    f_out.write('\n}\n')

                case VarMetatype.VAR:
                    print('yee var')
                    raise NotImplementedError()

                case VarMetatype.VAL:
                    print('yeee val')
                    raise NotImplementedError()

                case _:
                    assert False

    term(['gcc', '-Werror', '-Wextra', '-Wall', '-pedantic', '-Wfatal-errors', '-Wshadow', '-fwrapv', '-o', FILE_EXECUTABLE, FILE_TMP_OUTPUT])

    term([FILE_EXECUTABLE])

main()
