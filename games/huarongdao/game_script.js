/* global HRD_LAYOUTS, Klotski, FGBUI, FGBShell, fgbSubmitScore, celebrate, askConfirm, fmtTime */
(function () {
  "use strict";

  var ROWS = 5;
  var COLS = 4;
  var BOARD_PAD = 3;
  var BOARD_GAP = 0.55;
  var ESC = (HRD_LAYOUTS && HRD_LAYOUTS.escape) || { row: 3, col: 1 };
  var LEVELS = (HRD_LAYOUTS && HRD_LAYOUTS.layouts) || [];

  var views = {
    home: document.getElementById("view-home"),
    pick: document.getElementById("view-pick"),
    play: document.getElementById("view-play"),
    result: document.getElementById("view-result"),
  };

  var mode = "campaign";
  var levelId = "";
  var levelMeta = null;
  var pieces = [];
  var steps = 0;
  var startedAt = 0;
  var playing = false;
  var selectedId = null;
  var undoStack = [];
  var drag = null;
  var campaignUnlock = 1;

  function loadUnlock() {
    try {
      var n = parseInt(localStorage.getItem("hrg-campaign-unlock") || "1", 10);
      campaignUnlock = isNaN(n) ? 1 : Math.max(1, Math.min(18, n));
    } catch (e) {
      campaignUnlock = 1;
    }
  }

  function saveUnlock(n) {
    campaignUnlock = Math.max(campaignUnlock, n);
    try {
      localStorage.setItem("hrg-campaign-unlock", String(campaignUnlock));
    } catch (e) {}
  }

  function show(name) {
    Object.keys(views).forEach(function (k) {
      views[k].classList.toggle("hidden", k !== name);
    });
  }

  function levelsFor(m) {
    return LEVELS.filter(function (lv) {
      return lv.mode === m;
    });
  }

  function findLevel(id) {
    for (var i = 0; i < LEVELS.length; i++) {
      if (LEVELS[i].id === id) return LEVELS[i];
    }
    return null;
  }

  function clonePieces(src) {
    return src.map(function (p) {
      return {
        id: p.id,
        type: p.type,
        label: p.label,
        r: p.r,
        c: p.c,
        w: p.w,
        h: p.h,
      };
    });
  }

  function snapshot() {
    return JSON.stringify(clonePieces(pieces));
  }

  function restore(snap) {
    pieces = JSON.parse(snap);
  }

  function isWin() {
    var cao = pieces.filter(function (p) {
      return p.type === "cao";
    })[0];
    return cao && cao.r === ESC.row && cao.c === ESC.col;
  }

  function occupancy(excludeId) {
    var grid = [];
    var r, c;
    for (r = 0; r < ROWS; r++) {
      grid[r] = [];
      for (c = 0; c < COLS; c++) grid[r][c] = -1;
    }
    pieces.forEach(function (p, idx) {
      if (p.id === excludeId) return;
      for (r = 0; r < p.h; r++) {
        for (c = 0; c < p.w; c++) {
          grid[p.r + r][p.c + c] = idx;
        }
      }
    });
    return grid;
  }

  function canPlace(p, nr, nc, excludeId) {
    if (nr < 0 || nc < 0 || nr + p.h > ROWS || nc + p.w > COLS) return false;
    var grid = occupancy(excludeId);
    var r, c;
    for (r = 0; r < p.h; r++) {
      for (c = 0; c < p.w; c++) {
        if (grid[nr + r][nc + c] !== -1) return false;
      }
    }
    return true;
  }

  function pieceAt(nr, nc) {
    for (var i = 0; i < pieces.length; i++) {
      var p = pieces[i];
      if (nr >= p.r && nr < p.r + p.h && nc >= p.c && nc < p.c + p.w) return p;
    }
    return null;
  }

  function tryMovePiece(id, dr, dc) {
    var p = pieces.filter(function (x) {
      return x.id === id;
    })[0];
    if (!p) return false;
    var nr = p.r + dr;
    var nc = p.c + dc;
    if (!canPlace(p, nr, nc, id)) return false;
    p.r = nr;
    p.c = nc;
    return true;
  }

  function slideSelected(dr, dc) {
    if (!selectedId || !playing) return false;
    var moved = false;
    while (tryMovePiece(selectedId, dr, dc)) moved = true;
    return moved;
  }

  function piecesToBlocks() {
    return pieces.map(function (p) {
      return { shape: [p.h, p.w], position: [p.r, p.c] };
    });
  }

  function pieceBySolverIndex(blockIdx) {
    return pieces[blockIdx] || null;
  }

  function macroCount(moves) {
    if (!moves || !moves.length) return 0;
    var macro = 0;
    var last = -1;
    moves.forEach(function (m) {
      if (m.blockIdx !== last) macro += 1;
      last = m.blockIdx;
    });
    return macro;
  }

  function boardRect(r, c, w, h) {
    var innerW = 100 - 2 * BOARD_PAD - BOARD_GAP * (COLS - 1);
    var innerH = 100 - 2 * BOARD_PAD - BOARD_GAP * (ROWS - 1);
    var cellW = innerW / COLS;
    var cellH = innerH / ROWS;
    return {
      left: BOARD_PAD + c * (cellW + BOARD_GAP),
      top: BOARD_PAD + r * (cellH + BOARD_GAP),
      width: w * cellW + (w - 1) * BOARD_GAP,
      height: h * cellH + (h - 1) * BOARD_GAP,
    };
  }

  function applyBoardRect(el, rect) {
    el.style.left = rect.left + "%";
    el.style.top = rect.top + "%";
    el.style.width = rect.width + "%";
    el.style.height = rect.height + "%";
  }

  function renderBoard() {
    var board = document.getElementById("hrg-board");
    if (!board) return;
    board.innerHTML = "";
    var exit = document.createElement("div");
    exit.className = "hrg-exit";
    exit.setAttribute("aria-hidden", "true");
    exit.textContent = "出口";
    applyBoardRect(exit, boardRect(4, 1, 2, 1));
    board.appendChild(exit);

    pieces.forEach(function (p) {
      var el = document.createElement("button");
      el.type = "button";
      el.className =
        "hrg-piece hrg-" +
        p.type +
        (p.id === selectedId ? " is-selected" : "");
      el.dataset.id = p.id;
      applyBoardRect(el, boardRect(p.r, p.c, p.w, p.h));
      el.innerHTML =
        '<span class="hrg-piece-label">' + (p.label || "") + "</span>";
      board.appendChild(el);
    });
  }

  function updateHud() {
    var meta = document.getElementById("hrg-meta");
    var st = document.getElementById("hrg-steps");
    if (st) st.textContent = String(steps);
    if (meta && levelMeta) {
      meta.textContent =
        levelMeta.name +
        " · 最少 " +
        levelMeta.optimal +
        " 步 · 已走 " +
        steps +
        " 步";
    }
  }

  function starsFor(optimal, used) {
    if (used <= optimal * 1.2) return 3;
    if (used <= optimal * 2) return 2;
    return 1;
  }

  function finish() {
    playing = false;
    var elapsed = Date.now() - startedAt;
    var stars = starsFor(levelMeta.optimal, steps);
    document.getElementById("res-steps").textContent = String(steps);
    document.getElementById("res-opt").textContent = String(levelMeta.optimal);
    document.getElementById("res-stars").textContent =
      "★".repeat(stars) + "☆".repeat(3 - stars);
    document.getElementById("res-time").textContent = fmtTime(elapsed);
    show("result");
    celebrate(typeof FGB_MSG !== "undefined" ? FGB_MSG.done : "完成！");
    if (mode === "campaign") {
      var num = parseInt(levelId.replace("camp-", ""), 10);
      if (!isNaN(num) && num >= campaignUnlock) saveUnlock(num + 1);
    }
    if (typeof fgbSubmitScore === "function") {
      fgbSubmitScore({
        gameId: "huarongdao",
        mode: mode === "campaign" ? "challenge" : "casual",
        tier: levelId,
        tierLabel: levelMeta.name,
        metrics: {
          timeMs: elapsed,
          moves: steps,
          done: 1,
          total: 1,
          stars: stars,
        },
      });
    }
  }

  function pushUndo() {
    undoStack.push(snapshot());
  }

  function onMoved(didMove) {
    if (!didMove) return;
    steps += 1;
    updateHud();
    renderBoard();
    if (isWin()) finish();
  }

  function beginLevel(id) {
    levelMeta = findLevel(id);
    if (!levelMeta) return;
    levelId = id;
    pieces = clonePieces(levelMeta.pieces);
    steps = 0;
    undoStack = [];
    selectedId = null;
    playing = true;
    startedAt = Date.now();
    document.getElementById("play-title").textContent = levelMeta.name;
    updateHud();
    renderBoard();
    show("play");
  }

  function renderPickList() {
    var list = document.getElementById("level-list");
    if (!list) return;
    list.innerHTML = "";
    var items = levelsFor(mode);
    items.forEach(function (lv, idx) {
      var locked =
        mode === "campaign" && idx + 1 > campaignUnlock;
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "hrg-level-btn" + (locked ? " is-locked" : "");
      btn.disabled = locked;
      btn.innerHTML =
        "<strong>" +
        lv.name +
        "</strong><span>最少 " +
        lv.optimal +
        " 步" +
        (lv.verifiedMacro != null
          ? " · 验证 " + lv.verifiedMacro
          : "") +
        "</span>";
      btn.addEventListener("click", function () {
        if (!locked) beginLevel(lv.id);
      });
      list.appendChild(btn);
    });
  }

  function blocksForSolver() {
    return piecesToBlocks();
  }

  function showHint() {
    if (!playing || typeof Klotski === "undefined") return;
    var k = new Klotski();
    var moves = k.solve({ blocks: blocksForSolver() });
    if (!moves || !moves.length) {
      document.getElementById("hrg-hint").textContent = "暂无解法提示";
      return;
    }
    var m = moves[0];
    var p = pieceBySolverIndex(m.blockIdx);
    if (p) selectedId = p.id;
    var names = ["下", "右", "上", "左"];
    document.getElementById("hrg-hint").textContent =
      "提示：移动「" + (p ? p.label : "") + "」向" + names[m.dirIdx];
    renderBoard();
  }

  function bindBoard() {
    var board = document.getElementById("hrg-board");
    if (!board) return;

    board.addEventListener("click", function (e) {
      var t = e.target.closest(".hrg-piece");
      if (!t || !playing) return;
      selectedId = t.dataset.id;
      renderBoard();
    });

    function onPointerDown(e) {
      var t = e.target.closest(".hrg-piece");
      if (!t || !playing) return;
      selectedId = t.dataset.id;
      var p = pieces.filter(function (x) {
        return x.id === selectedId;
      })[0];
      if (!p) return;
      drag = {
        id: selectedId,
        startR: p.r,
        startC: p.c,
        moved: false,
        lastX: e.clientX,
        lastY: e.clientY,
      };
      pushUndo();
      e.preventDefault();
    }

    function onPointerMove(e) {
      if (!drag || !playing) return;
      var dx = e.clientX - drag.lastX;
      var dy = e.clientY - drag.lastY;
      var adx = Math.abs(dx);
      var ady = Math.abs(dy);
      if (adx < 14 && ady < 14) return;
      var dr = 0;
      var dc = 0;
      if (adx > ady) dc = dx > 0 ? 1 : -1;
      else dr = dy > 0 ? 1 : -1;
      if (tryMovePiece(drag.id, dr, dc)) {
        drag.moved = true;
        drag.lastX = e.clientX;
        drag.lastY = e.clientY;
        renderBoard();
      }
    }

    function onPointerUp() {
      if (!drag) return;
      if (drag.moved) onMoved(true);
      else undoStack.pop();
      drag = null;
    }

    board.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerUp);
  }

  document.getElementById("btn-campaign").addEventListener("click", function () {
    mode = "campaign";
    document.getElementById("pick-title").textContent = "闯关模式";
    loadUnlock();
    renderPickList();
    show("pick");
  });

  document.getElementById("btn-classic").addEventListener("click", function () {
    mode = "classic";
    document.getElementById("pick-title").textContent = "经典十局";
    renderPickList();
    show("pick");
  });

  document.getElementById("btn-pick-back").addEventListener("click", function () {
    show("home");
  });

  document.getElementById("btn-undo").addEventListener("click", function () {
    if (!playing || !undoStack.length) return;
    restore(undoStack.pop());
    steps = Math.max(0, steps - 1);
    updateHud();
    renderBoard();
  });

  document.getElementById("btn-restart").addEventListener("click", function () {
    beginLevel(levelId);
  });

  document.getElementById("btn-hint").addEventListener("click", showHint);

  document.getElementById("btn-exit-play").addEventListener("click", function () {
    askConfirm("确定退出本局？", function () {
      playing = false;
      show(mode === "campaign" ? "pick" : "pick");
      renderPickList();
    });
  });

  document.getElementById("btn-again").addEventListener("click", function () {
    beginLevel(levelId);
  });

  document.getElementById("btn-back-pick").addEventListener("click", function () {
    show("pick");
    renderPickList();
  });

  document.addEventListener("keydown", function (e) {
    if (views.play.classList.contains("hidden") || !playing) return;
    var map = {
      ArrowUp: [-1, 0],
      ArrowDown: [1, 0],
      ArrowLeft: [0, -1],
      ArrowRight: [0, 1],
      w: [-1, 0],
      s: [1, 0],
      a: [0, -1],
      d: [0, 1],
    };
    var k = e.key;
    var d = map[k] || map[k.toLowerCase()];
    if (!d) return;
    e.preventDefault();
    if (!selectedId) {
      selectedId = pieces[0] && pieces[0].id;
    }
    pushUndo();
    if (slideSelected(d[0], d[1])) onMoved(true);
    else undoStack.pop();
  });

  loadUnlock();
  bindBoard();
  show("home");
})();
