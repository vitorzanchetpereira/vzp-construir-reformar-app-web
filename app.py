"""
Construir & Reformar — MVP.
Fase 1: diretório da oferta.  Fase 2: login do prestador, painel e moderação de avaliações.
Fase "robusto": fotos (Cloudinary), contas de cliente/indicação, multi-região, PWA.
VZP Engenharia / Base Empreendimentos.
"""
import os
import re
import secrets
import unicodedata
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, abort, session, jsonify, g)
from werkzeug.security import generate_password_hash, check_password_hash
import api_auth
import busca_sinonimos
import db
import nomes_cards
import uploads

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-troque-em-producao")


@app.template_filter("data")
def _fmt_data(valor, n=10):
    """Formata data/hora de forma agnóstica ao banco (SQLite=texto, Postgres=datetime)."""
    return str(valor)[:n] if valor else ""


@app.before_request
def csrf_protect():
    """Gera um token de sessão e valida todo POST (proteção CSRF).
    As rotas /api/* autenticam por token (Authorization: Bearer), não por
    cookie de sessão — CSRF não se aplica a elas, então ficam de fora."""
    if request.path.startswith("/api/"):
        return
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    if request.method == "POST":
        enviado = request.form.get("_csrf", "")
        if not enviado or enviado != session.get("csrf"):
            abort(400)


# ---------------------------------------------------------------- helpers
def _sem_acento(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in texto if not unicodedata.combining(c)).lower()


def categorias_por_sinonimo(busca):
    """Quem busca não digita o nome da categoria — digita o problema ("vazamento",
    "luz", "goteira", até com erro de grafia). Usa o motor de busca_sinonimos
    (taxonomia curada em categorias-agrupadas.json) pra achar os nomes de
    categoria correspondentes, e incluir na busca além do nome/descrição."""
    return [r["label"] for r in busca_sinonimos.buscar(busca)]


def categorias():
    return db.query("SELECT * FROM categorias ORDER BY nome")


def regioes():
    return db.query("SELECT * FROM regioes ORDER BY nome")


def _slugify(*partes):
    texto = _sem_acento(" ".join(partes))
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return texto


def _slug_categoria_unico(nome):
    base = _slugify(nome) or "categoria"
    slug = base
    i = 2
    while db.query("SELECT 1 FROM categorias WHERE slug = ?", (slug,), one=True):
        slug = f"{base}-{i}"
        i += 1
    return slug


def obter_ou_criar_categoria(nome, icone="🔧"):
    nome = (nome or "").strip()
    if not nome:
        return None
    c = db.query("SELECT id FROM categorias WHERE LOWER(nome) = LOWER(?)", (nome,), one=True)
    if c:
        return c["id"]
    slug = _slug_categoria_unico(nome)
    return db.execute("INSERT INTO categorias (nome, slug, icone) VALUES (?,?,?)", (nome, slug, icone or "🔧"))


def obter_ou_criar_regiao(nome, uf):
    nome = (nome or "").strip()
    uf = (uf or "").strip().upper()[:2]
    if not nome or not uf:
        return None
    slug = _slugify(nome, uf)
    r = db.query("SELECT * FROM regioes WHERE slug = ?", (slug,), one=True)
    if r:
        return r["id"]
    return db.execute("INSERT INTO regioes (nome, uf, slug) VALUES (?,?,?)", (nome, uf, slug))


def resolver_regiao(form):
    """Lê o select de região do formulário; se for 'outra cidade', cria a região na hora."""
    valor = form.get("regiao_id", "")
    if valor == "__nova__":
        return obter_ou_criar_regiao(form.get("regiao_nome", ""), form.get("regiao_uf", ""))
    if valor.isdigit():
        return int(valor)
    return None


def garantir_nome_com_papel(nome, categoria_nome):
    """O card nunca pode mostrar só o nome da pessoa ("João") — quem busca com
    urgência procura a empresa ou o serviço, não o fulano. Usa o detector de
    nomes_cards (mesmo radical de ramo/marca que já filtra "VZP Engenharia",
    "Eletromais" etc. como nome comercial válido) pra só agir em quem realmente
    parece só nome de pessoa: "João" -> "Pedreiro João"."""
    nome = (nome or "").strip()
    if not nome or not categoria_nome:
        return nome
    if any(c in nome for c in "-–—()&") or nome.split()[0].isupper():
        return nome  # já tem cara de nome comercial/sigla — não força
    if not nomes_cards._parece_pessoa(nome):
        return nome
    papel = categoria_nome.split("•")[-1].strip()
    papel = papel.split("/")[0].strip()
    if not papel or _sem_acento(papel) in _sem_acento(nome):
        return nome
    return f"{papel} {nome}"


def usuario_atual():
    uid = session.get("usuario_id")
    if not uid:
        return None
    return db.query("SELECT * FROM usuarios WHERE id = ?", (uid,), one=True)


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not usuario_atual():
            flash("Faça login para continuar.", "erro")
            return redirect(url_for("entrar"))
        return f(*a, **kw)
    return wrapper


def _papel_required(papel):
    def deco(f):
        @wraps(f)
        def wrapper(*a, **kw):
            u = usuario_atual()
            if not u:                       # deslogado -> vai fazer login
                flash("Faça login para continuar.", "erro")
                return redirect(url_for("entrar"))
            if u["papel"] != papel:         # logado, mas papel errado -> proibido
                abort(403)
            return f(*a, **kw)
        return wrapper
    return deco


admin_required = _papel_required("admin")
prestador_required = _papel_required("prestador")


def api_admin_required(f):
    """Para as rotas /api/*, usadas pelo conector MCP: autentica por token
    (Authorization: Bearer <token>), não por cookie de sessão."""
    @wraps(f)
    def wrapper(*a, **kw):
        auth = request.headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else ""
        claims = api_auth.verificar_token(token)
        if not claims or claims.get("papel") != "admin":
            return jsonify({"erro": "não autorizado"}), 401
        g.api_usuario = claims
        return f(*a, **kw)
    return wrapper


