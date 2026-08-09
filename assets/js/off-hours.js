/* Off hours reveal: fades each card up as it comes into view. Vanilla, no
   dependencies, no build step. Safe to load on every page -- it exits if there
   is no Off hours section.

   THE ANIMATION IS BEST-EFFORT. THE CONTENT IS NOT. That distinction is the
   whole design of this file, and it is why the hidden state is applied HERE
   rather than in the stylesheet: a page with no JavaScript, a blocked or 404ing
   script, or a browser that never fires the observer shows six cards, because
   nothing ever hid them. Move `opacity: 0` into style.scss and every one of
   those cases renders the section blank instead.

   Both failure modes below were observed during design, not imagined:
   IntersectionObserver delivered no entries at all in one environment, and a
   requestAnimationFrame loop produced no frames in a hidden document. In each
   case the cards stayed at opacity 0 and the section rendered empty. So there
   are three floors, none of which depends on a frame or a callback:

     1. never hide anything if the document is already hidden at mount, which
        also covers print, PDF export and thumbnail capture;
     2. a timer that clears the hidden state on anything still hidden, whatever
        the reason;
     3. a visibilitychange listener, for a tab backgrounded mid-animation --
        transitions and observers both stall there and the timer above may
        already have fired.

   The reduced-motion check is in this file and not only in the stylesheet for
   the same reason: under `reduce` the script must not APPLY the hidden state,
   because a suppressed transition on a hidden card leaves it hidden forever
   rather than revealing it instantly. */

(function () {
  var section = document.querySelector('.off-hours');
  if (!section) return;

  var grid = section.querySelector('.off-hours-grid');
  var cards = Array.prototype.slice.call(
    section.querySelectorAll('.off-hours-card')
  );
  if (!grid || !cards.length) return;

  /* Floor 1. Nothing is looking at this document, so there is no reveal to
     play -- and whatever renders it may never run a frame. */
  if (document.hidden) return;

  /* Not a progressive enhancement to be suppressed later: under `reduce` the
     cards are simply never hidden in the first place. */
  var reduced = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)');
  if (reduced && reduced.matches) return;

  /* Play a card in. The delay has to be set BEFORE the attribute comes off:
     the transition is computed at the moment the hidden state is removed. */
  function reveal(card, delay) {
    card.style.transitionDelay = delay + 'ms';
    card.removeAttribute('data-reveal');
  }

  /* Every floor calls this, so it clears the stagger rather than honouring it:
     a floor is a rescue, not an animation.

     It touches only cards that are STILL HIDDEN. Rewriting transition-delay on
     a card already mid-transition restarts it, and the 1200ms timer would
     otherwise do exactly that to anything revealed just before it fired. */
  function showAll() {
    for (var i = 0; i < cards.length; i++) {
      if (!cards[i].hasAttribute('data-reveal')) continue;
      cards[i].style.transitionDelay = '0ms';
      cards[i].removeAttribute('data-reveal');
    }
  }

  /* The stagger runs across a row, so it needs the column count -- which is a
     media query the script cannot read directly. Counting the grid's resolved
     tracks works at every breakpoint without duplicating the breakpoints here.
     Falls back to 1, which is simply no stagger. */
  function columns() {
    var tracks = getComputedStyle(grid).gridTemplateColumns;
    if (!tracks || tracks === 'none') return 1;
    return tracks.split(' ').filter(Boolean).length || 1;
  }

  for (var i = 0; i < cards.length; i++) {
    cards[i].setAttribute('data-reveal', 'hidden');
  }

  /* Floor 2. Whatever happens above, nothing stays hidden past this. */
  var floor = setTimeout(showAll, 1200);

  /* Floor 3. A backgrounded tab stops delivering both frames and observer
     callbacks, and may do so after the timer has already run. */
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) showAll();
  });

  /* No observer support: the cards are already visible content, so show them
     and stop. Cancel the timer first so it has nothing left to do. */
  if (typeof IntersectionObserver !== 'function') {
    clearTimeout(floor);
    showAll();
    return;
  }

  /* Trigger when a card's top passes 94% of the viewport height. Trimming 6%
     off the root's bottom edge is what expresses that: intersection begins
     once the element reaches the remaining 94%. */
  var observer = new IntersectionObserver(function (entries) {
    for (var j = 0; j < entries.length; j++) {
      if (!entries[j].isIntersecting) continue;
      var card = entries[j].target;
      var index = cards.indexOf(card);
      reveal(card, (index % columns()) * 70);
      observer.unobserve(card);
    }
  }, { rootMargin: '0px 0px -6% 0px' });

  for (var k = 0; k < cards.length; k++) observer.observe(cards[k]);
})();
