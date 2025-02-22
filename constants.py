
NEWLINE = '\n'
WHITESPACE = [' ', '\t', NEWLINE]

FN_ARG_BEGIN = '['
FN_ARG_END = ']'

CODE_BLOCK_BEGIN = '{'
CODE_BLOCK_END = '}'

VAR_TYPE_SEP = ':'

TUPLE_BEGIN = FN_ARG_BEGIN
TUPLE_END = FN_ARG_END

STRING = "'"

FTS_NO_ERR = VAR_TYPE_SEP
FTS_ERR = '!'
FUNCTION_TYPE_SEPARATORS = [FTS_NO_ERR, FTS_ERR] # needs to be at least of length 1

SEPARATORS = WHITESPACE + [FN_ARG_BEGIN, FN_ARG_END] + [VAR_TYPE_SEP] + [TUPLE_BEGIN, TUPLE_END] + [STRING] + FUNCTION_TYPE_SEPARATORS

ST_BEG_RET = 'ret'
ST_BEG_VAL = 'val'
ST_BEG_VAR = 'var'
ST_BEG_INC = 'inc'
ST_BEG_DEC = 'dec'
ST_BEG_CAST = 'cast'
ST_BEG_IF = 'if'
STATEMENT_BEGINNINGS = [ST_BEG_RET, ST_BEG_VAL, ST_BEG_VAR, ST_BEG_INC, ST_BEG_DEC, ST_BEG_CAST, ST_BEG_IF]

MT_FN_DEF = 'fn'
MT_FN_DEC = 'fn@'
METATYPES = [MT_FN_DEF, MT_FN_DEC]

MACRO_BODY_BEGIN = '('
MACRO_BODY_END = ')'
# right now those CAN be part of a variable name
# I'm intentionally keeping this here, just to see what happens
