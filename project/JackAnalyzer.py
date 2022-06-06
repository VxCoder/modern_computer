import argparse
import logging
from enum import IntEnum
from pathlib import Path
from typing import TextIO, List, Dict, Optional


class TokenType(IntEnum):
    KEYWORD = 1
    SYMBOL = 2
    IDENTIFIER = 3
    INT_CONST = 4
    STRING_CONST = 5


class KeywordType(IntEnum):
    CLASS = 1
    METHOD = 2
    INT = 3
    FUNCTION = 4
    BOOLEAN = 5
    CONSTRUCTOR = 6
    CHAR = 7
    VOID = 8
    VAR = 9
    STATIC = 10
    FIELD = 11
    LET = 12
    DO = 13
    IF = 14
    ELSE = 15
    WHILE = 16
    RETURN = 17
    TRUE = 18
    FALSE = 19
    NULL = 20
    THIS = 21


class SymbolKind(IntEnum):
    SK_STATIC = 1
    SK_FIELD = 2
    SK_ARG = 3
    SK_VAR = 4


class SegmentType(IntEnum):
    ST_CONST = 1
    ST_ARG = 2
    ST_LOCAL = 3
    ST_STATIC = 4
    ST_THIS = 5
    ST_THAT = 6
    ST_POINTER = 7
    ST_TEMP = 8


SegmentType2Str: Dict[SegmentType, str] = {
    SegmentType.ST_CONST: 'constant',
    SegmentType.ST_TEMP: 'temp',
}

OsSupportOpMap = {
    "*": ("Math.multiply", 2),
}


class ArithmeticType(IntEnum):
    AT_ADD = 1
    AT_SUB = 2
    AT_NEG = 3
    AT_EQ = 4
    AT_GT = 5
    AT_LT = 6
    AT_AND = 7
    AT_OR = 8
    AT_NOT = 9


Str2ArithmeticType = {
    "+": ArithmeticType.AT_ADD,
    '-': ArithmeticType.AT_SUB,
    '==': ArithmeticType.AT_EQ,
    '>': ArithmeticType.AT_GT,
    '<': ArithmeticType.AT_LT
}

ArithmeticType2Str = {
    ArithmeticType.AT_ADD: 'add'
}


Str2KeywordType: Dict[str, KeywordType] = {
    "class": KeywordType.CLASS,
    "constructor": KeywordType.CONSTRUCTOR,
    "function": KeywordType.FUNCTION,
    "method": KeywordType.METHOD,
    "field": KeywordType.FIELD,
    "static": KeywordType.STATIC,
    "var": KeywordType.VAR,
    "int": KeywordType.INT,
    "char": KeywordType.CHAR,
    "boolean": KeywordType.BOOLEAN,
    "void": KeywordType.VOID,
    "true": KeywordType.TRUE,
    "false": KeywordType.FALSE,
    "null": KeywordType.NULL,
    "this": KeywordType.THIS,
    "let": KeywordType.LET,
    "do": KeywordType.DO,
    "if": KeywordType.IF,
    "else": KeywordType.ELSE,
    "while": KeywordType.WHILE,
    "return": KeywordType.RETURN
}

KeywordType2Str: Dict[KeywordType, str] = {value: key for key, value in Str2KeywordType.items()}
KeyWords = set(Str2KeywordType.keys())

Symbols = set("{}()[].,;+-*/&|<>=~")
OpSymbols = set("+-*/&|<>=")
UnaryOpSymbols = set('-~')


class Symbol:

    def __init__(self, name: str, type: str, kind: SymbolKind, index: int):
        self.name = name
        self.type = type
        self.kind = kind
        self.index = index


class SymbolTable:
    def __init__(self, parent: Optional["SymbolTable"] = None):
        self.symbol_table: Dict[str, Symbol] = {}
        self.parent = parent
        self.kind_index: Dict[SymbolKind, int] = {
            SymbolKind.SK_STATIC: 0,
            SymbolKind.SK_FIELD: 0,
            SymbolKind.SK_ARG: 0,
            SymbolKind.SK_VAR: 4,
        }

    def start_subroutine(self):
        return SymbolTable(self)

    def define(self, name: str, type: str, kind: SymbolKind):
        self.symbol_table[name] = Symbol(name, type, kind, self.kind_index[kind])
        self.kind_index[kind] += 1

    def var_count(self, kind: SymbolKind):
        return self.kind_index[kind]

    def kind_of(self, name) -> Optional[SymbolKind]:
        symbol = self.symbol_table.get(name, None)
        if not symbol:
            return None
        return symbol.kind

    def type_of(self, name) -> Optional[str]:
        symbol = self.symbol_table.get(name, None)
        if not symbol:
            return None
        return symbol.type

    def index_of(self, name) -> Optional[int]:
        symbol = self.symbol_table.get(name, None)
        if not symbol:
            return None
        return symbol.index


