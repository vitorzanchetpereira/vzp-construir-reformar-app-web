# Construir & Reformar — MVP

Indicação de mão de obra e material da construção civil, por **tipo de serviço e região**.
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

Na primeira execução o banco (`hub.db`) é criado e populado com categorias, a
região Sorriso/MT e prestadores de exemplo. Para recomeçar do zero, apague `hub.db`.

Fotos de perfil/portfólio e da indicação só funcionam com uma conta gratuita no
[Cloudinary](https://cloudinary.com) — sem a env var `CLOUDINARY_URL`, o app roda
normal, só sem upload de imagem. Para testar localmente, copie a `CLOUDINARY_URL`
do painel do Cloudinary (Settings → API Keys) e exporte antes de rodar:
```bash
set CLOUDINARY_URL=cloudinary://SUA_CHAVE_AQUI
```

## O que já funciona

**Fase 1 — diretório (lado da oferta)**
- Home com busca por categoria e região
- Listagem de prestadores com filtro por categoria, região, busca por texto e "só verificados"
- Perfil do prestador com contato (WhatsApp) e indicações
- Envio de indicações (nota + comentário + foto opcional) que persistem
- Selo **Verificado** (gancho de monetização: assinatura do prestador)
- Cadastro de novo prestador que salva de verdade

**Fase 2 — contas, painel e moderação**
- **Login** do prestador e da equipe (senha com hash)
- **Painel do prestador**: edita o próprio perfil e vê suas avaliações (inclusive as em moderação)
- **Moderação**: avaliação nova entra como *pendente*; só aparece no site após a VZP aprovar
- **Painel admin**: fila de aprovação (aprovar/rejeitar) + concessão/remoção do selo Verificado
- Controle de acesso por papel (deslogado → login; papel errado → 403)

**Rodada "robusto" — fotos, indicação de verdade, multi-região, PWA**
- **Conta de cliente**: quem indica/avalia cria conta própria — a indicação fica ligada a um nome real
- **Fotos**: capa e galeria de portfólio do prestador, foto opcional na indicação (via Cloudinary)
- **Multi-região**: cidade/UF deixou de ser fixo; prestador escolhe a região ao se cadastrar (ou cria uma nova)
- **Indicar no WhatsApp**: compartilhar o perfil de um prestador direto para os contatos
- **PWA**: instalável no celular (ícone, manifest, funciona como app)

### Contas de teste (troque em produção!)
| Papel | E-mail | Senha |
|---|---|---|
| Admin (equipe VZP) | `admin@construireformar.local` | `admin123` |
| Prestador (demo) | `demo@construireformar.local` | `demo123` |
| Cliente/indicação (demo) | `cliente@construireformar.local` | `demo123` |

Admin entra em **/admin**; prestador em **/painel**; cliente só precisa estar logado para indicar.

## Estrutura

| Arquivo | Função |
|---|---|
| `app.py` | Rotas e regras da aplicação (Flask) |
| `db.py` | Acesso ao banco (SQLite/Postgres) e migrações idempotentes |
| `uploads.py` | Upload de imagens no Cloudinary (no-op sem `CLOUDINARY_URL`) |
| `seed.py` | Categorias, região padrão, admin e dados de demonstração |
| `templates/` | Páginas HTML (Jinja2) |
| `static/style.css`, `static/app.js` | Estilo e pequenos scripts (região nova, service worker) |
| `static/manifest.json`, `static/sw.js`, `static/icons/` | PWA — instalável no celular |
| `hub.db` | Banco SQLite (gerado ao rodar localmente) |

## Roadmap (mapa E2)

1. ✅ **Fase 1:** liquidez pelo lado da oferta — diretório grátis + selo pago.
2. ✅ **Fase 2:** autenticação, painel do prestador, moderação de avaliações.
3. ✅ **Deploy:** publicado online em Postgres (dados que persistem).
4. ✅ **Robusto:** fotos, conta de quem indica, multi-região, PWA.
5. **Fase 3:** camada de transação usando os serviços da VZP (orçamento → contrato → medição),
   com take-rate sobre negócios fechados dentro da plataforma. Lead/destaque pago — consequência
   do produto funcionando, não o objetivo em si.

## Segurança — antes de publicar
- Trocar `app.secret_key` por um valor secreto (variável de ambiente).
- Trocar as senhas das contas de teste.
- Adicionar proteção CSRF nos formulários (ex.: Flask-WTF).
- Trocar o servidor de desenvolvimento por um WSGI de produção (gunicorn/waitress).
