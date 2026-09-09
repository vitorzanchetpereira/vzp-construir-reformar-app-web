# Construir & Reformar — Reorganização de Categorias + Naming

Base: 12 categorias no ar + 30 itens da lista manuscrita = **41 categorias em 8 grupos**.

---

## 1. Por que agrupar (e não só ordenar)

O `select` atual tem 12 itens em ordem alfabética — funciona. Com 41 itens em lista plana, três problemas aparecem de uma vez:

1. **Alfabético mistura mundos.** "Chapa", "Construtoras" e "Encanador" ficam colados, mas quem contrata chapa não está no mesmo momento de decisão de quem contrata construtora.
2. **Scroll cego.** Acima de ~15 opções o usuário para de ler e começa a caçar. Ele desiste antes de achar "Impermeabilização" porque não sabe se você tem.
3. **O cadastro erra a categoria.** O prestador escolhe a primeira coisa parecida, e o diretório apodrece por dentro — categoria errada é dado errado, e dado errado quebra a busca.

O agrupamento resolve os três com o mesmo movimento: `<optgroup>` no cadastro, seções na home, e busca por sinônimo por cima de tudo.

---

## 2. Os 8 grupos

Ordem proposta = **ordem cronológica da obra**. Não é alfabética de propósito: o usuário navega pelo momento em que está.

| # | Grupo | Itens | Lógica |
|---|-------|-------|--------|
| 1 | **Projeto, Gestão e Estudos** | 7 | Antes de cavar |
| 2 | **Terreno, Estrutura e Alvenaria** | 5 | Obra bruta |
| 3 | **Instalações e Sistemas** | 8 | Dentro da parede |
| 4 | **Acabamento e Ambientes** | 5 | O que aparece |
| 5 | **Materiais e Insumos** | 3 | Quem entrega no canteiro |
| 6 | **Máquinas, Manutenção e Logística** | 6 | O que move a obra |
| 7 | **Segurança do Trabalho e Treinamentos** | 3 | O que mantém legal |
| 8 | **Apoio, Manutenção e Pessoas** | 4 | Pós-obra e rotina |

### Detalhamento

**1. Projeto, Gestão e Estudos**
Projeto e Engenharia · Arquitetura e Design de Interiores · Gerenciamento e Fiscalização de Obra · Mestre de Obra · Topografia · Análise de Solo e Sondagem · Construtoras e Empreiteiras

**2. Terreno, Estrutura e Alvenaria**
Terraplenagem / Máquinas · Pedreiro / Alvenaria · Serralheiro / Estruturas Metálicas · Impermeabilização · Gesso / Drywall

**3. Instalações e Sistemas**
Eletricista · Encanador / Hidráulica · Energia Solar (Fotovoltaico) · Automação Predial e Industrial · T.I., Internet e Redes · Segurança Eletrônica (CFTV, Alarme, Cerca) · Sistema de Gás (GLP / GN) · Sistema de Ar (Climatização e Ar Comprimido)

**4. Acabamento e Ambientes**
Azulejista / Revestimentos · Pintor · Marmoraria · Vidraçaria · Marceneiro / Móveis Planejados

**5. Materiais e Insumos**
Materiais de Construção · Mineradoras e Agregados · Gás (Revenda e Abastecimento)

**6. Máquinas, Manutenção e Logística**
Locação de Equipamentos · Operador de Máquinas · Manutenção de Máquinas e Equipamentos · Tornearia e Usinagem · Frete e Transporte · Chapa (Carga e Descarga)

**7. Segurança do Trabalho e Treinamentos**
Segurança do Trabalho (SESMT, PGR, Laudos) · Treinamentos e Certificações (NRs) · EPI, EPC e Uniformes

**8. Apoio, Manutenção e Pessoas**
Limpeza Pós-Obra · Jardinagem e Paisagismo · Manutenção de Piscinas · Estágio e Jovem Aprendiz

---

## 3. Decisões de fusão e nomenclatura

Sua lista tinha itens que, soltos, gerariam categorias com 1 prestador cada. Fundi o que o mercado já trata junto:

