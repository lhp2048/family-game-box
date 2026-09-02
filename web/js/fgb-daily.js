(function (global) {
  "use strict";

  function parseQuery() {
    var q = new URLSearchParams(global.location.search || "");
    return {
      daily: q.get("daily") === "1",
      runId: q.get("runId") || "",
      tier: q.get("tier") || "",
      seed: Number(q.get("seed") || "0") || 0,
      stageIndex: Number(q.get("stageIndex") || "0") || 0,
    };
  }

  function makeRng(seed) {
    var t = (seed >>> 0) || 1;
    return function () {
      t += 0x6d2b79f5;
      var r = Math.imul(t ^ (t >>> 15), 1 | t);
      r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
      return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
  }

  function installMathRandom(seed) {
    var rng = makeRng(seed);
    var original = Math.random;
    Math.random = rng;
    return function restore() {
      Math.random = original;
    };
  }

  function notifyStageDone(timeMs) {
    if (global.parent && global.parent !== global) {
      global.parent.postMessage({ type: "fgb-daily-stage-done", timeMs: timeMs | 0 }, "*");
    }
  }

  function notifyAbort() {
    if (global.parent && global.parent !== global) {
      global.parent.postMessage({ type: "fgb-daily-abort" }, "*");
    }
  }

  var BOARD_SEL =
    "[data-fgb-board], .clover, .sudoku-wrap, .maze-wrap, .grid-wrap, .diff-panels, .board";

  function isVisible(el) {
    if (!el) return false;
    if (el.classList && el.classList.contains("hidden")) return false;
    var st = global.getComputedStyle(el);
    return st.display !== "none" && st.visibility !== "hidden";
  }

  function boxH(el) {
    if (!isVisible(el)) return 0;
    var st = global.getComputedStyle(el);
    var r = el.getBoundingClientRect();
    return (
      r.height +
      (parseFloat(st.marginTop) || 0) +
      (parseFloat(st.marginBottom) || 0)
    );
  }

  /**
   * 按视口动态计算对局主区域边长写入 --fgb-board。
   * 能放下则禁用滚动；低于 min 则用 min 并允许滚动。
   */
  function fitPlay(opts) {
    opts = opts || {};
    var root = document.documentElement;
    if (!root.classList.contains("fgb-daily-mode") && !opts.force) return null;

    var play = document.getElementById("view-play");
    if (!play || !isVisible(play)) return null;

    var vh = global.innerHeight || root.clientHeight || 0;
    var vw = global.innerWidth || root.clientWidth || 0;
    if (vh < 80) return null;

    var board = play.querySelector(opts.boardSelector || BOARD_SEL);
    if (!board) {
      var tall = (document.documentElement.scrollHeight || 0) > vh + 4;
      root.classList.toggle("fgb-play-scroll", tall);
      root.style.overflowY = tall ? "auto" : "hidden";
      if (document.body) document.body.style.overflowY = tall ? "auto" : "hidden";
      return null;
    }

    var reserved = 0;
    var i;
    var kids = play.children;
    for (i = 0; i < kids.length; i++) {
      var el = kids[i];
      if (board && (el === board || el.contains(board))) {
        var j;
        var sub = el.children;
        for (j = 0; j < sub.length; j++) {
          var c = sub[j];
          if (board && (c === board || c.contains(board))) continue;
          reserved += boxH(c);
        }
        var cst = global.getComputedStyle(el);
        reserved +=
          (parseFloat(cst.paddingTop) || 0) + (parseFloat(cst.paddingBottom) || 0);
        continue;
      }
      reserved += boxH(el);
    }

    var wrap = play.closest(".wrap") || document.querySelector(".wrap");
    if (wrap) {
      var wst = global.getComputedStyle(wrap);
      reserved +=
        (parseFloat(wst.paddingTop) || 0) + (parseFloat(wst.paddingBottom) || 0);
    }

    var pad = opts.pad != null ? opts.pad : 16;
    var minB = opts.min != null ? opts.min : 168;
    var maxB = opts.max != null ? opts.max : 480;
    maxB = Math.min(maxB, Math.floor(vw * 0.92));

    var avail = Math.floor(vh - reserved - pad);
    var needScroll = avail < minB;
    var size = needScroll ? minB : Math.min(maxB, avail);
    if (size < 1) size = minB;

    root.style.setProperty("--fgb-board", size + "px");
    root.classList.toggle("fgb-play-scroll", needScroll);
    root.style.overflowY = needScroll ? "auto" : "hidden";
    if (document.body) document.body.style.overflowY = needScroll ? "auto" : "hidden";
    return size;
  }

  var fitTimer = null;
  function scheduleFitPlay(opts) {
    if (fitTimer) global.clearTimeout(fitTimer);
    fitTimer = global.setTimeout(function () {
      fitTimer = null;
      fitPlay(opts);
    }, 16);
  }

  function installFitPlay(opts) {
    function run() {
      scheduleFitPlay(opts);
    }
    run();
    [50, 120, 300, 600, 1200].forEach(function (ms) {
      global.setTimeout(run, ms);
    });
    global.addEventListener("resize", run);
    global.addEventListener("orientationchange", function () {
      global.setTimeout(run, 100);
      global.setTimeout(run, 400);
    });
    if (global.visualViewport) {
      global.visualViewport.addEventListener("resize", run);
    }
    var play = document.getElementById("view-play");
    if (play && global.MutationObserver) {
      new MutationObserver(run).observe(play, {
        attributes: true,
        attributeFilter: ["class", "style"],
        childList: true,
        subtree: true,
      });
    }
  }

  global.FGBDaily = {
    parseQuery: parseQuery,
    isDaily: function () {
      return parseQuery().daily;
    },
    makeRng: makeRng,
    installMathRandom: installMathRandom,
    notifyStageDone: notifyStageDone,
    notifyAbort: notifyAbort,
    fitPlay: fitPlay,
    scheduleFitPlay: scheduleFitPlay,
    installFitPlay: installFitPlay,
  };
})(window);