def _resolver_categoria_por_nome(nome):
    nome = (nome or "").strip()
    if not nome:
        return None
    c = db.query("SELECT id FROM categorias WHERE LOWER(nome) = LOWER(?)", (nome,), one=True)
    return c["id"] if c else None


def _parse_regiao_texto(texto):
    """Aceita 'Cidade/UF' ou 'Cidade, UF'."""
    texto = (texto or "").strip()
    if not texto:
        return None, None
    for sep in ("/", ","):
        if sep in texto:
            cidade, uf = texto.split(sep, 1)
            return cidade.strip(), uf.strip()
    return None, None


def _prestador_enxuto(p):
    # p pode ser sqlite3.Row (sem .get()) ou RealDictRow do psycopg2 — usar só
    # indexação por chave, que as duas classes suportam.
    regiao_nome = p["regiao_nome"]
    return {
        "id": p["id"],
        "nome": p["nome"],
        "categoria": p["categoria_nome"],
        "regiao": f"{regiao_nome}/{p['regiao_uf']}" if regiao_nome else None,
        "telefone": p["telefone"],
        "whatsapp": p["whatsapp"],
        "descricao": p["descricao"],
        "verificado": bool(p["verificado"]),
        "media": float(p["media"]) if p["media"] is not None else 0.0,
        "n_avaliacoes": int(p["n_avaliacoes"] or 0),
    }


def stats_aprovadas(prestador_id):
    return db.query(
        "SELECT COUNT(*) AS n, COALESCE(ROUND(AVG(nota),1),0) AS media "
        "FROM avaliacoes WHERE prestador_id = ? AND status = 'aprovada'",
        (prestador_id,), one=True,
    )


@app.context_processor
def inject_globals():
    return {"todas_categorias": categorias(), "todas_regioes": regioes(),
            "usuario": usuario_atual(), "csrf_token": session.get("csrf", "")}


# ---------------------------------------------------------------- público
@app.route("/")
def index():
    regiao_slug = request.args.get("regiao", "").strip()
    sql = """
        SELECT p.*, c.nome AS categoria_nome, c.icone AS categoria_icone,
               r.nome AS regiao_nome, r.uf AS regiao_uf,
               COUNT(a.id) AS n_avaliacoes,
               COALESCE(ROUND(AVG(a.nota),1),0) AS media
        FROM prestadores p
        JOIN categorias c ON c.id = p.categoria_id
        LEFT JOIN regioes r ON r.id = p.regiao_id
        LEFT JOIN avaliacoes a ON a.prestador_id = p.id AND a.status = 'aprovada'
    """
    params = []
    if regiao_slug:
        sql += " WHERE r.slug = ?"
        params.append(regiao_slug)
    sql += """
        GROUP BY p.id, c.id, r.id
        ORDER BY p.verificado DESC, media DESC, n_avaliacoes DESC
        LIMIT 6
    """
    rows = db.query(sql, params)
    total = db.query("SELECT COUNT(*) AS n FROM prestadores", one=True)["n"]
    return render_template("index.html", categorias=categorias(), destaques=rows, total=total,
                           regiao_slug=regiao_slug)


@app.route("/prestadores")
def prestadores():
    busca = request.args.get("q", "").strip()
    cat_slug = request.args.get("categoria", "").strip()
    regiao_slug = request.args.get("regiao", "").strip()
    verificado = request.args.get("verificado", "")

    def _montar_sql(usar_busca):
        sql = """
            SELECT p.*, c.nome AS categoria_nome, c.icone AS categoria_icone, c.slug AS categoria_slug,
                   r.nome AS regiao_nome, r.uf AS regiao_uf, r.slug AS regiao_slug,
                   COUNT(a.id) AS n_avaliacoes,
                   COALESCE(ROUND(AVG(a.nota),1),0) AS media
            FROM prestadores p
            JOIN categorias c ON c.id = p.categoria_id
            LEFT JOIN regioes r ON r.id = p.regiao_id
            LEFT JOIN avaliacoes a ON a.prestador_id = p.id AND a.status = 'aprovada'
            WHERE 1=1
        """
        params = []
        if usar_busca and busca:
            categorias_sinonimo = categorias_por_sinonimo(busca)
            busca_lower = busca.lower()
            if categorias_sinonimo:
                # LIKE por conter o nome da categoria, não igualdade exata — sobrevive
                # a categorias renomeadas/reagrupadas (ex.: "Instalações — Eletricista").
                # LOWER() dos dois lados: no Postgres (produção) LIKE é sensível a
                # maiúsculas/minúsculas, no SQLite (local) não — sem isso, buscar
                # "bruna" nunca acha "Bruna - Criar" em produção.
                condicoes_cat = " OR ".join(["LOWER(c.nome) LIKE ?"] * len(categorias_sinonimo))
                sql += f" AND (LOWER(p.nome) LIKE ? OR LOWER(p.descricao) LIKE ? OR {condicoes_cat})"
                params += [f"%{busca_lower}%", f"%{busca_lower}%"] + [f"%{c.lower()}%" for c in categorias_sinonimo]
            else:
                sql += " AND (LOWER(p.nome) LIKE ? OR LOWER(p.descricao) LIKE ?)"
                params += [f"%{busca_lower}%", f"%{busca_lower}%"]
        if cat_slug:
            sql += " AND c.slug = ?"
            params.append(cat_slug)
        if regiao_slug:
            sql += " AND r.slug = ?"
            params.append(regiao_slug)
        if verificado == "1":
            sql += " AND p.verificado = 1"
        sql += " GROUP BY p.id, c.id, r.id ORDER BY p.verificado DESC, media DESC, n_avaliacoes DESC, p.nome"
        return sql, params

    sql, params = _montar_sql(usar_busca=True)
    rows = db.query(sql, params)

    # busca generica (nao bate com nenhuma categoria nem aparece em nome/descricao)
    # nunca deve deixar a tela vazia - mostra tudo (respeitando categoria/regiao/
    # verificado que a pessoa ja tiver escolhido) com um aviso, em vez de nada.
    busca_sem_resultado = bool(busca) and not rows
    if busca_sem_resultado:
        sql, params = _montar_sql(usar_busca=False)
        rows = db.query(sql, params)

    cat_atual = db.query("SELECT * FROM categorias WHERE slug = ?", (cat_slug,), one=True) if cat_slug else None
    regiao_atual = db.query("SELECT * FROM regioes WHERE slug = ?", (regiao_slug,), one=True) if regiao_slug else None
    return render_template("prestadores.html", prestadores=rows, busca=busca,
                           busca_sem_resultado=busca_sem_resultado,
                           cat_slug=cat_slug, cat_atual=cat_atual, verificado=verificado,
                           regiao_slug=regiao_slug, regiao_atual=regiao_atual)


