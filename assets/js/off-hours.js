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
     2. a fail-open timer that un-hides everything unless the observer has
        reported back by then;
     3. a visibilitychange listener, for a tab backgrounded mid-animation --
        transitions and observers both stall there;
     4. a beforeprint listener, because printing renders the whole document
        including the part nobody has scrolled to yet.

   FLOOR 2 IS A DEAD-OBSERVER DETECTOR FIRST AND A DEADLINE SECOND, and the
   difference from the handoff matters. It specified a flat ~1200ms timer that
   cleared anything still hidden. Measured on the built page, this section
   starts at y=1665 and the desktop viewport is 900 tall, so it is NEVER on
   screen at load: that timer fired about a second before any reader could
   reach the section, and the reveal never played at all on a desktop. Every
   card was simply un-hidden off-screen.

   The fix relies on a live observer always calling back once, even when
   nothing intersects. That falls out of the spec's own bookkeeping rather than
   from a sentence promising it: observe() records the target with
   `previousThresholdIndex` set to -1, and the update steps queue an entry
   whenever the computed thresholdIndex differs from it. -1 is not a value any
   computation produces, so the first pass always differs and always queues.

   So one callback of any kind proves the observer works: the timer is
   cancelled and the reveal is left to play whenever the reader arrives.
   Confirmed on the built page -- three seconds after an unscrolled desktop
   load the cards are still hidden, which is only possible if the floor was
   cancelled by a callback for cards nowhere near the viewport.

   1200ms IS A FAIL-OPEN DEADLINE, NOT A PROOF OF DEATH. The notification is
   delivered on a rendering update, and nothing bounds how long a stalled main
   thread can defer that. A live-but-late observer is therefore misread as dead
   and the cards are shown without animating. That is the correct way to be
   wrong here, and it is why showAll disconnects: a callback arriving after the
   deadline cannot re-hide or re-animate anything. The cost is the animation;
   the content is never at risk.

   Both the failure the handoff saw and the animation it asked for are
   preserved; a flat deadline cannot do both.

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
  var rescued = false;

  /* Cards whose animation has begun and not yet finished. Only these are worth
     rescuing when the tab goes away; see the visibilitychange floor. */
  var flying = [];

  function land(card) {
    var i = flying.indexOf(card);
    if (i !== -1) flying.splice(i, 1);
  }

  /* Play a card in. The delay has to be set BEFORE the attribute comes off:
     the transition is computed at the moment the hidden state is removed.

     The card counts as in flight until its stagger and transition have both
     had time to run. transitionend would be tidier but does not fire in a
     background tab, which is the case this bookkeeping exists for. */
  function reveal(card, delay) {
    card.style.transitionDelay = delay + 'ms';
    card.removeAttribute('data-reveal');
    flying.push(card);
    setTimeout(function () { land(card); }, delay + 600);
  }

  /* Finish just the cards that are mid-animation, and leave everything else
     armed. Used by the visibilitychange floor: a stalled transition is what
     needs saving, an untriggered card is not. */
  function settleFlying() {
    while (flying.length) {
      var card = flying.pop();
      card.style.transitionDelay = '';
      card.setAttribute('data-reveal-done', '');
    }
  }

  /* The full rescue, used by the mount, timer and print floors: every card in
     its final state NOW, transition killed, observer stopped so nothing
     re-animates behind it.

     IT MUST TOUCH EVERY CARD, NOT ONLY THE STILL-HIDDEN ONES. `reveal` removes
     data-reveal at the START of a card's animation, so for up to ~640ms -- 140
     of stagger plus a 500ms transition -- a card is unmarked and still
     transparent. An earlier version skipped unmarked cards to avoid restarting
     a transition; printing in that window captured opacities of 0.22, 0.014
     and 0, two cards fully invisible, on the very output the floor exists to
     protect. Killing the transition is what makes touching them safe.

     The done flag is PER CARD, not on the section, so settleFlying can use the
     same mechanism on a subset. */
  function showAll() {
    rescued = true;
    flying.length = 0;
    /* May be null when a floor fires before the observer is built -- the
       print-at-mount check does exactly that. `rescued` is what stops one
       being constructed afterwards. */
    if (observer) observer.disconnect();
    for (var i = 0; i < cards.length; i++) {
      cards[i].style.transitionDelay = '';
      cards[i].setAttribute('data-reveal-done', '');
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
     become a deadline the reader has to beat by SCROLLING. It is still a
     deadline for the observer itself -- see the header. */
  var floor = setTimeout(showAll, 1200);

  /* Floor 3. A backgrounded tab stops delivering frames, so a card caught
     mid-transition would stay part-faded when the tab is next shown.

     THIS FLOOR SETTLES ONLY WHAT IS IN FLIGHT. It does not call showAll, and
     the distinction has been wrong twice. First version: rescued on every
     hide, so switching tabs once before ever reaching the section forfeited
     the whole animation. Second version: rescued if any card had EVER
     started, so hiding the tab after the first card landed still forfeited the
     other five. A rescue finishes an animation that cannot finish itself; it
     has no business touching a card that has not been triggered. Those stay
     hidden, off-screen and armed, with the observer still live. */
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) settleFlying();
  });

  /* Floor 4. Printing renders the whole document, including everything below
     the reader's scroll position that has therefore never been revealed.

     beforeprint carries this in every current browser -- Chrome, Firefox and
     Safari, the last since Safari 13 and iOS 13, per MDN's compatibility data.
     It runs early enough for the paint that follows.

     The matchMedia('print') query below is NOT a Safari fallback. It is there
     for the case beforeprint cannot express: a renderer that is ALREADY in
     print media when the document loads never fires an event, because nothing
     transitions. That is checked at registration; the change listener beside
     it is cheap cover for a headless print pipeline that switches media
     without dispatching beforeprint.

     Both routes call the same function, and showAll is idempotent, so a
     browser that takes both does no extra work. */
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

  /* Nothing left to observe. Either a floor already fired -- the print-media
     check above runs before this point and can rescue everything -- or there
     is no IntersectionObserver to build, in which case the cards are visible
     content and simply stay visible. Building an observer after a rescue would
     leave a live callback writing transitionDelay onto finished cards. */
  if (rescued || typeof IntersectionObserver !== 'function') {
    clearTimeout(floor);
    showAll();
    return;
  }

  /* Trigger when a card's top passes 94% of the viewport height. Trimming 6%
     off the root's bottom edge is what expresses that: intersection begins
     once the element reaches the remaining 94%.

     THE ENORMOUS TOP MARGIN IS NOT PADDING, IT IS WHAT MAKES THE TEST
     MONOTONIC. IntersectionObserver reports CHANGES to isIntersecting. With a
     plain root, a card that is below the viewport and then above it -- one
     jump, no intermediate frame -- is not intersecting at either end, so no
     change is reported and the callback never runs. The card is left marked
     hidden while sitting above the reader.

     That is reachable in one click: `contact` is in the nav on every page and
     `/#contact` lands well past this section. Measured at 320x568 before this
     margin existed, after that jump all six cards sat above the viewport and
     all six were still marked hidden.

     To be accurate about the consequence, because an earlier version of this
     note overstated it: those cards are not lost for the life of the page. A
     reader who scrolls back up re-enters them through the root's top edge,
     which IS a change, and they reveal then. The real defects are that content
     above the reader is in a hidden state at all -- printing renders the whole
     document, as does a full-page capture -- and that scrolling UPWARD triggers an
     entrance animation on cards the reader has already passed, which is
     backwards.

     Extending the root 100000px upward means anything at or above the line is
     always inside it. isIntersecting then only ever goes false -> true, the
     jump is a change, and a card that has been passed counts as seen. */
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
