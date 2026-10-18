(function () {
  "use strict";

  var FLASH_N = 10;
  var GAME_ID = "yuwen";
  var bank = null;
  var bests = {};
  var round = null;
  var clockTimer = 0;

  var viewMap = document.getElementById("view-map");
  var viewPick = document.getElementById("view-pick");
  var viewPlay = document.getElementById("view-play");
  var viewResult = document.getElementById("view-result");
  var nickBar = document.getElementById("nick-bar");
  var nickForm = document.getElementById("nick-form");
  var nickInput = document.getElementById("nick-input");
  var nickErr = document.getElementById("nick-err");

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function show(name) {
    viewMap.hidden = name !== "map";
    viewPick.hidden = name !== "pick";
    viewPlay.hidden = name !== "play";
    viewResult.hidden = name !== "result";
  }

  function stageById(id) {
    for (var i = 0; i < bank.stages.length; i++) {
      if (bank.stages[i].id === id) return bank.stages[i];
    }
    return null;
  }

  function questionsFor(stageId) {
    return bank.questions.filter(function (q) { return q.stage === stageId; });
  }

  function isReadLane(stage) {
    return (stage.groups || []).some(function (g) { return g.count > 1; }) || stage.rhythm === "passage";
  }

  function bestText(stageId) {
    var item = bests[stageId];
    return item && item.display ? item.display : "还没玩过";
  }

  function plainMarked(text) {
    return String(text || "").replace(/<em class="yuwen-mark">/g, "").replace(/<\/em>/g, "");
  }

  function appendMarked(parent, text) {
    var src = String(text || "");
    var re = /<em class="yuwen-mark">([\s\S]*?)<\/em>/g;
    var last = 0;
    var match;
    while ((match = re.exec(src))) {
      if (match.index > last) parent.appendChild(document.createTextNode(src.slice(last, match.index)));
      var mark = document.createElement("em");
      mark.className = "yuwen-mark";
      mark.textContent = match[1];
      parent.appendChild(mark);
      last = match.index + match[0].length;
    }
    if (last < src.length) parent.appendChild(document.createTextNode(src.slice(last)));
  }

  function stemCoversPrompt(q) {
    if (!q.prompt || !q.stem) return false;
    var lead = q.prompt.replace(/\s/g, "").slice(0, 12);
    return lead.length > 0 && plainMarked(q.stem).replace(/\s/g, "").indexOf(lead) === 0;
  }

  function formatTime(ms) {
    var sec = Math.max(0, Math.floor(ms / 1000));
    var m = Math.floor(sec / 60);
    var s = sec % 60;
    return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
  }

  function shuffle(list) {
    var copy = list.slice();
    for (var i = copy.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = copy[i];
      copy[i] = copy[j];
      copy[j] = tmp;
    }
    return copy;
  }

  function renderMap() {
    viewMap.innerHTML = "";
    var lanes = [
      { id: "flash", title: "快问 · 抽 10 题，正确率优先，再比用时", read: false },
      { id: "read", title: "精读 · 一篇材料做完，正确率优先，再比用时", read: true },
    ];
    lanes.forEach(function (lane) {
      var stages = bank.stages.filter(function (stage) {
        return isReadLane(stage) === lane.read;
      });
      if (!stages.length) return;
      var section = el("section", "yuwen-lane" + (lane.read ? " is-read" : ""));
      section.appendChild(el("h2", "", lane.title));
      var grid = el("div", "yuwen-grid");
      stages.forEach(function (stage) {
        var btn = el("button", "yuwen-card");
        btn.type = "button";
        btn.appendChild(el("strong", "", stage.title));
        btn.appendChild(el("span", "", bestText(stage.id)));
        btn.addEventListener("click", function () { openStage(stage); });
        grid.appendChild(btn);
      });
      section.appendChild(grid);
      viewMap.appendChild(section);
    });
    show("map");
  }

  function openStage(stage) {
    if (stage.rhythm === "flash") {
      startFlash(stage);
      return;
    }
    viewPick.innerHTML = "";
    var head = el("div", "yuwen-play-head");
    head.appendChild(el("h2", "", stage.title));
    var back = el("button", "fgb-btn-ghost", "返回");
    back.type = "button";
    back.addEventListener("click", renderMap);
    head.appendChild(back);
    viewPick.appendChild(head);
    viewPick.appendChild(el("p", "yuwen-note", "最好成绩 " + bestText(stage.id)));

    if (stage.flashCount > 0) {
      var flashBtn = el("button", "fgb-btn yuwen-next", "单题快问 · " + Math.min(FLASH_N, stage.flashCount) + " 题");
      flashBtn.type = "button";
      flashBtn.addEventListener("click", function () { startFlash(stage); });
      viewPick.appendChild(flashBtn);
    }

    if (stage.groups.length) {
      var list = el("div", "yuwen-picks");
      stage.groups.forEach(function (group) {
        var btn = el("button", "yuwen-opt", group.title + " · " + group.count + " 题");
        btn.type = "button";
        btn.addEventListener("click", function () { startGroup(stage, group); });
        list.appendChild(btn);
      });
      viewPick.appendChild(list);
    }
    show("pick");
  }

  function startFlash(stage) {
    var pool = questionsFor(stage.id).filter(function (q) { return !q.group; });
    var picked = shuffle(pool).slice(0, FLASH_N);
    beginRound(stage, picked, true, stage.title);
  }

  function startGroup(stage, group) {
    var picked = questionsFor(stage.id).filter(function (q) { return q.group === group.id; });
    picked.sort(function (a, b) { return a.id - b.id; });
    beginRound(stage, picked, true, stage.title + " · " + group.title);
  }

  function beginRound(stage, items, timed, title) {
    stopClock();
    round = {
      stage: stage,
      title: title,
      items: items,
      index: 0,
      correct: 0,
      timed: timed,
      acc: 0,
      tickStart: 0,
      revealed: false,
    };
    renderQuestion();
    show("play");
  }

  function elapsed() {
    if (!round) return 0;
    var extra = round.tickStart ? performance.now() - round.tickStart : 0;
    return Math.round(round.acc + extra);
  }

  function startClock() {
    if (!round || !round.timed) return;
    round.tickStart = performance.now();
    clockTimer = window.setInterval(paintTimer, 200);
  }

  function pauseClock() {
    if (!round || !round.tickStart) return;
    round.acc += performance.now() - round.tickStart;
    round.tickStart = 0;
    window.clearInterval(clockTimer);
    clockTimer = 0;
    paintTimer();
  }

  function stopClock() {
    if (round && round.penaltyTimer) {
      window.clearInterval(round.penaltyTimer);
      round.penaltyTimer = 0;
    }
    window.clearInterval(clockTimer);
    clockTimer = 0;
  }

  function paintTimer() {
    var node = document.getElementById("yuwen-timer");
    if (node && round) node.textContent = formatTime(elapsed());
  }

  function renderQuestion() {
    var q = round.items[round.index];
    viewPlay.innerHTML = "";
    var head = el("div", "yuwen-play-head");
    head.appendChild(el("h2", "", round.title));
    var timer = el("div", "yuwen-timer", round.timed ? formatTime(elapsed()) : "不计时");
    timer.id = "yuwen-timer";
    head.appendChild(timer);
    viewPlay.appendChild(head);

    var progress = el("div", "yuwen-progress");
    var bar = el("i");
    bar.style.width = Math.round((round.index / round.items.length) * 100) + "%";
    progress.appendChild(bar);
    viewPlay.appendChild(progress);
    viewPlay.appendChild(el("p", "yuwen-note", "第 " + (round.index + 1) + " / " + round.items.length + " 题 · 题库 " + q.id));

    if (q.passage) {
      var passage = el("div", "yuwen-passage");
      appendMarked(passage, q.passage);
      viewPlay.appendChild(passage);
    }
    if (q.prompt && !stemCoversPrompt(q)) viewPlay.appendChild(el("p", "yuwen-prompt", q.prompt));
    if (q.stem) {
      var stem = el("p", "yuwen-stem");
      appendMarked(stem, q.stem);
      viewPlay.appendChild(stem);
    }

    var options = el("div", "yuwen-options");
    ["A", "B", "C", "D"].forEach(function (letter) {
      var btn = el("button", "yuwen-opt");
      btn.type = "button";
      var mark = el("b", "", letter);
      btn.appendChild(mark);
      appendMarked(btn, q.options[letter]);
      btn.addEventListener("click", function () { choose(letter, options); });
      options.appendChild(btn);
    });
    viewPlay.appendChild(options);

    var leave = el("button", "fgb-btn-ghost yuwen-next yuwen-leave", "返回关卡");
    leave.type = "button";
    leave.addEventListener("click", function () {
      stopClock();
      round = null;
      renderMap();
    });
    viewPlay.appendChild(leave);
    round.revealed = false;
    startClock();
  }

  function choose(letter, options) {
    if (!round || round.revealed) return;
    round.revealed = true;
    pauseClock();
    var q = round.items[round.index];
    var right = letter === q.answer;
    if (right) round.correct += 1;
    Array.prototype.forEach.call(options.children, function (btn) {
      var mark = btn.querySelector("b").textContent;
      btn.disabled = true;
      if (mark === q.answer) btn.classList.add("is-correct");
      else if (mark === letter) btn.classList.add("is-wrong");
    });
    var box = el("div", "yuwen-explain");
    box.appendChild(el("strong", "", right ? "答对了" : "正确答案 " + q.answer));
    var explain = el("p");
    appendMarked(explain, q.explain || "");
    box.appendChild(explain);
    var last = round.index + 1 >= round.items.length;
    var next = el("button", "fgb-btn yuwen-next", last ? "看成绩" : "下一题");
    next.type = "button";
    next.addEventListener("click", function () {
      if (next.disabled) return;
      if (round && round.penaltyTimer) {
        window.clearInterval(round.penaltyTimer);
        round.penaltyTimer = 0;
      }
      if (last) finishRound();
      else {
        round.index += 1;
        renderQuestion();
      }
    });
    if (!right && round.timed) {
      var left = 5;
      var label = next.textContent;
      next.disabled = true;
      next.textContent = label + "（" + left + "）";
      startClock();
      round.penaltyTimer = window.setInterval(function () {
        left -= 1;
        if (left <= 0) {
          window.clearInterval(round.penaltyTimer);
          round.penaltyTimer = 0;
          pauseClock();
          next.disabled = false;
          next.textContent = label;
          return;
        }
        next.textContent = label + "（" + left + "）";
      }, 1000);
    }
    var leave = viewPlay.querySelector(".yuwen-leave");
    if (leave) {
      viewPlay.insertBefore(box, leave);
      viewPlay.insertBefore(next, leave);
    } else {
      viewPlay.appendChild(box);
      viewPlay.appendChild(next);
    }
  }

  function scoreLine() {
    var total = round.items.length;
    var rate = total ? Math.round(round.correct * 100 / total) : 0;
    return "正确率 " + rate + "% · " + round.correct + "/" + total + " · " + formatTime(elapsed());
  }

  function finishRound() {
    stopClock();
    var line = scoreLine();
    var stage = round.stage;
    var payload = {
      gameId: GAME_ID,
      mode: "challenge",
      tier: stage.id,
      tierLabel: stage.title,
      display: line,
      metrics: {
        correct: round.correct,
        total: round.items.length,
        timeMs: elapsed(),
      },
    };
    viewResult.innerHTML = "";
    viewResult.appendChild(el("h2", "", round.title));
    viewResult.appendChild(el("p", "yuwen-score", line));
    var note = el("p", "yuwen-note", "正在记入成绩…");
    viewResult.appendChild(note);
    var board = el("ol", "yuwen-board");
    viewResult.appendChild(board);
    var actions = el("div", "yuwen-result-actions");
    var again = el("button", "fgb-btn", "再来一局");
    again.type = "button";
    again.addEventListener("click", function () {
      if (round.timed && round.items.every(function (q) { return !q.group; })) startFlash(stage);
      else openStage(stage);
    });
    var home = el("button", "fgb-btn-ghost", "回关卡");
    home.type = "button";
    home.addEventListener("click", function () {
      round = null;
      renderMap();
    });
    actions.appendChild(again);
    actions.appendChild(home);
    viewResult.appendChild(actions);
    show("result");

    FGB.fgbSubmitScore(payload).then(function (res) {
      if (!res) {
        note.textContent = "这局成绩还没记入排行。先在上面设置昵称。";
        return;
      }
      note.textContent = res.isPersonalBest ? "新纪录，已记入本关排行。" : "已记入。本关最好成绩还是更高的那一局。";
      bests[stage.id] = { display: line, score: res.entry && res.entry.score };
      return FGB.getLeaderboard(GAME_ID, "challenge", stage.id, 5);
    }).then(function (data) {
      if (!data || !data.items) return;
      board.innerHTML = "";
      data.items.forEach(function (item) {
        var li = el("li");
        li.appendChild(el("span", "", item.rank + ". " + (item.nickname || "—")));
        li.appendChild(el("span", "", item.display || ""));
        board.appendChild(li);
      });
    }).catch(function () {
      note.textContent = "成绩已在本机算完。排行榜暂时没连上。";
    });
  }

  function loadBests() {
    return FGB.getBests(GAME_ID).then(function (data) {
      var game = data && data.bests && data.bests[GAME_ID];
      bests = (game && game.challenge) || {};
    }).catch(function () {
      bests = {};
    });
  }

  nickForm.addEventListener("submit", function (event) {
    event.preventDefault();
    nickErr.textContent = "";
    var name = nickInput.value.replace(/^\s+|\s+$/g, "");
    if (!name) {
      nickErr.textContent = "先写一个昵称";
      return;
    }
    FGB.registerTerminal(name).then(function () {
      nickBar.hidden = true;
      return loadBests();
    }).then(renderMap).catch(function (err) {
      nickErr.textContent = (err && err.message) || "没保存上";
    });
  });

  fetch("questions.json")
    .then(function (res) {
      if (!res.ok) throw new Error("题库加载失败");
      return res.json();
    })
    .then(function (data) {
      bank = data;
      return FGB.ensureRegistered();
    })
    .then(function (user) {
      nickBar.hidden = !!(user && user.registered);
      return loadBests();
    })
    .then(renderMap)
    .catch(function (err) {
      viewMap.appendChild(el("p", "yuwen-err", (err && err.message) || "题库加载失败"));
    });
})();
