// AvoControl ERP — comportamiento mínimo de la interfaz (sin dependencias)
(function () {
  var root = document.documentElement;
  var KEY = "avocontrol.sidebar";

  function guardar(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest("[data-toggle-sidebar]");
    if (btn) {
      if (window.matchMedia("(max-width: 900px)").matches) {
        root.classList.toggle("sidebar-open");
      } else {
        var col = root.classList.toggle("sidebar-collapsed");
        guardar(col ? "collapsed" : "open");
      }
      return;
    }
    // En móvil, tocar fuera del menú lo cierra
    if (root.classList.contains("sidebar-open") && !ev.target.closest(".sidebar")) {
      root.classList.remove("sidebar-open");
    }

    var reveal = ev.target.closest("[data-reveal]");
    if (reveal) {
      var input = document.getElementById(reveal.getAttribute("data-reveal"));
      var visible = input.type === "text";
      input.type = visible ? "password" : "text";
      reveal.setAttribute("aria-label", visible ? "Mostrar contraseña" : "Ocultar contraseña");
    }
  });

  // Evita doble envío de formularios (doble clic en "Guardar")
  document.addEventListener("submit", function (ev) {
    var b = ev.target.querySelector("button[type=submit]");
    if (b) { setTimeout(function () { b.disabled = true; }, 0); }
  });
})();