class JackTokenizer:

    def __init__(self, parse_object: TextIO):
        self.parse_object = parse_object
        self.buffer = []
        self.preview_char = None

        self.token = ""
        self._token_type = None
        self._token_value = None

        self._next_token_value = None
        self._next_token_type = None

        self.line_num = 1

        # 先取一个符号
        self.has_more_commands()
        self.gen_token_info()

    def gen_token_info(self):
        self.token = "".join(self.buffer)
        self.buffer = []
        self.gen_token_type_and_value()

    def ignore_comments(self, char):
        if char == '/':   # // 类注释 到行尾
            while self.parse_object.read(1) != '\n':
                pass
            self.line_num += 1
        elif char == '*':  # /* 类注释 到 */
            preview = ''
            while char := self.parse_object.read(1):
                if char == '\n':
                    self.line_num += 1

                if preview == '*' and char == '/':
                    break
                else:
                    preview = char

    def has_more_commands(self) -> True:
        if self.preview_char in Symbols:
            self.buffer.append(self.preview_char)
            self.preview_char = None
            return True

        while char := self.preview_char or self.parse_object.read(1):  # 这样可支持流式输入
            if char == '\n':
                self.line_num += 1

            self.preview_char = None
            if char == '/':
                next_char = self.parse_object.read(1)
                if next_char in "*/":
                    self.ignore_comments(next_char)
                else:
                    self.buffer.append(char)
                    if next_char != " ":
                        self.preview_char = next_char
                    break
            elif char in Symbols:
                # 比较丑陋的实现
                if not self.buffer:
                    self.buffer.append(char)
                else:
                    self.preview_char = char
                break
            elif char == '"':
                self.buffer.append(char)
                while (char := self.parse_object.read(1)) != '"':
                    self.buffer.append(char)
                self.buffer.append(char)
                break
            elif char not in ('\n', '\t', '', ' '):
                self.buffer.append(char)
            else:
                if self.buffer:
                    break
        return len(self.buffer) > 0

    def gen_token_type_and_value(self):
        if self.token in KeyWords:
            self._next_token_type = TokenType.KEYWORD
            self._next_token_value = Str2KeywordType[self.token]
        elif self.token in Symbols:
            self._next_token_type = TokenType.SYMBOL
            self._next_token_value = self.token
        elif self.token.isnumeric():
            self._next_token_type = TokenType.INT_CONST
            self._next_token_value = int(self.token)
        elif self.token.startswith('"'):
            self._next_token_type = TokenType.STRING_CONST
            self._next_token_value = self.token[1:-1]
        else:
            self._next_token_type = TokenType.IDENTIFIER
            self._next_token_value = self.token

    def advance(self):
        self._token_type = self._next_token_type
        self._token_value = self._next_token_value

        # 提前获取下一个token
        self.has_more_commands()
        self.gen_token_info()
        return self.token

    @property
    def next_token_type(self) -> TokenType:
        return self._next_token_type

    @property
    def next_token_value(self):
        return self._next_token_value

    @property
    def token_type(self) -> TokenType:
        return self._token_type

    @property
    def token_value(self):
        return self._token_value

    @property
    def keyword(self) -> KeywordType:
        return self._token_value

    @property
    def symbol(self) -> str:
        return self._token_value

    @property
    def identifier(self) -> str:
        return self._token_value

    @property
    def int_value(self) -> int:
        return self._token_value

    @property
    def string_value(self) -> str:
        return self._token_value


