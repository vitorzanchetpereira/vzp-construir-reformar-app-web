# -*- coding: utf-8 -*-
"""
Padrao de nome no card do prestador — Construir & Reformar
===========================================================

Problema: o card destaca o nome da pessoa (Luiza, Monica, Dornia) no topo. Para
quem chega com urgencia e nao conhece ninguem, nome proprio nao informa nada. O
que o cliente procura e a marca ou o servico.

Regra:

    TITULO = Marca (Responsavel)

  - "Marca" e o nome comercial ou, quando nao existe, o foco do servico.
  - "(Responsavel)" e opcional: entra so quando ajuda a identificar — marca
    repetida entre dois cadastros, ou pessoa que o mercado local conhece.
  - A regiao NAO entra no titulo: a segunda linha do card ja imprime
    "Categoria - Regiao". Repetir rouba espaco e nao acrescenta nada.

Duas funcoes servem ao runtime:

    titulo_card(marca, responsavel)   -> string pronta para o card
    validar(marca, responsavel)       -> lista de avisos no momento do cadastro

E uma serve a migracao dos cadastros que ja existem:

    revisar(nome_atual)              -> (titulo_sugerido, situacao, motivo)

Dependencias: nenhuma.
"""

import re
import unicodedata

# ---------------------------------------------------------------- apoio

# palavras que, sozinhas, nao dizem que servico a empresa presta
_GENERICAS = {
    "casa", "home", "sama", "criar", "grupo", "servicos", "solucoes",
    "comercio", "comercial", "empreendimentos", "negocios", "center",
}

# radicais que ja identificam o ramo dentro do nome comercial
_RAMO = [
    "eletr", "hidra", "imperme", "imper", "vidr", "marmo", "granit", "topograf",
    "terrapl", "gesso", "drywall", "serralh", "metal", "ferrag", "tintas",
    "pintura", "marcen", "movei", "piscina", "solar", "energia", "gas",
    "climatiz", "refriger", "andaim", "ferrament", "locac", "constru",
    "engenhar", "arquitet", "projet", "topo", "solo", "sonda", "torn",
    "usina", "mineral", "minerad", "brita", "areia", "epi", "seguranc",
    "treinam", "jardi", "paisag", "limpez", "frete", "transport", "forma",
    "cobertur", "toldo", "esquadri", "veda", "laje", "manta",
]


