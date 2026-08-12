// Mostra os campos de "outra cidade" só quando o select de região está em "__nova__".
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("[data-regiao-select]").forEach(function (select) {
    var caixa = document.querySelector(select.dataset.regiaoSelect);
    if (!caixa) return;
    function atualizar() {
      caixa.classList.toggle("visivel", select.value === "__nova__");
    }
    select.addEventListener("change", atualizar);
    atualizar();
  });
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/static/sw.js");
  });
}

// Tema claro/escuro/sistema — a aplicação de verdade (variáveis CSS) mora
// em tema.js, carregado no <head> antes do primeiro paint. Aqui só cuida
// do menu (abrir/fechar) e de manter o botão marcado com a escolha atual.
document.addEventListener("DOMContentLoaded", function () {
  var botao = document.getElementById("tema-botao");
  var opcoes = document.getElementById("tema-opcoes");
  var menu = document.getElementById("tema-menu");
  if (!botao || !opcoes || !menu || !window.Tema) return;

  function marcarAtivo() {
    var atual = Tema.obterAtual();
    opcoes.querySelectorAll("[data-tema-opcao]").forEach(function (b) {
      b.classList.toggle("ativo", b.dataset.temaOpcao === atual);
    });
  }

  function fechar() {
    opcoes.classList.remove("aberto");
    botao.setAttribute("aria-expanded", "false");
  }

  botao.addEventListener("click", function (ev) {
    ev.stopPropagation();
    var vaiAbrir = !opcoes.classList.contains("aberto");
    opcoes.classList.toggle("aberto", vaiAbrir);
    botao.setAttribute("aria-expanded", String(vaiAbrir));
  });

  opcoes.querySelectorAll("[data-tema-opcao]").forEach(function (b) {
    b.addEventListener("click", function () {
      Tema.escolher(b.dataset.temaOpcao);
      marcarAtivo();
      fechar();
    });
  });

  document.addEventListener("click", function (ev) {
    if (!menu.contains(ev.target)) fechar();
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") fechar();
  });

  marcarAtivo();
});