@app.route("/prestador/<int:pid>")
def prestador(pid):
    row = db.query(
        """SELECT p.*, c.nome AS categoria_nome, c.icone AS categoria_icone, c.slug AS categoria_slug,
                  r.nome AS regiao_nome, r.uf AS regiao_uf
           FROM prestadores p JOIN categorias c ON c.id = p.categoria_id
           LEFT JOIN regioes r ON r.id = p.regiao_id WHERE p.id = ?""",
        (pid,), one=True,
    )
    if not row:
        abort(404)
    p = dict(row)
    s = stats_aprovadas(pid)
    p["n_avaliacoes"], p["media"] = s["n"], s["media"]
    avaliacoes = db.query(
        "SELECT * FROM avaliacoes WHERE prestador_id = ? AND status = 'aprovada' ORDER BY criado_em DESC",
        (pid,),
    )
    fotos = db.query("SELECT * FROM prestador_fotos WHERE prestador_id = ? ORDER BY criado_em DESC", (pid,))
    return render_template("prestador.html", p=p, avaliacoes=avaliacoes, fotos=fotos)


@app.route("/prestador/<int:pid>/avaliar", methods=["POST"])
@login_required
def avaliar(pid):
    if not db.query("SELECT 1 FROM prestadores WHERE id = ?", (pid,), one=True):
        abort(404)
    u = usuario_atual()
    comentario = request.form.get("comentario", "").strip()
    try:
        nota = int(request.form.get("nota", 0))
    except ValueError:
        nota = 0
    if nota < 1 or nota > 5:
        flash("Escolha uma nota de 1 a 5.", "erro")
        return redirect(url_for("prestador", pid=pid))
    arquivo_foto = request.files.get("foto")
    foto_url = uploads.upload_imagem(arquivo_foto)
    if arquivo_foto and arquivo_foto.filename and not foto_url:
        flash("A indicação foi enviada, mas a foto não pôde ser enviada "
              "(confira se é uma imagem de até 10MB).", "erro")
    db.execute(
        "INSERT INTO avaliacoes (prestador_id, usuario_id, autor, nota, comentario, foto_url, status) "
        "VALUES (?,?,?,?,?,?, 'pendente')",
        (pid, u["id"], u["nome"], nota, comentario, foto_url),
    )
    flash("Indicação enviada! Ela passará por moderação antes de aparecer no perfil.", "ok")
    return redirect(url_for("prestador", pid=pid))


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        f = request.form
        nome = f.get("nome", "").strip()
        categoria_id = f.get("categoria_id", "")
        regiao_id = resolver_regiao(f)
        telefone = f.get("telefone", "").strip()
        whatsapp = f.get("whatsapp", "").strip()
        descricao = f.get("descricao", "").strip()
        email = f.get("email", "").strip().lower()
        senha = f.get("senha", "")

        if not (nome and categoria_id and regiao_id and email and senha):
            flash("Preencha nome, categoria, região, e-mail e senha.", "erro")
            return render_template("cadastro.html", form=f)
        if len(senha) < 6:
            flash("A senha precisa ter ao menos 6 caracteres.", "erro")
            return render_template("cadastro.html", form=f)
        if db.query("SELECT 1 FROM usuarios WHERE email = ?", (email,), one=True):
            flash("Já existe uma conta com esse e-mail.", "erro")
            return render_template("cadastro.html", form=f)

        cat = db.query("SELECT nome FROM categorias WHERE id = ?", (categoria_id,), one=True)
        nome_ajustado = garantir_nome_com_papel(nome, cat["nome"] if cat else "")
        if nome_ajustado != nome:
            flash(f'Ajustamos o nome pra "{nome_ajustado}" — o card nunca mostra só o nome '
                  f"da pessoa, pra quem busca reconhecer o serviço. Pode editar depois no seu painel.", "ok")
            nome = nome_ajustado

        foto_url = uploads.upload_imagem(request.files.get("foto"))
        pid = db.execute(
            """INSERT INTO prestadores (nome, categoria_id, regiao_id, telefone, whatsapp, descricao, foto_url)
               VALUES (?,?,?,?,?,?,?)""",
            (nome, categoria_id, regiao_id, telefone, whatsapp, descricao, foto_url),
        )
        uid = db.execute(
            "INSERT INTO usuarios (nome, email, senha_hash, papel, prestador_id) VALUES (?,?,?, 'prestador', ?)",
            (nome, email, generate_password_hash(senha), pid),
        )
        session["usuario_id"] = uid
        flash("Cadastro realizado! Gerencie seu perfil por aqui.", "ok")
        return redirect(url_for("painel"))
    return render_template("cadastro.html", form={})


@app.route("/conta/cadastro", methods=["GET", "POST"])
def conta_cadastro():
    if request.method == "POST":
        f = request.form
        nome = f.get("nome", "").strip()
        email = f.get("email", "").strip().lower()
        senha = f.get("senha", "")
        if not (nome and email and senha):
            flash("Preencha nome, e-mail e senha.", "erro")
            return render_template("conta_cadastro.html", form=f)
        if len(senha) < 6:
            flash("A senha precisa ter ao menos 6 caracteres.", "erro")
            return render_template("conta_cadastro.html", form=f)
        if db.query("SELECT 1 FROM usuarios WHERE email = ?", (email,), one=True):
            flash("Já existe uma conta com esse e-mail.", "erro")
            return render_template("conta_cadastro.html", form=f)
        uid = db.execute(
            "INSERT INTO usuarios (nome, email, senha_hash, papel) VALUES (?,?,?, 'cliente')",
            (nome, email, generate_password_hash(senha)),
        )
        session["usuario_id"] = uid
        flash("Conta criada! Agora você pode indicar e avaliar prestadores.", "ok")
        return redirect(url_for("index"))
    return render_template("conta_cadastro.html", form={})


