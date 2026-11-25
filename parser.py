import re
from tokens import Token, TipoToken


class ErrorSintactico:
    def __init__(self, mensaje: str, linea: int = None, columna: int = None):
        self.mensaje = mensaje
        self.linea = linea
        self.columna = columna

    def __str__(self):
        if self.linea:
            return f"[Línea {self.linea}:Col {self.columna}] {self.mensaje}"
        return self.mensaje


ESTILOS_OVALO = {
    "root":      'fillcolor="#312e81", color="#a5b4fc", fontcolor="#ffffff", penwidth=2.2',
    "structure": 'fillcolor="#1e293b", color="#94a3b8", fontcolor="#f1f5f9", penwidth=1.6',
    "keyword":   'fillcolor="#1e1b4b", color="#818cf8", fontcolor="#e0e7ff", penwidth=1.8',
    "operator":  'fillcolor="#451a03", color="#fbbf24", fontcolor="#fef3c7", penwidth=1.8',
    "variable":  'fillcolor="#082f49", color="#38bdf8", fontcolor="#e0f2fe", penwidth=1.8',
    "literal":   'fillcolor="#064e3b", color="#34d399", fontcolor="#d1fae5", penwidth=1.8',
    "delimiter": 'fillcolor="#0f172a", color="#64748b", fontcolor="#cbd5e1", penwidth=1.4',
}


