(function (global) {
  "use strict";

  var STYLE_ID = "fgb-ui-style";
  var _confirmCb = null;
  var _toastTimer = null;

  function ensureDom() {
    if (!document.getElementById(STYLE_ID)) {
      var style = document.createElement("style");
      style.id = STYLE_ID;
      style.textContent =
        ".fgb-confirm-mask{position:fixed;inset:0;z-index:1000;display:flex;align-items:center;justify-content:center;padding:1rem;background:rgba(26,36,33,.42);backdrop-filter:blur(2px)}" +
        ".fgb-confirm-mask.hidden{display:none!important}" +
        ".fgb-confirm-box{width:min(360px,100%);background:#fffdf8;border:1px solid rgba(26,36,33,.12);border-radius:18px;box-shadow:0 16px 40px rgba(26,36,33,.16);padding:1.25rem 1.2rem 1.1rem;color:#1a2421}" +
        ".fgb-confirm-box p{margin:0 0 1.1rem;font-size:1.05rem;line-height:1.45}" +
        ".fgb-confirm-actions{display:grid;grid-template-columns:1fr 1fr;gap:.55rem}" +
        ".fgb-confirm-actions button{border-radius:14px;padding:.75rem 1rem;font:inherit;font-weight:700;cursor:pointer}" +
        ".fgb-confirm-cancel{border:1px solid rgba(26,36,33,.12);background:transparent;color:#5c6b66}" +
        ".fgb-confirm-ok{border:0;color:#f7fffb;background:linear-gradient(160deg,#0f7a5a,#0a5c44)}" +
        ".fgb-toast{position:fixed;left:50%;bottom:18%;transform:translateX(-50%) translateY(8px);z-index:1100;max-width:min(420px,90vw);padding:.7rem 1.1rem;border-radius:12px;background:rgba(26,36,33,.92);color:#fffdf8;font-size:.95rem;line-height:1.4;box-shadow:0 12px 32px rgba(26,36,33,.2);opacity:0;pointer-events:none;transition:opacity .18s ease,transform .22s ease}" +
        ".fgb-toast.show{opacity:1;transform:translateX(-50%) translateY(0)}" +
        ".fgb-toast.err{background:rgba(163,59,45,.95)}" +
        ".fgb-toast.ok{background:rgba(15,122,90,.95)}";
      document.head.appendChild(style);
    }
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
      var toast = document.createElement("div");
      toast.id = "fgb-toast";
      toast.className = "fgb-toast";
      toast.setAttribute("aria-live", "polite");
      document.body.appendChild(toast);
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
    ensureDom();
    var mask = document.getElementById("fgb-confirm-mask");
    var msg = document.getElementById("fgb-confirm-msg");
    msg.textContent = message || "确定？";
    _confirmCb = { yes: onYes, no: onNo };
    mask.classList.remove("hidden");
  }

  function toast(message, kind) {
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

  global.FGBUI = {
    askConfirm: askConfirm,
    toast: toast,
  };
})(window);
