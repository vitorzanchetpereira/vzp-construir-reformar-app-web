"""
Popula o banco. Idempotente e seguro para produção:
  • categorias e conta admin são sempre garantidas (checa antes de inserir);
  • dados de demonstração (prestadores/avaliações/conta demo) só entram se
    SEED_DEMO != "0" e ainda não houver prestadores.

Admin de produção vem das variáveis de ambiente ADMIN_EMAIL / ADMIN_SENHA.
"""
import os
import db
from werkzeug.security import generate_password_hash

CATEGORIAS = [
    ("Pedreiro / Alvenaria", "pedreiro", "🧱"),
    ("Eletricista", "eletricista", "⚡"),
    ("Encanador / Hidráulica", "encanador", "🚿"),
    ("Pintor", "pintor", "🎨"),
    ("Marceneiro / Móveis", "marceneiro", "🪚"),
    ("Serralheiro / Estruturas", "serralheiro", "🔩"),
    ("Terraplenagem / Máquinas", "terraplenagem", "🚜"),
    ("Locação de Equipamentos", "locacao", "🏗️"),
    ("Gesso / Drywall", "gesso", "🧰"),
    ("Projeto e Engenharia", "engenharia", "📐"),
    ("Materiais de Construção", "materiais", "🏬"),
    ("Limpeza Pós-Obra", "limpeza", "🧹"),
]

PRESTADORES = [
    ("Construtora Nova Era", "pedreiro", "(66) 3544-1010", "5566991110010",
     "Equipe de alvenaria estrutural e acabamento. Atende obras residenciais e comerciais em Sorriso e região.", 1),
    ("Elétrica Sorriso", "eletricista", "(66) 3544-2020", "5566992220020",
     "Instalações elétricas prediais, quadros de distribuição e laudos. Atendimento 24h para emergências.", 1),
    ("Hidro Center Norte", "encanador", "(66) 3544-3030", "5566993330030",
     "Hidráulica predial, caça-vazamento e instalação de sistemas de reuso de água.", 0),
    ("Pinturas Colorir", "pintor", "(66) 3544-4040", "5566994440040",
     "Pintura residencial, texturas e efeitos. Orçamento sem compromisso.", 0),
    ("Marcenaria do Vale", "marceneiro", "(66) 3544-5050", "5566995550050",
     "Móveis planejados sob medida em MDF. Cozinhas, closets e ambientes corporativos.", 1),
    ("Serralheria MT Aço", "serralheiro", "(66) 3544-6060", "5566996660060",
     "Estruturas metálicas, portões, guarda-corpos e coberturas. Projeto e montagem.", 0),
    ("Terraplanagem Boa Terra", "terraplenagem", "(66) 3544-7070", "5566997770070",
     "Escavadeira, retroescavadeira e caminhão basculante. Preparação de terreno e drenagem.", 1),
    ("Loca Fácil Equipamentos", "locacao", "(66) 3544-8080", "5566998880080",
     "Betoneiras, andaimes, compactadores e geradores para locação diária ou mensal.", 0),
    ("Gesso & Forro Premium", "gesso", "(66) 3544-9090", "5566999990090",
     "Forro de gesso, drywall, sancas e molduras. Acabamento de alto padrão.", 0),
    ("VZP Engenharia", "engenharia", "(66) 3544-0001", "5566990000001",
     "Projetos, orçamentos, gerenciamento e medição de obras. Fiscalização e ART.", 1),
    ("Casa Forte Materiais", "materiais", "(66) 3544-0002", "5566990000002",
     "Cimento, aço, blocos e acabamentos. Entrega no canteiro em toda a região de Sorriso.", 1),
    ("Brilho Final Limpeza", "limpeza", "(66) 3544-0003", "5566990000003",
     "Limpeza pesada pós-obra, remoção de entulho e polimento de pisos.", 0),
]

