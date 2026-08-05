"""
Construir & Reformar — MVP.
Fase 1: diretório da oferta.  Fase 2: login do prestador, painel e moderação de avaliações.
Fase "robusto": fotos (Cloudinary), contas de cliente/indicação, multi-região, PWA.
VZP Engenharia / Base Empreendimentos.
"""
import os
import re
import secrets
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, abort, session)
from werkzeug.security import generate_password_hash, check_password_hash
import db
import uploads

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-troque-em-producao")


@app.template_filter("data")
def _fmt_data(valor, n=10):
    """Formata data/hora de forma agnóstica ao banco (SQLite=texto, Postgres=datetime)."""
    return str(valor)[:n] if valor else ""


@app.before_request
def csrf_protect():
    """Gera um token de sessão e valida todo POST (proteção CSRF)."""
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    if request.method == "POST":
        enviado = request.form.get("_csrf", "")
        if not enviado or enviado != session.get("csrf"):
            abort(400)


# ---------------------------------------------------------------- helpers
def categorias():
    return db.query("SELECT * FROM categorias ORDER BY nome")


def regioes():
    return db.query("SELECT * FROM regioes ORDER BY nome")


def _slugify(*partes):
    texto = " ".join(partes).lower()
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return texto


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
    if busca:
        sql += " AND (p.nome LIKE ? OR p.descricao LIKE ?)"
        params += [f"%{busca}%", f"%{busca}%"]
    if cat_slug:
        sql += " AND c.slug = ?"
        params.append(cat_slug)
    if regiao_slug:
        sql += " AND r.slug = ?"
        params.append(regiao_slug)
    if verificado == "1":
        sql += " AND p.verificado = 1"
    sql += " GROUP BY p.id, c.id, r.id ORDER BY p.verificado DESC, media DESC, n_avaliacoes DESC, p.nome"

    rows = db.query(sql, params)
    cat_atual = db.query("SELECT * FROM categorias WHERE slug = ?", (cat_slug,), one=True) if cat_slug else None
    regiao_atual = db.query("SELECT * FROM regioes WHERE slug = ?", (regiao_slug,), one=True) if regiao_slug else None
    return render_template("prestadores.html", prestadores=rows, busca=busca,
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
    foto_url = uploads.upload_imagem(request.files.get("foto"))
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


@app.route("/painel/editar", methods=["GET", "POST"])
@prestador_required
def painel_editar():
    u = usuario_atual()
    pid = u["prestador_id"]
    if request.method == "POST":
        f = request.form
        nome = f.get("nome", "").strip()
        categoria_id = f.get("categoria_id", "")
        regiao_id = resolver_regiao(f)
        if not (nome and categoria_id and regiao_id):
            flash("Nome, categoria e região são obrigatórios.", "erro")
            return redirect(url_for("painel_editar"))
        campos = "nome=?, categoria_id=?, regiao_id=?, telefone=?, whatsapp=?, descricao=?"
        valores = [nome, categoria_id, regiao_id, f.get("telefone", "").strip(),
                   f.get("whatsapp", "").strip(), f.get("descricao", "").strip()]
        foto_url = uploads.upload_imagem(request.files.get("foto"))
        if foto_url:
            campos += ", foto_url=?"
            valores.append(foto_url)
        valores.append(pid)
        db.execute(f"UPDATE prestadores SET {campos} WHERE id=?", valores)
        flash("Perfil atualizado!", "ok")
        return redirect(url_for("painel"))
    p = db.query("SELECT * FROM prestadores WHERE id = ?", (pid,), one=True)
    return render_template("painel_editar.html", p=p)


@app.route("/painel/fotos", methods=["POST"])
@prestador_required
def painel_fotos_adicionar():
    u = usuario_atual()
    foto_url = uploads.upload_imagem(request.files.get("foto"))
    if foto_url:
        db.execute("INSERT INTO prestador_fotos (prestador_id, url) VALUES (?,?)", (u["prestador_id"], foto_url))
        flash("Foto adicionada à galeria!", "ok")
    else:
        flash("Não foi possível enviar a foto. Confira o arquivo (imagem, até 5MB) e tente de novo.", "erro")
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


# Inicialização executada tanto no dev server quanto sob gunicorn (--preload):
# cria as tabelas e garante categorias/admin (idempotente).
import seed  # noqa: E402
seed.run()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
