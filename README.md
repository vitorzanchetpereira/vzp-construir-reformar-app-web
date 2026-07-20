# Construir & Reformar — MVP

Diretório de prestadores e fornecedores da construção. Piloto **Sorriso/MT**.
Iniciativa VZP Engenharia / Base Empreendimentos.

## Como rodar

**Jeito fácil (Windows):** dê dois cliques em `iniciar.bat` e abra <http://localhost:5000>.

**Pelo terminal:**
```bash
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```
Acesse <http://localhost:5000>.

Na primeira execução o banco (`hub.db`) é criado e populado com categorias e
prestadores de exemplo de Sorriso/MT. Para recomeçar do zero, apague `hub.db`.

## O que já funciona

**Fase 1 — diretório (lado da oferta)**
- Home com busca e categorias
- Listagem de prestadores com filtro por categoria, busca por texto e "só verificados"
- Perfil do prestador com contato (WhatsApp) e avaliações
- Envio de avaliações (nota + comentário) que persistem
- Selo **Verificado** (gancho de monetização: assinatura do prestador)
- Cadastro de novo prestador que salva de verdade

**Fase 2 — contas, painel e moderação**
- **Login** do prestador e da equipe (senha com hash)
- **Painel do prestador**: edita o próprio perfil e vê suas avaliações (inclusive as em moderação)
- **Moderação**: avaliação nova entra como *pendente*; só aparece no site após a VZP aprovar
- **Painel admin**: fila de aprovação (aprovar/rejeitar) + concessão/remoção do selo Verificado
- Controle de acesso por papel (deslogado → login; papel errado → 403)

### Contas de teste (troque em produção!)
| Papel | E-mail | Senha |
|---|---|---|
| Admin (equipe VZP) | `admin@construireformar.local` | `admin123` |
| Prestador (demo) | `demo@construireformar.local` | `demo123` |

Admin entra em **/admin**; prestador em **/painel**.

## Estrutura

| Arquivo | Função |
|---|---|
| `app.py` | Rotas e regras da aplicação (Flask) |
| `db.py` | Acesso ao SQLite |
| `schema.sql` | Tabelas: categorias, prestadores, avaliacoes |
| `seed.py` | Dados de exemplo (Sorriso/MT) |
| `templates/` | Páginas HTML (Jinja2) |
| `static/style.css` | Estilo |
| `hub.db` | Banco SQLite (gerado ao rodar) |

## Roadmap (mapa E2)

1. ✅ **Fase 1:** liquidez pelo lado da oferta — diretório grátis + selo pago.
2. ✅ **Fase 2:** autenticação, painel do prestador, moderação de avaliações.
3. **Deploy:** publicar online migrando SQLite → Postgres (dados que persistem).
4. **Fase 3:** camada de transação usando os serviços da VZP (orçamento → contrato → medição),
   com take-rate sobre negócios fechados dentro da plataforma. Lead/destaque pago.

## Segurança — antes de publicar
- Trocar `app.secret_key` por um valor secreto (variável de ambiente).
- Trocar as senhas das contas de teste.
- Adicionar proteção CSRF nos formulários (ex.: Flask-WTF).
- Trocar o servidor de desenvolvimento por um WSGI de produção (gunicorn/waitress).
