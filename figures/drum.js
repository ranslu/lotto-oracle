/**
 * Drum: a wire lottery drum on a stand, a pile of balls in its belly, and a
 * cup in front holding the last ball drawn. Sweeping the pointer across the
 * drum flicks it round; the balls ride up the wall and tumble while friction
 * bleeds the spin. It settles on the nearest rod and drops one ball down the
 * chute into the cup. The slider is the coast, in seconds.
 *
 * The pattern: push the camera (Turntable). Friction, then a spring onto a
 * detent; the drop is a discrete change on the 700ms tween. The hit area is
 * the drum's rest box, which never moves.
 */
const {
  Cam, clamp, facing, fit, hull, open, poly, prism, proj, rings, ringAt, seg, spring, stepS,
  tset, tval, tdone, tween, disposer, mk, place, pointer, reducedMotion, register,
} = HL;

const L = 40, R = 36, ZA = 72, RB = 6.5, K = 10, UX = L + 7, DET = (2 * Math.PI) / K;
const GAIN = 0.11, WMAX = 12, WSTOP = 0.4;
const NUMS = [27, 8, 41, 13, 35, 2, 19, 44, 6, 31, 22, 49];
// the pile at rest: [x, distance from the axis, angle round it in degrees; -90 is the bottom]
const PILE = [
  [-27, 28.5, -112], [-12, 28.5, -88], [3, 28.5, -66], [18, 28.5, -95], [30, 28.5, -72], [-30, 28.5, -80],
  [9, 28.5, -118], [-20, 17, -95], [-3, 17, -110], [12, 17, -82], [26, 17, -100], [-8, 17, -70],
];
const SLOT = [0, 0, ZA - R + RB + 1], CUP = [10, 56, 8 + RB - 2.5];
// the camera looks from +x +y +z: a normal facing it has a positive dot with this
const VX = 0.612, VY = 0.612, VZ = 0.5, AC = Math.atan2(VZ, VY);
const depth = (p) => p[0] * VX + p[1] * VY + p[2] * VZ;