@app.route("/sobre")
def sobre():
    return render_template("sobre.html")


# ---------------------------------------------------------------- autenticação
@app.route("/entrar", methods=["GET", "POST"])
def entrar():
    proximo = request.values.get("next", "")
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        u = db.query("SELECT * FROM usuarios WHERE email = ?", (email,), one=True)
        if u and check_password_hash(u["senha_hash"], senha):
            session["usuario_id"] = u["id"]
            flash("Login efetuado.", "ok")
            if proximo and proximo.startswith("/"):
                return redirect(proximo)
            return redirect(url_for("admin_painel" if u["papel"] == "admin" else "painel"))
        flash("E-mail ou senha inválidos.", "erro")
    return render_template("entrar.html", proximo=proximo)


@app.route("/sair")
def sair():
    session.clear()
    flash("Você saiu da sua conta.", "ok")
    return redirect(url_for("index"))


# ---------------------------------------------------------------- painel do prestador
@app.route("/painel")
@prestador_required
def painel():
    u = usuario_atual()
    p = db.query(
        """SELECT p.*, c.nome AS categoria_nome, c.icone AS categoria_icone,
                  r.nome AS regiao_nome, r.uf AS regiao_uf
           FROM prestadores p JOIN categorias c ON c.id = p.categoria_id
           LEFT JOIN regioes r ON r.id = p.regiao_id WHERE p.id = ?""",
        (u["prestador_id"],), one=True,
    )
    if not p:
        abort(404)
    s = stats_aprovadas(p["id"])
    avaliacoes = db.query(
        "SELECT * FROM avaliacoes WHERE prestador_id = ? ORDER BY criado_em DESC", (p["id"],)
    )
    fotos = db.query("SELECT * FROM prestador_fotos WHERE prestador_id = ? ORDER BY criado_em DESC", (p["id"],))
    pendentes = sum(1 for a in avaliacoes if a["status"] == "pendente")
    return render_template("painel.html", p=p, stats=s, avaliacoes=avaliacoes, pendentes=pendentes, fotos=fotos)


def _atualizar_dados_prestador(pid, form, arquivo_foto):
    """Usado tanto pelo prestador editando o próprio perfil quanto pelo admin
    editando qualquer prestador. Devolve False se faltar campo obrigatório."""
    nome = form.get("nome", "").strip()
    categoria_id = form.get("categoria_id", "")
    regiao_id = resolver_regiao(form)
    if not (nome and categoria_id and regiao_id):
        return False
    campos = "nome=?, categoria_id=?, regiao_id=?, telefone=?, whatsapp=?, descricao=?"
    valores = [nome, categoria_id, regiao_id, form.get("telefone", "").strip(),
               form.get("whatsapp", "").strip(), form.get("descricao", "").strip()]
    if arquivo_foto and arquivo_foto.filename:
        foto_url = uploads.upload_imagem(arquivo_foto)
        if foto_url:
            campos += ", foto_url=?"
            valores.append(foto_url)
        else:
            flash("Os outros dados foram salvos, mas a foto não pôde ser enviada "
                  "(confira se é uma imagem de até 10MB).", "erro")
    valores.append(pid)
    db.execute(f"UPDATE prestadores SET {campos} WHERE id=?", valores)
    return True


@app.route("/painel/editar", methods=["GET", "POST"])
@prestador_required
def painel_editar():
    u = usuario_atual()
    pid = u["prestador_id"]
    if request.method == "POST":
        if not _atualizar_dados_prestador(pid, request.form, request.files.get("foto")):
            flash("Nome, categoria e região são obrigatórios.", "erro")
            return redirect(url_for("painel_editar"))
        flash("Perfil atualizado!", "ok")
        return redirect(url_for("painel"))
    p = db.query("SELECT * FROM prestadores WHERE id = ?", (pid,), one=True)
    return render_template("painel_editar.html", p=p,
                           acao=url_for("painel_editar"), voltar=url_for("painel"))


@app.route("/admin/prestador/<int:pid>/editar", methods=["GET", "POST"])
@admin_required
def admin_prestador_editar(pid):
    p = db.query("SELECT * FROM prestadores WHERE id = ?", (pid,), one=True)
    if not p:
        abort(404)
    if request.method == "POST":
        if not _atualizar_dados_prestador(pid, request.form, request.files.get("foto")):
            flash("Nome, categoria e região são obrigatórios.", "erro")
            return redirect(url_for("admin_prestador_editar", pid=pid))
        flash("Prestador atualizado!", "ok")
        return redirect(url_for("admin_painel"))
    return render_template("painel_editar.html", p=p,
                           acao=url_for("admin_prestador_editar", pid=pid), voltar=url_for("admin_painel"))


@app.route("/painel/fotos", methods=["POST"])
@prestador_required
def painel_fotos_adicionar():
    u = usuario_atual()
    foto_url = uploads.upload_imagem(request.files.get("foto"))
    if foto_url:
        db.execute("INSERT INTO prestador_fotos (prestador_id, url) VALUES (?,?)", (u["prestador_id"], foto_url))
        flash("Foto adicionada à galeria!", "ok")
    else:
        flash("Não foi possível enviar a foto. Confira o arquivo (imagem, até 10MB) e tente de novo.", "erro")
    return redirect(url_for("painel"))


@app.route("/painel/fotos/<int:fid>/remover", methods=["POST"])
@prestador_required
def painel_fotos_remover(fid):
    u = usuario_atual()
    foto = db.query(
        "SELECT * FROM prestador_fotos WHERE id = ? AND prestador_id = ?", (fid, u["prestador_id"]), one=True
    )
    if not foto:
        abort(404)
    db.execute("DELETE FROM prestador_fotos WHERE id = ?", (fid,))
    flash("Foto removida.", "ok")
    return redirect(url_for("painel"))


