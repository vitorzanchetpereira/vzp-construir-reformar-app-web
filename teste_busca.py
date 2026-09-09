# -*- coding: utf-8 -*-
"""Regressao da busca por termos alternativos.

Cada caso e (consulta_do_usuario, esperado). O esperado e um slug ou uma tupla
de slugs, quando o termo e legitimamente ambiguo: quem digita "areia" pode
querer a mineradora (volume) ou o deposito (saco) — as duas respostas estao
certas e o teste nao deve fingir que so uma serve.

Cobre as 36 categorias com termo informal, frase de sintoma, erro de grafia,
hifen e pergunta em linguagem natural.

    python teste_busca.py          # resumo
    python teste_busca.py -v       # lista caso a caso
"""

import sys
import time

from busca_sinonimos import CATEGORIAS, buscar

CASOS = [
    # --- G1 estrutura
    ("pedreiro", "pedreiro"),
    ("levantar parede", "pedreiro"),
    ("pedrero", "pedreiro"),
    ("quero um pedrero pra levantar um muro", "pedreiro"),
    ("reboco", "pedreiro"),
    ("forro de gesso", "gesso-drywall"),
    ("drywall", "gesso-drywall"),
    ("sanca", "gesso-drywall"),
    ("portao de ferro", "serralheiro"),
    ("solda", "serralheiro"),
    ("corrimao", "serralheiro"),
    ("patrol", "terraplenagem"),
    ("retro", "terraplenagem"),
    ("escavadera", "terraplenagem"),
    ("terraplanagem", "terraplenagem"),
    ("limpar terreno", "terraplenagem"),
    ("infiltracao na laje", "impermeabilizacao"),
    ("manta asfaltica", "impermeabilizacao"),
    ("impermiabilizacao", "impermeabilizacao"),
    ("caixa d agua vazando", "impermeabilizacao"),

    # --- G2 instalacoes
    ("luz", "eletricista"),
    ("tomada", "eletricista"),
    ("fio", "eletricista"),
    ("sem luz", "eletricista"),
    ("eletrecista", "eletricista"),
    ("eletrisista", "eletricista"),
    ("disjuntor caindo", "eletricista"),
    ("padrao de entrada", "eletricista"),
    ("cano estourado", "encanador"),
    ("vazamento", "encanador"),
    ("esgoto entupido", "encanador"),
    ("desentupimento", "encanador"),
    ("torneira pingando", "encanador"),
    ("botijao", "sistema-de-gas"),
    ("central de gas", "sistema-de-gas"),
    ("cheiro de gas", "sistema-de-gas"),
    ("ar condicionado", "sistema-de-ar"),
    ("nao gela", "sistema-de-ar"),
    ("split", "sistema-de-ar"),
    ("limpeza de ar condicionado", "sistema-de-ar"),
    ("placa solar", "energia-solar"),
    ("fotovoltaico", "energia-solar"),
    ("inversor", "energia-solar"),
    ("baixar conta de luz", "energia-solar"),
    ("portao automatico", "automacao"),
    ("clp", "automacao"),
    ("wi-fi", "ti-internet-redes"),
    ("wi fi", "ti-internet-redes"),
    ("cabeamento de rede", "ti-internet-redes"),
    ("internet nao funciona", "ti-internet-redes"),

    # --- G3 acabamentos
    ("pintor", "pintor"),
    ("pintura de fachada", "pintor"),
    ("grafiato", "pintor"),
    ("massa corrida", "pintor"),
    ("porcelanato", "azulejista"),
    ("azulegista", "azulejista"),
    ("assentar piso", "azulejista"),
    ("rejunte", "azulejista"),
    ("bancada de granito", "marmoraria"),
    ("marmoreria", "marmoraria"),
    ("pia de marmore", "marmoraria"),
    ("moveis planejados", "marceneiro"),
    ("armario sob medida", "marceneiro"),
    ("mdf", "marceneiro"),
    ("box de banheiro", "vidracaria"),
    ("vidro temperado", "vidracaria"),
    ("vidraceria", "vidracaria"),
    ("espelho", "vidracaria"),

    # --- G4 projeto e gestao
    ("projeto arquitetonico", "projeto-engenharia"),
    ("planta", "projeto-engenharia"),
    ("art do crea", "projeto-engenharia"),
    ("engenheiro civil", "projeto-engenharia"),
    ("mestre de obra", "mestre-de-obra"),
    ("encarregado de obra", "mestre-de-obra"),
    ("gerenciamento de obra", "gerenciamento-obra"),
    ("fiscalizacao de obra", "gerenciamento-obra"),
    ("topografo", "topografia"),
    ("locacao de obra", "topografia"),
    ("estacao total", "topografia"),
    ("sondagem", "analise-de-solo"),
    ("spt", "analise-de-solo"),
    ("laudo de solo", "analise-de-solo"),
    ("torno", "tornearia"),
    ("usinagem", "tornearia"),
    ("peca sob medida em metal", "tornearia"),

    # --- G5 apoio e logistica
    ("alugar andaime", "locacao-equipamentos"),
    ("betoneira", "locacao-equipamentos"),
    ("gerador", "locacao-equipamentos"),
    ("maquina quebrada", "manutencao-equipamentos"),
    ("manutencao preventiva", "manutencao-equipamentos"),
    ("operador de escavadeira", "operador-de-maquinas"),
    ("frete", "frete"),
    ("caminhao", "frete"),
    ("cacamba", "frete"),
    ("chapa", "chapa-carga-descarga"),
    ("carga e descarga", "chapa-carga-descarga"),
    ("ajudante por diaria", "chapa-carga-descarga"),
    ("limpeza pos obra", "limpeza-pos-obra"),
    ("limpeza pos-obra", "limpeza-pos-obra"),
    ("tirar entulho", "limpeza-pos-obra"),
    ("limpeza fina", "limpeza-pos-obra"),
    ("jardineiro", "jardinagem-paisagismo"),
    ("cortar grama", "jardinagem-paisagismo"),
    ("paisagismo", "jardinagem-paisagismo"),
    ("agua verde", "manutencao-piscinas"),
    ("limpeza de piscina", "manutencao-piscinas"),
    ("cimento", "materiais-construcao"),
    ("bloco de concreto", "materiais-construcao"),
    ("loja de material de construcao", "materiais-construcao"),
    ("deposito de material", "materiais-construcao"),

    # --- G6 seguranca e capacitacao
    ("epi", "seguranca-do-trabalho"),
    ("botina", "seguranca-do-trabalho"),
    ("pgr", "seguranca-do-trabalho"),
    ("cipa", "seguranca-do-trabalho"),
    ("cftv", "seguranca-eletronica"),
    ("camera de seguranca", "seguranca-eletronica"),
    ("cerca eletrica", "seguranca-eletronica"),
    ("alarme", "seguranca-eletronica"),
    ("nr 35", "treinamentos"),
    ("nr-35", "treinamentos"),
    ("trabalho em altura", "treinamentos"),
    ("brigada de incendio", "treinamentos"),
    ("espaco confinado", "treinamentos"),
    ("cascalho", "mineradoras"),
    ("pedreira", "mineradoras"),
    ("concreto usinado", "mineradoras"),
    ("caminhao de areia", "mineradoras"),
    # ambiguos de verdade: mineradora vende a granel, deposito vende em saco
    ("areia", ("mineradoras", "materiais-construcao")),
    ("brita", ("mineradoras", "materiais-construcao")),
    # NR-11 e norma de treinamento; quem quer a pessoa digita "operador"
    ("nr 11", "treinamentos"),
    ("nr-11", "treinamentos"),
    ("operador de empilhadeira", "operador-de-maquinas"),
]


def main():
    verboso = "-v" in sys.argv
    ok = falha = 0
    erros = []

    t0 = time.perf_counter()
    for consulta, esperado in CASOS:
        aceitos = esperado if isinstance(esperado, tuple) else (esperado,)
        r = buscar(consulta)
        obtido = r[0]["slug"] if r else None
        acertou = obtido in aceitos
        ok += acertou
        falha += not acertou
        if not acertou:
            erros.append((consulta, "/".join(aceitos), obtido,
                          r[0]["score"] if r else 0))
        if verboso:
            print("%-4s %-38s %s" % (
                "ok" if acertou else "FALHA", consulta,
                CATEGORIAS[obtido]["label"] if obtido else "nada encontrado"))
    ms = (time.perf_counter() - t0) * 1000 / len(CASOS)

    print("\n%d casos | %d ok | %d falha | %.1f%% | %.2f ms por busca" % (
        len(CASOS), ok, falha, 100 * ok / len(CASOS), ms))

    if erros:
        print("\nfalhas:")
        for consulta, esperado, obtido, sc in erros:
            print("  %-34s esperado %-24s veio %s (%d)" % (
                consulta, esperado, obtido or "nada", sc))
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
