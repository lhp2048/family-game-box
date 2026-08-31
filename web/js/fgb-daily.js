(function (global) {
  "use strict";

  function parseQuery() {
    var q = new URLSearchParams(global.location.search || "");
    return {
      daily: q.get("daily") === "1",
      runId: q.get("runId") || "",
      tier: q.get("tier") || "normal",
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

  global.FGBDaily = {
    parseQuery: parseQuery,
    isDaily: function () {
      return parseQuery().daily;
    },
    makeRng: makeRng,
    installMathRandom: installMathRandom,
    notifyStageDone: notifyStageDone,
    notifyAbort: notifyAbort,
  };
})(window);
