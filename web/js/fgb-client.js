(function (global) {
  "use strict";

  var STORAGE_ID = "fgb_terminal_id";
  var STORAGE_NICK = "fgb_nickname";

  function basePath() {
    var b = global.__FGB_BASE__;
    if (typeof b === "string" && b) {
      return b.replace(/\/$/, "");
    }
    var path = (global.location && location.pathname) || "";
    if (path === "/game-box" || path.indexOf("/game-box/") === 0) {
      return "/game-box";
    }
    return "";
  }

  function withBase(path) {
    if (!path) return basePath() || "/";
    if (path.charAt(0) !== "/") path = "/" + path;
    var base = basePath();
    if (base && (path === base || path.indexOf(base + "/") === 0)) return path;
    return base + path;
  }

  function uuid() {
    if (global.crypto && crypto.randomUUID) return crypto.randomUUID();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      var v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function getTerminalId() {
    var id = localStorage.getItem(STORAGE_ID);
    if (!id) {
      id = uuid();
      localStorage.setItem(STORAGE_ID, id);
    }
    return id;
  }

  function headers() {
    return {
      "Content-Type": "application/json",
      "X-Terminal-Id": getTerminalId(),
    };
  }

  function redirectToLogin() {
    var path = (global.location && (location.pathname + location.search)) || "/";
    var next = path;
    try {
      var base = basePath();
      if (base && next.indexOf(base) === 0) {
        next = next.slice(base.length) || "/";
      }
    } catch (e) { /* ignore */ }
    if (!next || next.charAt(0) !== "/") next = "/";
    global.location.assign(withBase("/login") + "?next=" + encodeURIComponent(next));
  }

  function api(path, options) {
    options = options || {};
    return fetch(withBase(path), {
      method: options.method || "GET",
      headers: Object.assign({}, headers(), options.headers || {}),
      body: options.body ? JSON.stringify(options.body) : undefined,
      credentials: "same-origin",
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) {
          var detail = (data && data.detail) || res.statusText || "request failed";
          if (res.status === 401 && String(detail).indexOf("需要登录") !== -1) {
            if (!options.skipAuthRedirect) redirectToLogin();
          }
          var err = new Error(detail);
          err.status = res.status;
          err.data = data;
          throw err;
        }
        return data;
      }, function () {
        if (!res.ok) {
          var err2 = new Error(res.statusText || "request failed");
          err2.status = res.status;
          throw err2;
        }
        return null;
      });
    });
  }

  function me() {
    return api("/api/v1/terminals/me");
  }

  function registerTerminal(nickname) {
    return api("/api/v1/terminals/register", {
      method: "POST",
      body: { terminalId: getTerminalId(), nickname: nickname },
    }).then(function (data) {
      if (data && data.nickname) localStorage.setItem(STORAGE_NICK, data.nickname);
      return data;
    });
  }

  /** If terminal missing, register it under the logged-in username (score/daily need a terminal). */
  function ensureTerminalFromUser(username) {
    var name = (username || "").trim();
    if (!name) return Promise.resolve(null);
    return me().then(function (data) {
      if (data && data.registered) {
        if (data.nickname) localStorage.setItem(STORAGE_NICK, data.nickname);
        return data;
      }
      return registerTerminal(name);
    }).catch(function () {
      return registerTerminal(name);
    });
  }

  function ensureRegistered() {
    return me().then(function (data) {
      if (data && data.registered) {
        if (data.nickname) localStorage.setItem(STORAGE_NICK, data.nickname);
        return data;
      }
      return authMe().then(function (auth) {
        if (auth && auth.loggedIn && auth.username) {
          return registerTerminal(auth.username);
        }
        return null;
      }).catch(function () { return null; });
    });
  }

  function authMe() {
    return api("/api/v1/auth/me", { skipAuthRedirect: true });
  }

  function login(username, password) {
    return api("/api/v1/auth/login", {
      method: "POST",
      body: { username: username, password: password },
      skipAuthRedirect: true,
    }).then(function (data) {
      var name = (data && data.username) || username;
      return ensureTerminalFromUser(name).then(function () { return data; });
    });
  }

  /** User account register (brief: FGB.register). Terminal nickname uses registerTerminal. */
  function register(username, password, passphrase) {
    var body = { username: username, password: password };
    if (passphrase != null && passphrase !== "") body.passphrase = passphrase;
    return api("/api/v1/auth/register", {
      method: "POST",
      body: body,
      skipAuthRedirect: true,
    }).then(function (data) {
      var name = (data && data.username) || username;
      return ensureTerminalFromUser(name).then(function () { return data; });
    });
  }

  function logout() {
    return api("/api/v1/auth/logout", {
      method: "POST",
      skipAuthRedirect: true,
    });
  }


  function rename(username) {
    return api("/api/v1/auth/rename", {
      method: "POST",
      body: { username: username },
      skipAuthRedirect: true,
    }).then(function (data) {
      var name = (data && data.username) || username;
      if (name) localStorage.setItem(STORAGE_NICK, name);
      return data;
    });
  }

  function claimTerminal(terminalId) {
    return api("/api/v1/auth/claim-terminal", {
      method: "POST",
      body: { terminalId: terminalId || getTerminalId() },
    });
  }

  function submitScore(payload) {
    return api("/api/v1/scores", { method: "POST", body: payload }).then(function (data) {
      if (data && data.isPersonalBest && typeof celebrate === "function") {
        celebrate("新纪录！");
      }
      return data;
    });
  }

  function getBests(gameId) {
    var q = gameId ? ("?gameId=" + encodeURIComponent(gameId)) : "";
    return api("/api/v1/scores/me/bests" + q);
  }

  function getLeaderboard(gameId, mode, tier, limit) {
    var params = new URLSearchParams({
      gameId: gameId,
      mode: mode,
      tier: tier,
      limit: String(limit || 20),
    });
    return api("/api/v1/leaderboard?" + params.toString());
  }

  function getRankMeta() {
    return api("/api/v1/rank/meta");
  }

  function fgbSubmitScore(payload) {
    if (!payload || !payload.gameId) return Promise.resolve(null);
    return ensureRegistered().then(function (user) {
      if (!user) return null;
      return submitScore(payload);
    }).catch(function () { return null; });
  }

  function getGlobalLeaderboard(limit) {
    var params = new URLSearchParams({ limit: String(limit || 50) });
    return api("/api/v1/leaderboard/global?" + params.toString());
  }

  function getRecentLeaderboard(limit) {
    var params = new URLSearchParams({ limit: String(limit || 20) });
    return api("/api/v1/leaderboard/recent?" + params.toString());
  }

  function loadDifficulty(gameId) {
    return api("/api/v1/difficulty?gameId=" + encodeURIComponent(gameId)).then(function (data) {
      return (data.games && data.games[gameId]) || null;
    }).catch(function () { return null; });
  }

  function loadLobbySummary() {
    return api("/api/v1/lobby/summary").catch(function () { return null; });
  }

  function markProductToyHtml() {
    try {
      var doc = global.document;
      if (!doc || !doc.documentElement) return;
      var body = doc.body;
      if (!body) return;
      if (
        body.classList.contains("fgb-console") ||
        body.classList.contains("fgb-lobby-toy") ||
        body.hasAttribute("data-game-skin")
      ) {
        doc.documentElement.classList.add("fgb-product-toy");
      }
    } catch (e) {}
  }

  if (global.document && global.document.body) {
    markProductToyHtml();
  } else if (global.document) {
    global.document.addEventListener("DOMContentLoaded", markProductToyHtml);
  }

  global.FGB = {
    basePath: basePath,
    url: withBase,
    getTerminalId: getTerminalId,
    me: me,
    register: register,
    registerTerminal: registerTerminal,
    ensureRegistered: ensureRegistered,
    ensureTerminalFromUser: ensureTerminalFromUser,
    authMe: authMe,
    login: login,
    logout: logout,
    claimTerminal: claimTerminal,
    rename: rename,
    submitScore: submitScore,
    getBests: getBests,
    getLeaderboard: getLeaderboard,
    getGlobalLeaderboard: getGlobalLeaderboard,
    getRecentLeaderboard: getRecentLeaderboard,
    getRankMeta: getRankMeta,
    fgbSubmitScore: fgbSubmitScore,
    loadDifficulty: loadDifficulty,
    loadLobbySummary: loadLobbySummary,
  };
  global.fgbSubmitScore = fgbSubmitScore;
})(window);
