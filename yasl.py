#! /usr/bin/env python3

from typing import IO
import subprocess
import shutil
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

VAR_NAME_SEPARATORS = WHITESPACE + [FN_ARG_BEGIN, FN_ARG_END] + [VAR_TYPE_SEP]

def term(args:list[str]) -> None:
    subprocess.run(args, check=True)

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

    data = data.replace('-', '_')

    return src, data

class Var_metatype(enum.Enum):
    fn = 0
    var = 1
    val = 2
def pop_var_metatype(src:str) -> tuple[str, Var_metatype]:
    src, metatype = pop_var_name(src)

    if metatype == 'fn':
        mt = Var_metatype.fn
    elif metatype == 'var':
        mt = Var_metatype.var
    elif metatype == 'val':
        mt = Var_metatype.val
    else:
        raise Exception(f'unknown var metatype `{metatype}`')

    return src, mt

def pop_fn_arg_begin(src:str) -> str:
    src, fn_arg_begin = pop_var_name(src, justreturnif=FN_ARG_BEGIN)
    assert fn_arg_begin == FN_ARG_BEGIN
    return src

def pop_fn_arg_or_end(src:str) -> tuple[str, None|tuple[str,str]]:
    src, name = pop_var_name(src, justreturnif=FN_ARG_END)
    if name == FN_ARG_END:
        return src, None
    
    src, sep = pop_var_name(src, justreturnif=VAR_TYPE_SEP)
    assert sep == VAR_TYPE_SEP
    
    src, typ = pop_var_name(src)

    return src, (name, typ)

def pop_fn_args(src:str) -> tuple[str, tuple[tuple[str,str], ...]]:
    src = pop_fn_arg_begin(src)

    args = []
    while True:
        src, arg = pop_fn_arg_or_end(src)
        if arg == None:
            break
        args.append(arg)

    return src, tuple(args)

def pop_fn_body_begin(src:str) -> str:
    src, fn_body_begin = pop_var_name(src, justreturnif=FN_BODY_BEGIN)
    assert fn_body_begin == FN_BODY_BEGIN
    return src

def pop_fn_body(src:str) -> tuple[str, str]:
    src = pop_fn_body_begin(src)

    # TODO missing implementation

    data = ''
    while True:
        ch = src[0]
        src = src[1:]

        if len(ch) == 0:
            assert False
        if ch == FN_BODY_END:
            break
        data += ch
    return src, data

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

            case Var_metatype.fn:
                print('yeee function')

                # return type

                f_out.write('__attribute__((warn_unused_result)) int ')
                # `-Wunused-result` doesn't do the trick

                # name

                yasl_src, name = pop_var_name(yasl_src)
                f_out.write(name)

                # args

                f_out.write('(')

                yasl_src, args = pop_fn_args(yasl_src)

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

            case Var_metatype.var:
                print('yee var')
                raise NotImplementedError()

            case Var_metatype.val:
                print('yeee val')
                raise NotImplementedError()

            case _:
                assert False

term(['gcc', '-Werror', '-Wextra', '-Wall', '-pedantic', '-Wfatal-errors', '-Wshadow', '-fwrapv', '-o', FILE_EXECUTABLE, FILE_TMP_OUTPUT])

term([FILE_EXECUTABLE])
