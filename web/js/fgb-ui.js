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

  patchNativeDialogs();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { ensureDom(); });
  } else {
    ensureDom();
  }

  global.FGBUI = {
    askConfirm: askConfirm,
    toast: toast,
    patchNativeDialogs: patchNativeDialogs,
  };
})(window);
