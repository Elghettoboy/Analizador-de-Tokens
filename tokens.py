from enum import Enum

class TipoToken(Enum):
    PALABRA_RESERVADA = "palabra reservada"
    VARIABLE = "variable"
    ENTERO = "entero"
    FLOTANTE = "flotante"
    OPERADOR = "operador"
    CARACTER_ESPECIAL = "caracter especial"
    ESPACIO = "espacio en blanco"
    SALTO_LINEA = "salto de linea"
    COMENTARIO = "comentario"

class Token:
    def __init__(self, tipo: TipoToken, valor: str, linea: int, columna: int):
        self.tipo = tipo
        self.valor = valor
        self.linea = linea
        self.columna = columna

    def formatear(self) -> str:
        if self.valor in ("\n", "\\n"):
            valor_mostrar = "\\n"
        elif self.valor == "\t":
            valor_mostrar = "\\t"
        else:
            valor_mostrar = self.valor
        return f"<'{valor_mostrar}', {self.tipo.value}>"

    def __repr__(self):
        return self.formatear()

PALABRAS_RESERVADAS = {
    "Python": {
        "def", "class", "if", "elif", "else", "for", "while", "return",
        "import", "from", "as", "try", "except", "finally", "with", "pass",
        "lambda", "True", "False", "None", "and", "or", "not", "in", "is", "print"
    },
    "Java": {
        "public", "private", "protected", "class", "interface", "void", "static",
        "final", "int", "double", "float", "boolean", "char", "String", "if",
        "else", "for", "while", "return", "import", "package", "new", "this", "System"
    },
    "JavaScript": {
        "function", "let", "const", "var", "if", "else", "for", "while",
        "return", "import", "export", "default", "async", "await", "class",
        "new", "this", "true", "false", "null", "undefined", "try", "catch", "console"
    },
    "C": {
        "int", "float", "double", "char", "void", "struct", "typedef", "if",
        "else", "for", "while", "do", "return", "include", "define", "switch",
        "case", "break", "continue", "static", "const", "sizeof", "printf", "scanf", "main"
    },
    "Rust": {
        "fn", "let", "mut", "struct", "enum", "impl", "trait", "pub", "use",
        "mod", "if", "else", "match", "for", "while", "loop", "return",
        "true", "false", "self", "Self", "where", "type", "i32", "i64", "u32", "f64", "bool", "println"
    }
}