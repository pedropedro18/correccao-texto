"""Correção automática de ditado em Português, Français e English.

Compara o texto original com o do aluno palavra a palavra e mostra:
certas (verde), erradas (vermelho riscado + certa), em falta (laranja),
a mais (vermelho), erros de acento e de maiúscula, com nota de 0 a 20.
Usa só a biblioteca padrão (mais o streamlit para a interface).
"""
import difflib
import html
import re
import unicodedata

TEXTOS = {
    "pt": {
        "escreva": "Escreva primeiro o ditado.",
        "nota": "Nota", "certas": "Palavras certas",
        "legenda": "Verde = certo · Vermelho riscado = errado/a mais · Laranja [ ] = em falta",
        "erros": "Erros", "perfeito": "Sem erros. Parabéns!",
        "cols": ("Tipo", "Escreveu", "Correto"),
        "tipos": {"errada": "Palavra errada", "falta": "Em falta", "mais": "A mais",
                  "acento": "Acento", "maiuscula": "Maiúscula/minúscula"},
    },
    "fr": {
        "escreva": "Écrivez d'abord la dictée.",
        "nota": "Note", "certas": "Mots corrects",
        "legenda": "Vert = correct · Rouge barré = faux/en trop · Orange [ ] = manquant",
        "erros": "Erreurs", "perfeito": "Aucune erreur. Bravo !",
        "cols": ("Type", "Écrit", "Correct"),
        "tipos": {"errada": "Mot faux", "falta": "Manquant", "mais": "En trop",
                  "acento": "Accent", "maiuscula": "Majuscule/minuscule"},
    },
    "en": {
        "escreva": "Please write the dictation first.",
        "nota": "Score", "certas": "Correct words",
        "legenda": "Green = correct · Red strikethrough = wrong/extra · Orange [ ] = missing",
        "erros": "Mistakes", "perfeito": "No mistakes. Well done!",
        "cols": ("Type", "Written", "Correct"),
        "tipos": {"errada": "Wrong word", "falta": "Missing", "mais": "Extra",
                  "acento": "Accent", "maiuscula": "Capitalisation"},
    },
}


def detectar_idioma(nome):
    """Aceita 'pt', 'fr', 'en' ou nomes como 'Português (PT)', 'Français', 'English'."""
    n = (nome or "").strip().lower()
    if n in TEXTOS:
        return n
    if n.startswith(("port",)):
        return "pt"
    if n.startswith(("fran", "fren")):
        return "fr"
    if n.startswith(("eng", "ingl")):
        return "en"
    return "pt"


def _normalizar(texto):
    texto = unicodedata.normalize("NFC", texto)
    for c in "’´`‘":
        texto = texto.replace(c, "'")
    return texto


def _sem_acentos(s):
    d = unicodedata.normalize("NFD", s)
    return "".join(c for c in d if unicodedata.category(c) != "Mn")


def _tokens(texto, pontuacao):
    palavra = r"[^\W_]+(?:['\-][^\W_]+)*"
    padrao = palavra + r"|[^\w\s]" if pontuacao else palavra
    return re.findall(padrao, _normalizar(texto))


def _chave(tok, maiusculas, acentos):
    if not maiusculas:
        tok = tok.lower()
    if not acentos:
        tok = _sem_acentos(tok)
    return tok


def _span(palavras, cor, riscado=False):
    estilo = f"color:{cor};font-weight:600;"
    if riscado:
        estilo += "text-decoration:line-through;"
    return " ".join(f'<span style="{estilo}">{html.escape(p)}</span>' for p in palavras)


def _tipo_par(escrito, certo):
    """Classifica um par de palavras diferentes."""
    if escrito.lower() == certo.lower():
        return "maiuscula"
    if _sem_acentos(escrito.lower()) == _sem_acentos(certo.lower()):
        return "acento"
    return "errada"


