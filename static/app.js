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
