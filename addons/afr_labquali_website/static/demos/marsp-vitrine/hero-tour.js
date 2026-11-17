/* One-shot camera tour for the /marsp hero — still first, video only when ready.
 *
 * The still (hero-bg.webp, full-bleed backdrop on wide screens) is a normal <img> and paints immediately; it is also the
 * tour's last frame. The inline gate in <head> adds .v-tour-ok to <html> only when the tour may run
 * (no reduced motion, no Save-Data, not Safari: no VP9 alpha there). This script then loads a muted
 * WebM (VP9 + alpha, same full-bleed frame as the still) in the background on the same layer. Only when the
 * browser says it can play through does it fade the video in over the still and play it once; the
 * last frame hands back to the still with no visible jump. If the video is not ready within
 * READY_TIMEOUT, or anything fails, the download is dropped and the still simply stays.
 * No globals.
 */
(function () {
  'use strict';

  var root = document.documentElement;
  if (!root.classList.contains('v-tour-ok')) return;

  var READY_TIMEOUT = 6000;
  var VERSION = '?v=3';

  var img = document.querySelector('.v-hero__machine img');
  var slot = img && img.closest('.v-hero__machine');
  if (!img || !slot) return;

  var video = null;
  var done = false;

  function drop(state) {
    if (done) return;
    done = true;
    root.setAttribute('data-tour', state);
    if (video) {
      video.removeAttribute('src');
      try { video.load(); } catch (e) { /* ignore */ }   // stops any pending download
      if (video.parentNode) video.parentNode.removeChild(video);
    }
    root.classList.remove('v-touring');
  }

  function handBack() {
    if (done) return;
    done = true;
    root.setAttribute('data-tour', 'done');
    // Last frame == still: show the still instantly under the video, then remove the video.
    img.style.transition = 'none';
    root.classList.remove('v-touring');
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        if (video && video.parentNode) video.parentNode.removeChild(video);
        img.style.transition = '';
      });
    });
  }

  try {
    video = document.createElement('video');
    video.className = 'v-hero__tour';
    video.setAttribute('aria-hidden', 'true');
    video.muted = true;
    video.defaultMuted = true;
    video.playsInline = true;
    video.setAttribute('playsinline', '');
    video.setAttribute('muted', '');
    video.preload = 'auto';
    video.src = new URL('hero-tour.webm' + VERSION, img.src).href;
    slot.appendChild(video);
    root.setAttribute('data-tour', 'loading');

    var timer = setTimeout(function () { drop('timeout'); }, READY_TIMEOUT);
    video.addEventListener('error', function () { clearTimeout(timer); drop('error'); });
    video.addEventListener('canplaythrough', function () {
      clearTimeout(timer);
      if (done) return;
      var p = video.play();
      if (p && p.catch) p.catch(function () { drop('blocked'); });
    }, { once: true });
    video.addEventListener('playing', function () {
      if (done) return;
      root.setAttribute('data-tour', 'playing');
      video.classList.add('is-on');
      root.classList.add('v-touring');              // still fades out under the video
    }, { once: true });
    video.addEventListener('ended', handBack);
  } catch (e) {
    drop('error');
  }
})();
