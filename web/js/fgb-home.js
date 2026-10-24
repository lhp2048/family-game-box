/**
 * fgb-home.js — home / library shelf (console product shell)
 * Depends on FGB.url from fgb-client.js
 */
(function (global) {
  "use strict";

  var COVER_ART = {
    "24points": { glyph: "24", accent: "#3ecf8e", accent2: "#1a9f68" },
    schulte: { glyph: "格", accent: "#45d498", accent2: "#159a64" },
    stroop: { glyph: "色", accent: "#6b9bff", accent2: "#3d6ad6" },
    cancel: { glyph: "划", accent: "#3ecf8e", accent2: "#1a9f68" },
    simon: { glyph: "听", accent: "#c084fc", accent2: "#9333ea" },
    "spot-diff": { glyph: "找", accent: "#38bdf8", accent2: "#0284c7" },
    maze: { glyph: "迷", accent: "#34d399", accent2: "#059669" },
    sudoku: { glyph: "数", accent: "#fbbf24", accent2: "#d97706" },
    yuwen: { glyph: "文", accent: "#f0c14a", accent2: "#c4922a" },
    "24points-library": { glyph: "库", accent: "#8fa399", accent2: "#5c6b63" },
  };

  function esc(s) {
    return String(s || "").replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function coverFor(gameId) {
    return COVER_ART[gameId] || { glyph: "玩", accent: "#3ecf8e", accent2: "#1a9f68" };
  }

  function url(path) {
    if (global.FGB && typeof FGB.url === "function") return FGB.url(path);
    return path;
  }

  /**
   * Render console-style cover tiles into listEl.
   * @param {HTMLElement} listEl
   * @param {Array<object>} games
   */
  function renderGameShelf(listEl, games) {
    if (!listEl) return;
    listEl.innerHTML = "";
    var items = games || [];
    items.forEach(function (g, index) {
      var art = coverFor(g.id);
      var isRef = g.extra && g.extra.kind === "reference";
      var path = g.path || "";
      var href = url(path.charAt(0) === "/" ? path : "/" + path);

      var a = document.createElement("a");
      a.className =
        "fgb-cover" +
        (isRef ? " is-ref" : "") +
        (g.extra && g.extra.kind === "reference" ? " is-muted" : "");
      a.setAttribute("data-game-id", g.id);
      a.setAttribute("role", "listitem");
      a.href = href;
      a.style.setProperty("--cover-a", art.accent);
      a.style.setProperty("--cover-b", art.accent2);
      a.innerHTML =
        '<span class="fgb-cover-art" aria-hidden="true"><span class="fgb-cover-glyph">' +
        esc(art.glyph) +
        "</span></span>" +
        '<span class="fgb-cover-body">' +
        '<strong class="fgb-cover-title">' +
        esc(g.title) +
        "</strong>" +
        '<span class="fgb-cover-meta">' +
        esc(g.subtitle || (isRef ? "工具" : "训练")) +
        "</span>" +
        '<span class="fgb-cover-cta">' +
        (isRef ? "查阅" : "开始") +
        "</span>" +
        "</span>";

      a.addEventListener("keydown", function (e) {
        if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
        var row = listEl.querySelectorAll(".fgb-cover");
        var i = -1;
        for (var j = 0; j < row.length; j++) {
          if (row[j] === a) {
            i = j;
            break;
          }
        }
        if (i < 0) return;
        var next = e.key === "ArrowRight" ? i + 1 : i - 1;
        if (next >= 0 && next < row.length) {
          e.preventDefault();
          row[next].focus();
        }
      });

      listEl.appendChild(a);
    });

    if (!items.length) {
      listEl.innerHTML = '<p class="fgb-lead fgb-shelf-empty">暂无可用游戏</p>';
    }
  }

  function mountClock(el) {
    if (!el) return;
    function tick() {
      var now = new Date();
      var h = String(now.getHours()).padStart(2, "0");
      var m = String(now.getMinutes()).padStart(2, "0");
      el.textContent = h + ":" + m;
    }
    tick();
    global.setInterval(tick, 30000);
  }

  global.FGBHome = {
    renderGameShelf: renderGameShelf,
    mountClock: mountClock,
    coverFor: coverFor,
  };
})(window);
