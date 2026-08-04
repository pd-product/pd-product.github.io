/* Chapter rail: marks the chapter you are reading and fills the rail's top
   hairline as you move through the story. Vanilla, no dependencies, no build
   step. Safe to load on every page -- it exits if there is no rail.

   Without this file the rail still works: every entry is a live anchor link,
   and CSS handles hover and :target. This only adds the reading state. */

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

  function update() {
    var line = readLine();
    var active = headings[0];
    for (var i = 0; i < headings.length; i++) {
      if (headings[i].getBoundingClientRect().top <= line) active = headings[i];
    }
    setCurrent(active.id);

    var box = prose.getBoundingClientRect();
    var travelled = line - box.top;
    var total = box.height - line;
    var progress = total > 0 ? travelled / total : 0;
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
