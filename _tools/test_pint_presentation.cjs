// Deterministic presentation regressions; no browser or third-party dependency.
// Run: node _tools/test_pint_presentation.cjs
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../assets/js/pint-gallery.js'), 'utf8');
const functions = source.slice(source.indexOf('  function show('), source.indexOf('  function select('));

function fixture(lean = false) {
  const pending = [], frames = new Map();
  let nextId = 0, attachedWrites = 0, allocations = 0, sizeWrites = 0;
  class Image {
    constructor(attrs = {}) { this.attrs = {...attrs}; this.complete = true; this.naturalWidth = 800; }
    cloneNode() { return new Image(this.attrs); }
    setAttribute(k, v) { if (this.attached) attachedWrites++; this.attrs[k] = v; }
    removeAttribute(k) { if (this.attached) attachedWrites++; delete this.attrs[k]; }
    set src(v) { this.setAttribute('src', v); this.complete = false; this.naturalWidth = 0; }
    set srcset(v) { this.setAttribute('srcset', v); }
    get src() { return this.attrs.src; }
    get currentSrc() { return this.attrs.srcset ? this.attrs.srcset.split(', ').at(-1).split(' ')[0] : this.src; }
    decode() {
      return new Promise((resolve, reject) => pending.push({image: this, reject, resolve: () => {
        this.complete = true; this.naturalWidth = 800; resolve();
      }}));
    }
    replaceWith(image) {
      throw new Error('Never replace the poster DOM node');
    }
  }
  const image = new Image({src: '/p/frame-00.webp', srcset: 'front 800w', sizes: '400px'});
  image.attached = true;
  const view = {
    image, base: '/p/', sizes: '400px', sources: Array.from({length: 31}, (_, n) => `/p/motion-600/frame-${String(n).padStart(2,'0')}.webp`),
    position: 0, target: 0, requestedFrame: -1, presentationToken: 0, presentation: Promise.resolve(),
    token: 0, animation: 0, framesReady: true,
    canvas: null, context: null,
    card: {dataset: {}}, labelButton: {hidden: true},
    link: {append(canvas) {assert(canvas.lastDraw, 'Never mount a blank canvas');}},
    button: {firstChild: {}, setAttribute(k,v) {this[k]=v;}}
  };
  const context = vm.createContext({
    document: {createElement(tag) {
      assert.equal(tag, 'canvas'); allocations++;
      const canvas = {dataset: {}, setAttribute() {},
        set width(v) {sizeWrites++; this.w=v;}, get width() {return this.w;},
        set height(v) {sizeWrites++; this.h=v;}, get height() {return this.h;},
        getContext(type, options) {
          assert.equal(type, '2d'); assert.equal(options.alpha, false);
          return {drawImage(image, x, y, w, h) {
            assert(image.complete && image.naturalWidth > 0, 'Never draw an undecoded frame');
            assert.equal(w,canvas.width); assert.equal(h,canvas.height);
            canvas.lastDraw=image;
          }, clearRect() {throw new Error('Never clear the surface between frames');}};
        }
      };
      return canvas;
    }},
    leanConnection: lean, reducedMotion: {matches: false}, duration: 1100,
    status: {}, performance: {now: () => 0},
    cancelAnimationFrame: id => frames.delete(id),
    requestAnimationFrame: fn => {frames.set(++nextId, fn); return nextId;},
    setLoading: (v, loading) => loading ? v.card.dataset.loading = 'true' : delete v.card.dataset.loading,
    loadFrame: async () => {}, prepare: async () => {},
  });
  vm.runInContext(functions, context);
  return {context, view, pending, frames, writes: () => attachedWrites, allocations: () => allocations, sizeWrites: () => sizeWrites};
}
const settle = async () => {await Promise.resolve(); await Promise.resolve(); await Promise.resolve();};