# ---------------------------------------------------------------- admin (equipe VZP)
@app.route("/admin")
@admin_required
def admin_painel():
    pendentes = db.query(
        """SELECT a.*, p.nome AS prestador_nome, p.id AS pid
           FROM avaliacoes a JOIN prestadores p ON p.id = a.prestador_id
           WHERE a.status = 'pendente' ORDER BY a.criado_em"""
    )
    prestadores = db.query(
        """SELECT p.*, c.nome AS categoria_nome, r.nome AS regiao_nome, r.uf AS regiao_uf,
                  (SELECT COUNT(*) FROM avaliacoes a WHERE a.prestador_id=p.id AND a.status='aprovada') AS n_aprov
           FROM prestadores p JOIN categorias c ON c.id = p.categoria_id
           LEFT JOIN regioes r ON r.id = p.regiao_id
           ORDER BY p.verificado DESC, p.nome"""
    )
    return render_template("admin.html", pendentes=pendentes, prestadores=prestadores)


@app.route("/admin/avaliacao/<int:aid>/<acao>", methods=["POST"])
@admin_required
def admin_avaliacao(aid, acao):
    if acao not in ("aprovar", "rejeitar"):
        abort(404)
    novo = "aprovada" if acao == "aprovar" else "rejeitada"
    db.execute("UPDATE avaliacoes SET status = ? WHERE id = ?", (novo, aid))
    flash(f"Avaliação {novo}.", "ok")
    return redirect(url_for("admin_painel"))


@app.route("/admin/convidar", methods=["GET", "POST"])
@admin_required
def admin_convidar():
    if request.method == "POST":
        f = request.form
        nome = f.get("nome", "").strip()
        email = f.get("email", "").strip().lower()
        senha = f.get("senha", "")
        if not (nome and email and senha):
            flash("Preencha nome, e-mail e senha.", "erro")
            return redirect(url_for("admin_convidar"))
        if len(senha) < 6:
            flash("A senha precisa ter ao menos 6 caracteres.", "erro")
            return redirect(url_for("admin_convidar"))
        if db.query("SELECT 1 FROM usuarios WHERE email = ?", (email,), one=True):
            flash("Já existe uma conta com esse e-mail.", "erro")
            return redirect(url_for("admin_convidar"))
        db.execute(
            "INSERT INTO usuarios (nome, email, senha_hash, papel) VALUES (?,?,?, 'admin')",
            (nome, email, generate_password_hash(senha)),
        )
        flash(f"Admin {nome} criado — já pode entrar em /entrar com esse e-mail.", "ok")
        return redirect(url_for("admin_convidar"))
    admins = db.query("SELECT nome, email, criado_em FROM usuarios WHERE papel = 'admin' ORDER BY criado_em")
    return render_template("admin_convidar.html", admins=admins)


@app.route("/admin/categoria/criar", methods=["POST"])
@admin_required
def admin_categoria_criar():
    nome = request.form.get("nome", "").strip()
    icone = request.form.get("icone", "").strip()
    if not nome:
        flash("Informe o nome da categoria.", "erro")
        return redirect(url_for("admin_painel"))
    if db.query("SELECT 1 FROM categorias WHERE LOWER(nome) = LOWER(?)", (nome,), one=True):
        flash("Já existe uma categoria com esse nome.", "erro")
        return redirect(url_for("admin_painel"))
    obter_ou_criar_categoria(nome, icone)
    flash(f"Categoria '{nome}' criada!", "ok")
    return redirect(url_for("admin_painel"))


@app.route("/admin/categoria/<int:cid>/editar", methods=["POST"])
@admin_required
def admin_categoria_editar(cid):
    if not db.query("SELECT 1 FROM categorias WHERE id = ?", (cid,), one=True):
        abort(404)
    nome = request.form.get("nome", "").strip()
    icone = request.form.get("icone", "").strip() or "🔧"
    if not nome:
        flash("Informe o nome da categoria.", "erro")
        return redirect(url_for("admin_painel"))
    outra = db.query("SELECT 1 FROM categorias WHERE LOWER(nome) = LOWER(?) AND id != ?", (nome, cid), one=True)
    if outra:
        flash("Já existe outra categoria com esse nome.", "erro")
        return redirect(url_for("admin_painel"))
    db.execute("UPDATE categorias SET nome = ?, icone = ? WHERE id = ?", (nome, icone, cid))
    flash("Categoria atualizada!", "ok")
    return redirect(url_for("admin_painel"))


@app.route("/admin/categoria/<int:cid>/excluir", methods=["POST"])
@admin_required
def admin_categoria_excluir(cid):
    cat = db.query("SELECT nome FROM categorias WHERE id = ?", (cid,), one=True)
    if not cat:
        abort(404)
    em_uso = db.query("SELECT COUNT(*) AS n FROM prestadores WHERE categoria_id = ?", (cid,), one=True)["n"]
    if em_uso:
        flash(f"Não é possível excluir: {em_uso} prestador(es) ainda usam a categoria '{cat['nome']}'.", "erro")
        return redirect(url_for("admin_painel"))
    db.execute("DELETE FROM categorias WHERE id = ?", (cid,))
    flash(f"Categoria '{cat['nome']}' excluída.", "ok")
    return redirect(url_for("admin_painel"))


@app.route("/admin/regiao/criar", methods=["POST"])
@admin_required
def admin_regiao_criar():
    nome = request.form.get("nome", "").strip()
    uf = request.form.get("uf", "").strip()
    if not (nome and uf):
        flash("Informe cidade e UF.", "erro")
        return redirect(url_for("admin_painel"))
    if not obter_ou_criar_regiao(nome, uf):
        flash("Não foi possível criar a região — confira cidade e UF.", "erro")
        return redirect(url_for("admin_painel"))
    flash(f"Região '{nome}/{uf.upper()}' criada!", "ok")
    return redirect(url_for("admin_painel"))


