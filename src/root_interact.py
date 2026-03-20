import matplotlib
# Uncomment the line below for faster pan/zoom (requires: pip install PyQt5)
# matplotlib.use('QtAgg')

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons, Slider, Button
from itertools import product

# Render large scatter plots faster
plt.rcParams['agg.path.chunksize'] = 10_000


# ── Constants ────────────────────────────────────────────────────────────────

DEGREES      = list(range(1, 16))      # 1 – 15  (degree 0 has no roots)
COEFF_VALUES = list(range(-5, 6))      # coefficient choices: -5 to 5 including 0
INIT_DEGREES = [5]                     # checked on startup
INIT_COEFFS  = [-1, 1]                # checked on startup
COMBO_LIMIT  = 500_000                # skip a degree if it would need more polys than this
INIT_DOT_PT2 = 4.0                    # default dot area in pt²
INIT_RANGE   = 2.0                    # default half-width for both axes

# Rainbow from pink → red → orange → yellow → green → blue → violet
# plt.cm.hsv maps [0, 1] to the HSV hue wheel (red at 0 and 1, going through rainbow)
# pink ≈ hue 0.92, violet ≈ hue 0.75 — stepping forward wraps through the full rainbow
_start, _span = 0.92, 0.83
COLORS = [plt.cm.hsv((_start + t) % 1.0)
          for t in np.linspace(0, _span, len(DEGREES))]


# ── Root computation ─────────────────────────────────────────────────────────

def compute_roots_with_meta(degree, coeff_vals):
    """
    Returns:
        roots  — complex array, one entry per root
        polys  — list of coefficient tuples, same length as roots;
                 polys[i] is the non-leading coefficients of the polynomial
                 whose root is roots[i]
    """
    all_roots, all_polys = [], []
    for t in product(coeff_vals, repeat=degree):
        r = np.roots(np.array([1.0, *t]))
        all_roots.extend(r)
        all_polys.extend([t] * len(r))
    return np.array(all_roots, dtype=np.complex128), all_polys


def _format_poly(degree, coeff_tuple):
    """Format a monic polynomial as a readable string, e.g. 'x^3 - 2x + 1 = 0'."""
    terms = []
    for i, c in enumerate((1, *coeff_tuple)):
        power = degree - i
        if c == 0:
            continue
        sign     = '+' if c > 0 else '-'
        abs_c    = abs(c)
        if power == 0:
            term = str(abs_c)
        elif power == 1:
            term = 'x' if abs_c == 1 else f'{abs_c}x'
        else:
            term = f'x^{power}' if abs_c == 1 else f'{abs_c}x^{power}'
        terms.append((sign, term))

    if not terms:
        return '0 = 0'
    result = ('-' if terms[0][0] == '-' else '') + terms[0][1]
    for sign, term in terms[1:]:
        result += f' {sign} {term}'
    return result + ' = 0'


# ── Figure / axes layout ─────────────────────────────────────────────────────
#
#   ┌──────────┬──────────────────────────────────┐
#   │ Degree   │                                  │
#   │ checks   │          main plot               │
#   ├──────────│                                  │
#   │ Coeff    ├──────────────────────────────────┤
#   │ checks   │  Range slider                    │
#   │          │  Dot Size slider                 │
#   └──────────┴──────────────────────────────────┘

fig = plt.figure(figsize=(13, 9))

ax          = fig.add_axes([0.20, 0.15, 0.77, 0.81])
ax_deg_cb   = fig.add_axes([0.01, 0.43, 0.15, 0.50])
ax_coeff_cb = fig.add_axes([0.01, 0.05, 0.15, 0.35])
ax_xrange   = fig.add_axes([0.36, 0.08, 0.45, 0.03])
ax_size     = fig.add_axes([0.36, 0.03, 0.45, 0.03])
ax_fit      = fig.add_axes([0.22, 0.025, 0.038, 0.055])  # square: 0.038×13 ≈ 0.055×9

# ── Widgets ──────────────────────────────────────────────────────────────────

deg_check = CheckButtons(
    ax_deg_cb,
    labels  = [str(d) for d in DEGREES],
    actives = [d in INIT_DEGREES for d in DEGREES],
)

