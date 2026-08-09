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
   are four floors:

     1. never hide anything if the document is already hidden at mount, which
        covers thumbnail capture and any renderer that never paints;
     2. a timer that un-hides everything IF THE OBSERVER NEVER CALLED BACK;
     3. a visibilitychange listener, for a tab backgrounded mid-animation --
        transitions and observers both stall there;
     4. a beforeprint listener, because printing renders the whole document
        including the part nobody has scrolled to yet.

   FLOOR 2 IS A DEAD-OBSERVER DETECTOR, NOT A DEADLINE, and the difference
   matters. The handoff specified a flat ~1200ms timer that cleared anything
   still hidden. Measured on the built page, this section starts at y=1665 and
   the desktop viewport is 900 tall, so it is NEVER on screen at load: that
   timer fired about a second before any reader could reach the section, and
   the reveal never played at all on a desktop. Every card was simply un-hidden
   off-screen.

   The fix relies on a guarantee in the IntersectionObserver spec: observe()
   queues an initial notification carrying the element's current state, whether
   or not it intersects. A live observer therefore always calls back within a
   frame or two of mount. One callback of any kind proves it works, so the
   timer is cancelled and the reveal is left to play whenever the reader
   arrives. No callback by 1200ms means the observer is the broken kind, and
   the cards go visible. Both the failure the handoff saw and the animation it
   asked for are preserved; a flat deadline cannot do both.

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

  /* Declared here rather than at the observer below, because showAll needs to
     disconnect it and the floors that call showAll are armed first. It stays
     null until there is something to disconnect. */
  var observer = null;

  /* Play a card in. The delay has to be set BEFORE the attribute comes off:
     the transition is computed at the moment the hidden state is removed. */
  function reveal(card, delay) {
    card.style.transitionDelay = delay + 'ms';
    card.removeAttribute('data-reveal');
  }

  /* Every floor calls this. A rescue is not an animation: it puts every card
     in its final state NOW, kills the transition outright, and stops the
     observer so nothing re-animates behind it.

     IT MUST TOUCH EVERY CARD, NOT ONLY THE STILL-HIDDEN ONES. `reveal` removes
     data-reveal at the START of a card's animation, so between then and ~640ms
     later (up to 140ms of stagger plus a 500ms transition) a card is
     unmarked and still transparent. An earlier version skipped unmarked cards
     to avoid restarting a transition; printing mid-reveal then captured
     opacities of 0.22, 0.014 and 0 -- two cards fully invisible on the page
     the floor exists to protect. Killing the transition is what makes touching
     them safe, and is why the flag goes on the SECTION: one attribute, one
     rule, no per-card inline styles to unpick. */
  function showAll() {
    section.setAttribute('data-reveal-done', '');
    if (observer) observer.disconnect();
    for (var i = 0; i < cards.length; i++) {
      cards[i].style.transitionDelay = '';
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

  /* Floor 2. Cancelled by the first observer callback of any kind -- see the
     note at the top: this detects an observer that never runs, and must not
     become a deadline the reader has to beat by scrolling. */
  var floor = setTimeout(showAll, 1200);

  /* Floor 3. A backgrounded tab stops delivering both frames and observer
     callbacks, so a card mid-transition would stay part-faded. */
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) showAll();
  });

  /* Floor 4. Printing renders the whole document, including everything below
     the reader's scroll position that has therefore never been revealed.

     TWO LISTENERS, because no single one covers every browser. beforeprint is
     the Chrome and Firefox route and runs early enough for the paint that
     follows. Safari does not implement it at all -- on desktop or iOS -- and
     instead flips a matchMedia('print') query, so Safari needs the second one
     or it prints a page of blank cards. Both call the same function, and
     showAll is idempotent, so a browser that fires both does no extra work. */
  addEventListener('beforeprint', showAll);

  var printQuery = window.matchMedia && window.matchMedia('print');
  if (printQuery) {
    /* ALREADY in print media at mount, which a `change` listener can never
       see: a renderer that loads the document straight into print media never
       transitions into it. Nothing else catches this either -- document.hidden
       is false, and the observer's initial callback cancels the 1200ms floor
       while reporting the cards as not intersecting. Measured before this
       line existed: loading under print media left all six at opacity 0. */
    if (printQuery.matches) showAll();

    if (printQuery.addEventListener) {
      printQuery.addEventListener('change', function (e) {
        if (e.matches) showAll();
      });
    } else if (printQuery.addListener) {
      /* Safari below 14 has only the deprecated form. */
      printQuery.addListener(function (q) {
        if (q.matches) showAll();
      });
    }
  }

  /* No observer support: the cards are already visible content, so show them
     and stop. Cancel the timer first so it has nothing left to do. */
  if (typeof IntersectionObserver !== 'function') {
    clearTimeout(floor);
    showAll();
    return;
  }

  /* Trigger when a card's top passes 94% of the viewport height. Trimming 6%
     off the root's bottom edge is what expresses that: intersection begins
     once the element reaches the remaining 94%.

     THE ENORMOUS TOP MARGIN IS NOT PADDING, IT IS WHAT MAKES THE TEST
     MONOTONIC, and without it the section can be left permanently blank.
     IntersectionObserver reports CHANGES to isIntersecting. With a plain root,
     a card that is below the viewport and then above it -- one jump, no
     intermediate frame -- is not intersecting at either end, so no change is
     reported and the callback never runs. The card stays hidden for the rest
     of the page's life, and scrolling back up does not help: it is above the
     trigger line, not below it.

     That is reachable in one click. `contact` is in the nav on every page and
     `/#contact` lands well past this section. Measured at 320x568 before this
     margin existed: after that jump all six cards sat above the viewport,
     all six still hidden, and scrolling back up revealed only the three that
     happened to re-cross the line.

     Extending the root 100000px upward means anything at or above the line is
     always inside it. isIntersecting then only ever goes false -> true, the
     jump is a change, and the callback fires. */
  observer = new IntersectionObserver(function (entries) {
    /* Proof of life. The spec guarantees an initial notification per observed
       element, so reaching this line at all means the observer works and the
       dead-observer floor must stand down. */
    clearTimeout(floor);

    for (var j = 0; j < entries.length; j++) {
      if (!entries[j].isIntersecting) continue;
      var card = entries[j].target;
      var index = cards.indexOf(card);
      reveal(card, (index % columns()) * 70);
      observer.unobserve(card);
    }
  }, { rootMargin: '100000px 0px -6% 0px' });

  for (var k = 0; k < cards.length; k++) observer.observe(cards[k]);
})();