def _sem_acento(t):
    t = unicodedata.normalize("NFKD", str(t or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def _tem_ramo(marca):
    m = _sem_acento(marca)
    return any(r in m for r in _RAMO)


def _parece_pessoa(nome):
    """Heuristica: nome curto, sem radical de ramo e sem palavra de empresa."""
    n = _sem_acento(nome).strip()
    if not n or _tem_ramo(n):
        return False
    palavras = n.split()
    # "Criar", "Sama", "Home" sao marcas vagas, nao pessoas: o problema delas e
    # nao dizer o ramo, e o aviso precisa ser esse e nao "parece nome de gente".
    if len(palavras) == 1 and n in _GENERICAS:
        return False
    if len(palavras) > 3:
        return False
    marcadores = {"ltda", "me", "mei", "eireli", "sa", "cia", "e", "&"}
    return not (set(palavras) & marcadores)


# ---------------------------------------------------------------- runtime

def titulo_card(marca, responsavel=None):
    """Monta o titulo do card. A regiao fica fora — o card ja mostra na 2a linha."""
    marca = (marca or "").strip()
    if not marca:
        return ""
    resp = (responsavel or "").strip()
    if not resp:
        return marca
    # so o primeiro nome: sobrenome nao ajuda a identificar e ocupa a linha
    primeiro = resp.split()[0]
    if _sem_acento(primeiro) in _sem_acento(marca).split():
        return marca          # nao repetir "Eletromais (Eletromais)"
    return "%s (%s)" % (marca, primeiro)


def validar(marca, responsavel=None, categoria=None):
    """Avisos para a tela de cadastro. Lista vazia = nome dentro do padrao."""
    avisos = []
    marca = (marca or "").strip()

    if not marca:
        avisos.append("Informe o nome comercial ou o foco do servico.")
        return avisos

    if _parece_pessoa(marca):
        avisos.append(
            "\"%s\" parece ser nome de pessoa. No card, quem busca com urgencia "
            "procura a marca ou o servico — use o nome comercial e coloque a "
            "pessoa entre parenteses." % marca)

    if len(marca.split()) == 1 and _sem_acento(marca) in _GENERICAS:
        avisos.append(
            "\"%s\" nao diz que servico voce presta. Acrescente o foco: "
            "\"%s Materiais\", \"%s Engenharia\"." % (marca, marca, marca))
    elif not _tem_ramo(marca) and categoria:
        avisos.append(
            "O nome nao indica o ramo. Considere \"%s - %s\" para o cliente "
            "reconhecer na lista." % (marca, categoria))

    if re.search(r"\d{4,}", marca):
        avisos.append("Evite telefone ou numero no nome do card.")

    if marca.isupper() and len(marca) > 4:
        avisos.append("Evite caixa alta no nome: no card ela pesa e corta.")

    return avisos


# ---------------------------------------------------------------- migracao

def revisar(nome_atual, categoria=None):
    """Le um cadastro existente e devolve (titulo, situacao, motivo).

    situacao: "ok"        — ja esta no padrao
              "inverter"  — pessoa em evidencia, marca existe: e so reordenar
              "completar" — falta nome comercial ou falta o ramo; precisa
                            perguntar ao prestador, nao da para inventar
    """
    nome = (nome_atual or "").strip()

    m = re.match(r"^(.*?)\s*[\(\-—]\s*([^\)]+)\)?$", nome)
    if m and m.group(2):
        marca, resp = m.group(1).strip(), m.group(2).strip()
        if _parece_pessoa(resp) and _tem_ramo(marca):
            return titulo_card(marca, resp), "ok", "Marca na frente, responsavel entre parenteses."
        if _parece_pessoa(resp):
            return (titulo_card(marca, resp), "completar",
                    "A marca \"%s\" nao diz o ramo. Falta o foco do servico." % marca)
        return nome, "ok", "Dois termos comerciais — nao ha pessoa a mover."

    if _parece_pessoa(nome):
        return (nome, "completar",
                "Cadastro so com nome de pessoa. Precisa do nome comercial ou "
                "do foco do servico — nao da para inventar.")

    if not _tem_ramo(nome):
        return (nome, "completar",
                "Nome comercial sem indicacao de ramo. Acrescentar o foco do servico.")

    return nome, "ok", "Nome comercial claro, sem pessoa em evidencia."


if __name__ == "__main__":
    import json
    from pathlib import Path

    d = json.loads((Path(__file__).resolve().parent /
                    "categorias-agrupadas.json").read_text(encoding="utf-8"))

    vistos, linhas = set(), []
    for g in d["grupos"]:
        for item in g["itens"]:
            for f in (item.get("fornecedores") or []):
                if f in vistos or f.startswith("Dezenas"):
                    continue
                vistos.add(f)
                titulo, sit, motivo = revisar(f, item["label"])
                linhas.append((sit, f, titulo, item["label"], motivo))

    ordem = {"completar": 0, "inverter": 1, "ok": 2}
    linhas.sort(key=lambda x: (ordem[x[0]], x[1]))

    print("%-11s %-42s %s" % ("SITUACAO", "COMO ESTA", "COMO FICA"))
    print("-" * 100)
    for sit, atual, titulo, cat, motivo in linhas:
        print("%-11s %-42s %s" % (sit, atual[:42], titulo))
        if sit != "ok":
            print("%-11s   -> %s" % ("", motivo))

    print("\n%d cadastros | %d ok | %d a completar" % (
        len(linhas),
        sum(1 for x in linhas if x[0] == "ok"),
        sum(1 for x in linhas if x[0] == "completar")))