coeff_check = CheckButtons(
    ax_coeff_cb,
    labels  = [str(c) for c in COEFF_VALUES],
    actives = [c in INIT_COEFFS for c in COEFF_VALUES],
)

slider_xrange = Slider(ax_xrange, 'Range', 0.1, 10,
                       valinit=INIT_RANGE, valstep=0.1)
slider_size   = Slider(ax_size,  'Dot Size', 0.01, 5,
                       valinit=INIT_DOT_PT2 / 10, valstep=0.01)
btn_fit       = Button(ax_fit, 'Fit', hovercolor='0.85')

# Panel headings
fig.text(0.085, 0.945, 'Degree',       ha='center', fontsize=9, fontweight='bold')
fig.text(0.085, 0.025, 'Coefficients', ha='center', fontsize=9, fontweight='bold')

# ── Static plot elements ─────────────────────────────────────────────────────

# One scatter per degree so each degree gets its own colour
scats = {
    d: ax.scatter([], [], s=INIT_DOT_PT2, color=COLORS[i],
                  alpha=0.6, linewidths=0, label=f'd = {d}')
    for i, d in enumerate(DEGREES)
}

theta = np.linspace(0, 2 * np.pi, 400)
ax.plot(np.cos(theta), np.sin(theta), 'k--', alpha=0.3, lw=0.8)
ax.axhline(0, color='k', lw=0.5, alpha=0.4)
ax.axvline(0, color='k', lw=0.5, alpha=0.4)
ax.set_aspect('equal')
ax.set_xlabel('Real')
ax.set_ylabel('Imaginary')
ax.grid(True, alpha=0.2)
ax.legend(loc='upper right', fontsize=8, markerscale=2)
ax.set_xlim(-INIT_RANGE, INIT_RANGE)
ax.set_ylim(-INIT_RANGE, INIT_RANGE)

# Colour each degree label to match its scatter colour
for i, txt in enumerate(deg_check.labels):
    txt.set_color(COLORS[i])


# ── Axis range ───────────────────────────────────────────────────────────────

def _fit_all(event=None):
    """Fit the view to show all currently plotted roots."""
    if not _root_meta:
        return
    all_real = np.concatenate([m['roots'].real for m in _root_meta.values()])
    all_imag = np.concatenate([m['roots'].imag for m in _root_meta.values()])
    cx = (all_real.min() + all_real.max()) / 2
    cy = (all_imag.min() + all_imag.max()) / 2
    r  = max(all_real.max() - cx, cx - all_real.min(),
             all_imag.max() - cy, cy - all_imag.min()) * 1.08
    r  = max(r, 0.1)
    # Set the view first so _apply_range reads the right centre
    ax.set_xlim(cx - r, cx + r)
    ax.set_ylim(cy - r, cy + r)
    slider_xrange.set_val(np.clip(r, slider_xrange.valmin, slider_xrange.valmax))


def _apply_range(event=None):
    r  = slider_xrange.val
    cx = sum(ax.get_xlim()) / 2
    cy = sum(ax.get_ylim()) / 2
    ax.set_xlim(cx - r, cx + r)
    ax.set_ylim(cy - r, cy + r)
    fig.canvas.draw_idle()


# ── Dot size ─────────────────────────────────────────────────────────────────

def _dot_size():
    return slider_size.val * 10


def _apply_sizes(event=None):
    s = _dot_size()
    for scat in scats.values():
        n = len(scat.get_offsets())
        if n:
            scat.set_sizes(np.full(n, s))
    fig.canvas.draw_idle()


# ── Layer ordering ───────────────────────────────────────────────────────────
# Lower degree always on top: degree 1 → zorder 9, degree 9 → zorder 1.

for d in DEGREES:
    scats[d].set_zorder(len(DEGREES) + 1 - d)


# ── Root metadata (for click-to-identify) ────────────────────────────────────
# _root_meta[degree] = {'roots': complex array, 'polys': list of coeff tuples}

_root_meta = {}


# ── Main update ──────────────────────────────────────────────────────────────