def corrigir_ditado(original, aluno, idioma="pt", maiusculas=False,
                    pontuacao=False, acentos=True):
    """Devolve dict com nota (0-20), percentagem, html e lista de erros.

    maiusculas=True -> maiúsculas/minúsculas contam como erro
    pontuacao=True  -> a pontuação também é avaliada
    acentos=True    -> acento em falta/errado conta como erro (recomendado em pt e fr)
    """
    t = TEXTOS[detectar_idioma(idioma)]["tipos"]
    a = _tokens(original, pontuacao)
    b = _tokens(aluno, pontuacao)
    ka = [_chave(x, maiusculas, acentos) for x in a]
    kb = [_chave(x, maiusculas, acentos) for x in b]

    sm = difflib.SequenceMatcher(None, ka, kb, autojunk=False)
    partes, erros, certas = [], [], 0

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            certas += i2 - i1
            partes.append(_span(b[j1:j2], "#15803d"))
        elif op == "replace":
            if i2 - i1 == j2 - j1:  # emparelha palavra a palavra
                for x, y in zip(b[j1:j2], a[i1:i2]):
                    partes.append(_span([x], "#dc2626", riscado=True))
                    partes.append(_span([y], "#15803d"))
                    erros.append((t[_tipo_par(x, y)], x, y))
            else:
                partes.append(_span(b[j1:j2], "#dc2626", riscado=True))
                partes.append(_span(a[i1:i2], "#15803d"))
                erros.append((t["errada"], " ".join(b[j1:j2]), " ".join(a[i1:i2])))
        elif op == "delete":
            partes.append(_span(["[" + " ".join(a[i1:i2]) + "]"], "#ea580c"))
            erros.append((t["falta"], "", " ".join(a[i1:i2])))
        elif op == "insert":
            partes.append(_span(b[j1:j2], "#dc2626", riscado=True))
            erros.append((t["mais"], " ".join(b[j1:j2]), ""))

    total = len(a)
    pct = round(100 * certas / total, 1) if total else 0.0
    return {
        "nota": round(pct / 5, 1),  # escala 0-20
        "percentagem": pct,
        "certas": certas,
        "total": total,
        "html": " ".join(partes),
        "erros": erros,
    }


def mostrar_correcao(st, original, aluno, idioma="pt", maiusculas=False,
                     pontuacao=False, acentos=True):
    """Mostra a correção no Streamlit. st é o módulo streamlit.

    idioma pode ser 'pt', 'fr', 'en' ou o nome escolhido na app
    (por exemplo 'Português (PT)', 'Français', 'English').
    """
    lang = detectar_idioma(idioma)
    tx = TEXTOS[lang]
    if not aluno.strip():
        st.warning(tx["escreva"])
        return None

    r = corrigir_ditado(original, aluno, lang, maiusculas, pontuacao, acentos)

    c1, c2 = st.columns(2)
    c1.metric(tx["nota"], f"{r['nota']}/20")
    c2.metric(tx["certas"], f"{r['certas']}/{r['total']}")

    st.markdown(r["html"], unsafe_allow_html=True)
    st.caption(tx["legenda"])

    if r["erros"]:
        st.subheader(tx["erros"])
        c = tx["cols"]
        st.table([{c[0]: e[0], c[1]: e[1], c[2]: e[2]} for e in r["erros"]])
    else:
        st.success(tx["perfeito"])
    return r


# ---------------------------------------------------------------------------
# Interface da app (só corre quando este arquivo é o principal no Streamlit)
# ---------------------------------------------------------------------------
if _name_ == "_main_":
    import streamlit as st

    st.set_page_config(page_title="Correção de ditado", page_icon="✍️")
    st.title("✍️ Correção de ditado")

    idioma = st.selectbox("Idioma", ["Português", "Français", "English"])
    original = st.text_area("Texto original (do professor)", height=150)
    aluno = st.text_area("Texto escrito pelo aluno", height=150)

    col1, col2, col3 = st.columns(3)
    maiusculas = col1.checkbox("Maiúsculas contam")
    pontuacao = col2.checkbox("Avaliar pontuação")
    acentos = col3.checkbox("Acentos contam", value=True)

    if st.button("Corrigir", type="primary"):
        if not original.strip():
            st.warning("Escreva primeiro o texto original.")
        else:
            mostrar_correcao(st, original, aluno, idioma,
                             maiusculas, pontuacao, acentos)