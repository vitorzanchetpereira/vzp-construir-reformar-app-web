# -*- coding: utf-8 -*-
"""
Busca por termos alternativos — Construir & Reformar
=====================================================

Resolve o problema levantado pelo Vitor: o usuario digita UMA palavra, informal
e as vezes errada ("luz", "tomada", "fio", "eletrecista") e precisa achar o
prestador certo (Instalações - Eletricista).

Como usar no backend (Flask):

    from busca_sinonimos import buscar

    @app.route("/buscar")
    def rota_buscar():
        termo = request.args.get("q", "")
        acertos = buscar(termo)          # [{'slug','label','grupo','score','via'}, ...]
        if not acertos:
            return render_template("sem_resultado.html", termo=termo,
                                   sugestoes=sugerir(termo))
        slugs = [a["slug"] for a in acertos]
        prestadores = Prestador.query.filter(Prestador.categoria.in_(slugs)).all()
        return render_template("resultado.html", ...)

Dependencias: nenhuma. Somente biblioteca padrao.
Custo: o indice e construido uma vez no import (~1000 termos). A busca e O(1)
para acerto exato e O(n) somente no fallback de erro de grafia.
"""

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

# ---------------------------------------------------------------- normalizacao

_ESPACO = re.compile(r"\s+")
_LIXO = re.compile(r"[^a-z0-9\s]")

# palavras que nao carregam significado de busca
_STOP = {
    "de", "da", "do", "das", "dos", "e", "o", "a", "os", "as", "um", "uma",
    "para", "por", "com", "sem", "em", "no", "na", "nos", "nas", "ao", "aos",
    "que", "qual", "quero", "queria", "preciso", "precisava", "procuro",
    "procurando", "busco", "buscando", "alguem", "alguém", "quem", "faz",
    "fazer", "servico", "serviço", "empresa", "profissional", "orcamento",
    "orçamento", "me", "meu", "minha", "aqui", "perto", "urgente", "barato",
    "bom", "boa", "melhor", "indica", "indicacao", "indicação",
}


def normalizar(texto):
    """minusculas, sem acento, sem pontuacao, espaco unico.

    O hifen vira espaco: "nr-35" e "nr 35" passam a ser o mesmo termo, idem
    "ar-condicionado", "pos-obra", "wi-fi", "habite-se".
    """
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", str(texto).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.replace("-", " ")
    t = _LIXO.sub(" ", t)
    return _ESPACO.sub(" ", t).strip()


def _tokens(texto):
    return [p for p in normalizar(texto).split() if p and p not in _STOP]


# ---------------------------------------------------------------- carga do dicionario

_AQUI = Path(__file__).resolve().parent
PESO = {"canon": 10, "forte": 6, "fraco": 3}


def _carregar():
    """Le o dicionario do JSON da taxonomia (campo 'busca' de cada categoria)."""
    caminho = _AQUI / "categorias-agrupadas.json"
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    cats = {}
    for g in dados["grupos"]:
        for item in g["itens"]:
            b = item.get("busca") or {}
            cats[item["slug"]] = {
                "label": item["label"],
                "grupo": g["titulo"],
                "grupo_n": g["n"],
                "prefixo": g["prefixo"],
                "forte": b.get("forte", []),
                "fraco": b.get("fraco", []),
                "tags": item.get("tags", []),
            }
    return cats


CATEGORIAS = _carregar()

# indice invertido: termo normalizado -> [(slug, peso), ...]
INDICE = {}
# vocabulario para o fallback de erro de grafia
VOCAB = set()


def _indexar(termo, slug, peso):
    t = normalizar(termo)
    if not t:
        return
    INDICE.setdefault(t, [])
    if slug not in [s for s, _ in INDICE[t]]:
        INDICE[t].append((slug, peso))
    VOCAB.add(t)


for _slug, _c in CATEGORIAS.items():
    _indexar(_c["label"], _slug, PESO["canon"])
    _indexar(_slug.replace("-", " "), _slug, PESO["canon"])
    for _t in _c["forte"]:
        _indexar(_t, _slug, PESO["forte"])
    for _t in _c["fraco"]:
        _indexar(_t, _slug, PESO["fraco"])

# frases com mais de uma palavra, da mais longa para a mais curta
FRASES = sorted((t for t in INDICE if " " in t), key=lambda s: -len(s))

# maior numero de palavras numa frase indexada
_MAX_N = max((len(t.split()) for t in INDICE), default=1)


# ---------------------------------------------------------------- erro de grafia