@app.route("/admin/regiao/<int:rid>/editar", methods=["POST"])
@admin_required
def admin_regiao_editar(rid):
    r = db.query("SELECT * FROM regioes WHERE id = ?", (rid,), one=True)
    if not r:
        abort(404)
    nome = request.form.get("nome", "").strip() or r["nome"]
    uf = (request.form.get("uf", "").strip() or r["uf"]).upper()[:2]
    db.execute("UPDATE regioes SET nome = ?, uf = ? WHERE id = ?", (nome, uf, rid))
    flash("Região atualizada!", "ok")
    return redirect(url_for("admin_painel"))


@app.route("/admin/regiao/<int:rid>/excluir", methods=["POST"])
@admin_required
def admin_regiao_excluir(rid):
    r = db.query("SELECT nome, uf FROM regioes WHERE id = ?", (rid,), one=True)
    if not r:
        abort(404)
    em_uso = db.query("SELECT COUNT(*) AS n FROM prestadores WHERE regiao_id = ?", (rid,), one=True)["n"]
    if em_uso:
        flash(f"Não é possível excluir: {em_uso} prestador(es) ainda usam '{r['nome']}/{r['uf']}'.", "erro")
        return redirect(url_for("admin_painel"))
    db.execute("DELETE FROM regioes WHERE id = ?", (rid,))
    flash(f"Região '{r['nome']}/{r['uf']}' excluída.", "ok")
    return redirect(url_for("admin_painel"))


@app.route("/admin/prestador/<int:pid>/excluir", methods=["POST"])
@admin_required
def admin_prestador_excluir(pid):
    p = db.query("SELECT nome FROM prestadores WHERE id = ?", (pid,), one=True)
    if not p:
        abort(404)
    db.execute("DELETE FROM prestadores WHERE id = ?", (pid,))
    flash(f"Prestador '{p['nome']}' excluído.", "ok")
    return redirect(url_for("admin_painel"))


@app.route("/admin/prestador/<int:pid>/verificar", methods=["POST"])
@admin_required
def admin_verificar(pid):
    p = db.query("SELECT verificado FROM prestadores WHERE id = ?", (pid,), one=True)
    if not p:
        abort(404)
    novo = 0 if p["verificado"] else 1
    db.execute("UPDATE prestadores SET verificado = ? WHERE id = ?", (novo, pid))
    flash("Selo Verificado " + ("concedido." if novo else "removido."), "ok")
    return redirect(url_for("admin_painel"))


# ---------------------------------------------------------------- API (conector MCP)
# Autenticação por token (Authorization: Bearer), não por cookie de sessão —
# usada pelo conector do Claude, não pelo navegador.
@app.route("/api/login", methods=["POST"])
def api_login():
    dados = request.get_json(silent=True) or {}
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""
    u = db.query("SELECT * FROM usuarios WHERE email = ?", (email,), one=True)
    if not u or not check_password_hash(u["senha_hash"], senha):
        return jsonify({"ok": False, "erro": "e-mail ou senha inválidos"}), 401
    if u["papel"] != "admin":
        return jsonify({"ok": False, "erro": "esta conta não é admin"}), 403
    token = api_auth.emitir_token(u)
    return jsonify({"ok": True, "token": token, "nome": u["nome"], "papel": u["papel"]})


@app.route("/api/categorias")
@api_admin_required
def api_categorias():
    return jsonify([dict(c) for c in categorias()])


@app.route("/api/regioes")
@api_admin_required
def api_regioes():
    return jsonify([dict(r) for r in regioes()])


@app.route("/api/regioes", methods=["POST"])
@api_admin_required
def api_regioes_criar():
    dados = request.get_json(silent=True) or {}
    nome = (dados.get("nome") or "").strip()
    uf = (dados.get("uf") or "").strip()
    if not (nome and uf):
        return jsonify({"erro": "informe nome (cidade) e uf"}), 400
    existente = db.query(
        "SELECT id FROM regioes WHERE LOWER(nome) = LOWER(?) AND LOWER(uf) = LOWER(?)", (nome, uf), one=True
    )
    if existente:
        return jsonify({"ja_existia": True, "id": existente["id"], "nome": nome, "uf": uf.upper()})
    rid = obter_ou_criar_regiao(nome, uf)
    if not rid:
        return jsonify({"erro": "não foi possível criar — confira cidade e uf"}), 400
    return jsonify({"ok": True, "id": rid, "nome": nome, "uf": uf.upper()})


@app.route("/api/categorias", methods=["POST"])
@api_admin_required
def api_categorias_criar():
    dados = request.get_json(silent=True) or {}
    nome = (dados.get("nome") or "").strip()
    if not nome:
        return jsonify({"erro": "informe o nome da categoria"}), 400
    existente = _resolver_categoria_por_nome(nome)
    if existente:
        return jsonify({"ja_existia": True, "id": existente, "nome": nome})
    cid = obter_ou_criar_categoria(nome, dados.get("icone"))
    return jsonify({"ok": True, "id": cid, "nome": nome})


@app.route("/api/categorias/<int:cid>", methods=["PUT"])
@api_admin_required
def api_categoria_editar(cid):
    if not db.query("SELECT 1 FROM categorias WHERE id = ?", (cid,), one=True):
        return jsonify({"erro": "categoria não encontrada"}), 404
    dados = request.get_json(silent=True) or {}
    nome = (dados.get("nome") or "").strip()
    if not nome:
        return jsonify({"erro": "informe o nome"}), 400
    outra = db.query("SELECT 1 FROM categorias WHERE LOWER(nome) = LOWER(?) AND id != ?", (nome, cid), one=True)
    if outra:
        return jsonify({"erro": "já existe outra categoria com esse nome"}), 400
    icone = (dados.get("icone") or "").strip() or "🔧"
    db.execute("UPDATE categorias SET nome = ?, icone = ? WHERE id = ?", (nome, icone, cid))
    return jsonify({"ok": True, "id": cid, "nome": nome, "icone": icone})


