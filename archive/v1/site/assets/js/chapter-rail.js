/* Chapter rail: marks the chapter you are reading and fills the rail's top
   hairline as you move through the story. Vanilla, no dependencies, no build
   step. Safe to load on every page -- it exits if there is no rail.

   Without this file the rail still works as navigation: every entry is a live
   anchor link and CSS handles hover. There is NO current-chapter indication
   without it -- the accent bar is driven by the aria-current this script sets.
   A `:target` rule cannot supply one: :target matches the element whose own id
   equals the fragment, and the rail's anchors carry href="#situation" with no
   id of their own. Putting ids on them would collide with the heading ids that
   are the actual link targets. */

(function () {
  var rail = document.querySelector('.chapter-rail');
  var prose = document.querySelector('.story-prose');
  if (!rail || !prose) return;

  var headings = Array.prototype.slice.call(prose.querySelectorAll('h2[id]'));
  if (!headings.length) return;

  var links = {};
  Array.prototype.forEach.call(rail.querySelectorAll('a[href^="#"]'), function (a) {
    links[a.getAttribute('href').slice(1)] = a;
  });

  var current = null;

  function setCurrent(id) {
    if (id === current) return;
    if (current && links[current]) links[current].removeAttribute('aria-current');
    if (links[id]) links[id].setAttribute('aria-current', 'true');
    current = id;
  }

  /* The active chapter is the last heading whose top has passed the read line
     (a third of the way down the viewport). Scroll position, not intersection,
     so a chapter longer than the viewport stays marked. */
  var readLine = function () { return window.innerHeight / 3; };

  /* True once the page cannot scroll any further.

     Without this the final chapter is unreachable. The last section is usually
     shorter than the gap between the read line and the bottom of the viewport,
     so its heading never rises past the line however far you scroll, and the
     rail stays stuck on the second-to-last chapter. Clamping to the last
     heading at the bottom of the page is the fix; the progress fill has the
     same problem and is clamped with it. */
  function atBottom() {
    return window.innerHeight + window.scrollY >=
      document.documentElement.scrollHeight - 2;
  }

  function update() {
    var line = readLine();
    var bottom = atBottom();
    var active = headings[0];
    for (var i = 0; i < headings.length; i++) {
      if (headings[i].getBoundingClientRect().top <= line) active = headings[i];
    }
    if (bottom) active = headings[headings.length - 1];
    setCurrent(active.id);

    var box = prose.getBoundingClientRect();
    var travelled = line - box.top;
    var total = box.height - line;
    var progress = total > 0 ? travelled / total : 0;
    if (bottom) progress = 1;
    rail.style.setProperty('--rail-progress', Math.min(1, Math.max(0, progress)).toFixed(3));
  }

  var queued = false;
  function onScroll() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () { queued = false; update(); });
  }

  update();
  addEventListener('scroll', onScroll, { passive: true });
  addEventListener('resize', onScroll, { passive: true });
})();
