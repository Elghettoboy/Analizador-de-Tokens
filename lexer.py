import re
from tokens import Token, TipoToken, PALABRAS_RESERVADAS

class Lexer:
    def __init__(self, lenguaje: str):
        self.lenguaje = lenguaje
        self.palabras_reservadas = PALABRAS_RESERVADAS.get(lenguaje, set())

    def tokenizar(self, codigo: str) -> list[Token]:
        tokens = []
        lineas = codigo.splitlines(keepends=True)

        especificacion_tokens = [
            ("COMENTARIO",        r'//[^\n]*'),
            ("ESCAPE_SALTO",      r'\\n'),
            ("FLOTANTE",          r'\b\d+\.\d+\b'),
            ("ENTERO",            r'\b\d+\b'),
            ("OPERADOR",          r'===|!==|==|!=|<=|>=|=>|->|::|\+\+|--|\&\&|\|\||[+\-*/=><!&|^]'),
            ("IDENTIFICADOR",     r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'),
            ("ESPACIO",           r' '),
            ("TABULACION",        r'\t'),
            ("SALTO_LINEA",       r'\n'),
            ("CARACTER_ESPECIAL", r'.'),
        ]

        if self.lenguaje == "Python":
            especificacion_tokens.insert(0, ("COMENTARIO_PY", r'#[^\n]*'))

        regex_maestra = '|'.join(f'(?P<{nombre}>{patron})' for nombre, patron in especificacion_tokens)

        for num_linea, contenido_linea in enumerate(lineas, start=1):
            for match in re.finditer(regex_maestra, contenido_linea):
                grupo = match.lastgroup
                valor = match.group()
                columna = match.start() + 1

                if grupo == "IDENTIFICADOR":
                    tipo = TipoToken.PALABRA_RESERVADA if valor in self.palabras_reservadas else TipoToken.VARIABLE
                elif grupo == "ENTERO":
                    tipo = TipoToken.ENTERO
                elif grupo == "FLOTANTE":
                    tipo = TipoToken.FLOTANTE
                elif grupo == "OPERADOR":
                    tipo = TipoToken.OPERADOR
                elif grupo in ("ESPACIO", "TABULACION"):
                    tipo = TipoToken.ESPACIO
                elif grupo in ("SALTO_LINEA", "ESCAPE_SALTO"):
                    tipo = TipoToken.SALTO_LINEA
                elif grupo in ("COMENTARIO", "COMENTARIO_PY"):
                    tipo = TipoToken.COMENTARIO
                else:
                    tipo = TipoToken.CARACTER_ESPECIAL

                tokens.append(Token(tipo, valor, num_linea, columna))

        return tokens