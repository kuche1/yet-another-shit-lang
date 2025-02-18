#! /usr/bin/env python3

import subprocess
import shutil
import os

HERE = os.path.dirname(os.path.realpath(__file__))
FOLDER_TMP = os.path.join(HERE, 'tmp')
FILE_INPUT = os.path.join(HERE, 'test.yasl')
FILE_EXECUTABLE = os.path.join(FOLDER_TMP, 'executable')

def term(args:list[str]) -> None:
    subprocess.run(args, check=True)

os.makedirs(FOLDER_TMP, exist_ok=True)

with open(FILE_INPUT, 'r') as f_in:
    file_c = os.path.join(FOLDER_TMP, 'test.c')
    with open(file_c, 'w') as f_out:
        f_out.write(f_in.read())

term(['gcc', '-Werror', '-Wextra', '-Wall', '-pedantic', '-Wfatal-errors', '-Wshadow', '-fwrapv', '-o', FILE_EXECUTABLE, file_c])

term([FILE_EXECUTABLE])
