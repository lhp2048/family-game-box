/**
 * fgb-shell.js — shared top bar, session chip, and safeNext helpers
 *
 * Include on shell pages (Tasks 3–5+): play-gate, login, register, hall (index),
 * daily / yuwen-daily, leaderboards. Game pages (P2) reuse mountTopbar via #fgb-topbar.
 *
 * Script order (after theme CSS):
 *   fgb-client.js → fgb-ui.js → fgb-shell.js
 *
 * Depends on window.FGB from fgb-client (url, authMe, logout, basePath).
 * FGBUI is optional (not required for topbar / safeNext).
 *
 * Public API: window.FGBShell
 *   - mountTopbar(rootEl, options)
 *       options: { title?, showBack?, backHref?, showUser? }
 *   - safeNext(defaultPath)  — open-redirect-safe ?next= (same-origin relative only)
 *   - requireUserOrRedirect() — authMe; if not logged in, redirect to /login?next=…
 */
(function (global) {
  "use strict";

  function fgbUrl(path) {
    if (global.FGB && typeof FGB.url === "function") return FGB.url(path);
    if (!path) return "/";
    return path.charAt(0) === "/" ? path : "/" + path;
  }

  function decodeNext(raw) {
    var prev = raw;
    for (var n = 0; n < 5; n++) {
      var nxt;
      try {
        nxt = decodeURIComponent(prev);
      } catch (e) {
        return "";
      }
      if (nxt === prev) return nxt;
      prev = nxt;
    }
    return prev;
  }

  function posixNormpath(path) {
    if (!path) return ".";
    var initial = 0;
    if (path.charAt(0) === "/") {
      initial = 1;
      if (path.indexOf("//") === 0 && path.indexOf("///") !== 0) initial = 2;
    }
    var comps = path.split("/");
    var out = [];
    for (var i = 0; i < comps.length; i++) {
      var comp = comps[i];
      if (comp === "" || comp === ".") continue;
      if (
        comp !== ".." ||
        (initial === 0 && !out.length) ||
        (out.length && out[out.length - 1] === "..")
      ) {
        out.push(comp);
      } else if (out.length) {
        out.pop();
      }
    }
    var joined = out.join("/");
    if (initial) joined = new Array(initial + 1).join("/") + joined;
    return joined || ".";
  }

  /**
   * Sanitize a raw next path (open-redirect safe).
   * Only same-origin relative paths starting with a single "/".
   * Blocks /login and /register to avoid auth loops (login/register pattern).
   */
  function sanitizeNext(raw) {
    if (!raw) return "/";
    var decoded = decodeNext(raw);
    if (!decoded) return "/";
    if (decoded.indexOf("\\") !== -1) return "/";
    for (var i = 0; i < decoded.length; i++) {
      var code = decoded.charCodeAt(i);
      if (code < 32 || code === 127) return "/";
    }
    if (decoded.indexOf("/") !== 0 || decoded.indexOf("//") === 0) return "/";
    var q = decoded.indexOf("?");
    var pathOnly = q === -1 ? decoded : decoded.slice(0, q);
    var query = q === -1 ? "" : decoded.slice(q);
    var normalized = posixNormpath(pathOnly);
    if (normalized.indexOf("/") !== 0 || normalized.indexOf("//") === 0) return "/";
    if (pathOnly === "/login" || pathOnly === "/register") return "/";
    return pathOnly + query;
  }

  /**
   * Read ?next= from the current URL, or use defaultPath. Returns a safe relative path.
   * @param {string} [defaultPath="/"]
   * @returns {string}
   */
  function safeNext(defaultPath) {
    var fallback = defaultPath != null && defaultPath !== "" ? defaultPath : "/";
    var raw = fallback;
    try {
      var params = new URLSearchParams(global.location.search);
      var n = params.get("next");
      if (n != null && n !== "") raw = n;
    } catch (e) {
      /* ignore */
    }
    return sanitizeNext(raw);
  }

  function stripBaseFromPath(fullPath) {
    var next = fullPath || "/";
    try {
      var base =
        global.FGB && typeof FGB.basePath === "function" ? FGB.basePath() : "";
      if (base && next.indexOf(base) === 0) {
        next = next.slice(base.length) || "/";
      }
    } catch (e) {
      /* ignore */
    }
    if (!next || next.charAt(0) !== "/") next = "/";
    return next;
  }

  function redirectToLogin() {
    var path =
      (global.location && global.location.pathname + global.location.search) ||
      "/";
    var next = stripBaseFromPath(path);
    global.location.assign(
      fgbUrl("/login") + "?next=" + encodeURIComponent(next)
    );
  }

  /**
   * If not logged in, redirect to login with ?next= current path.
   * @returns {Promise<object|null>} auth me payload when logged in, else null after redirect
   */
  function requireUserOrRedirect() {
    if (!global.FGB || typeof FGB.authMe !== "function") {
      redirectToLogin();
      return Promise.resolve(null);
    }
    return FGB.authMe()
      .then(function (me) {
        if (me && me.loggedIn) return me;
        redirectToLogin();
        return null;
      })
      .catch(function () {
        redirectToLogin();
        return null;
      });
  }

  function showUserLoggedIn(nav, username) {
    var chip = nav.querySelector("[data-fgb-user-chip]");
    var authLinks = nav.querySelector("[data-fgb-auth-links]");
    var nameEl = nav.querySelector("[data-fgb-user-name]");
    if (nameEl) nameEl.textContent = username || "—";
    if (chip) chip.hidden = false;
    if (authLinks) authLinks.hidden = true;
  }

  function showUserLoggedOut(nav) {
    var chip = nav.querySelector("[data-fgb-user-chip]");
    var authLinks = nav.querySelector("[data-fgb-auth-links]");
    if (chip) chip.hidden = true;
    if (authLinks) authLinks.hidden = false;
  }


  function wireRename(nav) {
    var btn = nav.querySelector("[data-fgb-rename]");
    if (!btn || btn.getAttribute("data-fgb-rename-wired") === "1") return;
    btn.setAttribute("data-fgb-rename-wired", "1");
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      var nameEl = nav.querySelector("[data-fgb-user-name]");
      var current = nameEl ? String(nameEl.textContent || "").trim() : "";
      if (current === "—") current = "";
      var openPrompt = function () {
        if (!global.FGBUI || typeof FGBUI.askPrompt !== "function") {
          if (global.FGBUI && FGBUI.toast) FGBUI.toast("无法打开改名对话框", "err");
          return;
        }
        FGBUI.askPrompt("输入新用户名（1–16 个字符）", current, function (value) {
          var next = String(value || "").trim();
          if (!next) {
            if (FGBUI.toast) FGBUI.toast("请输入新用户名", "err");
            return;
          }
          if (!global.FGB || typeof FGB.rename !== "function") {
            if (FGBUI.toast) FGBUI.toast("改名功能不可用", "err");
            return;
          }
          FGB.rename(next)
            .then(function (data) {
              var name = (data && data.username) || next;
              showUserLoggedIn(nav, name);
              if (FGBUI.toast) FGBUI.toast("已改名为「" + name + "」", "ok");
            })
            .catch(function (err) {
              if (FGBUI.toast) {
                FGBUI.toast((err && err.message) || "改名失败", "err");
              }
            });
        });
      };
      if (global.FGBUI && typeof FGBUI.askConfirm === "function") {
        FGBUI.askConfirm("要修改登录用户名吗？改名后需用新名字登录。", openPrompt);
      } else {
        openPrompt();
      }
    });
  }

  function wireLogout(nav) {
    var btn = nav.querySelector("[data-fgb-logout]");
    if (!btn) return;
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      var goHall = function () {
        global.location.assign(fgbUrl("/"));
      };
      if (!global.FGB || typeof FGB.logout !== "function") {
        goHall();
        return;
      }
      FGB.logout().then(goHall).catch(goHall);
    });
  }

  function fillUserChip(nav) {
    wireLogout(nav);
    wireRename(nav);
    if (!global.FGB || typeof FGB.authMe !== "function") {
      showUserLoggedOut(nav);
      return;
    }
    FGB.authMe()
      .then(function (me) {
        if (me && me.loggedIn) {
          showUserLoggedIn(nav, me.username || "—");
        } else {
          showUserLoggedOut(nav);
        }
      })
      .catch(function () {
        showUserLoggedOut(nav);
      });
  }

  /**
   * Build / fill a top bar in rootEl using theme classes (.fgb-topbar, .fgb-brand, …).
   * @param {HTMLElement} rootEl
   * @param {{ title?: string, showBack?: boolean, backHref?: string, showUser?: boolean }} [options]
   */
  function mountTopbar(rootEl, options) {
    if (!rootEl) return;
    var opts = options || {};
    var title = opts.title || "";
    var showBack = !!opts.showBack;
    var backHref = opts.backHref != null && opts.backHref !== "" ? opts.backHref : "/";
    var showUser = !!opts.showUser;

    if (
      rootEl.className.indexOf("fgb-topbar") === -1
    ) {
      rootEl.className = (rootEl.className
        ? rootEl.className + " "
        : "") + "fgb-topbar";
    }

    var backLabel =
      !opts.backHref || opts.backHref === "/" ? "回大厅" : "返回";

    var brandHtml =
      '<div>' +
      '<a class="fgb-brand" href="' +
      fgbUrl("/") +
      '">家庭<em>游戏盒</em></a>' +
      (title
        ? '<span class="fgb-page-kicker">' + escapeHtml(title) + "</span>"
        : "") +
      "</div>";

    var navParts = [];
    if (showBack) {
      navParts.push(
        '<a class="fgb-nav-link" href="' +
          fgbUrl(backHref) +
          '">' +
          escapeHtml(backLabel) +
          "</a>"
      );
    }
    if (showUser) {
      navParts.push(
        '<div class="fgb-chip" data-fgb-user-chip hidden>你好，' +
          '<strong data-fgb-user-name>—</strong> ' +
          '<a href="#" data-fgb-rename style="margin-left:6px;color:var(--muted);font-size:.85rem">改名</a> ' +
          '<a href="#" data-fgb-logout style="margin-left:2px;color:var(--muted);font-size:.85rem">退出</a>' +
          "</div>"
      );
      navParts.push(
        '<span data-fgb-auth-links>' +
          '<a class="fgb-nav-link" href="' +
          fgbUrl("/login") +
          '">登录</a> ' +
          '<a class="fgb-nav-link" href="' +
          fgbUrl("/register") +
          '">注册</a>' +
          "</span>"
      );
    }

    rootEl.innerHTML =
      brandHtml + '<div class="fgb-nav">' + navParts.join("") + "</div>";

    if (showUser) {
      fillUserChip(rootEl.querySelector(".fgb-nav") || rootEl);
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  global.FGBShell = {
    mountTopbar: mountTopbar,
    safeNext: safeNext,
    requireUserOrRedirect: requireUserOrRedirect,
  };
})(window);
