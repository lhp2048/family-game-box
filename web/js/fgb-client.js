(function (global) {
  "use strict";

  var STORAGE_ID = "fgb_terminal_id";
  var STORAGE_NICK = "fgb_nickname";

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

  function api(path, options) {
    options = options || {};
    return fetch(path, {
      method: options.method || "GET",
      headers: Object.assign({}, headers(), options.headers || {}),
      body: options.body ? JSON.stringify(options.body) : undefined,
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) {
          var err = new Error((data && data.detail) || res.statusText || "request failed");
          err.status = res.status;
          err.data = data;
          throw err;
        }
        return data;
      });
    });
  }

  function me() {
    return api("/api/v1/terminals/me");
  }

  function register(nickname) {
    return api("/api/v1/terminals/register", {
      method: "POST",
      body: { terminalId: getTerminalId(), nickname: nickname },
    }).then(function (data) {
      if (data && data.nickname) localStorage.setItem(STORAGE_NICK, data.nickname);
      return data;
    });
  }

  function ensureRegistered() {
    return me().then(function (data) {
      if (data && data.registered) {
        if (data.nickname) localStorage.setItem(STORAGE_NICK, data.nickname);
        return data;
      }
      return null;
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

  global.FGB = {
    getTerminalId: getTerminalId,
    me: me,
    register: register,
    ensureRegistered: ensureRegistered,
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
