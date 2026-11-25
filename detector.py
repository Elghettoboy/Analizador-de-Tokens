import re

def detectar_lenguaje(codigo: str) -> tuple[str, dict[str, int]]:
    puntajes = {
        "Python": 0,
        "Java": 0,
        "JavaScript": 0,
        "C": 0,
        "Rust": 0
    }

    reglas = {
        "Rust": [
            (r'\bfn\s+[a-zA-Z_]\w*\s*\(', 6),
            (r'\blet\s+mut\b', 6),
            (r'\bprintln!\s*\(', 7),
            (r'\b(i8|i16|i32|i64|u8|u16|u32|u64|usize|isize|f32|f64|str)\b', 4),
            (r'->\s*[\w&<>]+', 5),
            (r'\b(impl|trait|match|pub\s+fn|use\s+\w+::)\b', 5),
            (r'::', 3),
        ],
        "Python": [
            (r'\bdef\s+[a-zA-Z_]\w*\s*\(', 6),
            (r'\belif\b', 6),
            (r'\bfrom\s+\w+\s+import\b', 5),
            (r'\bprint\s*\(', 3),
            (r'\b(True|False|None)\b', 4),
            (r':\s*$', 3),
            (r'(?m)^\s*#(?!include\b|define\b|ifdef\b|ifndef\b|endif\b).*', 3),
        ],
        "Java": [
            (r'\bpublic\s+class\b', 7),
            (r'\bpublic\s+static\s+void\s+main\b', 8),
            (r'\bSystem\.out\.print(ln)?\b', 7),
            (r'\b(private|protected)\s+(static\s+)?(final\s+)?[\w<>]+\s+\w+', 4),
            (r'\bString\b', 3),
            (r'\bboolean\b', 3),
            (r'\bimport\s+java\.', 6),
        ],
        "JavaScript": [
            (r'\bfunction\s+[a-zA-Z_$]\w*\s*\(', 6),
            (r'\b(const|let|var)\s+[a-zA-Z_$]\w*\s*=', 4),
            (r'\bconsole\.log\s*\(', 7),
            (r'(===|!==)', 5),
            (r'=>', 4),
            (r'\b(undefined|NaN)\b', 4),
            (r'\b(async|await)\b', 2),
        ],
        "C": [
            (r'#\s*include\s*<[\w.]+>', 8),
            (r'#\s*define\s+\w+', 7),
            (r'\bprintf\s*\(', 6),
            (r'\bscanf\s*\(', 6),
            (r'\b(int|void)\s+main\s*\(', 6),
            (r'\b(malloc|calloc|free|sizeof)\s*\(', 5),
            (r'\bstruct\s+\w+\s*\{', 4),
        ]
    }

    for lenguaje, patrones in reglas.items():
        for patron, peso in patrones:
            coincidencias = re.findall(patron, codigo, flags=re.MULTILINE)
            puntajes[lenguaje] += len(coincidencias) * peso

    if re.search(r';\s*$', codigo, flags=re.MULTILINE):
        for lang in ("C", "Java", "JavaScript", "Rust"):
            puntajes[lang] += 1

    if re.search(r'\b(int|float|double|char|void)\s+[a-zA-Z_]\w*\s*(=|;|\(|,)', codigo):
        puntajes["C"] += 2
        puntajes["Java"] += 1

    if max(puntajes.values()) == 0:
        puntajes["Python"] = 1

    lenguaje_detectado = max(puntajes, key=puntajes.get)
    return lenguaje_detectado, puntajes