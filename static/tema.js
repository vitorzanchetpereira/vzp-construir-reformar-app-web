/*
 * Tema claro/escuro/sistema.
 *
 * "Sistema" (padrão, sem escolha salva) é 100% CSS — @media
 * (prefers-color-scheme) no style.css, funciona até sem JS.
 *
 * Uma escolha manual (claro/escuro) precisa vencer a preferência do
 * sistema. Descobrimos ao testar que só marcar um atributo em <html> e
 * deixar o CSS reagir por seletor (":root:not([data-tema=...])" dentro
 * de "@media") nem sempre recalcula a tela na hora nesse motor de
 * navegador — só depois de recarregar. Por isso a escolha manual seta
 * as variáveis direto (style.setProperty), que sempre atualiza
 * corretamente. O atributo data-tema continua servindo pra CSS estático
 * (ex.: [data-tema="escuro"] em style.css) e pra saber qual botão
 * marcar como ativo.
 */
(function (global) {
  var VARS = [
    "--laranja", "--laranja-esc", "--azul", "--azul-claro",
    "--tinta", "--cinza", "--cinza-claro", "--linha", "--fundo",
    "--branco", "--superficie-sutil", "--verde", "--verde-zap",
    "--sombra", "--sombra-alta",
    "--chip-azul-bg", "--chip-azul-fg", "--chip-azul-borda",
    "--chip-verde-bg", "--chip-verde-fg", "--chip-verde-borda",
    "--chip-ok-bg", "--chip-ok-fg", "--chip-ok-borda",
    "--chip-erro-bg", "--chip-erro-fg", "--chip-erro-borda",
    "--chip-alerta-bg", "--chip-alerta-fg", "--chip-alerta-borda",
    "--chip-cinza-bg", "--chip-cinza-fg", "--chip-cinza-borda",
  ];

  var CLARO = [
    "#f2711c", "#d65f11", "#1f3a5f", "#2b5f8f",
    "#1c2530", "#5b6673", "#8a94a1", "#e7eaef", "#f5f7fa",
    "#fff", "#f8fafc", "#1f9d55", "#25d366",
    "0 2px 10px rgba(28,37,48,.06)", "0 8px 26px rgba(28,37,48,.10)",
    "#e8f4ff", "#2b5f8f", "#cfe6fb",
    "#eef7f0", "#1f9d55", "#cdeed6",
    "#e6f7ee", "#0f7a3d", "#b7e6cb",
    "#fdecec", "#c0392b", "#f4c4c0",
    "#fff3e0", "#b25a00", "#f6d9bd",
    "#eef1f5", "#8a94a1", "#e7eaef",
  ];

  var ESCURO = [
    "#ff8a4a", "#ff9d64", "#7fb0e8", "#9cc4f0",
    "#e9edf2", "#a8b1bd", "#7e8794", "#2a333f", "#0f141b",
    "#182029", "#1d2632", "#3ecb7c", "#25d366",
    "0 2px 10px rgba(0,0,0,.35)", "0 8px 26px rgba(0,0,0,.45)",
    "#1c2f42", "#9cc4f0", "#2c4a68",
    "#173627", "#3ecb7c", "#20573c",
    "#173626", "#59d693", "#1f5738",
    "#3a1d1d", "#f28b82", "#5c2b2b",
    "#3a2a12", "#f2ab5c", "#5c4420",
    "#232c37", "#8f98a5", "#2a333f",
  ];

  function aplicarTema(tema) {
    var raiz = document.documentElement.style;
    if (tema === "claro" || tema === "escuro") {
      var valores = tema === "claro" ? CLARO : ESCURO;
      VARS.forEach(function (nome, i) {
        raiz.setProperty(nome, valores[i]);
      });
      document.documentElement.setAttribute("data-tema", tema);
    } else {
      VARS.forEach(function (nome) {
        raiz.removeProperty(nome);
      });
      document.documentElement.removeAttribute("data-tema");
    }
  }

  function escolherTema(tema) {
    if (tema === "sistema") {
      localStorage.removeItem("tema");
    } else {
      localStorage.setItem("tema", tema);
    }
    aplicarTema(tema);
  }

  global.Tema = { aplicar: aplicarTema, escolher: escolherTema, obterAtual: function () {
    return localStorage.getItem("tema") || "sistema";
  } };

  aplicarTema(global.Tema.obterAtual());
})(window);
