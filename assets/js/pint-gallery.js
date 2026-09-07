(() => {
  const shelf = document.querySelector(".pint-shelf");
  if (!shelf) return;

  const cards = [...shelf.querySelectorAll(".pint-card")];
  const dialog = document.querySelector(".label-dialog");
  const status = document.getElementById("pint-status");
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const duration = 1100;
  shelf.dataset.renderer = "persistent-canvas-v3";
  let mobilePreloadObserver = null;
  // Keep constrained connections on the small sequence. The richer
  // sequence is selected per pint, not downloaded globally at page load.
  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  const leanConnection = Boolean(connection && (connection.saveData || /(^|-)2g$/.test(connection.effectiveType || "")));

  const views = cards.map((card) => {
    const image = card.querySelector("img");
    const base = image.src.replace(/frame-00\.webp(?:\?.*)?$/, "");
    const rich = !leanConnection && image.getBoundingClientRect().width * (devicePixelRatio || 1) > 400;
    card.dataset.quality = rich ? "retina" : "lean";
    return {
      card,
      image,
      base,
      rich,
      sizes: image.getAttribute("sizes"),
      link: card.querySelector(".pint-stage"),
      button: card.querySelector(".pint-turn"),
      labelButton: card.querySelector(".pint-label-read"),
      sources: Array.from({ length: 31 }, (_, frame) => {
        const tier = rich ? (frame === 0 || frame === 30 ? "still-800/" : "motion-600/") : "";
        return `${base}${tier}frame-${String(frame).padStart(2, "0")}.webp`;
      }),
      position: 0,
      target: 0,
      animation: 0,
      token: 0,
      presentationToken: 0,
      requestedFrame: -1,
      presentation: Promise.resolve(),
      canvas: null,
      context: null,
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
    view.labelButton.hidden = view.target !== 30;
    // Several animation ticks round to the same frame. Do not restart its
    // image request (or responsive-source selection) on every display refresh.
    if (frame === view.requestedFrame) return view.presentation;
    view.requestedFrame = frame;
    const token = ++view.presentationToken;
    const endpoint = frame === 0 || frame === 30;
    const filename = `frame-${String(frame).padStart(2, "0")}.webp`;
    // Decode off-DOM, then paint into one persistent surface. Even replacing a
    // decoded <img> can expose a blank compositor frame during concurrent turns.
    // Keep the original responsive poster mounted and NEVER resize, clear or
    // replace the canvas between frames: its last pixels survive slow decodes.
    const next = view.image.cloneNode(false);
    next.loading = "eager";
    if (endpoint && !leanConnection) {
      // srcset must follow the endpoint, never remain stuck on the front while
      // src changes to a motion frame. Responsive stills also work without JS.
      next.setAttribute("sizes", view.sizes);
      next.srcset = `${view.base}${filename} 400w, ${view.base}still-800/${filename} 800w`;
      next.src = `${view.base}${filename}`;
    } else {
      next.removeAttribute("srcset");
      next.removeAttribute("sizes");
      next.src = view.sources[frame];
    }
    view.presentation = next.decode().then(() => {
      if (token !== view.presentationToken) return;
      let canvas = view.canvas;
      let context = view.context;
      if (!canvas) {
        canvas = document.createElement("canvas");
        canvas.className = "pint-motion";
        canvas.setAttribute("aria-hidden", "true");
        canvas.width = leanConnection ? 400 : 800;
        canvas.height = canvas.width * 1.5;
        context = canvas.getContext("2d", { alpha: false });
        if (!context) throw new Error("Pint canvas unavailable");
      }
      context.drawImage(next, 0, 0, canvas.width, canvas.height);
      if (!view.canvas) {
        // Do not mount an empty/black surface before its first successful draw.
        view.link.append(canvas);
        view.canvas = canvas;
        view.context = context;
      }
      canvas.dataset.source = next.currentSrc || next.src;
      view.card.dataset.frame = String(frame);
    }).catch(() => {
      if (token !== view.presentationToken) return;
      // Keep the last successfully displayed frame and readable case access.
      cancelAnimationFrame(view.animation);
      status.textContent = "Rotation unavailable. The case links still work.";
      setLoading(view, false);
      view.card.dataset.error = "true";
      view.button.hidden = true;
    });
    return view.presentation;
  }

  async function turn(view, back) {
    const token = ++view.token;
    cancelAnimationFrame(view.animation);
    // A pending decoded frame from an interrupted turn must not commit later.
    ++view.presentationToken;
    view.requestedFrame = -1;
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
        await show(view, view.target);
        if (token === view.token) setLoading(view, false);
        return;
      }

      if (!view.framesReady) {
        // A turn should always read as a physical turn, including the first
        // interaction. Wait for the complete sequence instead of snapping to
        // a cold endpoint; narrow layouts prewarm each pint as it approaches
        // the viewport below, so this is usually already resolved on mobile.
        await prepare(view);
        if (token !== view.token) return;
      }
    } catch {
      if (token !== view.token) return;
      status.textContent = "Rotation unavailable. The case links still work.";
      setLoading(view, false);
      view.card.dataset.error = "true";
      view.button.hidden = true;
      return;
    }
    if (token !== view.token) return;

    if (reducedMotion.matches) {
      await show(view, view.target);
      if (token === view.token) setLoading(view, false);
      return;
    }

    const from = view.position;
    const to = view.target;
    const start = performance.now();
    const runFor = duration * (Math.abs(to - from) / 30);
    const tick = (now) => {
      const progress = runFor ? Math.min(1, (now - start) / runFor) : 1;
      const eased = progress * progress * (3 - 2 * progress);
      const presented = show(view, from + (to - from) * eased);
      if (progress < 1) view.animation = requestAnimationFrame(tick);
      else presented.then(() => {
        if (token === view.token) setLoading(view, false);
      });
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
    if (leanConnection) {
      // Restrict the poster too, not only the animation layered over it. Lazy
      // offscreen posters must not later fetch retina stills on Save-Data/2G.
      // This is initial setup only; no source mutations occur during turns.
      view.image.removeAttribute("srcset");
      view.image.removeAttribute("sizes");
    }
    // Preserve the poster's lazy-loading policy and allocate no canvas until
    // interaction, including on constrained connections.
    view.requestedFrame = 0;
    view.card.dataset.frame = "0";

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

  /* On the one-pint mobile layout, warm only the pint that is visible or about
     to enter the viewport. Desktop keeps hover-led loading, and reduced-motion
     users keep the endpoint-only path above. */
  function startMobilePreloading() {
    if (mobilePreloadObserver || leanConnection || reducedMotion.matches || !matchMedia("(max-width: 880px)").matches || !("IntersectionObserver" in window)) return;
    mobilePreloadObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const view = views.find((candidate) => candidate.card === entry.target);
        if (view) prepare(view).catch(() => {});
        mobilePreloadObserver.unobserve(entry.target);
      });
    }, { rootMargin: "240px 0px" });
    views.forEach((view) => mobilePreloadObserver.observe(view.card));
  }
  startMobilePreloading();

  // Endpoint source selection remains responsive after a viewport change. The
  // canvas allocation itself stays fixed, avoiding a clear/reallocation flash.
  let resizeFrame = 0;
  window.addEventListener("resize", () => {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => views.forEach((view) => {
      if (view.canvas && !view.card.dataset.loading && (view.position === 0 || view.position === 30)) {
        view.requestedFrame = -1;
        show(view, view.position);
      }
    }));
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

  const motionChanged = () => {
    if (reducedMotion.matches && mobilePreloadObserver) {
      mobilePreloadObserver.disconnect();
      mobilePreloadObserver = null;
    } else if (!reducedMotion.matches) {
      startMobilePreloading();
    }
    views.forEach((view) => {
      if (view.ready || view.target === 30) turn(view, view.target === 30);
    });
  };
  if (reducedMotion.addEventListener) reducedMotion.addEventListener("change", motionChanged);
  else reducedMotion.addListener(motionChanged);
})();
