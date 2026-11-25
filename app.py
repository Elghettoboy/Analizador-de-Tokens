import sys
import json
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import streamlit as st
import streamlit.components.v1 as components
from detector import detectar_lenguaje
from lexer import Lexer
from parser import Parser

st.set_page_config(
    page_title="Analizador Léxico y Sintáctico",
    page_icon="💻",
    layout="wide"
)

st.markdown("""
<style>
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 1.5rem !important;
        max-width: 96% !important;
    }
</style>
""", unsafe_allow_html=True)


def renderizar_arbol_interactivo(dot_code: str, altura: int = 440):
    dot_json = json.dumps(dot_code).replace("</", "<\\/")
    html_visor = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8" />
    <script src="https://unpkg.com/@viz-js/viz@3.7.0/lib/viz-standalone.js"></script>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        html, body {{
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: transparent;
            font-family: system-ui, -apple-system, sans-serif;
        }}
        #viewport {{
            width: 100%;
            height: {altura}px;
            position: relative;
            overflow: hidden;
            cursor: grab;
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 10px;
            background: rgba(15, 23, 42, 0.25);
            user-select: none;
        }}
        #viewport:active {{
            cursor: grabbing;
        }}
        #canvas {{
            position: absolute;
            top: 0;
            left: 0;
            transform-origin: 0 0;
        }}
        .controles-zoom {{
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 20;
            display: flex;
            gap: 6px;
            background: rgba(15, 23, 42, 0.85);
            padding: 5px 8px;
            border-radius: 8px;
            border: 1px solid #334155;
            backdrop-filter: blur(4px);
        }}
        .controles-zoom button {{
            background: #1e293b;
            color: #f8fafc;
            border: 1px solid #475569;
            border-radius: 5px;
            padding: 3px 9px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.15s;
        }}
        .controles-zoom button:hover {{
            background: #334155;
        }}
        .ayuda-zoom {{
            position: absolute;
            bottom: 8px;
            left: 12px;
            z-index: 10;
            font-size: 11px;
            color: #94a3b8;
            pointer-events: none;
        }}
    </style>
    </head>
    <body>
        <div id="viewport">
            <div class="controles-zoom">
                <button id="btn-zoom-in" title="Acercar">+</button>
                <button id="btn-zoom-out" title="Alejar">−</button>
                <button id="btn-reset" title="Centrar y ajustar">Centrar</button>
            </div>
            <div id="canvas"></div>
            <div class="ayuda-zoom">Rueda del ratón: zoom • Arrastrar: mover</div>
        </div>

        <script>
            const dotSrc = {dot_json};
            const viewport = document.getElementById("viewport");
            const canvas = document.getElementById("canvas");

            let scale = 1;
            let translateX = 0;
            let translateY = 0;
            let isDragging = false;
            let startX = 0;
            let startY = 0;
            let svgWidth = 400;
            let svgHeight = 300;

            function updateTransform() {{
                canvas.style.transform = `translate(${{translateX}}px, ${{translateY}}px) scale(${{scale}})`;
            }}

            function fitAndCenter() {{
                const vw = viewport.clientWidth;
                const vh = viewport.clientHeight;
                const scaleX = (vw - 32) / svgWidth;
                const scaleY = (vh - 32) / svgHeight;
                scale = Math.min(scaleX, scaleY, 1.15);
                scale = Math.max(scale, 0.25);
                translateX = (vw - svgWidth * scale) / 2;
                translateY = Math.max((vh - svgHeight * scale) / 2, 16);
                updateTransform();
            }}

            function zoomAt(factor, centerX, centerY) {{
                const newScale = Math.min(Math.max(scale * factor, 0.08), 16);
                translateX = centerX - (centerX - translateX) * (newScale / scale);
                translateY = centerY - (centerY - translateY) * (newScale / scale);
                scale = newScale;
                updateTransform();
            }}

            Viz.instance().then(function(viz) {{
                const svg = viz.renderSVGElement(dotSrc);
                canvas.appendChild(svg);
                const rect = svg.getBoundingClientRect();
                svgWidth = rect.width || 400;
                svgHeight = rect.height || 300;
                fitAndCenter();
            }});

            viewport.addEventListener("wheel", function(e) {{
                e.preventDefault();
                const rect = viewport.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;
                const factor = e.deltaY < 0 ? 1.16 : 0.86;
                zoomAt(factor, mouseX, mouseY);
            }}, {{ passive: false }});

            viewport.addEventListener("mousedown", function(e) {{
                if (e.target.tagName === "BUTTON") return;
                isDragging = true;
                startX = e.clientX - translateX;
                startY = e.clientY - translateY;
            }});

            window.addEventListener("mousemove", function(e) {{
                if (!isDragging) return;
                translateX = e.clientX - startX;
                translateY = e.clientY - startY;
                updateTransform();
            }});

            window.addEventListener("mouseup", function() {{
                isDragging = false;
            }});

            viewport.addEventListener("dblclick", fitAndCenter);

            document.getElementById("btn-zoom-in").addEventListener("click", function() {{
                zoomAt(1.5, viewport.clientWidth / 2, viewport.clientHeight / 2);
            }});

            document.getElementById("btn-zoom-out").addEventListener("click", function() {{
                zoomAt(0.67, viewport.clientWidth / 2, viewport.clientHeight / 2);
            }});

            document.getElementById("btn-reset").addEventListener("click", fitAndCenter);
        </script>
    </body>
    </html>
    """
    components.html(html_visor, height=altura + 10)


# Distribución en 3 columnas simultáneas: Entrada | Salida de Tokens | Árbol Sintáctico
col_izq, col_centro, col_der = st.columns([1.15, 1.0, 1.25], gap="large")

with col_izq:
    st.subheader("💻 Analizador Léxico y Sintáctico")
    st.caption("Ingresa el código en Python, Java, JavaScript, C o Rust:")

    codigo_entrada = st.text_area(
        "Caja de texto",
        height=310,
        placeholder='Ejemplo:\ndef calcular(a, b):\n    total = a + b * 2\n    if total > 10:\n        print(total)\n    return total'
    )

    btn_analizar = st.button("🚀 Analizar código", type="primary", use_container_width=True)

tiene_codigo = bool(codigo_entrada.strip())

if tiene_codigo:
    lenguaje_detectado, _ = detectar_lenguaje(codigo_entrada)
    lexer = Lexer(lenguaje_detectado)
    tokens = lexer.tokenizar(codigo_entrada)
    parser = Parser(lenguaje_detectado, tokens)
    es_valido, errores, arbol_dot = parser.analizar()

    with col_izq:
        st.success(f"🧠 **Lenguaje detectado:** {lenguaje_detectado}")
        if es_valido:
            st.info(f"✅ Sintaxis válida ({len(tokens)} tokens reconocidos).")
        else:
            st.error(f"❌ Se detectaron {len(errores)} error(es) sintáctico(s):")
            for err in errores:
                st.markdown(f"- `{err}`")
elif btn_analizar:
    with col_izq:
        st.warning("⚠️ Ingresa código en la caja de texto para analizar.")

with col_centro:
    st.subheader("Salida de Tokens")
    with st.container(height=440, border=True):
        if tiene_codigo:
            salida_tokens = "\n".join(t.formatear() for t in tokens)
            st.code(salida_tokens, language="text")
        else:
            st.caption("Aquí se mostrará la secuencia de tokens generada...")

with col_der:
    st.subheader("Árbol Sintáctico")
    if tiene_codigo:
        renderizar_arbol_interactivo(arbol_dot, altura=440)
    else:
        st.caption("Aquí se dibujará el árbol sintáctico del código...")