def _parecido(palavra, minimo=0.82):
    """Acha o termo do vocabulario mais parecido. Cobre 'eletrecista',
    'azulegista', 'terraplanagem', 'impermiabilizacao'."""
    if len(palavra) < 4:
        return None
    melhor, nota = None, 0.0
    for cand in VOCAB:
        if " " in cand or abs(len(cand) - len(palavra)) > 3:
            continue
        # exige a mesma letra inicial: barato e evita falso positivo
        if cand[0] != palavra[0]:
            continue
        r = SequenceMatcher(None, palavra, cand).ratio()
        if r > nota:
            melhor, nota = cand, r
    return melhor if nota >= minimo else None


# ---------------------------------------------------------------- busca

def buscar(consulta, limite=8, minimo=3):
    """Devolve categorias ordenadas por relevancia.

    [{'slug', 'label', 'grupo', 'prefixo', 'score', 'via': [termos que casaram]}]
    """
    bruto = normalizar(consulta)
    if not bruto:
        return []

    pontos = {}
    via = {}

    def marcar(slug, peso, termo):
        pontos[slug] = pontos.get(slug, 0) + peso
        via.setdefault(slug, [])
        if termo not in via[slug]:
            via[slug].append(termo)

    # 1) frase inteira primeiro — "caixa d agua" nao e "caixa" + "agua"
    resto = " " + bruto + " "
    for frase in FRASES:
        if " " + frase + " " in resto:
            for slug, peso in INDICE[frase]:
                # bonus por especificidade: frase vale mais que palavra
                marcar(slug, peso + 2 * len(frase.split()), frase)
            resto = resto.replace(" " + frase + " ", " ")

    # 2) palavras que sobraram
    sobrou = [p for p in resto.split() if p and p not in _STOP]
    for palavra in sobrou:
        if palavra in INDICE:
            for slug, peso in INDICE[palavra]:
                marcar(slug, peso, palavra)
        else:
            # 3) fallback: erro de grafia
            corr = _parecido(palavra)
            if corr:
                for slug, peso in INDICE[corr]:
                    marcar(slug, max(peso - 2, 1), palavra + "~" + corr)

    saida = []
    for slug, sc in pontos.items():
        if sc < minimo:
            continue
        c = CATEGORIAS[slug]
        saida.append({
            "slug": slug,
            "label": c["label"],
            "grupo": c["grupo"],
            "grupo_n": c["grupo_n"],
            "prefixo": c["prefixo"],
            "score": sc,
            "via": via[slug],
        })
    saida.sort(key=lambda x: (-x["score"], x["label"]))
    return saida[:limite]


def sugerir(consulta, limite=5):
    """Para a tela de 'nada encontrado': devolve os termos mais proximos."""
    palavras = _tokens(consulta)
    achados = []
    for p in palavras:
        c = _parecido(p, minimo=0.70)
        if c:
            achados.extend(s for s, _ in INDICE[c])
    vistos, saida = set(), []
    for slug in achados:
        if slug in vistos:
            continue
        vistos.add(slug)
        saida.append({"slug": slug, "label": CATEGORIAS[slug]["label"]})
    return saida[:limite]


def tags_do_prestador(slug, quantas=5):
    """Tags para EXIBIR no card do prestador.

    Usa a lista curada do campo 'tags' — nao os termos de busca, que contem
    erros de grafia de proposito e nao devem aparecer na tela.
    """
    c = CATEGORIAS.get(slug)
    return c["tags"][:quantas] if c else []


_TAGS_POR_LABEL = {c["label"]: c["tags"] for c in CATEGORIAS.values()}


def tags_por_nome(nome_categoria, quantas=5):
    """Mesma coisa que tags_do_prestador, mas casando pelo nome (rotulo) da
    categoria em vez do slug — o site pode ter categorias com slug gerado
    antes de uma correcao de acentuacao, que nao bate mais com o slug
    canonico daqui. Nome (mesmo com prefixo "Grupo - Item") sempre casa,
    porque procura o rotulo como substring."""
    nome = (nome_categoria or "")
    for label, tags in _TAGS_POR_LABEL.items():
        if label.lower() in nome.lower():
            return tags[:quantas]
    return []


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        for r in buscar(" ".join(sys.argv[1:])):
            print("%3d  %-42s %-38s %s" % (
                r["score"], r["label"], r["grupo"], ", ".join(r["via"][:4])))
    else:
        print("uso: python busca_sinonimos.py <termo>")
