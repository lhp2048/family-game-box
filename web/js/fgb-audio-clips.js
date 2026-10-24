/**
 * fgb-audio-clips.js — fetch + decode short MP3 clips for low-latency SFX/voice.
 *
 * - warmNetwork(): start HTTP fetch on page load (no AudioContext required)
 * - unlock(): resume AudioContext + decode cached ArrayBuffers (call on user gesture)
 * - preloadAll(): unlock + ensure every clipId is decoded
 * - play(id, onDone): play decoded buffer; waits briefly if still loading
 */
(function (global) {
  "use strict";

  function FgbAudioClips(options) {
    var opts = options || {};
    var resolveUrl =
      typeof opts.resolveUrl === "function"
        ? opts.resolveUrl
        : function (id) {
            return id;
          };
    var clipIds = opts.clipIds || [];

    var ctx = null;
    var unlocked = false;
    var buffers = {};
    var raw = {};
    var fetchPromises = {};
    var decodePromises = {};
    var bad = {};
    var playToken = 0;
    var activeSource = null;

    function getCtx() {
      if (ctx) return ctx;
      var AC = global.AudioContext || global.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
      return ctx;
    }

    function html5Unlock() {
      try {
        var silent = new Audio(
          "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA"
        );
        silent.volume = 0.01;
        var p = silent.play();
        if (p && p.then) p.catch(function () {});
      } catch (e) {}
    }

    function fetchClip(id) {
      if (bad[id] || buffers[id] || raw[id]) {
        return Promise.resolve(buffers[id] || null);
      }
      if (fetchPromises[id]) return fetchPromises[id];
      var url = resolveUrl(id);
      fetchPromises[id] = fetch(url)
        .then(function (res) {
          if (!res.ok) throw new Error("http " + res.status);
          return res.arrayBuffer();
        })
        .then(function (buf) {
          raw[id] = buf;
          delete fetchPromises[id];
          return decodeClip(id);
        })
        .catch(function () {
          bad[id] = true;
          delete fetchPromises[id];
          return null;
        });
      return fetchPromises[id];
    }

    function decodeClip(id) {
      if (bad[id]) return Promise.resolve(null);
      if (buffers[id]) return Promise.resolve(buffers[id]);
      if (!raw[id]) return fetchClip(id);
      if (decodePromises[id]) return decodePromises[id];
      var audioCtx = getCtx();
      if (!audioCtx) {
        return Promise.resolve(null);
      }
      decodePromises[id] = audioCtx
        .decodeAudioData(raw[id].slice(0))
        .then(function (decoded) {
          buffers[id] = decoded;
          delete raw[id];
          delete decodePromises[id];
          return decoded;
        })
        .catch(function () {
          bad[id] = true;
          delete decodePromises[id];
          return null;
        });
      return decodePromises[id];
    }

    function warmNetwork() {
      clipIds.forEach(function (id) {
        if (!bad[id] && !buffers[id] && !raw[id] && !fetchPromises[id]) {
          fetch(resolveUrl(id))
            .then(function (res) {
              if (!res.ok) throw new Error("http");
              return res.arrayBuffer();
            })
            .then(function (buf) {
              raw[id] = buf;
              if (unlocked) decodeClip(id);
            })
            .catch(function () {
              bad[id] = true;
            });
        }
      });
    }

    function unlock() {
      if (unlocked) {
        var c = getCtx();
        if (c && c.state === "suspended") {
          return c.resume().then(function () {
            return preloadAll();
          });
        }
        return preloadAll();
      }
      unlocked = true;
      html5Unlock();
      var audioCtx = getCtx();
      if (!audioCtx) {
        return Promise.resolve();
      }
      return audioCtx.resume().then(function () {
        return preloadAll();
      }).catch(function () {
        return preloadAll();
      });
    }

    function preloadAll() {
      warmNetwork();
      return Promise.all(
        clipIds.map(function (id) {
          return decodeClip(id).catch(function () {
            return null;
          });
        })
      );
    }

    function readyPromise(id, timeoutMs) {
      timeoutMs = timeoutMs == null ? 8000 : timeoutMs;
      if (bad[id]) return Promise.resolve(false);
      if (buffers[id]) return Promise.resolve(true);
      var work = decodeClip(id).then(function (b) {
        return !!b;
      });
      return Promise.race([
        work,
        new Promise(function (resolve) {
          global.setTimeout(function () {
            resolve(!!buffers[id]);
          }, timeoutMs);
        }),
      ]);
    }

    function stopSourceOnly() {
      if (activeSource) {
        try {
          activeSource.onended = null;
          activeSource.stop(0);
        } catch (e) {}
        try {
          activeSource.disconnect();
        } catch (e2) {}
        activeSource = null;
      }
    }

    function stop() {
      playToken += 1;
      stopSourceOnly();
    }

    function play(id, onDone) {
      if (!id) {
        if (onDone) onDone(false);
        return false;
      }
      if (bad[id]) {
        if (onDone) onDone(false);
        return false;
      }
      var myToken = playToken;
      readyPromise(id, 6000).then(function (ready) {
        if (myToken !== playToken) return;
        if (!ready || !buffers[id]) {
          if (onDone) onDone(false);
          return;
        }
        var audioCtx = getCtx();
        if (!audioCtx) {
          if (onDone) onDone(false);
          return;
        }
        function startPlayback() {
          if (myToken !== playToken) return;
          stopSourceOnly();
          try {
            var source = audioCtx.createBufferSource();
            source.buffer = buffers[id];
            source.connect(audioCtx.destination);
            source.onended = function () {
              if (myToken !== playToken) return;
              activeSource = null;
              if (onDone) onDone(true);
            };
            activeSource = source;
            source.start(0);
          } catch (e) {
            bad[id] = true;
            if (onDone) onDone(false);
          }
        }
        if (audioCtx.state === "suspended") {
          audioCtx.resume().then(startPlayback).catch(function () {
            if (onDone) onDone(false);
          });
        } else {
          startPlayback();
        }
      });
      return true;
    }

    function isReady(id) {
      return !!buffers[id];
    }

    function allReady() {
      for (var i = 0; i < clipIds.length; i++) {
        var id = clipIds[i];
        if (!buffers[id] && !bad[id]) return false;
      }
      return true;
    }

    function isBad(id) {
      return !!bad[id];
    }

    return {
      warmNetwork: warmNetwork,
      unlock: unlock,
      preloadAll: preloadAll,
      readyPromise: readyPromise,
      play: play,
      stop: stop,
      isReady: isReady,
      allReady: allReady,
      isBad: isBad,
    };
  }

  global.FgbAudioClips = FgbAudioClips;
})(window);