| Da sua lista | Virou | Motivo |
|---|---|---|
| Internet e rede + T.I. | **T.I., Internet e Redes** | Mesmo fornecedor, na prática |
| Sistema de segurança | **Segurança Eletrônica (CFTV, Alarme, Cerca)** | "Sistema de segurança" confunde com Segurança do Trabalho |
| Designer de interiores e arquiteto | **Arquitetura e Design de Interiores** | Mesma habilitação (CAU), mesmo comprador |
| Gerenciador de obra | **Gerenciamento e Fiscalização de Obra** | Separa de Mestre de Obra, que é chão de fábrica |
| Chapa | **Chapa (Carga e Descarga)** | Regionalismo — o parêntese evita ambiguidade |
| Gás + Sistema de gás | **Dois itens distintos** | Revenda (insumo) ≠ instalação (serviço com ART). Não fundir. |
| Manutenção de máquinas + Tornearia | **Dois itens distintos** | Usinagem é fabricação, não conserto |

**Mantidos separados de propósito:** Mestre de Obra vs. Gerenciamento (níveis diferentes), Terraplenagem vs. Operador de Máquinas (com máquina vs. só mão de obra), Locação vs. Manutenção.

⚠️ **Um item para você confirmar:** o 4º da lista manuscrita eu li como **"Vidraçaria"** (segui com isso). Se for **"Andaimaria"**, o lugar dela é no grupo 6, junto com Locação de Equipamentos — troca de uma linha no JSON.

---

## 4. Camada de habilitação (Suprimentos)

O `categorias-agrupadas.json` traz, em cada item, um campo `docs` com a documentação exigida para aquele tipo de fornecedor. Não é enfeite: é o que transforma o diretório em pré-qualificação.

Exemplos do que já está mapeado:

- **Eletricista** → NR-10 vigente (bienal) + ART para entrada e SPDA
- **Mineradoras** → título ANM + licença ambiental + CFEM em dia
- **Frete** → RNTRC ativo + CT-e/MDF-e + seguro RCTR-C e RCF-DC
- **EPI** → CA vigente por item + NF com o CA descrito + ficha de entrega
- **Treinamentos** → certificado com carga horária e validade + evento S-2221 no eSocial
- **Construtoras** → CND federal/estadual/municipal + FGTS + CNDT + certidão de falência
- **Estágio** → termo de compromisso (Lei 11.788) + seguro + controle de cota

Isso habilita duas coisas depois:
- Selo **Verificado** deixa de ser "pagou a assinatura" e passa a ser "documentação conferida" — o que sustenta preço.
- Alerta de **documento vencendo** (NR-10 e ASO são os que mais pegam) vira produto por si só.

---

## 5. Como implementar

### 5.1 Cadastro — `<optgroup>`

Um atributo nativo, zero JS, e o dropdown de 41 itens fica navegável:

```html
<label for="categoria">Categoria *</label>
<select id="categoria" name="categoria" required>
  <option value="">Selecione...</option>

  <optgroup label="Projeto, Gestão e Estudos">
    <option value="projeto-engenharia">Projeto e Engenharia</option>
    <option value="arquitetura-interiores">Arquitetura e Design de Interiores</option>
    <option value="gerenciamento-obra">Gerenciamento e Fiscalização de Obra</option>
    <option value="mestre-de-obra">Mestre de Obra</option>
    <option value="topografia">Topografia</option>
    <option value="analise-de-solo">Análise de Solo e Sondagem</option>
    <option value="construtoras">Construtoras e Empreiteiras</option>
  </optgroup>

  <optgroup label="Terreno, Estrutura e Alvenaria">
    <option value="terraplenagem">Terraplenagem / Máquinas</option>
    <option value="pedreiro">Pedreiro / Alvenaria</option>
    <option value="serralheiro">Serralheiro / Estruturas Metálicas</option>
    <option value="impermeabilizacao">Impermeabilização</option>
    <option value="gesso-drywall">Gesso / Drywall</option>
  </optgroup>

  <!-- ... demais grupos, gerados a partir do JSON ... -->
</select>
```

Melhor ainda: gere no servidor a partir do JSON, para lista e dropdown nunca divergirem.

### 5.2 Home — seções com acordeão

Hoje você tem 12 cards soltos. Com 41, use os 8 grupos como seções: as 3 primeiras abertas, as outras recolhidas com contador ("Materiais e Insumos · 3"). Densidade sem parede de texto.

### 5.3 Busca por sinônimo — o item que mais resolve

O campo `aliases` do JSON existe para isso. Quem digita **"escavadeira"** deve cair em Terraplenagem. **"vazamento"** → Encanador. **"porcelanato"** → Azulejista. **"placa solar"** → Energia Solar. **"NR-35"** → Treinamentos.