AVALIACOES = [
    ("Construtora Nova Era", "João M.", 5, "Entregaram a obra no prazo e com acabamento impecável.", "aprovada"),
    ("Construtora Nova Era", "Ana P.", 4, "Bom serviço, só atrasou um pouco por causa da chuva.", "aprovada"),
    ("Elétrica Sorriso", "Carlos R.", 5, "Resolveram uma emergência à noite. Recomendo demais.", "aprovada"),
    ("Elétrica Sorriso", "Marina S.", 5, "Profissionais e pontuais.", "aprovada"),
    ("Marcenaria do Vale", "Fernanda L.", 5, "Cozinha planejada ficou perfeita.", "aprovada"),
    ("Terraplanagem Boa Terra", "Roberto A.", 4, "Serviço pesado bem executado.", "aprovada"),
    ("VZP Engenharia", "Construtora Alfa", 5, "Gerenciamento e medição muito bem feitos, sem surpresas.", "aprovada"),
    ("Casa Forte Materiais", "Pedro G.", 4, "Entrega rápida no canteiro.", "aprovada"),
    ("Hidro Center Norte", "Lucas T.", 4, "Acharam o vazamento que ninguém tinha achado.", "aprovada"),
    ("Pinturas Colorir", "Sandra M.", 5, "Pintaram minha casa toda, ficou ótimo!", "pendente"),
    ("Serralheria MT Aço", "Anônimo", 1, "spam spam compre já www.exemplo", "pendente"),
]


def ensure_categorias():
    for nome, slug, icone in CATEGORIAS:
        if not db.query("SELECT 1 FROM categorias WHERE slug = ?", (slug,), one=True):
            db.execute("INSERT INTO categorias (nome, slug, icone) VALUES (?,?,?)", (nome, slug, icone))


def ensure_admin():
    email = os.environ.get("ADMIN_EMAIL", "admin@vzphub.local").strip().lower()
    senha = os.environ.get("ADMIN_SENHA", "admin123")
    if not db.query("SELECT 1 FROM usuarios WHERE email = ?", (email,), one=True):
        db.execute(
            "INSERT INTO usuarios (email, senha_hash, papel) VALUES (?,?, 'admin')",
            (email, generate_password_hash(senha)),
        )


def seed_demo():
    cat_id = {r["slug"]: r["id"] for r in db.query("SELECT id, slug FROM categorias")}
    prest_id = {}
    for nome, slug, tel, wpp, desc, verif in PRESTADORES:
        prest_id[nome] = db.execute(
            """INSERT INTO prestadores (nome, categoria_id, cidade, telefone, whatsapp, descricao, verificado)
               VALUES (?,?,?,?,?,?,?)""",
            (nome, cat_id[slug], "Sorriso/MT", tel, wpp, desc, verif),
        )
    for pnome, autor, nota, coment, status in AVALIACOES:
        db.execute(
            "INSERT INTO avaliacoes (prestador_id, autor, nota, comentario, status) VALUES (?,?,?,?,?)",
            (prest_id[pnome], autor, nota, coment, status),
        )
    # conta de prestador para demonstração
    if not db.query("SELECT 1 FROM usuarios WHERE email = ?", ("demo@vzphub.local",), one=True):
        db.execute(
            "INSERT INTO usuarios (email, senha_hash, papel, prestador_id) VALUES (?,?, 'prestador', ?)",
            ("demo@vzphub.local", generate_password_hash("demo123"), prest_id["Pinturas Colorir"]),
        )


def run():
    db.init_db()
    ensure_categorias()
    ensure_admin()
    tem_prestadores = db.query("SELECT COUNT(*) AS n FROM prestadores", one=True)["n"] > 0
    if os.environ.get("SEED_DEMO", "1") != "0" and not tem_prestadores:
        seed_demo()
        print("Seed: categorias + admin + dados de demonstração.")
    else:
        print("Seed: categorias + admin garantidos (sem demo).")


if __name__ == "__main__":
    run()
