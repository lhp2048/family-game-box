(function () {
  "use strict";

  var paper = null;
  var acc = 0;
  var penaltyMs = 0;
  var tickStart = 0;
  var clockTimer = 0;
  var revealed = false;
  var waitTimer = 0;

  var viewPrep = document.getElementById("view-prep");
  var viewPlay = document.getElementById("view-play");
  var viewResult = document.getElementById("view-result");
  var errEl = document.getElementById("err");

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
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

  function show(name) {
    viewPrep.hidden = name !== "prep";
    viewPlay.hidden = name !== "play";
    viewResult.hidden = name !== "result";
  }

  function api(path, options) {
    options = options || {};
    return fetch(FGB.url(path), {
      method: options.method || "GET",
      headers: {
        "Content-Type": "application/json",
        "X-Terminal-Id": FGB.getTerminalId(),
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) {
          var error = new Error((data && data.detail) || "请求失败");
          error.data = data;
          throw error;
        }
        return data;
      });
    });
  }

  function formatTime(ms) {
    var sec = Math.max(0, Math.floor(ms / 1000));
    return (Math.floor(sec / 60) < 10 ? "0" : "") + Math.floor(sec / 60) + ":" + (sec % 60 < 10 ? "0" : "") + (sec % 60);
  }

  var PENALTY_MS = 5000;

  function shownMs() {
    return elapsed() + penaltyMs;
  }
    var extra = tickStart ? performance.now() - tickStart : 0;
    return Math.round(acc + extra);
  }

  function startClock() {
    tickStart = performance.now();
    window.clearInterval(clockTimer);
    clockTimer = window.setInterval(function () {
      var node = document.getElementById("yuwen-timer");
      if (node) node.textContent = formatTime(shownMs());
    }, 200);
  }

  function pauseClock() {
    if (tickStart) {
      acc += performance.now() - tickStart;
      tickStart = 0;
    }
    window.clearInterval(clockTimer);
    var node = document.getElementById("yuwen-timer");
    if (node) node.textContent = formatTime(shownMs());
  }

  function wrongPenalty(progress) {
    var answered = (progress && progress.answered) || [];
    var wrong = 0;
    answered.forEach(function (item) {
      if (!item.correct) wrong += 1;
    });
    return wrong * PENALTY_MS;
  }
    var map = {};
    ((paper.progress && paper.progress.answered) || []).forEach(function (item) {
      map[item.id] = item;
    });
    return map;
  }

  function nextIndex() {
    var done = answeredMap();
    for (var i = 0; i < paper.questions.length; i++) {
      if (!done[paper.questions[i].id]) return i;
    }
    return -1;
  }

  function renderPrep() {
    viewPrep.innerHTML = "";
    var progress = paper.progress || {};
    viewPrep.appendChild(el("p", "yuwen-note", paper.date + " · 共 " + paper.questions.length + " 题"));
    if (progress.status === "finished") {
      showResult(progress.display, progress.rank);
      return;
    }
    var btn = el("button", "fgb-btn", progress.status === "running" ? "继续作答" : "开始挑战");
    btn.type = "button";
    btn.addEventListener("click", function () {
      acc = progress.timeMs || 0;
      penaltyMs = wrongPenalty(progress);
      var index = nextIndex();
      if (index < 0) submitPaper();
      else renderQuestion(index);
    });
    viewPrep.appendChild(btn);
    show("prep");
  }

  function clearWait() {
    window.clearInterval(waitTimer);
    waitTimer = 0;
  }

  function renderQuestion(index) {
    clearWait();
    var q = paper.questions[index];
    revealed = false;
    viewPlay.innerHTML = "";
    var head = el("div", "yuwen-play-head");
    head.appendChild(el("h2", "", q.stageTitle || "每日语文挑战"));
    var timer = el("div", "yuwen-timer", formatTime(shownMs()));
    timer.id = "yuwen-timer";
    head.appendChild(timer);
    viewPlay.appendChild(head);
    viewPlay.appendChild(el("p", "yuwen-note", "第 " + (index + 1) + " / " + paper.questions.length + " 题"));
    if (q.passage) {
      var passage = el("div", "yuwen-passage");
      appendMarked(passage, q.passage);
      viewPlay.appendChild(passage);
    }
    if (q.prompt && plainMarked(q.stem).indexOf(q.prompt.slice(0, 8)) !== 0) viewPlay.appendChild(el("p", "yuwen-prompt", q.prompt));
    if (q.stem) {
      var stem = el("p", "yuwen-stem");
      appendMarked(stem, q.stem);
      viewPlay.appendChild(stem);
    }
    var options = el("div", "yuwen-options");
    ["A", "B", "C", "D"].forEach(function (letter) {
      var button = el("button", "yuwen-opt");
      button.type = "button";
      button.appendChild(el("b", "", letter));
      appendMarked(button, q.options[letter] || "");
      button.addEventListener("click", function () { choose(q, letter, options, index); });
      options.appendChild(button);
    });
    viewPlay.appendChild(options);
    show("play");
    startClock();
  }

  function showFeedback(options, result) {
    Array.prototype.forEach.call(options.children, function (button) {
      var mark = button.querySelector("b").textContent;
      button.disabled = true;
      if (mark === result.answer) button.classList.add("is-correct");
      else if (mark === result.choice && !result.correct) button.classList.add("is-wrong");
    });
    var box = el("div", "yuwen-explain");
    box.appendChild(el("strong", "", result.correct ? "答对了" : "正确答案 " + result.answer));
    var explain = el("p");
    appendMarked(explain, result.explain || "");
    box.appendChild(explain);
    viewPlay.appendChild(box);
  }

  function choose(q, letter, options, index) {
    if (revealed) return;
    revealed = true;
    pauseClock();
    errEl.textContent = "";
    api("/api/v1/yuwen-daily/answer", {
      method: "POST",
      body: { paperId: paper.paperId, questionId: q.id, choice: letter, timeMs: Math.round(acc) },
    }).then(function (result) {
      if (!paper.progress.answered) paper.progress.answered = [];
      paper.progress.answered.push(result);
      paper.progress.status = "running";
      paper.progress.timeMs = result.timeMs || Math.round(acc);
      acc = paper.progress.timeMs;
      showFeedback(options, result);
      var last = index + 1 >= paper.questions.length;
      var label = last ? "交卷" : "下一题";
      var next = el("button", "fgb-btn yuwen-next", label);
      next.type = "button";
      next.addEventListener("click", function () {
        if (next.disabled) return;
        clearWait();
        if (last) submitPaper();
        else renderQuestion(index + 1);
      });
      if (!result.correct) {
        var left = 5;
        var added = 0;
        var base = penaltyMs;
        next.disabled = true;
        next.textContent = label + "（" + left + "）";
        waitTimer = window.setInterval(function () {
          added = Math.min(PENALTY_MS, added + 200);
          penaltyMs = base + added;
          var node = document.getElementById("yuwen-timer");
          if (node) node.textContent = formatTime(shownMs());
          if (added % 1000 === 0) {
            left -= 1;
            if (left <= 0) {
              penaltyMs = base + PENALTY_MS;
              clearWait();
              if (node) node.textContent = formatTime(shownMs());
              next.disabled = false;
              next.textContent = label;
              return;
            }
            next.textContent = label + "（" + left + "）";
          }
        }, 200);
      }
      viewPlay.appendChild(next);
    }).catch(function (error) {
      revealed = false;
      errEl.textContent = error.message || "没交上去";
      startClock();
    });
  }

  function submitPaper() {
    errEl.textContent = "";
    api("/api/v1/yuwen-daily/finish", {
      method: "POST",
      body: { paperId: paper.paperId, timeMs: Math.round(acc) },
    }).then(function (data) {
      var run = data.run || {};
      paper.progress.status = "finished";
      paper.progress.display = run.display;
      paper.progress.rank = data.rank;
      showResult(run.display, data.rank);
    }).catch(function (error) {
      errEl.textContent = error.message || "交卷失败";
    });
  }

  function showResult(display, rank) {
    clearWait();
    viewResult.innerHTML = "";
    viewResult.appendChild(el("h2", "", "今日成绩"));
    viewResult.appendChild(el("p", "yuwen-score", display || "—"));
    viewResult.appendChild(el("p", "yuwen-note", rank ? ("语文挑战榜第 " + rank + " 名") : "已记入语文挑战榜"));
    var actions = el("div", "yuwen-result-actions");
    var board = el("a", "fgb-btn", "看语文挑战榜");
    board.href = FGB.url("/yuwen-daily/leaderboard");
    var home = el("a", "fgb-btn-ghost", "回大厅");
    home.href = FGB.url("/");
    actions.appendChild(board);
    actions.appendChild(home);
    viewResult.appendChild(actions);
    show("result");
  }

  FGB.ensureRegistered().then(function (user) {
    if (!user || !user.registered) {
      errEl.textContent = "先回大厅设置昵称，再来挑战。";
      return null;
    }
    return api("/api/v1/yuwen-daily/today");
  }).then(function (data) {
    if (!data) return;
    paper = data;
    acc = (data.progress && data.progress.timeMs) || 0;
    renderPrep();
  }).catch(function (error) {
    errEl.textContent = error.message || "卷子加载失败";
  });
})();