@app.route("/api/categorias/<int:cid>", methods=["DELETE"])
@api_admin_required
def api_categoria_excluir(cid):
    cat = db.query("SELECT nome FROM categorias WHERE id = ?", (cid,), one=True)
    if not cat:
        return jsonify({"erro": "categoria não encontrada"}), 404
    em_uso = db.query("SELECT COUNT(*) AS n FROM prestadores WHERE categoria_id = ?", (cid,), one=True)["n"]
    if em_uso:
        return jsonify({"erro": f"{em_uso} prestador(es) ainda usam essa categoria — "
                                 f"mova-os para outra categoria antes de excluir"}), 409
    db.execute("DELETE FROM categorias WHERE id = ?", (cid,))
    return jsonify({"ok": True, "nome": cat["nome"]})


@app.route("/api/regioes/<int:rid>", methods=["PUT"])
@api_admin_required
def api_regiao_editar(rid):
    r = db.query("SELECT * FROM regioes WHERE id = ?", (rid,), one=True)
    if not r:
        return jsonify({"erro": "região não encontrada"}), 404
    dados = request.get_json(silent=True) or {}
    nome = (dados.get("nome") or r["nome"]).strip()
    uf = (dados.get("uf") or r["uf"]).strip().upper()[:2]
    db.execute("UPDATE regioes SET nome = ?, uf = ? WHERE id = ?", (nome, uf, rid))
    return jsonify({"ok": True, "id": rid, "nome": nome, "uf": uf})


@app.route("/api/regioes/<int:rid>", methods=["DELETE"])
@api_admin_required
def api_regiao_excluir(rid):
    r = db.query("SELECT nome, uf FROM regioes WHERE id = ?", (rid,), one=True)
    if not r:
        return jsonify({"erro": "região não encontrada"}), 404
    em_uso = db.query("SELECT COUNT(*) AS n FROM prestadores WHERE regiao_id = ?", (rid,), one=True)["n"]
    if em_uso:
        return jsonify({"erro": f"{em_uso} prestador(es) ainda usam essa região — "
                                 f"mova-os para outra região antes de excluir"}), 409
    db.execute("DELETE FROM regioes WHERE id = ?", (rid,))
    return jsonify({"ok": True, "nome": f"{r['nome']}/{r['uf']}"})


@app.route("/api/prestadores", methods=["GET"])
@api_admin_required
def api_prestadores_listar():
    busca = request.args.get("q", "").strip()
    cat = request.args.get("categoria", "").strip()
    reg = request.args.get("regiao", "").strip()
    try:
        limite = min(int(request.args.get("limite", 50)), 200)
    except ValueError:
        limite = 50

    sql = """
        SELECT p.*, c.nome AS categoria_nome, r.nome AS regiao_nome, r.uf AS regiao_uf,
               COUNT(a.id) AS n_avaliacoes, COALESCE(ROUND(AVG(a.nota),1),0) AS media
        FROM prestadores p
        JOIN categorias c ON c.id = p.categoria_id
        LEFT JOIN regioes r ON r.id = p.regiao_id
        LEFT JOIN avaliacoes a ON a.prestador_id = p.id AND a.status = 'aprovada'
        WHERE 1=1
    """
    params = []
    if busca:
        categorias_sinonimo = categorias_por_sinonimo(busca)
        busca_lower = busca.lower()
        if categorias_sinonimo:
            condicoes_cat = " OR ".join(["LOWER(c.nome) LIKE ?"] * len(categorias_sinonimo))
            sql += f" AND (LOWER(p.nome) LIKE ? OR LOWER(p.descricao) LIKE ? OR {condicoes_cat})"
            params += [f"%{busca_lower}%", f"%{busca_lower}%"] + [f"%{c.lower()}%" for c in categorias_sinonimo]
        else:
            sql += " AND (LOWER(p.nome) LIKE ? OR LOWER(p.descricao) LIKE ?)"
            params += [f"%{busca_lower}%", f"%{busca_lower}%"]
    if cat:
        sql += " AND LOWER(c.nome) LIKE ?"
        params.append(f"%{cat.lower()}%")
    if reg:
        sql += " AND (LOWER(r.nome) LIKE ? OR LOWER(r.uf) LIKE ?)"
        params += [f"%{reg.lower()}%", f"%{reg.lower()}%"]
    sql += " GROUP BY p.id, c.id, r.id ORDER BY p.nome LIMIT ?"
    params.append(limite)
    rows = db.query(sql, params)
    return jsonify([_prestador_enxuto(r) for r in rows])


@app.route("/api/prestadores", methods=["POST"])
@api_admin_required
def api_prestadores_criar():
    dados = request.get_json(silent=True) or {}
    nome = (dados.get("nome") or "").strip()
    categoria_nome = dados.get("categoria") or ""
    regiao_texto = dados.get("regiao") or ""
    forcar = bool(dados.get("forcar"))
    if not (nome and categoria_nome and regiao_texto):
        return jsonify({"erro": "informe nome, categoria e regiao (ex.: 'Sinop/MT')"}), 400

    categoria_id = _resolver_categoria_por_nome(categoria_nome)
    if not categoria_id:
        return jsonify({"erro": f"categoria '{categoria_nome}' não existe",
                        "opcoes": [c["nome"] for c in categorias()]}), 400

    nome_original = nome
    nome = garantir_nome_com_papel(nome, categoria_nome)

    cidade, uf = _parse_regiao_texto(regiao_texto)
    regiao_id = obter_ou_criar_regiao(cidade, uf)
    if not regiao_id:
        return jsonify({"erro": "região inválida — use o formato 'Cidade/UF'"}), 400

    if not forcar:
        existentes = db.query(
            "SELECT id, nome FROM prestadores WHERE regiao_id = ? AND LOWER(nome) = LOWER(?)",
            (regiao_id, nome),
        )
        if existentes:
            return jsonify({
                "ja_existia": True,
                "aviso": "Já existe prestador com esse nome nessa região — não criei outro. "
                         "Use forcar=true se quiser cadastrar mesmo assim.",
                "candidatos": [dict(e) for e in existentes],
            })

    pid = db.execute(
        """INSERT INTO prestadores (nome, categoria_id, regiao_id, telefone, whatsapp, descricao)
           VALUES (?,?,?,?,?,?)""",
        (nome, categoria_id, regiao_id, (dados.get("telefone") or "").strip(),
         (dados.get("whatsapp") or "").strip(), (dados.get("descricao") or "").strip()),
    )
    novo = db.query(
        """SELECT p.*, c.nome AS categoria_nome, r.nome AS regiao_nome, r.uf AS regiao_uf,
                  0 AS n_avaliacoes, 0 AS media
           FROM prestadores p JOIN categorias c ON c.id = p.categoria_id
           LEFT JOIN regioes r ON r.id = p.regiao_id WHERE p.id = ?""",
        (pid,), one=True,
    )
    if not novo:
        return jsonify({"erro": "falha ao gravar — tente de novo"}), 500
    resp = {"ok": True, "prestador": _prestador_enxuto(novo)}
    if nome != nome_original:
        resp["aviso"] = (f"nome ajustado de '{nome_original}' para '{nome}' — o card nunca "
                          f"mostra só o nome da pessoa, sempre a empresa ou a função antes")
    return jsonify(resp)


