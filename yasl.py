#! /usr/bin/env python3

import subprocess
import shutil
import os

HERE = os.path.dirname(os.path.realpath(__file__))
FOLDER_TMP = os.path.join(HERE, 'tmp')
FILE_EXECUTABLE = os.path.join(FOLDER_TMP, 'executable')

def term(args:list[str]) -> None:
    subprocess.run(args, check=True)

os.makedirs(FOLDER_TMP, exist_ok=True)

inp = os.path.join(HERE, 'test.yasl')
out = os.path.join(FOLDER_TMP, 'test.c')
shutil.copyfile(inp, out)

term(['gcc', '-Werror', '-Wextra', '-Wall', '-pedantic', '-Wfatal-errors', '-Wshadow', '-fwrapv', '-o', FILE_EXECUTABLE, out])

term([FILE_EXECUTABLE])
