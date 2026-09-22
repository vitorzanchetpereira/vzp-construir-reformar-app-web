# Publicar o Construir & Reformar no Cloud Run

No ar: <https://construir-reformar-898146672742.southamerica-east1.run.app>
(Cloud Run, projeto `central-vzp`, região `southamerica-east1`).

O app saiu do Render. O `render.yaml` não existe mais e o blueprint do Render não
é mais o caminho — quem define o ambiente agora é o `Dockerfile` na raiz, que fixa
Python 3.12 justamente porque o builder do Cloud Run só oferece 3.13/3.14 e o
`psycopg2-binary` não tem pacote pronto para as versões mais novas.

## Subir uma alteração

Não há trigger de CI versionado neste repositório: o deploy é o comando abaixo,
rodado da pasta do projeto.

```bash
gcloud run deploy construir-reformar --source . --project central-vzp --region southamerica-east1
```

O `--source .` faz o Cloud Build montar a imagem pelo `Dockerfile` e publicar uma
revisão nova. O `Procfile` continua no repo por conveniência de execução local —
no Cloud Run o comando que vale é o `CMD` do `Dockerfile`.

## Variáveis de ambiente

Vivem no serviço do Cloud Run (**Editar e implantar nova revisão → Variáveis**),
não em arquivo no repositório:

| Variável | Para quê |
|---|---|
| `DATABASE_URL` | Postgres de produção. Sem ela o `db.py` cai no SQLite local (`hub.db`) — nunca é o que se quer em produção. |
| `SECRET_KEY` | Assina a sessão. Segredo forte, fixo por serviço. |
| `ADMIN_EMAIL` / `ADMIN_SENHA` | A conta que entra em `/admin` e modera as indicações. |
| `CR_API_SECRET` | Autentica o acesso via API (`api_auth.py`). |
| `CLOUDINARY_URL` | Opcional. Sem ela o site funciona inteiro, só sem upload de foto. Pegue em Cloudinary → Settings → API Keys → "API Environment variable". |
| `SEED_DEMO` | `1` popula dados de exemplo. **Antes do lançamento real, ponha `0`** e apague os prestadores de exemplo, para não misturar dado fictício com real. |

## Contas de demonstração (troque/apague em produção)

| Papel | E-mail | Senha |
|---|---|---|
| Admin | definido em `ADMIN_EMAIL` / `ADMIN_SENHA` | (a que você escolher) |
| Prestador demo | `demo@construireformar.local` | `demo123` |
