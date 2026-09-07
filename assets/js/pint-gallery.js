(() => {
  const shelf = document.querySelector(".pint-shelf");
  if (!shelf) return;

  const cards = [...shelf.querySelectorAll(".pint-card")];
  const dialog = document.querySelector(".label-dialog");
  const status = document.getElementById("pint-status");
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const duration = 1100;

  const views = cards.map((card) => {
    const image = card.querySelector("img");
    const base = image.src.replace(/frame-00\.webp(?:\?.*)?$/, "");
    return {
      card,
      image,
      link: card.querySelector(".pint-stage"),
      button: card.querySelector(".pint-turn"),
      labelButton: card.querySelector(".pint-label-read"),
      sources: Array.from({ length: 31 }, (_, frame) =>
        `${base}frame-${String(frame).padStart(2, "0")}.webp`
      ),
      position: 0,
      target: 0,
      animation: 0,
      token: 0,
      timer: 0,
      ready: null,
      framesReady: false,
      loads: [],
      pinned: false,
      pointerType: "",
    };
  });

  function loadFrame(view, frame) {
    if (!view.loads[frame]) {
      const image = new Image();
      image.src = view.sources[frame];
      view.loads[frame] = image.decode().then(() => view.sources[frame]);
    }
    return view.loads[frame];
  }

  function prepare(view) {
    if (!view.ready) {
      view.ready = Promise.all(view.sources.map((_, frame) => loadFrame(view, frame)))
        .then(() => { view.framesReady = true; });
    }
    return view.ready;
  }

  function setLoading(view, loading) {
    if (loading) {
      view.card.dataset.loading = "true";
      view.link.setAttribute("aria-busy", "true");
    } else {
      delete view.card.dataset.loading;
      view.link.removeAttribute("aria-busy");
    }
  }

  function show(view, position) {
    view.position = position;
    const frame = Math.max(0, Math.min(30, Math.round(position)));
    view.image.src = view.sources[frame];
    view.card.dataset.frame = String(frame);
    // The text alternative belongs to the back-label state, not only its final
    // frame. Reveal it with the button-label change so it is available while
    // the pint is turning instead of appearing a beat after the animation.
    view.labelButton.hidden = view.target !== 30;
  }

  async function turn(view, back) {
    const token = ++view.token;
    cancelAnimationFrame(view.animation);
    view.target = back ? 30 : 0;
    view.button.firstChild.textContent = back ? "Show flavor " : "Turn pint ";
    view.button.setAttribute("aria-pressed", String(back));
    view.labelButton.hidden = !back;
    delete view.card.dataset.error;
    setLoading(view, true);

    try {
      if (reducedMotion.matches) {
        await loadFrame(view, view.target);
        if (token !== view.token) return;
        show(view, view.target);
        setLoading(view, false);
        return;
      }

      if (!view.framesReady) {
        // The requested face is the useful response to a cold interaction.
        // Decode it first and keep the animation frames warming in the
        // background; later turns use the complete smooth sequence.
        const endpoint = loadFrame(view, view.target);
        prepare(view).catch(() => {});
        await endpoint;
        if (token !== view.token) return;
        if (!view.framesReady) {
          show(view, view.target);
          setLoading(view, false);
          return;
        }
      }
    } catch {
      status.textContent = "Rotation unavailable. The case links still work.";
      setLoading(view, false);
      view.card.dataset.error = "true";
      view.button.hidden = true;
      return;
    }
    if (token !== view.token) return;

    if (reducedMotion.matches) {
      show(view, view.target);
      return;
    }

    const from = view.position;
    const to = view.target;
    const start = performance.now();
    const runFor = duration * (Math.abs(to - from) / 30);
    const tick = (now) => {
      const progress = runFor ? Math.min(1, (now - start) / runFor) : 1;
      const eased = progress * progress * (3 - 2 * progress);
      show(view, from + (to - from) * eased);
      if (progress < 1) view.animation = requestAnimationFrame(tick);
      else setLoading(view, false);
    };
    view.animation = requestAnimationFrame(tick);
  }

  function select(view, pinned = false) {
    views.forEach((other) => {
      clearTimeout(other.timer);
      if (other !== view) {
        other.pinned = false;
        if (other.target !== 0 || other.position !== 0) turn(other, false);
      }
    });
    view.pinned = pinned;
    turn(view, true);
  }

  dialog.querySelector(".label-dialog-close").addEventListener("click", () => dialog.close());

  views.forEach((view) => {
    view.button.hidden = false;
    show(view, 0);

    view.link.addEventListener("pointerdown", (event) => {
      view.pointerType = event.pointerType;
    });
    view.link.addEventListener("pointerenter", (event) => {
      if (event.pointerType !== "mouse") return;
      clearTimeout(view.timer);
      if (!reducedMotion.matches) prepare(view).catch(() => {});
      view.timer = setTimeout(() => select(view), 140);
    });
    view.card.addEventListener("pointerleave", (event) => {
      if (event.pointerType === "mouse" && !view.pinned) {
        clearTimeout(view.timer);
        view.timer = setTimeout(() => turn(view, false), 170);
      }
    });
    view.link.addEventListener("focus", () => {
      /* Touch moves focus before click. Let the click handler own that gesture
         so its first tap turns the pint instead of navigating immediately. */
      if (view.pointerType && view.pointerType !== "mouse") return;
      select(view);
    });
    view.card.addEventListener("focusout", (event) => {
      if (!view.card.contains(event.relatedTarget) && !view.pinned) turn(view, false);
    });
    view.link.addEventListener("click", (event) => {
      if (view.pointerType && view.pointerType !== "mouse" && view.target === 0) {
        event.preventDefault();
        select(view, true);
      }
      view.pointerType = "";
    });
    view.button.addEventListener("click", () => {
      clearTimeout(view.timer);
      const showBack = view.target !== 30;
      view.pinned = showBack;
      turn(view, showBack);
      status.textContent = `${view.card.getAttribute("aria-label")}: ${showBack ? "turning to case facts" : "turning to flavor label"}`;
    });
    view.labelButton.addEventListener("click", () => {
      clearTimeout(view.timer);
      view.pinned = true;
      dialog.querySelector("h2").textContent = view.card.getAttribute("aria-label");
      dialog.querySelector(".label-dialog-content").replaceChildren(
        view.card.querySelector(".pint-facts").content.querySelector("dl").cloneNode(true)
      );
      dialog.querySelector(".label-dialog-case").href = view.link.href;
      dialog.showModal();
    });
  });

  shelf.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || dialog.open) return;
    views.forEach((view) => {
      clearTimeout(view.timer);
      view.pinned = false;
      if (view.target !== 0 || view.position !== 0) turn(view, false);
    });
    status.textContent = "All flavor labels shown";
  });

  const motionChanged = () => views.forEach((view) => {
    if (view.ready || view.target === 30) turn(view, view.target === 30);
  });
  if (reducedMotion.addEventListener) reducedMotion.addEventListener("change", motionChanged);
  else reducedMotion.addListener(motionChanged);
})();