def update(label=None):
    active_degs   = [d for d, on in zip(DEGREES,      deg_check.get_status())   if on]
    active_coeffs = [c for c, on in zip(COEFF_VALUES, coeff_check.get_status()) if on]

    _dismiss_annotation()   # clear any annotation when data changes

    for d in DEGREES:
        if d not in active_degs or not active_coeffs:
            scats[d].set_offsets(np.empty((0, 2)))
            _root_meta.pop(d, None)
            continue

        n_combos = len(active_coeffs) ** d
        if n_combos > COMBO_LIMIT:
            print(f'[skip] degree {d}: {n_combos:,} combinations > limit {COMBO_LIMIT:,}')
            scats[d].set_offsets(np.empty((0, 2)))
            _root_meta.pop(d, None)
            continue

        roots, polys = compute_roots_with_meta(d, active_coeffs)
        valid = np.isfinite(roots.real) & np.isfinite(roots.imag)
        roots  = roots[valid]
        polys  = [p for p, v in zip(polys, valid) if v]

        if len(roots):
            scats[d].set_offsets(np.column_stack([roots.real, roots.imag]))
            scats[d].set_sizes(np.full(len(roots), _dot_size()))
            _root_meta[d] = {'roots': roots, 'polys': polys}
        else:
            scats[d].set_offsets(np.empty((0, 2)))
            _root_meta.pop(d, None)

    total = sum(len(scats[d].get_offsets()) for d in active_degs)

    deg_str   = str(sorted(active_degs))   if active_degs   else '—'
    coeff_str = str(sorted(active_coeffs)) if active_coeffs else '—'
    ax.set_title(
        f'Degrees {deg_str}  |  Coefficients {coeff_str}  |  {total:,} roots',
        fontsize=10,
    )

    fig.canvas.draw_idle()


# ── Click-to-identify ─────────────────────────────────────────────────────────

_annot = [None]   # holds the current annotation artist


def _dismiss_annotation():
    if _annot[0] is not None:
        _annot[0].remove()
        _annot[0] = None


def on_click(event):
    # Ignore clicks when a toolbar mode (pan / zoom) is active
    toolbar = fig.canvas.toolbar
    if toolbar is not None and getattr(toolbar, 'mode', '') != '':
        return
    if event.inaxes != ax or event.xdata is None:
        return

    cx, cy = event.xdata, event.ydata

    # Convert a 12-pixel radius to data units for the proximity threshold
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    bbox = ax.get_window_extent()
    px_x = (xlim[1] - xlim[0]) / bbox.width  * 12
    px_y = (ylim[1] - ylim[0]) / bbox.height * 12
    threshold2 = px_x ** 2 + px_y ** 2

    # Collect every degree that has a root within the threshold,
    # then pick the lowest degree (nearest root as tiebreaker within same degree).
    candidates = []
    for d, meta in _root_meta.items():
        roots = meta['roots']
        dist2 = (roots.real - cx) ** 2 + (roots.imag - cy) ** 2
        idx   = int(np.argmin(dist2))
        if dist2[idx] <= threshold2:
            candidates.append((d, dist2[idx], roots[idx], meta['polys'][idx]))

    _dismiss_annotation()

    if not candidates:
        fig.canvas.draw_idle()
        return


    # Lowest degree first; nearest root as tiebreaker within the same degree
    candidates.sort(key=lambda c: (c[0], c[1]))
    best_degree, _, best_root, best_poly = candidates[0]

    poly_str = _format_poly(best_degree, best_poly)
    root_str = (f'{best_root.real:+.4f} {best_root.imag:+.4f}i'
                if best_root.imag != 0 else f'{best_root.real:+.4f}')

    label = f'degree {best_degree}\n{poly_str}\nroot ≈ {root_str}'

    _annot[0] = ax.annotate(
        label,
        xy         = (best_root.real, best_root.imag),
        xytext     = (18, 18), textcoords='offset points',
        fontsize   = 9,
        bbox       = dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.85, edgecolor='grey'),
        arrowprops = dict(arrowstyle='->', color='black', lw=0.8),
    )
    fig.canvas.draw_idle()


fig.canvas.mpl_connect('button_press_event', on_click)


# ── Wire up ──────────────────────────────────────────────────────────────────

deg_check.on_clicked(update)
coeff_check.on_clicked(update)
slider_xrange.on_changed(_apply_range)
slider_size.on_changed(_apply_sizes)
btn_fit.on_clicked(_fit_all)

update()
plt.show()
