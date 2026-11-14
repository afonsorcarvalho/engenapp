/* One-shot hero spin for /marsp.
 *
 * The inline gate in <head> adds .v-spin to <html> only when the spin may run (JS on, no reduced
 * motion, no Save-Data). Under .v-spin the still is hidden but keeps its box. This script loads the
 * frames, plays them once on a canvas laid over that box (3 s, ease-out), then reveals the
 * high-resolution still, which is the same pose in the same box, and removes the canvas.
 * Any failure or timeout reveals the still instead. No globals.
 */
(function () {
  'use strict';

  var root = document.documentElement;
  if (!root.classList.contains('v-spin')) return;
  root.setAttribute('data-spin', 'loading');        // tells the gate's safety timer we took over

  var DURATION = 3000;
  var FIRST_TIMEOUT = 1500;
  var ALL_TIMEOUT = 6000;
  var VERSION = '?v=1';

  var img = document.querySelector('.v-hero__machine img');
  var slot = img && img.parentNode;
  var canvas = null;
  var finished = false;
  var t0 = performance.now();

  function pad(n) { return ('000' + n).slice(-4); }

  function fallback() {
    if (finished) return;
    finished = true;
    if (canvas && canvas.parentNode) canvas.parentNode.removeChild(canvas);
    root.classList.add('v-spin-fallback');           // fades the still in
    root.classList.remove('v-spin');
    root.setAttribute('data-spin', 'fallback');
  }

  function load(src) {
    return new Promise(function (resolve, reject) {
      var im = new Image();
      im.decoding = 'async';
      im.onload = function () {
        (im.decode ? im.decode() : Promise.resolve()).then(function () { resolve(im); }, function () { resolve(im); });
      };
      im.onerror = function () { reject(new Error('frame failed: ' + src)); };
      im.src = src;
    });
  }

  function withTimeout(promise, ms) {
    var left = Math.max(0, ms - (performance.now() - t0));
    return Promise.race([promise, new Promise(function (_, reject) {
      setTimeout(function () { reject(new Error('timeout')); }, left);
    })]);
  }

  function whenVisible() {
    if (!document.hidden) return Promise.resolve();
    return new Promise(function (resolve) {
      document.addEventListener('visibilitychange', function on() {
        if (!document.hidden) { document.removeEventListener('visibilitychange', on); resolve(); }
      });
    });
  }

  /* Canvas covers the <img> box exactly; frames are drawn with the same "contain, centred" math
     the still uses, so the last frame and the still land on the same pixels. */
  var box = { w: 0, h: 0, dpr: 0 };
  function fit(ctx) {
    var w = img.clientWidth, h = img.clientHeight, dpr = window.devicePixelRatio || 1;
    if (w !== box.w || h !== box.h || dpr !== box.dpr) {
      box = { w: w, h: h, dpr: dpr };
      canvas.style.left = img.offsetLeft + 'px';
      canvas.style.top = img.offsetTop + 'px';
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.imageSmoothingQuality = 'high';
    }
  }
  function draw(ctx, frame) {
    fit(ctx);
    var cw = canvas.width, ch = canvas.height;
    var s = Math.min(cw / frame.naturalWidth, ch / frame.naturalHeight);
    var dw = frame.naturalWidth * s, dh = frame.naturalHeight * s;
    ctx.clearRect(0, 0, cw, ch);
    ctx.drawImage(frame, (cw - dw) / 2, (ch - dh) / 2, dw, dh);
  }

  try {
    if (!img || !window.Promise || !window.requestAnimationFrame) throw new Error('unsupported');
    var phone = window.matchMedia('(max-width: 760px)').matches;
    var count = phone ? 30 : 60;
    var dir = phone ? 'hero-seq-m/' : 'hero-seq/';
    // Resolve against the still's served URL: works whether assets come from /afr_labquali_website/static/
    // or through the /marsp/ controller.
    var urls = [];
    for (var i = 1; i <= count; i++) urls.push(new URL(dir + 'h_' + pad(i) + '.webp' + VERSION, img.src).href);

    canvas = document.createElement('canvas');
    canvas.className = 'v-hero__spin';
    canvas.setAttribute('aria-hidden', 'true');
    slot.appendChild(canvas);
    var ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('no 2d context');

    var first = load(urls[0]);
    var rest = Promise.all(urls.slice(1).map(load));
    var still = img.complete && img.naturalWidth
      ? (img.decode ? img.decode() : Promise.resolve())
      : new Promise(function (resolve, reject) { img.addEventListener('load', resolve); img.addEventListener('error', reject); })
          .then(function () { return img.decode ? img.decode() : null; });
    rest.catch(function () {});
    still.catch(function () {});

    withTimeout(first, FIRST_TIMEOUT).then(function (f1) {
      if (finished) return null;
      draw(ctx, f1);
      canvas.classList.add('is-on');                 // short CSS fade-in of frame 1
      return withTimeout(Promise.all([rest, still]), ALL_TIMEOUT).then(function (res) {
        return [f1].concat(res[0]);
      });
    }).then(function (frames) {
      if (!frames || finished) return null;
      return whenVisible().then(function () { play(ctx, frames); });
    }).catch(fallback);
  } catch (e) {
    fallback();
  }

  function play(ctx, frames) {
    if (finished) return;
    root.setAttribute('data-spin', 'playing');
    root.setAttribute('data-spin-plays', String((+root.getAttribute('data-spin-plays') || 0) + 1));
    if (performance.mark) performance.mark('hero-spin-start');
    var start = null, last = frames.length - 1, shown = -1;

    function tick(now) {
      if (finished) return;
      try {
        if (start === null) start = now;
        var p = Math.min(1, (now - start) / DURATION);
        var eased = 1 - Math.pow(1 - p, 3);          // easeOutCubic on the frame index
        var idx = Math.round(eased * last);
        if (idx !== shown) { draw(ctx, frames[idx]); shown = idx; }
        if (p < 1) { requestAnimationFrame(tick); return; }
        finish();
      } catch (e) { fallback(); }
    }
    requestAnimationFrame(tick);
  }

  function finish() {
    finished = true;
    if (performance.mark) {
      performance.mark('hero-spin-end');
      try { performance.measure('hero-spin', 'hero-spin-start', 'hero-spin-end'); } catch (e) { /* ignore */ }
    }
    root.classList.remove('v-spin');                 // still (already decoded) appears under the canvas
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        if (canvas && canvas.parentNode) canvas.parentNode.removeChild(canvas);
        root.setAttribute('data-spin', 'done');
      });
    });
  }
})();