Sem isso, o agrupamento resolve só metade do problema: organiza quem navega, mas continua falhando com quem busca pelo nome que conhece.

### 5.4 Compatibilidade

Os 12 slugs que já estão no ar foram **preservados** (`?categoria=encanador` continua funcionando). Nenhum link ou índice quebra.

---

## 6. Sugestões de título

O nome atual — *Construir & Reformar / Mão de obra & Material* — descreve, mas não fica na cabeça. É o rótulo de uma categoria, não de uma marca. Abaixo, candidatos pensados para pegar como chiclete.

### Recomendado

> # **Obra Certa**
> ### Quem faz, quem entrega, quem responde.

Duas palavras, quatro sílabas, dita numa respiração. "Obra certa" já existe na boca do setor ("essa obra tá certa") — você não ensina expressão nova, você ocupa uma que já circula. E "certa" carrega os dois sentidos que você vende: **certa como acertada** e **certa como em conformidade** — exatamente a ponte entre o pedreiro e a pasta de certidões.

O subtítulo faz o trabalho pragmático: os três verbos cobrem mão de obra, material e — o diferencial — **responsabilidade**. "Quem responde" é a promessa que nenhum concorrente faz.

### Alternativas fortes

**Canteiro**
> *Todo mundo que sua obra precisa.*

Uma palavra. É o lugar físico onde tudo isso acontece — a metáfora não precisa ser explicada a ninguém do setor. Poético sem ser floreado: canteiro é onde se constrói e onde se planta. Risco: sozinho não diz que é diretório, depende do subtítulo trabalhar.

**Prumo**
> *A obra em ordem, do projeto à chave.*

O mais autoral da lista. Prumo é o instrumento que define o que está reto — e "estar no prumo" já significa estar correto, em conformidade. Casa perfeitamente com a camada de habilitação documental: você é o prumo do fornecedor. Curto, memorável, praticamente inexplorado como marca no setor. Risco: exige um instante de leitura de quem é de fora da construção.

**Obra Viva**
> *Do terreno à chave, com quem faz.*

"Obra viva" é termo náutico (a parte submersa do casco) e também descreve obra em andamento. Bonito, mas menos direto que Obra Certa.

**Pé de Obra**
> *Mão de obra, material e máquina — por serviço e região.*

Trocadilho com "pé de obra"/"mão de obra". Simpático, regional, fácil de lembrar. Menos institucional — pode limitar se um dia você vender pré-qualificação para construtora grande.

### Comparativo

| Título | Chiclete | Pragmático | Poético | Autoral | Escala |
|---|---|---|---|---|---|
| **Obra Certa** | ●●●●● | ●●●●● | ●●●○○ | ●●●○○ | ●●●●● |
| **Prumo** | ●●●●○ | ●●●○○ | ●●●●● | ●●●●● | ●●●●○ |
| **Canteiro** | ●●●●○ | ●●●○○ | ●●●●● | ●●●●○ | ●●●●○ |
| Obra Viva | ●●●○○ | ●●○○○ | ●●●●● | ●●●●○ | ●●●○○ |
| Pé de Obra | ●●●●● | ●●●○○ | ●●○○○ | ●●●○○ | ●●○○○ |
| *Construir & Reformar (atual)* | ●●○○○ | ●●●●● | ●○○○○ | ●○○○○ | ●●●●○ |

**Minha leitura:** **Obra Certa** se você quer o nome que mais vende e menos explica. **Prumo** se você aceita um pouco mais de construção de marca em troca de algo que ninguém mais tem e que combina exatamente com o rigor documental que você está montando.

### Frases de apoio (independentes do nome)

Servem de headline na home e no rodapé:

- *Indicação de verdade, documento em dia.*
- *Do terreno à chave.*
- *Quem faz, quem entrega, quem responde.*
- *Sua obra não para por falta de quem.*
- *Antes de contratar, confira aqui.*

⚠️ Antes de fechar qualquer nome: consultar disponibilidade de domínio e busca de marca no **INPI** (classes 35 e 42). "Obra Certa" é expressão comum e provavelmente tem registro anterior em alguma classe — o que não impede o uso, mas muda a estratégia de proteção. "Prumo" tende a ter caminho mais livre como marca.