class CompilationEngine:
    def __init__(self, tokenizer: JackTokenizer, file_name):
        self.tokenizer = tokenizer
        self.file_name = file_name
        self.class_name = None
        self.vm_writer: Optional[VMWriter] = None

    def advance_and_check_token(self, token_type: TokenType, token_value=None, token_values=None):
        self.tokenizer.advance()
        if token_type != self.tokenizer.token_type:
            raise Exception(f"expect token_type[{token_type}] get token_type[{self.tokenizer.token_type}]")
        if token_value is not None and self.tokenizer.token_value != token_value:
            raise Exception(f"expect token_value[{token_value}] get token_value[{self.tokenizer.token_value}]")
        if token_values is not None and self.tokenizer.token_value not in token_values:
            raise Exception(f"expect token_values in [{token_values}] get token_value[{self.tokenizer.token_value}]")

    def check_token(self, token_type: TokenType, token_value=None, token_values=None) -> bool:
        if token_type != self.tokenizer.token_type:
            return False
        if token_value is not None and self.tokenizer.token_value != token_value:
            return False
        if token_values is not None and self.tokenizer.token_value not in token_values:
            return False
        return True

    def check_next_token(self, token_type: TokenType, token_value=None, token_values=None) -> bool:
        if token_type != self.tokenizer.next_token_type:
            return False
        if token_value is not None and self.tokenizer.next_token_value != token_value:
            return False
        if token_values is not None and self.tokenizer.next_token_value not in token_values:
            return False
        return True

    def check_next_symbol(self, symbol_value=None, symbol_values=None) -> bool:
        return self.check_next_token(TokenType.SYMBOL, symbol_value, symbol_values)

    def check_symbol(self, symbol_value=None, symbol_values=None) -> bool:
        return self.check_token(TokenType.SYMBOL, symbol_value, symbol_values)

    def compile_symbol(self, symbol_value=None, symbol_values=None):
        self.advance_and_check_token(TokenType.SYMBOL, symbol_value, symbol_values)

    def compile_op(self):
        self.advance_and_check_token(TokenType.SYMBOL, token_values=OpSymbols)

    def compile_identifier(self):
        self.advance_and_check_token(TokenType.IDENTIFIER)

    def compile_var_name(self):
        self.compile_identifier()

    def compile_classname(self):
        self.compile_identifier()
        self.class_name = self.tokenizer.token_value
        self.close_vm_writer()
        self.vm_writer = VMWriter(self.class_name)

    def compile_keyword(self, keyword=None, keywords=None):
        self.advance_and_check_token(TokenType.KEYWORD, keyword, keywords)

    def compile(self):
        try:
            self.compile_class()
        except Exception as error:
            logging.exception(error)
            print(f"**************line_num={self.tokenizer.line_num} {error}")
        finally:
            self.close_vm_writer()

    def close_vm_writer(self):
        if self.vm_writer:
            self.vm_writer.close()
        self.vm_writer = None

    def compile_class(self):
        """
            'class' className '{' classVarDec* subroutineDec* '}'
        """
        self.compile_keyword(KeywordType.CLASS)
        self.compile_classname()
        self.compile_symbol('{')

        # classVarDec*
        while self.check_next_token(TokenType.KEYWORD, token_values={KeywordType.STATIC, KeywordType.FIELD}):
            self.compile_class_var_dec()

        # subroutineDec*
        while self.check_next_token(TokenType.KEYWORD, token_values={KeywordType.CONSTRUCTOR, KeywordType.FUNCTION, KeywordType.METHOD}):
            self.compile_subroutine()

        self.compile_symbol('}')

    def compile_class_var_dec(self):
        """
            ('static'|'filed') type varName (',' varName)* ';'
        """
        # ('static'|'filed')
        self.advance_and_check_token(TokenType.KEYWORD, token_values={KeywordType.STATIC, KeywordType.FIELD})

        self.compile_type()
        self.compile_var_name()

        while self.check_next_symbol(","):
            self.compile_symbol(",")
            self.compile_var_name()

        self.compile_symbol(";")

    def compile_subroutine(self):
        """
            ('constructor' | 'function' | 'method') ('void'|type) subroutineName '(' parameterList ')' subroutineBody
        """
        # ('constructor' | 'function' | 'method')
        self.advance_and_check_token(TokenType.KEYWORD, token_values={KeywordType.CONSTRUCTOR, KeywordType.FUNCTION, KeywordType.METHOD})

        # ('void'|type)
        self.compile_type()

        # subroutineName
        self.compile_identifier()
        subroutine_name = self.tokenizer.token_value
        self.vm_writer.write_function(f"{self.class_name}.{subroutine_name}", 0)

        self.compile_symbol('(')
        self.compile_parameter_list()
        self.compile_symbol(')')

        self.compile_subroutine_body()

    def compile_type(self):
        self.tokenizer.advance()
        if self.check_token(TokenType.KEYWORD, token_values={KeywordType.VOID, KeywordType.INT, KeywordType.CHAR, KeywordType.BOOLEAN}):
            return self.tokenizer.token_value
        elif self.check_token(TokenType.IDENTIFIER):
            return self.tokenizer.token_value

    def compile_parameter_list(self, finish_char=')'):
        """
            (type varName)(',' type varName)*
        """
        if self.check_next_symbol(finish_char):
            return

        self.compile_type()
        self.compile_var_name()

        # ',' type varName)*
        while self.check_next_symbol(','):
            self.compile_symbol(',')
            self.compile_type()
            self.compile_var_name()

    def compile_subroutine_body(self):
        """
            '{‘ varDec* statement '}'
        """
        self.compile_symbol('{')

        # varDec*
        while self.check_next_token(TokenType.KEYWORD, KeywordType.VAR):
            self.compile_var_dec()
        self.compile_statements()
        self.compile_symbol('}')

    def compile_var_dec(self):
        """
            ’var‘ type varName (',' varName)* ';'
        """
        # var
        self.advance_and_check_token(TokenType.KEYWORD, token_value=KeywordType.VAR)

        self.compile_type()
        self.compile_var_name()

        while self.check_next_symbol(","):
            self.compile_symbol(",")
            self.compile_var_name()

        self.compile_symbol(";")

    def compile_statements(self):

        while self.check_next_token(TokenType.KEYWORD, token_values={
            KeywordType.LET, KeywordType.IF, KeywordType.WHILE, KeywordType.DO, KeywordType.RETURN
        }):
            if self.check_next_token(TokenType.KEYWORD, token_value=KeywordType.LET):
                self.compile_let()
            elif self.check_next_token(TokenType.KEYWORD, token_value=KeywordType.DO):
                self.compile_do()
            elif self.check_next_token(TokenType.KEYWORD, token_value=KeywordType.RETURN):
                self.compile_return()
            elif self.check_next_token(TokenType.KEYWORD, token_value=KeywordType.IF):
                self.compile_if()
            elif self.check_next_token(TokenType.KEYWORD, token_value=KeywordType.WHILE):
                self.compile_while()

    def compile_subroutine_call(self):
        # subroutineName
        self.advance_and_check_token(TokenType.IDENTIFIER)
        subroutine_name = self.tokenizer.token_value

        if self.check_next_token(TokenType.SYMBOL, "."):
            self.compile_symbol(".")
            self.advance_and_check_token(TokenType.IDENTIFIER)
            subroutine_name = f"{subroutine_name}.{self.tokenizer.token_value}"

        self.compile_symbol('(')
        expr_num = self.compile_expression_list()
        self.compile_symbol(')')
        self.vm_writer.write_call(subroutine_name, expr_num)

    def compile_do(self):
        """
            'do' subroutineCall ';'

        """
        # do
        self.advance_and_check_token(TokenType.KEYWORD, KeywordType.DO)

        # subroutineCall
        self.compile_subroutine_call()

        self.compile_symbol(";")

    def compile_let(self):
        """
            'let' varName ('[' expression ']')? '=' expression ';'
        """
        self.compile_keyword(KeywordType.LET)

        self.compile_var_name()

        # ('[' expression ']')?
        if self.check_next_symbol("["):
            self.compile_symbol("[")
            self.compile_expression()
            self.compile_symbol("]")

        self.compile_symbol("=")
        self.compile_expression()
        self.compile_symbol(";")

    def compile_while(self):
        self.advance_and_check_token(TokenType.KEYWORD, KeywordType.WHILE)

        self.compile_symbol('(')
        self.compile_expression()
        self.compile_symbol(')')

        self.compile_symbol('{')
        self.compile_statements()
        self.compile_symbol('}')

    def compile_return(self):
        """
            'return' expression? ';'
        """
        self.advance_and_check_token(TokenType.KEYWORD, KeywordType.RETURN)

        if not self.check_next_symbol(";"):
            self.compile_expression()
        else:
            self.vm_writer.write_push(SegmentType.ST_CONST, 0)
        self.vm_writer.write_return()

        self.compile_symbol(";")

    def compile_if(self):
        self.compile_keyword(KeywordType.IF)

        self.compile_symbol('(')
        self.compile_expression()
        self.compile_symbol(')')

        self.compile_symbol('{')
        self.compile_statements()
        self.compile_symbol('}')

        if self.check_next_token(TokenType.KEYWORD, KeywordType.ELSE):
            self.compile_keyword(KeywordType.ELSE)
            self.compile_symbol('{')
            self.compile_statements()
            self.compile_symbol('}')

    def compile_expression(self):
        """
            term (op term)*
        """
        self.compile_term()

        # (op term)*
        while self.check_next_symbol(symbol_values=OpSymbols):
            self.compile_op()
            op_func = self.tokenizer.token_value
            self.compile_term()
            if op_func in OsSupportOpMap:
                self.vm_writer.write_call(*OsSupportOpMap[op_func], is_op_func=True)
            else:
                self.vm_writer.write_arithmetic(Str2ArithmeticType[op_func])

    def compile_term(self):
        self.tokenizer.advance()
        if self.check_token(TokenType.IDENTIFIER):
            if self.check_next_symbol("."):
                self.compile_symbol(".")
                self.compile_identifier()
                self.compile_symbol("(")
                self.compile_expression_list()
                self.compile_symbol(")")
            elif self.check_next_symbol("["):
                self.compile_symbol("[")
                self.compile_expression()
                self.compile_symbol("]")
        elif self.check_token(TokenType.KEYWORD):
            return self.tokenizer.token_value
        elif self.check_token(TokenType.INT_CONST):
            self.vm_writer.write_push(SegmentType.ST_CONST, self.tokenizer.token_value)
        elif self.check_token(TokenType.STRING_CONST):
            return self.tokenizer.token_value
        elif self.check_token(TokenType.SYMBOL, '('):
            self.compile_expression()
            self.compile_symbol(")")
            return self.tokenizer.token_value
        elif self.check_symbol(symbol_values=UnaryOpSymbols):
            self.compile_term()
            return self.tokenizer.token_value

    def compile_expression_list(self, finish_char=')') -> int:
        """
            (expression (',' expression)*)?
        """
        expr_num = 0
        if self.check_next_symbol(finish_char):
            return expr_num

        expr_num += 1
        self.compile_expression()

        # (',' expression)*
        while self.check_next_symbol(","):
            self.compile_symbol(",")
            expr_num += 1
            self.compile_expression()
        return expr_num