function mount({ stage, svg, read }, value) {
  const bag = disposer();
  let coast = value;

  const C = Cam(45, 0.5, 1.55);
  fit(C, [[-UX - 8, -26, 0], [UX + 8, 26, 0], [-L, 0, ZA + R], [L, 0, ZA + R], [L, R, ZA], [-L, -R, ZA], [22, 66, 0], [-2, 66, 0]], 200, 166);
  const P = proj(C);
  const W = (x, a, r = R) => P(x, r * Math.cos(a), ZA + r * Math.sin(a));
  const arc = (x, a0, a1) => { const pts = []; for (let j = 0; j <= 24; j++) pts.push(W(x, a0 + ((a1 - a0) * j) / 24)); return pts; };
  const front = (a) => VY * Math.cos(a) + VZ * Math.sin(a) > 0;

  const g = mk("g", {}, svg);
  const block = (ring, inner, z0, z1, parent) => {
    const s = prism(P, facing(C), ring, inner, z0, z1);
    mk("path", { d: s.sil, class: "sil" }, parent); mk("path", { d: s.crease, class: "nf lo" }, parent);
  };

  // back to front: base, far upright, the back of the cage, balls, the front of the cage, near upright, chute, cup
  block(...rings(-UX - 8, -26, UX + 8, 26, 8, 2), 0, 6, g);
  block(...rings(-UX - 3, -4, -UX + 3, 4, 2, 0.8), 6, ZA + 4, g);
  mk("path", { d: seg(P(-UX, 0, ZA), P(-L, 0, ZA)), class: "nf" }, g);
  mk("path", { d: open(arc(-L, AC + Math.PI / 2, AC + 1.5 * Math.PI)) + open(arc(L, AC + Math.PI / 2, AC + 1.5 * Math.PI)), class: "nf lo" }, g);
  const backRods = mk("path", { class: "nf lo" }, g), farSpokes = mk("path", { class: "nf lo" }, g);
  const ballG = mk("g", {}, g);
  const balls = PILE.map(() => mk("ellipse", { rx: RB * 1.55, ry: RB * 1.55 }, ballG));
  const frontRods = mk("path", { class: "nf" }, g), nearSpokes = mk("path", { class: "nf lo" }, g);
  mk("path", { d: open(arc(-L, AC - Math.PI / 2, AC + Math.PI / 2)) + open(arc(L, AC - Math.PI / 2, AC + Math.PI / 2)), class: "nf" }, g);
  const ends = arc(-L, 0, 2 * Math.PI).concat(arc(L, 0, 2 * Math.PI));
  mk("path", { d: poly(hull(ends)), class: "nf sil" }, g);
  mk("path", { d: seg(P(L, 0, ZA), P(UX, 0, ZA)), class: "nf" }, g);
  block(...rings(UX - 3, -4, UX + 3, 4, 2, 0.8), 6, ZA + 4, g);
  mk("path", { d: seg(W(4, -Math.PI / 2 + 0.5), P(CUP[0], CUP[1] - 8, 8)), class: "nf dash" }, g);
  const [cr, ci] = rings(-2, 46, 22, 66, 7, 2);
  block(cr, ci, 0, 8, g);
  mk("path", { d: poly(ringAt(P, ci, 8)), class: "nf lo" }, g);
  const topG = mk("g", {}, g);
  const cup = mk("ellipse", { rx: RB * 1.55, ry: RB * 1.55, class: "hi" }, topG);

  // the hit area: the drum's box at rest, which never moves
  const box = hull(ends).reduce((b, [x, y]) => [Math.min(b[0], x), Math.min(b[1], y), Math.max(b[2], x), Math.max(b[3], y)], [1e9, 1e9, -1e9, -1e9]);
  const inside = ([x, y]) => x > box[0] && x < box[2] && y > box[1] && y < box[3];

  let th = 0.21, w = 0, mode = "rest", sp = null, order = "", lastTh = NaN, lastT = NaN;
  const drop = tween(1);

  /** Where ball i sits for the drum at angle th, spinning at w. */
  function ball(i) {
    const [x, r0, b0] = PILE[i], s = clamp(w / 10, -1, 1), m = Math.abs(s);
    const b = (b0 * Math.PI) / 180 + 1.3 * s * (0.6 + 0.4 * Math.sin(i)) + 0.5 * m * Math.sin(th * (1.1 + 0.13 * i) + i * 1.7);
    const r = Math.min(R - RB - 1, r0 - 9 * m * (0.5 + 0.5 * Math.cos(th * (0.9 + 0.11 * i) + i)));
    return [x, r * Math.cos(b), ZA + r * Math.sin(b)];
  }

  function draw(t) {
    if (th !== lastTh) {
      lastTh = th;
      let bk = "", fr = "", fs = "", ns = "";
      for (let k = 0; k < K; k++) {
        const a = th + k * DET, d = seg(W(-L, a), W(L, a));
        if (front(a)) fr += d; else bk += d;
      }
      for (let j = 0; j < 4; j++) {
        const a = th + (j * Math.PI) / 2;
        fs += seg(P(-L, 0, ZA), W(-L, a)); ns += seg(P(L, 0, ZA), W(L, a));
      }
      backRods.setAttribute("d", bk); frontRods.setAttribute("d", fr);
      farSpokes.setAttribute("d", fs); nearSpokes.setAttribute("d", ns);
      const pos = PILE.map((_, i) => ball(i));
      pos.forEach((p, i) => place(balls[i], P(...p)));
      const idx = pos.map((p, i) => [depth(p), i]).sort((a, b) => a[0] - b[0]).map((e) => e[1]);
      if (idx.join() !== order) { order = idx.join(); idx.forEach((i) => ballG.append(balls[i])); }
    }
    if (t !== lastT) {
      lastT = t;
      const p = [0, 1, 2].map((k) => SLOT[k] + (CUP[k] - SLOT[k]) * t);
      p[2] += Math.sin(Math.PI * t) * 10;
      place(cup, P(...p));
      const out = t > 0.5;
      cup.classList.toggle("hi", out);
      if (out && cup.parentNode !== topG) topG.append(cup);
      if (!out && cup.parentNode !== ballG) ballG.prepend(cup);
    }
  }

  function land(now) {
    const k = Math.round(th / DET);
    read.textContent = "ball " + String(NUMS[((k % 12) + 12) % 12]).padStart(2, "0");
    tset(drop, 1, now, 0);
  }

  const B = register(stage, (dt, now) => {
    let moving = false;
    if (mode === "spin") {
      if (reducedMotion()) w = 0;
      w *= Math.exp(-dt / coast); th += w * dt;
      if (Math.abs(w) < WSTOP) { w = 0; mode = "settle"; sp = spring(th); sp.t = Math.round(th / DET) * DET; }
      moving = true;
    } else if (mode === "settle") {
      const m = stepS(sp, dt); th = sp.x;
      if (!m) { mode = "rest"; land(now); }
      moving = true;
    }
    if (!tdone(drop, now)) moving = true;
    draw(tval(drop, now));
    return moving;
  });
  bag.add(B.unregister);
  draw(1);

  let last = null;
  function move(p) {
    if (last && inside(p) && inside(last)) {
      const dx = p[0] - last[0];
      if (Math.abs(dx) > 0.5) {
        if (mode !== "spin") { mode = "spin"; tset(drop, 0, performance.now(), 0); read.textContent = "spin"; }
        w = clamp(w + dx * GAIN, -WMAX, WMAX);
        B.wake();
      }
    }
    last = p;
  }

  bag.add(pointer(stage, { move, leave: () => { last = null; if (mode === "rest" && tval(drop, performance.now()) >= 1) read.textContent = "rest"; } }));
  bag.add(() => svg.replaceChildren());

  return {
    set: (v) => { coast = v; },
    destroy: bag.dispose,
  };
}

hairline({
  name: "drum",
  means: "A lottery drum: sweep across it to spin, the balls tumble, and when it settles one drops into the cup.",
  rules: [1, 5, 6, 8],
  range: [0.5, 1.1, 2.2],
  tour: [[120, 135], [290, 140], [220, 265], null],
  mount,
});
