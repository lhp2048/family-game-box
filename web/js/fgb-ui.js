(function (global) {
  "use strict";

  /* Styles live in /css/fgb-theme.css (.fgb-toast, .fgb-confirm-*). This module only mounts DOM + behavior. */

  var _confirmCb = null;
  var _toastTimer = null;
  var _patched = false;

  function ensureDom() {
    if (!document.body) return;
    if (!document.getElementById("fgb-confirm-mask")) {
      var mask = document.createElement("div");
      mask.id = "fgb-confirm-mask";
      mask.className = "fgb-confirm-mask hidden";
      mask.setAttribute("role", "dialog");
      mask.setAttribute("aria-modal", "true");
      mask.innerHTML =
        '<div class="fgb-confirm-box">' +
        '<p id="fgb-confirm-msg">确定？</p>' +
        '<div class="fgb-confirm-actions">' +
        '<button type="button" class="fgb-confirm-cancel" id="fgb-confirm-cancel">取消</button>' +
        '<button type="button" class="fgb-confirm-ok" id="fgb-confirm-ok">确定</button>' +
        "</div></div>";
      document.body.appendChild(mask);
      document.getElementById("fgb-confirm-ok").addEventListener("click", function () {
        resolveConfirm(true);
      });
      document.getElementById("fgb-confirm-cancel").addEventListener("click", function () {
        resolveConfirm(false);
      });
      mask.addEventListener("click", function (e) {
        if (e.target === mask) resolveConfirm(false);
      });
    }
    if (!document.getElementById("fgb-toast")) {
      var toastEl = document.createElement("div");
      toastEl.id = "fgb-toast";
      toastEl.className = "fgb-toast";
      toastEl.setAttribute("aria-live", "polite");
      document.body.appendChild(toastEl);
    }
  }

  function resolveConfirm(ok) {
    var mask = document.getElementById("fgb-confirm-mask");
    if (mask) mask.classList.add("hidden");
    var cb = _confirmCb;
    _confirmCb = null;
    if (!cb) return;
    if (ok && cb.yes) cb.yes();
    if (!ok && cb.no) cb.no();
  }

  function askConfirm(message, onYes, onNo) {
    if (!document.body) {
      setTimeout(function () { askConfirm(message, onYes, onNo); }, 0);
      return;
    }
    ensureDom();
    var mask = document.getElementById("fgb-confirm-mask");
    var msg = document.getElementById("fgb-confirm-msg");
    msg.textContent = message || "确定？";
    _confirmCb = { yes: onYes, no: onNo };
    mask.classList.remove("hidden");
  }

  function toast(message, kind) {
    if (!document.body) {
      setTimeout(function () { toast(message, kind); }, 0);
      return;
    }
    ensureDom();
    var el = document.getElementById("fgb-toast");
    el.textContent = message || "";
    el.classList.remove("err", "ok", "show");
    if (kind === "err") el.classList.add("err");
    if (kind === "ok") el.classList.add("ok");
    void el.offsetWidth;
    el.classList.add("show");
    if (_toastTimer) clearTimeout(_toastTimer);
    _toastTimer = setTimeout(function () {
      el.classList.remove("show");
    }, 2200);
  }

  var _stageDoneTimer = null;

  function ensureStageDoneDom() {
    if (!document.body) return null;
    var el = document.getElementById("fgb-stage-done");
    if (!el) {
      el = document.createElement("div");
      el.id = "fgb-stage-done";
      el.className = "fgb-stage-done hidden";
      el.setAttribute("aria-live", "polite");
      el.innerHTML =
        '<span class="fgb-stage-done-mark" aria-hidden="true">✓</span>' +
        '<span class="fgb-stage-done-text"></span>';
      document.body.appendChild(el);
    }
    return el;
  }

  /**
   * Unified round/stage finish banner (free play + daily).
   * opts.duration — visible ms (default 520)
   */
  function stageDone(message, opts) {
    opts = opts || {};
    if (!document.body) {
      setTimeout(function () { stageDone(message, opts); }, 0);
      return;
    }
    var el = ensureStageDoneDom();
    if (!el) return;
    var textEl = el.querySelector(".fgb-stage-done-text");
    var fallback =
      global.FGB_MSG && global.FGB_MSG.done ? global.FGB_MSG.done : "完成！";
    if (textEl) textEl.textContent = message || fallback;
    el.classList.remove("show");
    void el.offsetWidth;
    el.classList.add("show");
    el.classList.remove("hidden");
    if (_stageDoneTimer) clearTimeout(_stageDoneTimer);
    var duration = opts.duration != null ? opts.duration : 520;
    _stageDoneTimer = setTimeout(function () {
      el.classList.remove("show");
      setTimeout(function () {
        el.classList.add("hidden");
      }, 200);
    }, duration);
  }


  var _promptCb = null;

  function ensurePromptDom() {
    if (!document.body) return;
    if (document.getElementById("fgb-prompt-mask")) return;
    var mask = document.createElement("div");
    mask.id = "fgb-prompt-mask";
    mask.className = "fgb-confirm-mask hidden";
    mask.setAttribute("role", "dialog");
    mask.setAttribute("aria-modal", "true");
    mask.innerHTML =
      '<div class="fgb-confirm-box">' +
      '<p id="fgb-prompt-msg">请输入</p>' +
      '<div class="fgb-field" style="margin:0 0 1rem">' +
      '<input class="fgb-input" type="text" id="fgb-prompt-input" maxlength="16" autocomplete="username">' +
      "</div>" +
      '<div class="fgb-confirm-actions">' +
      '<button type="button" class="fgb-confirm-cancel" id="fgb-prompt-cancel">取消</button>' +
      '<button type="button" class="fgb-confirm-ok" id="fgb-prompt-ok">确定</button>' +
      "</div></div>";
    document.body.appendChild(mask);
    function finish(ok) {
      var input = document.getElementById("fgb-prompt-input");
      var value = input ? String(input.value || "") : "";
      mask.classList.add("hidden");
      var cb = _promptCb;
      _promptCb = null;
      if (!cb) return;
      if (ok && cb.yes) cb.yes(value);
      if (!ok && cb.no) cb.no();
    }
    document.getElementById("fgb-prompt-ok").addEventListener("click", function () {
      finish(true);
    });
    document.getElementById("fgb-prompt-cancel").addEventListener("click", function () {
      finish(false);
    });
    mask.addEventListener("click", function (e) {
      if (e.target === mask) finish(false);
    });
    document.getElementById("fgb-prompt-input").addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        finish(true);
      }
    });
  }

  function askPrompt(message, defaultValue, onYes, onNo) {
    if (!document.body) {
      setTimeout(function () { askPrompt(message, defaultValue, onYes, onNo); }, 0);
      return;
    }
    ensureDom();
    ensurePromptDom();
    var mask = document.getElementById("fgb-prompt-mask");
    var msg = document.getElementById("fgb-prompt-msg");
    var input = document.getElementById("fgb-prompt-input");
    msg.textContent = message || "请输入";
    input.value = defaultValue != null ? String(defaultValue) : "";
    _promptCb = { yes: onYes, no: onNo };
    mask.classList.remove("hidden");
    setTimeout(function () {
      try {
        input.focus();
        input.select();
      } catch (e) { /* ignore */ }
    }, 0);
  }

  /** 拦截浏览器原生阻塞弹窗，统一改走页面内 UI */
  function patchNativeDialogs() {
    if (_patched) return;
    _patched = true;
    try {
      global.alert = function (message) {
        toast(String(message == null ? "" : message), "err");
      };
      global.confirm = function (message) {
        // 无法同步返回；直接拒绝并弹出非阻塞确认供人工操作
        // 调用方若依赖返回值，应改用 FGBUI.askConfirm
        console.warn("[FGBUI] blocked native confirm:", message);
        askConfirm(String(message == null ? "确定？" : message), null, null);
        return false;
      };
      global.prompt = function (message, defaultValue) {
        console.warn("[FGBUI] blocked native prompt:", message);
        toast(String(message == null ? "" : message), "err");
        return null;
      };
    } catch (e) { /* ignore */ }
  }

  /**
   * Run prepare (build board, preload), wait for paint, then onPlayable(playableAt).
   * playableAt is Date.now() — use as challenge startedAt / roundStart.
   * In daily iframe, posts fgb-daily-stage-ready unless opts.signalReady === false.
   */
  function runWhenPlayable(prepare, onPlayable, opts) {
    opts = opts || {};
    function signalReady() {
      if (opts.signalReady === false) return;
      if (global.FGBDaily && FGBDaily.notifyStageReady) FGBDaily.notifyStageReady();
      else if (global.parent && global.parent !== global) {
        global.parent.postMessage({ type: "fgb-daily-stage-ready" }, "*");
      }
    }
    function afterLoad() {
      Promise.resolve()
        .then(function () {
          return typeof prepare === "function" ? prepare() : undefined;
        })
        .then(function () {
          return new Promise(function (resolve) {
            requestAnimationFrame(function () {
              requestAnimationFrame(resolve);
            });
          });
        })
        .then(function () {
          var t = Date.now();
          signalReady();
          if (typeof onPlayable === "function") onPlayable(t);
        })
        .catch(function (err) {
          console.error(err);
          var t = Date.now();
          signalReady();
          if (typeof onPlayable === "function") onPlayable(t);
        });
    }
    if (document.readyState === "complete") afterLoad();
    else global.addEventListener("load", afterLoad, { once: true });
  }

  patchNativeDialogs();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { ensureDom(); });
  } else {
    ensureDom();
  }

  global.FGBUI = {
    askConfirm: askConfirm,
    askPrompt: askPrompt,
    toast: toast,
    stageDone: stageDone,
    runWhenPlayable: runWhenPlayable,
    patchNativeDialogs: patchNativeDialogs,
  };
})(window);
