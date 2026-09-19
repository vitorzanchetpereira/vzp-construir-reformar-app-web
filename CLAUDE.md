# Construir & Reformar

Diretorio de prestadores de servico e fornecedores de material da construcao
civil, por tipo de servico e regiao.

**Python (Flask), nao Node** — `app.py`, `db.py`, `requirements.txt`,
`Procfile`. Telas estaticas em `static/` (`manifest.json`, `sw.js` ali tambem).
Publicacao descrita em `DEPLOY.md`.

## Antes de mexer em qualquer tela

Toda tela daqui segue a skill **`desenvolver-app-vzp`** (plugin
`vzp-engenharia`, marketplace do grupo). Carregue-a antes de criar tela nova,
mexer em tela que existe ou consertar layout.

Ela nao e sugestao — **essas decisoes ja estao tomadas e nao se pergunta por
elas**: PWA com botao de instalar, botao de voltar em toda tela, nada de
`target="_blank"` nem `window.open`, explicacao por mouse, dedo e foco, lista
vazia que ensina, e caber de 320 px ate a TV sem rolagem horizontal.

O que se pergunta e o que so o Vitor decide: o que o programa faz, que numero
importa, como o trabalho acontece.

Se alguma dessas regras nao couber neste trabalho, **diga qual e por que** —
nao a pule calado.

A skill fala em Node + Express porque e o molde da casa. **Aqui o servidor e
Python** — as regras de tela valem inteiras; o que muda e onde o HTML e servido
e como o carimbo de versao entra no endereco do arquivo. Faca o equivalente, nao
copie o codigo.
