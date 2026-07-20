# Publicar o Construir & Reformar no Render

O código já está pronto para produção: banco **Postgres** (via `DATABASE_URL`),
servidor **gunicorn**, `SECRET_KEY` e admin por variável de ambiente, e o
`render.yaml` que cria tudo conectado. Siga os passos.

## 1. Criar o repositório no GitHub
Crie um repositório **vazio** (sem README/licença) em <https://github.com/new>.
Sugestão de nome: `construir-reformar` · visibilidade **Private**.

## 2. Enviar o código (rode na pasta do projeto)
```bash
cd C:\Users\vitor\vzp-hub
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/construir-reformar.git
git push -u origin main
```
> Se pedir login, o Git abre o navegador / usa suas credenciais já salvas.

## 3. Criar os serviços no Render (Blueprint)
1. Render → **New +** → **Blueprint**.
2. Conecte a conta GitHub e escolha o repositório `construir-reformar`.
3. O Render lê o `render.yaml` e propõe criar **1 web service + 1 Postgres**.
4. Ele vai pedir os valores marcados como `sync: false`:
   - **ADMIN_EMAIL** — o e-mail de login do admin (o seu).
   - **ADMIN_SENHA** — uma senha forte (essa é a conta que modera avaliações).
5. Clique em **Apply**. O Render instala, cria o banco, sobe o app e semeia os dados.

## 4. Pronto
- A URL fica tipo `https://construir-reformar.onrender.com`.
- Entre em `/admin` com o ADMIN_EMAIL/ADMIN_SENHA que você definiu.
- O `SECRET_KEY` foi gerado automaticamente pelo Render.

## Observações
- **Plano free do Render**: o web service "dorme" após ~15 min sem acesso (a
  primeira visita depois disso demora alguns segundos). O Postgres free tem
  validade limitada — o Render avisa; dá para migrar para um plano pago quando validar.
- **Antes do lançamento real** (com prestadores de verdade): no painel do web
  service, mude a variável `SEED_DEMO` para `0` e apague os prestadores de
  exemplo, para o site não misturar dados fictícios com reais.
- **Atualizar o site depois**: basta `git push` — o Render redeploya sozinho.
  Como agora é Postgres, os dados **não** se perdem entre deploys.

## Contas de demonstração (troque/apague em produção)
| Papel | E-mail | Senha |
|---|---|---|
| Admin | definido em ADMIN_EMAIL / ADMIN_SENHA | (a que você escolher) |
| Prestador demo | `demo@construireformar.local` | `demo123` |
