/* Off hours reveal: fades each card up as it comes into view. Vanilla, no
   dependencies, no build step. Safe to load on every page -- it exits if there
   is no Off hours section.

   THE ANIMATION IS BEST-EFFORT. THE CONTENT IS NOT. That distinction is the
   whole design of this file, and it is why the hidden state is applied HERE
   rather than in the stylesheet: a page with no JavaScript, a blocked or 404ing
   script, or a browser that never fires the observer shows six cards, because
   nothing ever hid them. Move `opacity: 0` into style.scss and every one of
   those cases renders the section blank instead.

   NOTHING IS HIDDEN UNTIL THE READER SCROLLS. That is the primary guarantee,
   and everything below it is a backstop. A renderer that reads the document
   without scrolling -- a full-page capture, an archiver, a print, a
   reader-mode extraction -- never triggers the arming pass and therefore sees
   six plain visible cards. The full explanation, and the measurement that
   forced it, is on `arm` below.

   Four floors cover the cases where the reveal HAS been armed and then cannot
   finish:

     1. never arm at all if the document is already hidden at mount, which
        covers thumbnail capture and any renderer that never paints;
     2. a fail-open timer that un-hides everything unless the observer has
        reported back by then;
     3. a visibilitychange listener, which settles only the cards actually
        mid-fade -- transitions stall in a background tab;
     4. two print routes, because printing renders the whole document including
        the part nobody has scrolled to.

   FLOOR 2 IS A DEAD-OBSERVER DETECTOR FIRST AND A DEADLINE SECOND, and the
   difference from the handoff matters. It specified a flat ~1200ms timer from
   page load that cleared anything still hidden. Measured on the built page,
   this section starts at y=1665 against a 900px desktop viewport, so it is
   never on screen at load: that timer fired about a second before any reader
   could reach the section, and the reveal never played at all on a desktop.
   Arming on scroll fixes the same problem from the other end, and the timer
   now starts from the arming moment rather than from load.

   The detector relies on a live observer always calling back once, even when
   nothing intersects. That falls out of the spec's own bookkeeping rather than
   from a sentence promising it: observe() records the target with
   `previousThresholdIndex` set to -1, and the update steps queue an entry
   whenever the computed thresholdIndex differs from it. -1 is not a value any
   computation produces, so the first pass always differs and always queues.

   1200ms IS STILL A FAIL-OPEN DEADLINE, NOT A PROOF OF DEATH. The notification
   is delivered on a rendering update, and nothing bounds how long a stalled
   main thread can defer that. A live-but-late observer is therefore misread as
   dead and its cards are shown without animating. That is the correct way to
   be wrong here, and it is why showAll disconnects: a callback arriving after
   the deadline cannot re-hide or re-animate anything. The cost is the
   animation; the content is never at risk.

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

  /* The four numbers this file runs on. THREE OF THEM ARE COUPLED TO
     style.scss and cannot be changed alone:

       TRIGGER and TRIM are the same threshold written twice, once for the
       arming pass in JavaScript and once for the observer's root margin, which
       only takes a CSS length. 0.94 and -6% must always sum to 1.

       TRANSITION mirrors the .5s on .off-hours-card. It sizes the backstop
       that closes the in-flight window when transitionend cannot fire.
       SETTLE_SLACK is a whole extra TRANSITION on purpose: overshooting that
       window is free, undershooting it silently breaks the visibilitychange
       floor, and no wall clock can know when the transition actually started.

       STAGGER is per column index, so a 3-up row runs 0 / 70 / 140ms. */
  var TRIGGER = 0.94;
  var TRIM = '-6%';
  var TRANSITION = 500;
  var SETTLE_SLACK = 500;
  var STAGGER = 70;

  /* Declared here rather than at the observer below, because showAll needs to
     disconnect it and the floors that call showAll are armed first. It stays
     null until there is something to disconnect. */
  var observer = null;
  var rescued = false;
  var armed = false;

  /* Cards whose animation has begun and not yet finished. Only these are worth
     rescuing when the tab goes away; see the visibilitychange floor. */
  var flying = [];

  function land(card) {
    var i = flying.indexOf(card);
    if (i !== -1) flying.splice(i, 1);
  }

  /* Play a card in. The delay has to be set BEFORE the attribute comes off:
     the transition is computed at the moment the hidden state is removed.

     TWO WAYS OUT, and the asymmetry is deliberate. transitionend is the exact
     signal and lands the card the moment it really finishes. It cannot be the
     only one, because it does not fire in a background tab -- which is the
     case this bookkeeping exists for. So a timer backs it up.

     The timer is sized to OVERSHOOT. Leaving a card in `flying` too long costs
     nothing: settleFlying would set a done flag on a card that already looks
     done. Leaving it too short is the actual bug -- the card drops out while
     still fading and a later hide no longer settles it -- and a wall clock
     cannot know when the transition really began, since style resolution and
     the first frame can both be delayed. Hence a full extra TRANSITION of
     slack rather than a tight cushion. */
  function reveal(card, delay) {
    card.style.transitionDelay = delay + 'ms';
    card.removeAttribute('data-reveal');
    flying.push(card);

    var done = function () {
      card.removeEventListener('transitionend', done);
      land(card);
    };
    card.addEventListener('transitionend', done);
    setTimeout(done, delay + TRANSITION + SETTLE_SLACK);
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

  /* NOTHING IS HIDDEN UNTIL THE READER SCROLLS, and that is what makes the
     reveal safe rather than merely floored.

     Hiding at mount means any renderer that never scrolls sees the hidden
     state. Measured with Chrome's full-page capture on the built page: the
     whole Off hours grid came out blank, because the capture neither scrolls
     nor waits out a transition. document.hidden is false there, no print event
     fires, and the two resize events it does emit report an innerHeight of 1
     -- there is no signal from inside the page that says "this is a capture".

     So the arming moment moves instead. Before the first scroll every card is
     simply visible, which is the correct rendering for anything that reads the
     document without scrolling it: a capture, an archiver, a reader-mode
     extraction, a print. On the first scroll -- of any kind, including a
     fragment jump -- the cards still below the trigger line are hidden and the
     observer takes over. Those are exactly the cards that were going to
     animate anyway, and they are off-screen when it happens, so there is
     nothing to see. A reader gets the full reveal; a machine gets the content.

     This also makes the floors below narrower in scope: they now only ever run
     against a page a human has already scrolled. */
  function arm() {
    if (armed || rescued) return;
    armed = true;
    removeEventListener('scroll', arm);

    var line = window.innerHeight * TRIGGER;
    var pending = [];
    for (var i = 0; i < cards.length; i++) {
      if (cards[i].getBoundingClientRect().top > line) {
        cards[i].setAttribute('data-reveal', 'hidden');
        pending.push(cards[i]);
      }
    }

    /* Nothing below the line, so there is nothing to reveal and the section
       stays exactly as it rendered. This ARMS PERMANENTLY WITH NOTHING TO DO,
       which is intended rather than a leak: it is what happens when the page
       loads at a fragment past this section -- /#contact, a restored scroll
       position, a back navigation -- and the browser's own scroll to that
       fragment is the scroll that arms us. Every card is above the line, so
       every card counts as already seen. Measured: loading /#contact leaves
       all six visible, and they stay visible whichever way the reader scrolls
       afterwards. The animation is skipped for that visit, which is the right
       call for a reader who arrived past it, and no content is ever at risk. */
    if (!pending.length) return;

    /* Floor 2. Cancelled by the first observer callback of any kind -- see the
       note at the top: this detects an observer that never runs, and must not
       become a deadline the reader has to beat by SCROLLING. It is still a
       deadline for the observer itself -- see the header. */
    floor = setTimeout(showAll, 1200);

    startObserving(pending);
  }

  var floor = null;
  addEventListener('scroll', arm, { passive: true });

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

  /* Without IntersectionObserver there is nothing to arm: the scroll listener
     is never attached, so the cards are never hidden and simply stay visible
     content. Nothing to fall back to, because nothing was taken away. */
  if (typeof IntersectionObserver !== 'function') {
    removeEventListener('scroll', arm);
    return;
  }

  /* Trigger when a card's top passes 94% of the viewport height. Trimming 6%
     off the root's bottom edge is what expresses that: intersection begins
     once the element reaches the remaining 94%. Top and bottom percentages
     resolve against the root's HEIGHT -- probed at 1440x900, 390x844,
     1000x1000 and 1600x500, the trigger sat at 93.1 to 93.8 percent of height
     at every aspect ratio.

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
     above the reader sits in a hidden state at all, and that scrolling UPWARD
     triggers an entrance animation on cards the reader has already passed,
     which is backwards.

     Extending the root 100000px upward means anything at or above the line is
     always inside it. isIntersecting then only ever goes false -> true, the
     jump is a change, and a card that has been passed counts as seen. */
  function startObserving(pending) {
    observer = new IntersectionObserver(function (entries) {
      /* Proof of life: reaching this line at all means the observer runs, so
         the dead-observer floor stands down. See the header for why one
         callback always arrives on a working observer. */
      clearTimeout(floor);

      for (var j = 0; j < entries.length; j++) {
        if (!entries[j].isIntersecting) continue;
        var card = entries[j].target;
        var index = cards.indexOf(card);
        reveal(card, (index % columns()) * STAGGER);
        observer.unobserve(card);
      }
    }, { rootMargin: '100000px 0px ' + TRIM + ' 0px' });

    for (var k = 0; k < pending.length; k++) observer.observe(pending[k]);
  }
})();