_CAMPOS_EDITAVEIS = ("nome", "telefone", "whatsapp", "descricao")


@app.route("/api/prestadores/<int:pid>", methods=["PUT"])
@api_admin_required
def api_prestadores_editar(pid):
    if not db.query("SELECT 1 FROM prestadores WHERE id = ?", (pid,), one=True):
        return jsonify({"erro": "prestador não encontrado"}), 404
    dados = request.get_json(silent=True) or {}
    sets, valores = [], []
    for campo in _CAMPOS_EDITAVEIS:
        if campo in dados:
            sets.append(f"{campo} = ?")
            valores.append((dados[campo] or "").strip())
    if "categoria" in dados:
        cid = _resolver_categoria_por_nome(dados["categoria"])
        if not cid:
            return jsonify({"erro": f"categoria '{dados['categoria']}' não existe",
                            "opcoes": [c["nome"] for c in categorias()]}), 400
        sets.append("categoria_id = ?")
        valores.append(cid)
    if "regiao" in dados:
        cidade, uf = _parse_regiao_texto(dados["regiao"])
        rid = obter_ou_criar_regiao(cidade, uf)
        if not rid:
            return jsonify({"erro": "região inválida — use o formato 'Cidade/UF'"}), 400
        sets.append("regiao_id = ?")
        valores.append(rid)
    if not sets:
        return jsonify({"erro": "nenhum campo válido para atualizar"}), 400
    valores.append(pid)
    db.execute(f"UPDATE prestadores SET {', '.join(sets)} WHERE id = ?", valores)
    atualizado = db.query(
        """SELECT p.*, c.nome AS categoria_nome, r.nome AS regiao_nome, r.uf AS regiao_uf,
                  (SELECT COUNT(*) FROM avaliacoes a WHERE a.prestador_id=p.id AND a.status='aprovada') AS n_avaliacoes,
                  (SELECT COALESCE(ROUND(AVG(nota),1),0) FROM avaliacoes a
                    WHERE a.prestador_id=p.id AND a.status='aprovada') AS media
           FROM prestadores p JOIN categorias c ON c.id = p.categoria_id
           LEFT JOIN regioes r ON r.id = p.regiao_id WHERE p.id = ?""",
        (pid,), one=True,
    )
    return jsonify({"ok": True, "prestador": _prestador_enxuto(atualizado)})


@app.route("/api/prestadores/<int:pid>", methods=["DELETE"])
@api_admin_required
def api_prestadores_excluir(pid):
    p = db.query("SELECT nome FROM prestadores WHERE id = ?", (pid,), one=True)
    if not p:
        return jsonify({"erro": "prestador não encontrado"}), 404
    db.execute("DELETE FROM prestadores WHERE id = ?", (pid,))
    return jsonify({"ok": True, "nome": p["nome"]})


@app.route("/api/avaliacoes/pendentes", methods=["GET"])
@api_admin_required
def api_avaliacoes_pendentes():
    try:
        limite = min(int(request.args.get("limite", 50)), 200)
    except ValueError:
        limite = 50
    rows = db.query(
        """SELECT a.id, a.autor, a.nota, a.comentario, a.criado_em,
                  p.id AS prestador_id, p.nome AS prestador_nome
           FROM avaliacoes a JOIN prestadores p ON p.id = a.prestador_id
           WHERE a.status = 'pendente' ORDER BY a.criado_em LIMIT ?""",
        (limite,),
    )
    return jsonify([{**dict(r), "criado_em": str(r["criado_em"])} for r in rows])


@app.route("/api/avaliacoes/<int:aid>/<acao>", methods=["POST"])
@api_admin_required
def api_avaliacao_moderar(aid, acao):
    if acao not in ("aprovar", "rejeitar"):
        return jsonify({"erro": "ação inválida — use aprovar ou rejeitar"}), 400
    if not db.query("SELECT 1 FROM avaliacoes WHERE id = ?", (aid,), one=True):
        return jsonify({"erro": "avaliação não encontrada"}), 404
    novo = "aprovada" if acao == "aprovar" else "rejeitada"
    db.execute("UPDATE avaliacoes SET status = ? WHERE id = ?", (novo, aid))
    return jsonify({"ok": True, "id": aid, "status": novo})


# ---------------------------------------------------------------- erros
@app.errorhandler(400)
def requisicao_invalida(e):
    return render_template("erro.html", codigo=400,
                           msg="Sessão expirada ou requisição inválida. Recarregue a página e tente de novo."), 400


@app.errorhandler(403)
def sem_permissao(e):
    return render_template("erro.html", codigo=403,
                           msg="Você não tem permissão para acessar esta página."), 403


@app.errorhandler(404)
def nao_encontrado(e):
    return render_template("erro.html", codigo=404,
                           msg="O que você procura não existe ou foi movido."), 404


@app.errorhandler(500)
def erro_interno(e):
    return render_template("erro.html", codigo=500,
                           msg="Algo deu errado do nosso lado. Tente de novo em um instante."), 500


# Inicialização executada tanto no dev server quanto sob gunicorn (--preload):
# cria as tabelas e garante categorias/admin (idempotente).
import seed  # noqa: E402
seed.run()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