class Parser:
    def __init__(self, lenguaje: str, tokens: list[Token]):
        self.lenguaje = lenguaje
        self.tokens = tokens
        self.errores: list[ErrorSintactico] = []
        self._contador_nodos = 0
        self._lineas_dot: list[str] = []

    def analizar(self) -> tuple[bool, list[ErrorSintactico], str]:
        self.errores.clear()
        self._validar_delimitadores()
        self._validar_reglas_lenguaje()
        dot = self._construir_arbol_dot()
        return len(self.errores) == 0, self.errores, dot

    def _validar_delimitadores(self):
        pila = []
        pares = {')': '(', '}': '{', ']': '['}
        en_comillas = None

        for t in self.tokens:
            if t.valor in ('"', "'"):
                if en_comillas == t.valor:
                    en_comillas = None
                elif en_comillas is None:
                    en_comillas = t.valor
                continue
            if en_comillas is not None:
                continue

            if t.valor in "({[":
                pila.append((t.valor, t.linea, t.columna))
            elif t.valor in ")}]":
                if not pila:
                    self.errores.append(ErrorSintactico(f"Cierre inesperado '{t.valor}'", t.linea, t.columna))
                else:
                    tope, l, c = pila.pop()
                    if tope != pares[t.valor]:
                        self.errores.append(
                            ErrorSintactico(
                                f"Se esperaba cerrar '{tope}' (L{l}:C{c}) pero se encontró '{t.valor}'",
                                t.linea,
                                t.columna,
                            )
                        )

        if en_comillas is not None:
            self.errores.append(ErrorSintactico(f"Cadena sin cerrar con {en_comillas}"))

        for abierto, l, c in pila:
            self.errores.append(ErrorSintactico(f"Delimitador sin cerrar '{abierto}'", l, c))

    def _validar_reglas_lenguaje(self):
        tokens_utiles = [
            t for t in self.tokens
            if t.tipo not in (TipoToken.ESPACIO, TipoToken.SALTO_LINEA, TipoToken.COMENTARIO)
        ]
        if self.lenguaje == "Python":
            for i, t in enumerate(tokens_utiles):
                if t.tipo == TipoToken.PALABRA_RESERVADA and t.valor in (
                    "def", "if", "elif", "else", "for", "while", "class"
                ):
                    tiene_dos_puntos = any(
                        tokens_utiles[j].valor == ":"
                        for j in range(i + 1, len(tokens_utiles))
                        if tokens_utiles[j].linea == t.linea
                    )
                    if not tiene_dos_puntos:
                        self.errores.append(ErrorSintactico(f"Falta ':' en '{t.valor}'", t.linea, t.columna))

    # --- GENERACIÓN DEL ÁRBOL SINTÁCTICO JERÁRQUICO (AST) ---

    def _clasificar_hoja(self, valor: str) -> str:
        if re.match(r'^\d+(\.\d+)?$', valor) or valor.startswith(('"', "'")):
            return "literal"
        if valor in ("True", "False", "None", "true", "false", "null", "undefined"):
            return "keyword"
        return "variable"

    def _nuevo_nodo(self, etiqueta: str, categoria: str = "variable") -> str:
        self._contador_nodos += 1
        nid = f"n{self._contador_nodos}"
        etiqueta_escapada = (
            etiqueta
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "")
        )
        estilo = ESTILOS_OVALO.get(categoria, ESTILOS_OVALO["variable"])
        self._lineas_dot.append(f'  {nid} [label="{etiqueta_escapada}", {estilo}];')
        return nid

    def _conectar(self, padre: str, hijo: str):
        if padre and hijo:
            self._lineas_dot.append(f"  {padre} -> {hijo};")

    def _construir_arbol_dot(self) -> str:
        self._contador_nodos = 0
        self._lineas_dot = [
            "digraph ArbolSintactico {",
            '  bgcolor="transparent";',
            '  pad="0.2";',
            '  rankdir=TB;',
            '  splines=line;',
            '  nodesep=0.55;',
            '  ranksep=0.48;',
            (
                '  node [shape=ellipse, style="filled", penwidth=1.8, '
                'fontname="Consolas", fontsize=14, '
                'margin="0.20,0.08", width=0.8, height=0.42];'
            ),
            '  edge [arrowhead=vee, arrowsize=0.65, color="#64748b", penwidth=1.6];',
        ]

        codigo_limpio = "".join(
            t.valor for t in self.tokens if t.tipo != TipoToken.COMENTARIO
        )
        sentencias = self._extraer_sentencias(codigo_limpio)

        n_raiz = self._nuevo_nodo("Programa", "root")
        for sent in sentencias:
            self._procesar_sentencia(sent, n_raiz)

        self._lineas_dot.append("}")
        return "\n".join(self._lineas_dot)

    def _extraer_sentencias(self, codigo: str) -> list[str]:
        if self.lenguaje == "Python":
            return self._extraer_sentencias_python(codigo)

        sentencias = []
        actual = []
        llaves = 0
        parentesis = 0
        en_comilla = None

        for linea in codigo.splitlines():
            s = linea.strip()
            if not s:
                continue

            if s.startswith("#") and llaves == 0 and not actual:
                sentencias.append(s)
                continue

            for ch in linea + "\n":
                if ch in ('"', "'"):
                    if en_comilla == ch:
                        en_comilla = None
                    elif en_comilla is None:
                        en_comilla = ch

                if en_comilla is None:
                    if ch == "(":
                        parentesis += 1
                    elif ch == ")":
                        parentesis -= 1
                    elif ch == "{":
                        llaves += 1
                    elif ch == "}":
                        llaves -= 1

                actual.append(ch)

                if en_comilla is None and parentesis == 0 and llaves == 0:
                    if ch in (";", "}"):
                        bloque = "".join(actual).strip()
                        if bloque:
                            sentencias.append(bloque)
                        actual = []
                    elif ch == "\n" and "".join(actual).strip():
                        texto_actual = "".join(actual).strip()
                        if not texto_actual.endswith((")", "{", ",")):
                            sentencias.append(texto_actual)
                            actual = []

        resto = "".join(actual).strip()
        if resto:
            sentencias.append(resto)
        return sentencias

    def _extraer_sentencias_python(self, codigo: str) -> list[str]:
        lineas = [l for l in codigo.splitlines() if l.strip()]
        sentencias = []
        i = 0
        while i < len(lineas):
            linea = lineas[i]
            indent_actual = len(linea) - len(linea.lstrip())
            s = linea.strip()

            if s.endswith(":"):
                bloque = [linea[indent_actual:]]
                i += 1
                while i < len(lineas):
                    sig_linea = lineas[i]
                    sig_indent = len(sig_linea) - len(sig_linea.lstrip())
                    sig_s = sig_linea.strip()
                    if sig_indent > indent_actual:
                        bloque.append(sig_linea[indent_actual:])
                        i += 1
                    elif sig_indent == indent_actual and sig_s.startswith(("elif ", "else:")):
                        bloque.append(sig_linea[indent_actual:])
                        i += 1
                    else:
                        break
                sentencias.append("\n".join(bloque))
            else:
                sentencias.append(s)
                i += 1
        return sentencias

    def _procesar_sentencia(self, sent: str, padre: str):
        sent = sent.strip()
        if not sent:
            return

        tiene_pc = sent.endswith(";")
        sin_pc = sent[:-1].strip() if tiene_pc else sent

        # 1. Directiva #define
        m_def = re.match(r'^#\s*define\s+([a-zA-Z_]\w*)\s*(.*)$', sent)
        if m_def:
            nombre, resto = m_def.group(1), m_def.group(2).strip()
            n_def = self._nuevo_nodo(f"#define: {nombre}", "keyword")
            self._conectar(padre, n_def)
            if resto:
                self._procesar_expresion(resto, n_def)
            return

        # 2. Directiva #include
        m_inc = re.match(r'^#\s*include\s*(.+)$', sent)
        if m_inc:
            n_inc = self._nuevo_nodo(f"#include {m_inc.group(1).strip()}", "keyword")
            self._conectar(padre, n_inc)
            return

        # 3. Funciones en C, Java, JS, Rust
        m_func = re.match(
            r'^(?:(?:public|private|protected|static|async|pub)\s+)*'
            r'(void|int|float|double|char|boolean|String|fn|function)\s+'
            r'([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*(?:->\s*[^{]+\s*)?\{(.*)\}$',
            sent,
            flags=re.DOTALL,
        )
        if m_func:
            tipo_ret, nombre_fn, params, cuerpo = m_func.groups()
            n_fn = self._nuevo_nodo(f"Función: {nombre_fn}", "keyword")
            self._conectar(padre, n_fn)

            # Tipo
            n_tipo = self._nuevo_nodo(f"Tipo: {tipo_ret}", "structure")
            self._conectar(n_fn, n_tipo)

            # Parámetros
            n_params = self._nuevo_nodo("Parámetros", "structure")
            self._conectar(n_fn, n_params)
            if params.strip():
                for p in [x.strip().split(":")[0].split()[-1] for x in params.split(",") if x.strip()]:
                    np = self._nuevo_nodo(p, "variable")
                    self._conectar(n_params, np)
            else:
                nv = self._nuevo_nodo("()", "delimiter")
                self._conectar(n_params, nv)

            # Cuerpo
            n_cuerpo = self._nuevo_nodo("Cuerpo", "structure")
            self._conectar(n_fn, n_cuerpo)
            sub_sentencias = self._extraer_sentencias(cuerpo)
            for sub in sub_sentencias:
                self._procesar_sentencia(sub, n_cuerpo)
            return

        # 4. Funciones en Python: def nombre(params):
        m_py_func = re.match(
            r'^def\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*:\s*\n(.*)$',
            sent,
            flags=re.DOTALL,
        )
        if m_py_func:
            nombre_fn, params, cuerpo = m_py_func.groups()
            n_fn = self._nuevo_nodo(f"Función: {nombre_fn}", "keyword")
            self._conectar(padre, n_fn)

            # Parámetros
            n_params = self._nuevo_nodo("Parámetros", "structure")
            self._conectar(n_fn, n_params)
            if params.strip():
                for p in [x.strip().split(":")[0].split("=")[0].strip() for x in params.split(",") if x.strip()]:
                    np = self._nuevo_nodo(p, "variable")
                    self._conectar(n_params, np)
            else:
                nv = self._nuevo_nodo("()", "delimiter")
                self._conectar(n_params, nv)

            # Cuerpo
            n_cuerpo = self._nuevo_nodo("Cuerpo", "structure")
            self._conectar(n_fn, n_cuerpo)
            sub_sentencias = self._extraer_sentencias(cuerpo)
            for sub in sub_sentencias:
                self._procesar_sentencia(sub, n_cuerpo)
            return

        # 5. Condicional if (...) { ... } [else { ... }]
        m_if = re.match(
            r'^if\s*\((.+?)\)\s*\{(.*?)\}(?:\s*else\s*\{(.*)\})?$',
            sent,
            flags=re.DOTALL,
        )
        if m_if:
            cond, cuerpo_if, cuerpo_else = m_if.groups()
            n_if = self._nuevo_nodo("if", "keyword")
            self._conectar(padre, n_if)

            n_cond = self._nuevo_nodo("Condición", "structure")
            self._conectar(n_if, n_cond)
            self._procesar_expresion(cond, n_cond)

            n_then = self._nuevo_nodo("Entonces", "structure")
            self._conectar(n_if, n_then)
            for sub in self._extraer_sentencias(cuerpo_if):
                self._procesar_sentencia(sub, n_then)

            if cuerpo_else is not None:
                n_else = self._nuevo_nodo("Sino", "structure")
                self._conectar(n_if, n_else)
                for sub in self._extraer_sentencias(cuerpo_else):
                    self._procesar_sentencia(sub, n_else)
            return

        # 6. Condicional if en Python: if cond:\n... [else:\n...]
        m_py_if = re.match(
            r'^if\s+(.+?)\s*:\s*\n(.*?)(?:\nelse\s*:\s*\n(.*))?$',
            sent,
            flags=re.DOTALL,
        )
        if m_py_if:
            cond, cuerpo_if, cuerpo_else = m_py_if.groups()
            n_if = self._nuevo_nodo("if", "keyword")
            self._conectar(padre, n_if)

            n_cond = self._nuevo_nodo("Condición", "structure")
            self._conectar(n_if, n_cond)
            self._procesar_expresion(cond, n_cond)

            n_then = self._nuevo_nodo("Entonces", "structure")
            self._conectar(n_if, n_then)
            for sub in self._extraer_sentencias(cuerpo_if):
                self._procesar_sentencia(sub, n_then)

            if cuerpo_else is not None:
                n_else = self._nuevo_nodo("Sino", "structure")
                self._conectar(n_if, n_else)
                for sub in self._extraer_sentencias(cuerpo_else):
                    self._procesar_sentencia(sub, n_else)
            return

        # 7. Ciclo while (...) { ... }
        m_while = re.match(r'^while\s*\((.+?)\)\s*\{(.*)\}$', sent, flags=re.DOTALL)
        if m_while:
            cond, cuerpo = m_while.groups()
            n_while = self._nuevo_nodo("while", "keyword")
            self._conectar(padre, n_while)

            n_cond = self._nuevo_nodo("Condición", "structure")
            self._conectar(n_while, n_cond)
            self._procesar_expresion(cond, n_cond)

            n_cuerpo = self._nuevo_nodo("Cuerpo", "structure")
            self._conectar(n_while, n_cuerpo)
            for sub in self._extraer_sentencias(cuerpo):
                self._procesar_sentencia(sub, n_cuerpo)
            return

        # 8. Ciclo while en Python: while cond:\n...
        m_py_while = re.match(r'^while\s+(.+?)\s*:\s*\n(.*)$', sent, flags=re.DOTALL)
        if m_py_while:
            cond, cuerpo = m_py_while.groups()
            n_while = self._nuevo_nodo("while", "keyword")
            self._conectar(padre, n_while)

            n_cond = self._nuevo_nodo("Condición", "structure")
            self._conectar(n_while, n_cond)
            self._procesar_expresion(cond, n_cond)

            n_cuerpo = self._nuevo_nodo("Cuerpo", "structure")
            self._conectar(n_while, n_cuerpo)
            for sub in self._extraer_sentencias(cuerpo):
                self._procesar_sentencia(sub, n_cuerpo)
            return

        # 9. Ciclo for en Python: for var in iter:\n...
        m_py_for = re.match(r'^for\s+([a-zA-Z_]\w*)\s+in\s+(.+?)\s*:\s*\n(.*)$', sent, flags=re.DOTALL)
        if m_py_for:
            var_iter, iterable, cuerpo = m_py_for.groups()
            n_for = self._nuevo_nodo("for", "keyword")
            self._conectar(padre, n_for)

            n_iter = self._nuevo_nodo(f"Iterador: {var_iter}", "variable")
            self._conectar(n_for, n_iter)

            n_en = self._nuevo_nodo("En", "structure")
            self._conectar(n_for, n_en)
            self._procesar_expresion(iterable, n_en)

            n_cuerpo = self._nuevo_nodo("Cuerpo", "structure")
            self._conectar(n_for, n_cuerpo)
            for sub in self._extraer_sentencias(cuerpo):
                self._procesar_sentencia(sub, n_cuerpo)
            return

        # 10. Bloque { ... }
        if sent.startswith("{") and sent.endswith("}"):
            n_bloque = self._nuevo_nodo("Bloque", "structure")
            self._conectar(padre, n_bloque)
            for sub in self._extraer_sentencias(sent[1:-1]):
                self._procesar_sentencia(sub, n_bloque)
            return

        # 11. Declaración múltiple: int w, x, y;
        m_multi = re.match(
            r'^(int|float|double|char|boolean|String|let|var|const)\s+([a-zA-Z_]\w*(?:\s*,\s*[a-zA-Z_]\w*)+)$',
            sin_pc,
        )
        if m_multi:
            tipo_var, vars_str = m_multi.groups()
            n_decl = self._nuevo_nodo(f"Declaración ({tipo_var})", "keyword")
            self._conectar(padre, n_decl)
            for v in vars_str.split(","):
                nv = self._nuevo_nodo(v.strip(), "variable")
                self._conectar(n_decl, nv)
            return

        # 12. Declaración con asignación: int x = 2; / let mut x = 2;
        m_decl_asig = re.match(
            r'^(int|float|double|char|boolean|String|let\s+mut|let|var|const)\s+([a-zA-Z_]\w*)(?:\s*:\s*[\w<>]+)?\s*=\s*(.+)$',
            sin_pc,
        )
        if m_decl_asig:
            tipo_var, var_nom, expr = m_decl_asig.groups()
            n_decl = self._nuevo_nodo(f"Declaración ({tipo_var})", "keyword")
            self._conectar(padre, n_decl)

            n_igual = self._nuevo_nodo("=", "operator")
            self._conectar(n_decl, n_igual)

            n_var = self._nuevo_nodo(var_nom, "variable")
            self._conectar(n_igual, n_var)
            self._procesar_expresion(expr, n_igual)
            return

        # 13. Declaración simple: int x;
        m_decl_simple = re.match(
            r'^(int|float|double|char|boolean|String|let\s+mut|let|var|const)\s+([a-zA-Z_]\w*)$',
            sin_pc,
        )
        if m_decl_simple:
            tipo_var, var_nom = m_decl_simple.groups()
            n_decl = self._nuevo_nodo(f"Declaración ({tipo_var})", "keyword")
            self._conectar(padre, n_decl)
            n_var = self._nuevo_nodo(var_nom, "variable")
            self._conectar(n_decl, n_var)
            return

        # 14. Asignación directa: x = 2; / w = i + j;
        m_asig = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(.+)$', sin_pc)
        if m_asig and not sin_pc.startswith(("if", "while", "for")):
            var_nom, expr = m_asig.groups()
            n_igual = self._nuevo_nodo("=", "operator")
            self._conectar(padre, n_igual)

            n_var = self._nuevo_nodo(var_nom, "variable")
            self._conectar(n_igual, n_var)
            self._procesar_expresion(expr, n_igual)
            return

        # 15. Incremento / decremento: contador++
        m_inc_dec = re.match(r'^([a-zA-Z_]\w*)\s*(\+\+|--)$', sin_pc)
        if m_inc_dec:
            var_nom, op = m_inc_dec.groups()
            n_op = self._nuevo_nodo(op, "operator")
            self._conectar(padre, n_op)
            n_var = self._nuevo_nodo(var_nom, "variable")
            self._conectar(n_op, n_var)
            return

        # 16. Llamada a función: printf("%d\n", x); / print(x)
        m_call = re.match(r'^([a-zA-Z_][\w.:!]*)\s*\((.*)\)$', sin_pc, flags=re.DOTALL)
        if m_call:
            fn_nom, args_str = m_call.groups()
            cat_fn = "keyword" if fn_nom in ("printf", "scanf", "print", "println!", "System.out.println") else "variable"
            n_fn = self._nuevo_nodo(f"Llamada: {fn_nom}", cat_fn)
            self._conectar(padre, n_fn)

            if args_str.strip():
                n_args = self._nuevo_nodo("Argumentos", "structure")
                self._conectar(n_fn, n_args)
                for arg in self._dividir_argumentos(args_str):
                    self._procesar_expresion(arg.strip(), n_args)
            else:
                n_par = self._nuevo_nodo("()", "delimiter")
                self._conectar(n_fn, n_par)
            return

        # 17. Return
        if sin_pc.startswith("return"):
            expr = sin_pc[6:].strip()
            n_ret = self._nuevo_nodo("return", "keyword")
            self._conectar(padre, n_ret)
            if expr:
                self._procesar_expresion(expr, n_ret)
            return

        # 18. Respaldo general
        n_gen = self._nuevo_nodo(sin_pc, self._clasificar_hoja(sin_pc))
        self._conectar(padre, n_gen)

    def _quitar_parentesis_externos(self, expr: str) -> str:
        expr = expr.strip()
        while expr.startswith("(") and expr.endswith(")"):
            nivel = 0
            envuelve_todo = True
            for i, ch in enumerate(expr):
                if ch == "(":
                    nivel += 1
                elif ch == ")":
                    nivel -= 1
                if nivel == 0 and i < len(expr) - 1:
                    envuelve_todo = False
                    break
            if envuelve_todo:
                expr = expr[1:-1].strip()
            else:
                break
        return expr

    def _procesar_expresion(self, expr: str, padre: str):
        expr = self._quitar_parentesis_externos(expr)
        if not expr:
            return

        grupos_operadores = [
            ("||", "or"),
            ("&&", "and"),
            ("===", "!==", "==", "!="),
            ("<=", ">=", "<", ">"),
            ("+", "-"),
            ("*", "/", "%"),
        ]

        for ops in grupos_operadores:
            nivel = 0
            en_comilla = None
            for i in range(len(expr) - 1, -1, -1):
                ch = expr[i]
                if ch in ('"', "'"):
                    if en_comilla == ch:
                        en_comilla = None
                    elif en_comilla is None:
                        en_comilla = ch
                if en_comilla is not None:
                    continue

                if ch == ")":
                    nivel += 1
                elif ch == "(":
                    nivel -= 1
                elif nivel == 0:
                    for op in ops:
                        if expr[i:i + len(op)] == op:
                            if op.isalpha():
                                antes_ok = i == 0 or not expr[i - 1].isalnum()
                                desp_ok = (i + len(op) == len(expr)) or not expr[i + len(op)].isalnum()
                                if not (antes_ok and desp_ok):
                                    continue

                            izq = expr[:i].strip()
                            der = expr[i + len(op):].strip()
                            if izq and der:
                                n_op = self._nuevo_nodo(op, "operator")
                                self._conectar(padre, n_op)
                                self._procesar_expresion(izq, n_op)
                                self._procesar_expresion(der, n_op)
                                return

        m_call = re.match(r'^([a-zA-Z_][\w.:!]*)\s*\((.*)\)$', expr, flags=re.DOTALL)
        if m_call:
            fn_nom, args_str = m_call.groups()
            n_fn = self._nuevo_nodo(f"Llamada: {fn_nom}", "variable")
            self._conectar(padre, n_fn)
            if args_str.strip():
                n_args = self._nuevo_nodo("Argumentos", "structure")
                self._conectar(n_fn, n_args)
                for arg in self._dividir_argumentos(args_str):
                    self._procesar_expresion(arg.strip(), n_args)
            else:
                n_par = self._nuevo_nodo("()", "delimiter")
                self._conectar(n_fn, n_par)
            return

        n_hoja = self._nuevo_nodo(expr, self._clasificar_hoja(expr))
        self._conectar(padre, n_hoja)

    def _dividir_argumentos(self, args_str: str) -> list[str]:
        args = []
        actual = []
        nivel = 0
        en_comilla = None
        for ch in args_str:
            if ch in ('"', "'"):
                if en_comilla == ch:
                    en_comilla = None
                elif en_comilla is None:
                    en_comilla = ch
            if en_comilla is None:
                if ch == "(":
                    nivel += 1
                elif ch == ")":
                    nivel -= 1
                elif ch == "," and nivel == 0:
                    args.append("".join(actual))
                    actual = []
                    continue
            actual.append(ch)
        if actual:
            args.append("".join(actual))
        return args