(async () => {
  const f = fixture(), {context:c,view:v,pending:p} = f;
  const initial = v.image;
  const first = c.show(v, 1);
  assert.equal(v.image, initial, 'Hold previous frame while decoding');
  assert.equal(initial.complete, true);
  assert.equal(c.show(v, 1.2), first, 'Deduplicate the same rounded frame');
  assert.equal(p.length, 1);
  p[0].resolve(); await first;
  assert.equal(v.card.dataset.frame, '1');
  assert.equal(v.canvas.lastDraw.attrs.srcset, undefined, 'Motion uses one non-responsive source');
  assert.equal(v.image, initial, 'Responsive poster stays mounted');
  const surface = v.canvas;
  c.show(v, 2); c.show(v, 3);
  p[2].resolve(); await settle(); p[1].resolve(); await settle();
  assert.equal(v.card.dataset.frame, '3', 'Late older decode cannot overwrite newer frame');
  c.show(v, 4);
  await c.turn(v, false);
  p[3].resolve(); await settle();
  assert.equal(v.card.dataset.frame, '3', 'An interrupted turn invalidates its pending image');
  const endpoint = c.show(v, 30); p[4].resolve(); await endpoint;
  assert(v.canvas.lastDraw.attrs.srcset.includes('still-800/frame-30.webp 800w'));
  assert.equal(v.canvas.lastDraw.attrs.sizes, '400px');
  const good = v.canvas.lastDraw;
  const failed = c.show(v, 29); p[5].reject(new Error('decode failed')); await failed;
  assert.equal(v.canvas.lastDraw, good, 'Decode failure preserves last good pixels');
  assert.equal(v.card.dataset.error, 'true');
  assert.equal(v.button.hidden, true);
  assert.equal(f.writes(), 0, 'Never mutate src/srcset/sizes on the visible image');
  assert.equal(v.canvas, surface, 'One persistent surface throughout the turn');
  assert.equal(f.allocations(), 1);
  assert.equal(f.sizeWrites(), 2, 'Allocate dimensions once, never reset between frames');

  const lean = fixture(true); const lp = lean.context.show(lean.view, 30);
  lean.pending[0].resolve(); await lp;
  assert.equal(lean.view.canvas.lastDraw.attrs.srcset, undefined, 'Constrained delivery stays single-source');
  assert.equal(lean.view.canvas.width, 400);
  assert.equal(v.canvas.width, 800);

  const end = fixture(); await end.context.turn(end.view, true);
  assert.equal(end.view.labelButton.hidden, false, 'Read label appears immediately');
  assert.equal(end.view.button.firstChild.textContent, 'Show flavor ');
  [...end.frames.values()][0](1100);
  assert.equal(end.view.card.dataset.loading, 'true', 'Busy state waits for endpoint presentation');
  end.pending[0].resolve(); await settle();
  assert.equal(end.view.card.dataset.frame, '30');
  assert.equal(end.view.card.dataset.loading, undefined);

  // Overlapping forward/reverse paint requests across independent pints. Each
  // keeps its own fixed backing surface and rejects obsolete pending decodes.
  const adjacent = [fixture(), fixture(), fixture()];
  for (let n=0; n<600; n++) {
    await Promise.all(adjacent.map(async (f,i) => {
      const requested = (n+i*7)%60;
      const frame = requested <= 30 ? requested : 60-requested;
      const before = f.pending.length;
      const painted = f.context.show(f.view, frame);
      if (f.pending.length > before) f.pending.at(-1).resolve();
      await painted;
      assert.equal(f.view.card.dataset.frame, String(frame));
      assert.equal(f.allocations(), 1);
      assert.equal(f.sizeWrites(), 2);
      assert.equal(f.writes(), 0);
    }));
  }
  console.log('PASS: persistent painted surface, no clears/resizes/DOM replacement, decoded handoff, deduplication, stale/out-of-order rejection, safe failure, responsive/lean endpoints, immediate label, busy completion');
})().catch(e => {console.error(e); process.exitCode = 1;});
