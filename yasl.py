#! /usr/bin/env python3

# TODO
# make the input code into an object so that line number and character number can be tracked, so that we can put some understandable errors on screen

import subprocess
import enum
import os

HERE = os.path.dirname(os.path.realpath(__file__))
FOLDER_TMP = os.path.join(HERE, 'tmp')
FILE_INPUT = os.path.join(HERE, 'test.yasl')
FILE_TMP_OUTPUT = os.path.join(FOLDER_TMP, 'code.c')
FILE_EXECUTABLE = os.path.join(FOLDER_TMP, 'executable')

WHITESPACE = [' ', '\t', '\n']

FN_ARG_BEGIN = '['
FN_ARG_END = ']'

FN_BODY_BEGIN = '{'
FN_BODY_END = '}'

VAR_TYPE_SEP = ':'

TUPLE_BEGIN = FN_ARG_BEGIN
TUPLE_END = FN_ARG_END

VAR_NAME_SEPARATORS = WHITESPACE + [FN_ARG_BEGIN, FN_ARG_END] + [VAR_TYPE_SEP] + [TUPLE_BEGIN, TUPLE_END]

def term(args:list[str]) -> None:
    subprocess.run(args, check=True)

# pop: whitespace

def pop_whitespace(src:str) -> str:

    while True:
        if len(src) == 0:
            break

        ch = src[0]

        if ch in WHITESPACE:
            src = src[1:]
            continue

        if ch == '/':
            if len(src) >= 2:
                if src[1] == '/':
                    next_newline = src.find('\n')
                    if next_newline == -1:
                        next_newline = len(src)
                    src = src[next_newline+1:]
                    continue

        break

    return src

# pop: var name

def pop_var_name(src:str, justreturnif:None|str=None) -> tuple[str, str]:
    src = pop_whitespace(src)

    data = ''

    while True:
        ch = src[0]
        src = src[1:]

        if data + ch == justreturnif:
            data += ch
            break

        if ch in VAR_NAME_SEPARATORS:
            src = ch + src
            break

        data += ch

    assert len(data)

    # this make the resulting C code less readable
    data = data.replace('-', '$MINUS$')
    data = data.replace('+', '$PLUS$')

    return src, data

# pop: var name and type

def pop_var_name_and_type(src:str, just_return_if_varname_is:None|str=None) -> tuple[str, str|tuple[str, str]]:
    src, name = pop_var_name(src, just_return_if_varname_is)
    if isinstance(just_return_if_varname_is, str):
        if name == just_return_if_varname_is:
            return src, just_return_if_varname_is
    
    src, sep = pop_var_name(src, justreturnif=VAR_TYPE_SEP)
    assert sep == VAR_TYPE_SEP
    
    src, typ = pop_var_name(src)

    return src, (name, typ)

# pop: var metatype

class VarMetatype(enum.Enum):
    FN = 0
    VAR = 1
    VAL = 2

def pop_var_metatype(src:str) -> tuple[str, VarMetatype]:
    src, metatype = pop_var_name(src)

    if metatype == 'fn':
        mt = VarMetatype.FN
    elif metatype == 'var':
        mt = VarMetatype.VAR
    elif metatype == 'val':
        mt = VarMetatype.VAL
    else:
        raise Exception(f'unknown var metatype `{metatype}`')

    return src, mt

# pop: tuple

def pop_tuple(src:str) -> tuple[str, tuple[str, ...]]:
    # TODO we're not taking care of string

    src, tuple_begin = pop_var_name(src, justreturnif=TUPLE_BEGIN)
    assert tuple_begin == TUPLE_BEGIN

    the_tuple = []
    while True:
        src, item = pop_var_name(src, justreturnif=TUPLE_END)
        if item == TUPLE_END:
            break
        the_tuple.append(item)
    return src, tuple(the_tuple)

# pop: fn name

def pop_fn_name_and_returntype(src:str) -> tuple[str, tuple[str, str]]:
    src, name_and_returntype = pop_var_name_and_type(src)
    assert isinstance(name_and_returntype, tuple) # make mypy happy
    return src, name_and_returntype

def pop_fn_name(src:str, orr:None|str=None) -> tuple[str, str]:
    return pop_var_name(src, orr)

# pop: fn arg

def pop_fn_arg_begin(src:str) -> str:
    src, fn_arg_begin = pop_var_name(src, justreturnif=FN_ARG_BEGIN)
    assert fn_arg_begin == FN_ARG_BEGIN
    return src

def pop_fn_def_arg_or_end(src:str) -> tuple[str, None|tuple[str,str]]:
    src, name_and_type = pop_var_name_and_type(src, just_return_if_varname_is=FN_ARG_END)
    if name_and_type == FN_ARG_END:
        return src, None

    assert isinstance(name_and_type, tuple)
    # make mypy happy
    
    return src, name_and_type

def pop_fn_def_args(src:str) -> tuple[str, tuple[tuple[str,str], ...]]:
    src = pop_fn_arg_begin(src)

    args = []
    while True:
        src, arg = pop_fn_def_arg_or_end(src)
        if arg is None:
            break
        args.append(arg)

    return src, tuple(args)

def pop_fn_call_args(src:str) -> tuple[str, tuple[str, ...]]:
    return pop_tuple(src)

# pop: fn body

def pop_fn_body_begin(src:str) -> str:
    src, fn_body_begin = pop_var_name(src, justreturnif=FN_BODY_BEGIN)
    assert fn_body_begin == FN_BODY_BEGIN
    return src

def pop_fn_body(src:str) -> tuple[str, str]:
    src = pop_fn_body_begin(src)

    # TODO missing implementation

    data = ''
    while True:
        src, fn_name = pop_fn_name(src, orr=FN_BODY_END)
        if fn_name == FN_BODY_END:
            break

        src, fn_call_args = pop_fn_call_args(src)

        data += f'{fn_name}({','.join(fn_call_args)});\n'

    return src, data

# main

def main() -> None:

    os.makedirs(FOLDER_TMP, exist_ok=True)

    with open(FILE_INPUT, 'r') as f_in:
        yasl_src = f_in.read()

    with open(FILE_TMP_OUTPUT, 'w') as f_out:

        f_out.write('#include <stdio.h>\n')
        f_out.write('\n')

        while True:

            yasl_src = pop_whitespace(yasl_src)

            if len(yasl_src) == 0:
                break

            yasl_src, metatype = pop_var_metatype(yasl_src)

            match metatype:

                case VarMetatype.FN:
                    print('yeee function')

                    # name and return type

                    yasl_src, (name, ret_type) = pop_fn_name_and_returntype(yasl_src)

                    f_out.write(f'__attribute__((warn_unused_result)) {ret_type} {name}')
                    # `-Wunused-result` doesn't do the trick

                    # args

                    f_out.write('(')

                    yasl_src, args = pop_fn_def_args(yasl_src)

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
                    yasl_src, body = pop_fn_body(yasl_src)
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
