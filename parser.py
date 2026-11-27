import copy
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

# Niveles de precedencia de menor (arriba en el árbol) a mayor (más profundo)
PRECEDENCIA_OPERADORES = [
    {"=", "+=", "-=", "*=", "/=", "%="},
    {"or", "||"},
    {"and", "&&"},
    {"==", "!=", "<", ">", "<=", ">="},
    {"+", "-"},
    {"*", "/", "%"},
]
TODOS_OPERADORES = set().union(*PRECEDENCIA_OPERADORES)


class Parser:
    def __init__(self, lenguaje: str, tokens: list[Token]):
        self.lenguaje = lenguaje
        self.tokens = tokens
        self.errores: list[ErrorSintactico] = []
        self._contador_nodos = 0
        self._lineas_dot: list[str] = []
        self._niveles_rank: list[list[str]] = []

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

    def _categoria_token(self, tok: Token) -> str:
        nombre_tipo = tok.tipo.name.upper() if hasattr(tok.tipo, "name") else str(tok.tipo).upper()
        if "PALABRA" in nombre_tipo or "RESERVADA" in nombre_tipo or "KEYWORD" in nombre_tipo:
            return "keyword"
        if "NUMERO" in nombre_tipo or "CADENA" in nombre_tipo or "LITERAL" in nombre_tipo or "CHAR" in nombre_tipo:
            return "literal"
        if "OPERADOR" in nombre_tipo or "OP" in nombre_tipo or tok.valor in TODOS_OPERADORES:
            return "operator"
        if "DELIMITADOR" in nombre_tipo or "PUNTUACION" in nombre_tipo or tok.valor in (
            "()", "{}", "[]", "(", ")", "{", "}", "[", "]", ",", ":", ";", "#"
        ):
            return "delimiter"
        if re.match(r'^\d+(\.\d+)?$', tok.valor) or tok.valor.startswith(('"', "'")):
            return "literal"
        if tok.valor in ("True", "False", "None", "true", "false", "null", "undefined", "void", "int", "def"):
            return "keyword"
        return "variable"

    def _escapar(self, texto: str) -> str:
        return (
            texto
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "")
        )

    def _nuevo_nodo_token(self, tok: Token) -> str:
        self._contador_nodos += 1
        nid = f"t{self._contador_nodos}"
        etiqueta = self._escapar(tok.valor)
        nombre_tipo = tok.tipo.name if hasattr(tok.tipo, "name") else str(tok.tipo)
        tooltip = self._escapar(f"Token: '{tok.valor}' | Tipo: {nombre_tipo} | L{tok.linea}:C{tok.columna}")
        cat = self._categoria_token(tok)
        estilo = ESTILOS_OVALO.get(cat, ESTILOS_OVALO["variable"])
        self._lineas_dot.append(
            f'  {nid} [label="{etiqueta}", tooltip="{tooltip}", {estilo}];'
        )
        return nid

    def _nuevo_nodo_fin(self) -> str:
        self._contador_nodos += 1
        nid = f"fin{self._contador_nodos}"
        estilo = ESTILOS_OVALO["root"]
        self._lineas_dot.append(
            f'  {nid} [label="fin", tooltip="Fin del flujo sintáctico", {estilo}];'
        )
        return nid

    def _registrar_nivel(self, ids_nodos: list[str]):
        limpios = [n for n in ids_nodos if n]
        if len(limpios) == 2:
            self._niveles_rank.append(limpios)

    def _conectar(self, origen: str, destino: str):
        if origen and destino:
            self._lineas_dot.append(f"  {origen} -> {destino};")

    def _conectar_todos(self, origenes: list[str], destino: str):
        for o in origenes:
            self._conectar(o, destino)

    def _buscar_cierre(self, toks: list[Token], idx_abre: int, abre: str, cierra: str) -> int:
        nivel = 1
        j = idx_abre + 1
        while j < len(toks) and nivel > 0:
            if toks[j].valor == abre:
                nivel += 1
            elif toks[j].valor == cierra:
                nivel -= 1
            j += 1
        return j - 1 if nivel == 0 else -1

    def _dividir_por_comas(self, toks: list[Token]) -> list[list[Token]]:
        grupos: list[list[Token]] = []
        actual: list[Token] = []
        par = llave = cor = 0
        for t in toks:
            if t.valor == "(":
                par += 1
            elif t.valor == ")":
                par = max(0, par - 1)
            elif t.valor == "{":
                llave += 1
            elif t.valor == "}":
                llave = max(0, llave - 1)
            elif t.valor == "[":
                cor += 1
            elif t.valor == "]":
                cor = max(0, cor - 1)

            if t.valor == "," and par == 0 and llave == 0 and cor == 0:
                if actual:
                    grupos.append(actual)
                    actual = []
            else:
                actual.append(t)
        if actual:
            grupos.append(actual)
        return grupos

    def _construir_lista_binaria(self, items: list[list[Token]]) -> tuple[list[str], list[str]]:
        """Encadena argumentos/parámetros en pares (máx. 2 ramas) formando diamantes."""
        if not items:
            return [], []

        entradas_globales: list[str] = []
        salidas_previas: list[str] = []

        for idx in range(0, len(items), 2):
            par = items[idx : idx + 2]
            ent_par: list[str] = []
            sal_par: list[str] = []

            for sub_toks in par:
                e, s = self._construir_expresion(sub_toks)
                if e:
                    ent_par.append(e[0])
                sal_par.extend(s)

            if len(ent_par) == 2:
                self._registrar_nivel(ent_par)

            if not entradas_globales:
                entradas_globales = ent_par
            else:
                if len(ent_par) == 1:
                    self._conectar_todos(salidas_previas, ent_par[0])
                elif len(ent_par) == 2:
                    # Enlace balanceado para no superar 2 ramas salientes
                    for s_node in salidas_previas:
                        self._conectar(s_node, ent_par[0])
                        self._conectar(s_node, ent_par[1])

            salidas_previas = sal_par

        return entradas_globales, salidas_previas

    def _construir_expresion(self, toks: list[Token]) -> tuple[list[str], list[str]]:
        """Construye un subárbol binario jerárquico por precedencia de operadores."""
        if not toks:
            return [], []

        # Envolver paréntesis externos completos: ( expr ) -> nodo '()' -> expr
        while len(toks) >= 2 and toks[0].valor == "(" and self._buscar_cierre(toks, 0, "(", ")") == len(toks) - 1:
            tok_par = copy.copy(toks[0])
            tok_par.valor = "()"
            nid_par = self._nuevo_nodo_token(tok_par)
            internos = toks[1:-1]
            if not internos:
                return [nid_par], [nid_par]
            grupos = self._dividir_por_comas(internos)
            ent, sal = self._construir_lista_binaria(grupos)
            for e in ent:
                self._conectar(nid_par, e)
            return [nid_par], sal if sal else [nid_par]

        # Buscar operador de menor precedencia fuera de delimitadores (asociatividad izquierda)
        for nivel_ops in PRECEDENCIA_OPERADORES:
            par = llave = cor = 0
            split_idx = -1
            es_asignacion = "=" in nivel_ops

            indices = range(len(toks)) if es_asignacion else range(len(toks) - 1, -1, -1)
            for idx in indices:
                val = toks[idx].valor
                if val == "(":
                    par += 1
                elif val == ")":
                    par -= 1
                elif val == "{":
                    llave += 1
                elif val == "}":
                    llave -= 1
                elif val == "[":
                    cor += 1
                elif val == "]":
                    cor -= 1
                elif par == 0 and llave == 0 and cor == 0 and val in nivel_ops:
                    if idx > 0 and idx < len(toks) - 1:
                        split_idx = idx
                        break

            if split_idx != -1:
                op_id = self._nuevo_nodo_token(toks[split_idx])
                izq_ent, izq_sal = self._construir_expresion(toks[:split_idx])
                der_ent, der_sal = self._construir_expresion(toks[split_idx + 1 :])

                hijos = []
                if izq_ent:
                    self._conectar(op_id, izq_ent[0])
                    hijos.append(izq_ent[0])
                if der_ent:
                    self._conectar(op_id, der_ent[0])
                    hijos.append(der_ent[0])
                self._registrar_nivel(hijos)

                return [op_id], izq_sal + der_sal

        # Llamada a función o acceso encadenado con paréntesis al final: fn(a, b)
        if toks[-1].valor == ")":
            idx_abre = -1
            nivel = 0
            for j in range(len(toks) - 1, -1, -1):
                if toks[j].valor == ")":
                    nivel += 1
                elif toks[j].valor == "(":
                    nivel -= 1
                    if nivel == 0:
                        idx_abre = j
                        break

            if idx_abre > 0:
                prefijo = toks[:idx_abre]
                # Cadena lineal para nombres como System.out.println
                ent_pref: list[str] = []
                prev_p: str | None = None
                for t in prefijo:
                    if t.valor == ".":
                        continue
                    pid = self._nuevo_nodo_token(t)
                    if prev_p is None:
                        ent_pref = [pid]
                    else:
                        self._conectar(prev_p, pid)
                    prev_p = pid

                tok_par = copy.copy(toks[idx_abre])
                tok_par.valor = "()"
                nid_par = self._nuevo_nodo_token(tok_par)
                if prev_p:
                    self._conectar(prev_p, nid_par)

                internos = toks[idx_abre + 1 : -1]
                if internos:
                    grupos = self._dividir_por_comas(internos)
                    arg_ent, arg_sal = self._construir_lista_binaria(grupos)
                    for e in arg_ent:
                        self._conectar(nid_par, e)
                    return ent_pref, arg_sal if arg_sal else [nid_par]

                return ent_pref, [nid_par]

        # Declaración con tipo + asignación o secuencia simple (ej. int x = 2)
        if len(toks) > 1 and toks[0].valor.isidentifier() and any(t.valor in TODOS_OPERADORES for t in toks[1:]):
            tipo_id = self._nuevo_nodo_token(toks[0])
            resto_ent, resto_sal = self._construir_expresion(toks[1:])
            if resto_ent:
                self._conectar(tipo_id, resto_ent[0])
            return [tipo_id], resto_sal if resto_sal else [tipo_id]

        # Fallback secuencial lineal (1 rama por nodo)
        entrada: list[str] = []
        prev: str | None = None
        for t in toks:
            if t.valor == ",":
                continue
            nid = self._nuevo_nodo_token(t)
            if prev is None:
                entrada = [nid]
            else:
                self._conectar(prev, nid)
            prev = nid
        return entrada, [prev] if prev else []

    def _segmentar_sentencias(self, toks: list[Token]) -> list[list[Token]]:
        """Agrupa tokens en sentencias completas respetando bloques {} y sangría Python."""
        sentencias: list[list[Token]] = []
        i = 0
        n = len(toks)

        while i < n:
            t = toks[i]

            # Directivas de preprocesador (#include, #define)
            if t.valor == "#":
                linea = t.linea
                j = i
                while j < n and toks[j].linea == linea:
                    j += 1
                sentencias.append(toks[i:j])
                i = j
                continue

            # Bloques en Python (def, if, elif, else, while, for, class)
            if self.lenguaje == "Python" and t.valor in ("def", "if", "elif", "else", "while", "for", "class"):
                col_bloque = t.columna
                linea_cab = t.linea
                j = i
                # Avanzar hasta ':' de la cabecera
                while j < n and not (toks[j].valor == ":" and toks[j].linea == linea_cab):
                    j += 1
                if j < n and toks[j].valor == ":":
                    j += 1
                    # Incluir todas las líneas con sangría mayor a la cabecera
                    while j < n and (toks[j].linea == linea_cab or toks[j].columna > col_bloque):
                        j += 1
                    sentencias.append(toks[i:j])
                    i = j
                    continue

            # Sentencias con llaves { ... } o terminadas en ';'
            actual: list[Token] = []
            par = llave = 0
            j = i
            while j < n:
                curr = toks[j]
                if curr.valor == "(":
                    par += 1
                elif curr.valor == ")":
                    par = max(0, par - 1)
                elif curr.valor == "{":
                    llave += 1
                elif curr.valor == "}":
                    llave = max(0, llave - 1)

                actual.append(curr)
                j += 1

                if curr.valor == "}" and par == 0 and llave == 0:
                    break
                if curr.valor == ";" and par == 0 and llave == 0:
                    break
                if (
                    self.lenguaje == "Python"
                    and par == 0
                    and llave == 0
                    and j < n
                    and toks[j].linea != curr.linea
                ):
                    break

            if actual:
                sentencias.append(actual)
            i = j

        return sentencias

    def _construir_sentencia(self, toks: list[Token]) -> tuple[list[str], list[str]]:
        if not toks:
            return [], []

        # 1. Directivas #include / #define (flujo controlado de máx. 2 ramas)
        if toks[0].valor == "#":
            if len(toks) >= 2 and toks[1].valor == "include":
                n_inc = self._nuevo_nodo_token(toks[0])
                n_kw = self._nuevo_nodo_token(toks[1])
                self._conectar(n_inc, n_kw)
                prev = n_kw
                for t in toks[2:]:
                    nid = self._nuevo_nodo_token(t)
                    self._conectar(prev, nid)
                    prev = nid
                return [n_inc], [prev]

            if len(toks) >= 3 and toks[1].valor == "define":
                n_num = self._nuevo_nodo_token(toks[0])
                n_def = self._nuevo_nodo_token(toks[1])
                n_mac = self._nuevo_nodo_token(toks[2])
                self._conectar(n_num, n_def)
                self._conectar(n_def, n_mac)
                if len(toks) > 3:
                    val_ent, val_sal = self._construir_expresion(toks[3:])
                    if val_ent:
                        self._conectar(n_mac, val_ent[0])
                    return [n_num], val_sal if val_sal else [n_mac]
                return [n_num], [n_mac]

        # 2. Estructuras Python con ':' (def, if, elif, else, while, for)
        if self.lenguaje == "Python" and toks[0].valor in ("def", "if", "elif", "else", "while", "for"):
            idx_dos_puntos = next((k for k, tk in enumerate(toks) if tk.valor == ":"), -1)
            if idx_dos_puntos != -1:
                cabecera = toks[:idx_dos_puntos]
                tok_dp = toks[idx_dos_puntos]
                cuerpo_toks = toks[idx_dos_puntos + 1 :]

                n_dp = self._nuevo_nodo_token(tok_dp)
                sub_sents = self._segmentar_sentencias(cuerpo_toks)
                cuerpo_sal = self._encadenar_sentencias(sub_sents, inicio=[n_dp])

                kw = cabecera[0].valor
                n_kw = self._nuevo_nodo_token(cabecera[0])

                if kw == "def":
                    # def -> nombre -> () -> parámetros -> ':' -> cuerpo
                    prev_h = n_kw
                    idx_par = next((k for k, tk in enumerate(cabecera) if tk.valor == "("), -1)
                    for t in cabecera[1 : idx_par if idx_par != -1 else len(cabecera)]:
                        nid = self._nuevo_nodo_token(t)
                        self._conectar(prev_h, nid)
                        prev_h = nid

                    if idx_par != -1:
                        idx_cierre = self._buscar_cierre(cabecera, idx_par, "(", ")")
                        tok_par = copy.copy(cabecera[idx_par])
                        tok_par.valor = "()"
                        n_par = self._nuevo_nodo_token(tok_par)
                        self._conectar(prev_h, n_par)

                        params = cabecera[idx_par + 1 : idx_cierre if idx_cierre != -1 else len(cabecera)]
                        if params:
                            grupos = self._dividir_por_comas(params)
                            p_ent, p_sal = self._construir_lista_binaria(grupos)
                            for e in p_ent:
                                self._conectar(n_par, e)
                            self._conectar_todos(p_sal, n_dp)
                        else:
                            self._conectar(n_par, n_dp)
                    else:
                        self._conectar(prev_h, n_dp)

                    return [n_kw], cuerpo_sal

                if kw == "else":
                    self._conectar(n_kw, n_dp)
                    return [n_kw], cuerpo_sal

                # if / elif / while / for -> 2 ramas: condición (izq) y ':' (der) -> convergen al salir
                cond_toks = cabecera[1:]
                cond_ent, cond_sal = self._construir_expresion(cond_toks)
                hijos = []
                if cond_ent:
                    self._conectar(n_kw, cond_ent[0])
                    hijos.append(cond_ent[0])
                self._conectar(n_kw, n_dp)
                hijos.append(n_dp)
                self._registrar_nivel(hijos)

                return [n_kw], cond_sal + cuerpo_sal

        # 3. Bloques con llaves { ... } en C, Java, JS, Rust
        if toks[-1].valor == "}":
            idx_abre_llave = -1
            nivel = 0
            for k in range(len(toks) - 1, -1, -1):
                if toks[k].valor == "}":
                    nivel += 1
                elif toks[k].valor == "{":
                    nivel -= 1
                    if nivel == 0:
                        idx_abre_llave = k
                        break

            if idx_abre_llave != -1:
                cabecera = toks[:idx_abre_llave]
                tok_llave = copy.copy(toks[idx_abre_llave])
                tok_llave.valor = "{}"
                n_llave = self._nuevo_nodo_token(tok_llave)

                internos = toks[idx_abre_llave + 1 : -1]
                sub_sents = self._segmentar_sentencias(internos)
                cuerpo_sal = self._encadenar_sentencias(sub_sents, inicio=[n_llave])

                if not cabecera:
                    return [n_llave], cuerpo_sal

                # Control con llaves: if (...) { ... }, while (...) { ... }
                if cabecera[0].valor in ("if", "while", "for"):
                    n_kw = self._nuevo_nodo_token(cabecera[0])
                    cond_ent, cond_sal = self._construir_expresion(cabecera[1:])
                    hijos = []
                    if cond_ent:
                        self._conectar(n_kw, cond_ent[0])
                        hijos.append(cond_ent[0])
                    self._conectar(n_kw, n_llave)
                    hijos.append(n_llave)
                    self._registrar_nivel(hijos)
                    return [n_kw], cond_sal + cuerpo_sal

                # Función con llaves: int main() { ... } / function sumar(a, b) { ... }
                idx_par = next((k for k, tk in enumerate(cabecera) if tk.valor == "("), -1)
                ent_cab: list[str] = []
                prev_c: str | None = None
                limite_nombre = idx_par if idx_par != -1 else len(cabecera)
                for t in cabecera[:limite_nombre]:
                    nid = self._nuevo_nodo_token(t)
                    if prev_c is None:
                        ent_cab = [nid]
                    else:
                        self._conectar(prev_c, nid)
                    prev_c = nid

                if idx_par != -1:
                    idx_cierre = self._buscar_cierre(cabecera, idx_par, "(", ")")
                    tok_par = copy.copy(cabecera[idx_par])
                    tok_par.valor = "()"
                    n_par = self._nuevo_nodo_token(tok_par)
                    if prev_c:
                        self._conectar(prev_c, n_par)
                    else:
                        ent_cab = [n_par]

                    params = cabecera[idx_par + 1 : idx_cierre if idx_cierre != -1 else len(cabecera)]
                    if params:
                        grupos = self._dividir_por_comas(params)
                        p_ent, p_sal = self._construir_lista_binaria(grupos)
                        for e in p_ent:
                            self._conectar(n_par, e)
                        self._conectar_todos(p_sal, n_llave)
                    else:
                        self._conectar(n_par, n_llave)
                elif prev_c:
                    self._conectar(prev_c, n_llave)

                return ent_cab if ent_cab else [n_llave], cuerpo_sal

        # 4. Sentencia simple (con o sin ';' final que cierra el diamante)
        tiene_pc = toks[-1].valor == ";"
        cuerpo = toks[:-1] if tiene_pc else toks

        if not cuerpo and tiene_pc:
            nid_pc = self._nuevo_nodo_token(toks[-1])
            return [nid_pc], [nid_pc]

        ent, sal = self._construir_expresion(cuerpo)
        if tiene_pc:
            nid_pc = self._nuevo_nodo_token(toks[-1])
            self._conectar_todos(sal, nid_pc)
            return ent, [nid_pc]

        return ent, sal

    def _encadenar_sentencias(self, sentencias: list[list[Token]], inicio: list[str] | None = None) -> list[str]:
        prev_salidas: list[str] = list(inicio) if inicio else []
        for s_toks in sentencias:
            ent, sal = self._construir_sentencia(s_toks)
            if ent:
                if prev_salidas:
                    self._conectar_todos(prev_salidas, ent[0])
                prev_salidas = sal if sal else ent
        return prev_salidas

    def _construir_arbol_dot(self) -> str:
        self._contador_nodos = 0
        self._niveles_rank = []
        self._lineas_dot = [
            "digraph JerarquiaTokens {",
            '  bgcolor="transparent";',
            '  pad="0.3";',
            '  rankdir=TB;',
            '  splines=polyline;',
            '  nodesep=0.60;',
            '  ranksep=0.45;',
            (
                '  node [shape=ellipse, style="filled", penwidth=1.8, '
                'fontname="Consolas", fontsize=13, '
                'margin="0.18,0.07", width=0.58, height=0.36];'
            ),
            '  edge [arrowhead=vee, arrowsize=0.62, color="#38bdf8", penwidth=1.55];',
        ]

        tokens_limpios = [
            t for t in self.tokens
            if t.tipo not in (TipoToken.ESPACIO, TipoToken.SALTO_LINEA, TipoToken.COMENTARIO)
        ]

        sentencias = self._segmentar_sentencias(tokens_limpios)
        salidas_finales = self._encadenar_sentencias(sentencias)

        if salidas_finales:
            fin_id = self._nuevo_nodo_fin()
            self._conectar_todos(salidas_finales, fin_id)

        for grupo_mismo_nivel in self._niveles_rank:
            self._lineas_dot.append(f'  {{ rank=same; {"; ".join(grupo_mismo_nivel)}; }}')

        self._lineas_dot.append("}")
        return "\n".join(self._lineas_dot)