class VMWriter:
    def __init__(self, class_name):
        self.vm_file = open(f"{class_name}.vm", "w")

    def write_push(self, segment: SegmentType, index: int):
        segment_str = SegmentType2Str[segment]
        self.vm_file.write(f"push {segment_str} {index}\n")

    def write_pop(self, segment: SegmentType, index: int):
        segment_str = SegmentType2Str[segment]
        self.vm_file.write(f"pop {segment_str} {index}\n")

    def write_arithmetic(self, command: ArithmeticType):
        self.vm_file.write(f"{ArithmeticType2Str[command]}\n")

    def write_label(self, label: str):
        pass

    def write_goto(self, label: str):
        pass

    def write_if(self, label: str):
        pass

    def write_call(self, name: str, n_args: int, is_op_func=False):
        self.vm_file.write(f"call {name} {n_args}\n")
        if not is_op_func:
            self.write_pop(SegmentType.ST_TEMP, 0)

    def write_function(self, name: str, n_args: int):
        self.vm_file.write(f"function {name} {n_args}\n")

    def write_return(self):
        self.vm_file.write("return\n")

    def close(self):
        self.vm_file.close()


class JackCompiler:

    @staticmethod
    def handler_jack_file_or_dir(jack_file_or_dir: str) -> List[Path]:
        jack_path = Path(jack_file_or_dir)
        if jack_path.is_file():
            return [jack_path]
        elif jack_path.is_dir():
            jack_files = list(jack_path.glob("*.jack"))
            return jack_files

    def __init__(self, jack_file_or_dir: str):
        self.jack_files = self.handler_jack_file_or_dir(jack_file_or_dir)

    def compile_jack_file(self, jack_file: Path):
        with open(jack_file) as jack_file_object:
            tokenizer = JackTokenizer(jack_file_object)
            engine = CompilationEngine(tokenizer, jack_file.stem)
            engine.compile()

    def compile(self):
        for jack_file in self.jack_files:
            self.compile_jack_file(jack_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="JackAnalyzer")
    parser.add_argument("jack_file_or_dir", type=str, help="jack file or dir path")
    input_args = parser.parse_args()
    JackCompiler(input_args.jack_file_or_dir).compile()
