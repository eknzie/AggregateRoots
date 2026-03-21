import matplotlib
# Uncomment the line below for faster pan/zoom (requires: pip install PyQt5)
# matplotlib.use('QtAgg')

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons, Slider, Button, RadioButtons
from itertools import product

# Render large scatter plots faster
plt.rcParams['agg.path.chunksize'] = 10_000


# ── Constants ────────────────────────────────────────────────────────────────

DEGREES      = list(range(1, 16))      # 1 – 15  (degree 0 has no roots)
COEFF_VALUES = list(range(-10, 11))    # coefficient choices: -10 to 10 including 0
INIT_DEGREES = [5]                     # checked on startup
INIT_COEFFS  = [-1, 1]                # checked on startup
COMBO_LIMIT  = 500_000                # skip a degree if it would need more polys than this
INIT_DOT_PT2 = 4.0                    # default dot area in pt²
INIT_RANGE   = 2.0                    # default half-width for both axes

# Built-in gradient presets
# Each entry: (display name, callable t∈[0,1] → RGBA)
_start, _span = 0.92, 0.83   # kept for the default Pink→Violet preset
GRADIENTS = [
    ('Pink→Violet', lambda t: plt.cm.hsv((_start + t * _span) % 1.0)),
    ('Viridis',     plt.cm.viridis),
    ('Plasma',      plt.cm.plasma),
    ('Inferno',     plt.cm.inferno),
    ('Rainbow',     plt.cm.rainbow),
    ('Cool',        plt.cm.cool),
    ('Spring',      plt.cm.spring),
    ('Autumn',      plt.cm.autumn),
]
_gradient_idx = [0]   # index into GRADIENTS


# ── Root computation ─────────────────────────────────────────────────────────

def compute_roots_with_meta(degree, coeff_vals):
    """
    Returns:
        roots  — complex array, one entry per root
        polys  — list of full coefficient tuples (length degree+1), same length as roots;
                 polys[i] are all coefficients (including leading) of the polynomial
                 whose root is roots[i].
                 Polynomials with a zero leading coefficient are skipped.
    """
    all_roots, all_polys = [], []
    for t in product(coeff_vals, repeat=degree + 1):
        if t[0] == 0:          # leading coefficient must be non-zero
            continue
        r = np.roots(np.array(t, dtype=float))
        all_roots.extend(r)
        all_polys.extend([t] * len(r))
    return np.array(all_roots, dtype=np.complex128), all_polys


def _format_poly(degree, coeff_tuple):
    """Format a polynomial as a readable string, e.g. '2x^3 - x + 1 = 0'."""
    terms = []
    for i, c in enumerate(coeff_tuple):
        power = degree - i
        if c == 0:
            continue
        sign  = '+' if c > 0 else '-'
        abs_c = abs(c)
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
#   ┌──────────┬───────────────────────────────┬──────────┐
#   │ Degree   │                               │ Gradient │
#   │ checks   │          main plot            │ radio    │
#   ├──────────┤                               ├──┬───────┤
#   │ Coeff    │                               │Ra│DotSz  │
#   │ checks   │                               │ng│       │
#   │          │                               ├──┴───────┤
#   │          │                               │  [Fit]   │
#   └──────────┴───────────────────────────────┴──────────┘

fig = plt.figure(figsize=(13, 12))

# Right panel (x = 0.85–0.97):
#   gradient radio : bottom=0.48, top=0.96  (top matches degree box top)
#   vertical sliders: bottom=0.11, top=0.44  (two side-by-side, gap 0.04 below gradient, 0.03 above buttons)
#   fit + flip btns : bottom=0.03, top=0.08  (side-by-side square pair centred in panel)
ax           = fig.add_axes([0.18, 0.12, 0.65, 0.85])   # main plot — fills remaining middle space
ax_deg_cb    = fig.add_axes([0.01, 0.48, 0.15, 0.48])   # 0.48×12=5.76" / 15 rows = 0.38"/row
ax_coeff_cb  = fig.add_axes([0.01, 0.05, 0.15, 0.40])   # 0.40×12=4.80" / 21 rows = 0.23"/row
ax_color_btn = fig.add_axes([0.01, 0.453, 0.15, 0.022]) # color mode toggle
ax_grad_rb   = fig.add_axes([0.85, 0.48, 0.12, 0.48])   # gradient radio — top=0.96 = degree box top
ax_xrange    = fig.add_axes([0.855, 0.11, 0.05, 0.33])  # vertical Range slider
ax_size      = fig.add_axes([0.915, 0.11, 0.05, 0.33])  # vertical Dot Size slider
ax_fit       = fig.add_axes([0.860, 0.030, 0.046, 0.050]) # square: 0.046×13≈0.050×12≈0.60"
ax_flip      = fig.add_axes([0.916, 0.030, 0.046, 0.050]) # square, beside Fit

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
                       valinit=INIT_RANGE, valstep=0.1, orientation='vertical')
slider_size   = Slider(ax_size,  'Dot Size', 0.01, 5,
                       valinit=INIT_DOT_PT2 / 10, valstep=0.01, orientation='vertical')
btn_fit   = Button(ax_fit,       'Fit',           hovercolor='0.85')
btn_flip  = Button(ax_flip,      'Flip',          hovercolor='0.85')
btn_color = Button(ax_color_btn, 'Color: Fixed',  hovercolor='0.85')

grad_radio = RadioButtons(ax_grad_rb, [name for name, _ in GRADIENTS], active=0)
for lbl in grad_radio.labels:
    lbl.set_fontsize(8)

# Panel headings
fig.text(0.085, 0.970, 'Degree',       ha='center', fontsize=9, fontweight='bold')
fig.text(0.085, 0.022, 'Coefficients', ha='center', fontsize=9, fontweight='bold')
fig.text(0.910, 0.970, 'Gradient',     ha='center', fontsize=9, fontweight='bold')  # centre of x=[0.85,0.97]

# ── Static plot elements ─────────────────────────────────────────────────────

# One scatter per degree so each degree gets its own colour
scats = {
    d: ax.scatter([], [], s=INIT_DOT_PT2, color=(0.6, 0.6, 0.6, 1.0),
                  alpha=0.6, linewidths=0, label=f'd = {d}')
    for d in DEGREES
}

theta = np.linspace(0, 2 * np.pi, 400)
ax.plot(np.cos(theta), np.sin(theta), 'k--', alpha=0.3, lw=0.8)
ax.axhline(0, color='k', lw=0.5, alpha=0.4)
ax.axvline(0, color='k', lw=0.5, alpha=0.4)
ax.set_aspect('equal')
ax.set_zorder(10)   # draw ax (and its annotation children) above all widget axes
ax.set_xlabel('Real')
ax.set_ylabel('Imaginary')
ax.grid(True, alpha=0.2)
_init_legend = ax.legend(loc='upper right', fontsize=8)
for h in _init_legend.legend_handles:
    h.set_sizes([20.0])
ax.set_xlim(-INIT_RANGE, INIT_RANGE)
ax.set_ylim(-INIT_RANGE, INIT_RANGE)

# Initial colours — applied properly once update() runs; set grey for now
for txt in deg_check.labels:
    txt.set_color((0.6, 0.6, 0.6, 1.0))


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
    for d in DEGREES:
        n = len(scats[d].get_offsets())
        if not n:
            continue
        sizes = _sized_from_counts(d)
        scats[d].set_sizes(sizes if sizes is not None else np.full(n, _dot_size()))
    fig.canvas.draw_idle()


# ── Layer ordering ───────────────────────────────────────────────────────────
# Lower degree always on top: degree 1 → zorder 9, degree 9 → zorder 1.

for d in DEGREES:
    scats[d].set_zorder(len(DEGREES) + 1 - d)


# ── Root metadata (for click-to-identify) ────────────────────────────────────
# _root_meta[degree] = {'roots': complex array, 'polys': list of coeff tuples}

_root_meta = {}


# ── Colour mode & assignment ──────────────────────────────────────────────────
# 'fixed'   — gradient spread across all 15 degrees; inactive ones are grey
# 'dynamic' — gradient spread evenly across only the active degrees

_color_mode    = ['fixed']
_gradient_flip = [False]
_dot_counts    = {}    # {degree: np.array of per-dot repeat counts (int)}


def _degree_color(d, active_degs):
    """Return the full base colour for degree d (used for legend, labels, inactive dots)."""
    n = len(active_degs)
    if d not in active_degs or n == 0:
        return (0.6, 0.6, 0.6, 1.0)
    if _color_mode[0] == 'fixed':
        t = DEGREES.index(d) / max(len(DEGREES) - 1, 1)
    else:
        t = active_degs.index(d) / max(n - 1, 1)
    _, cmap = GRADIENTS[_gradient_idx[0]]
    return cmap(1.0 - t if _gradient_flip[0] else t)


def _compute_counts(roots, polys):
    """
    For each root, count how many distinct polynomials produced a root at that
    location (rounded to 4 d.p.).  Returns an integer array, same length as roots.
    """
    if len(roots) == 0:
        return np.array([], dtype=int)
    from collections import defaultdict
    rounded   = np.round(roots.real, 4) + 1j * np.round(roots.imag, 4)
    poly_sets = defaultdict(set)
    for r, p in zip(rounded, polys):
        poly_sets[r].add(p)
    return np.array([len(poly_sets[r]) for r in rounded], dtype=int)


def _sized_from_counts(d):
    """
    Return per-dot size array for degree d scaled by repeat count:
      - most-repeated root  → full slider size
      - least-repeated root → 30 % of slider size
    Returns None if no count data is stored for d.
    """
    if d not in _dot_counts or len(_dot_counts[d]) == 0:
        return None
    counts  = _dot_counts[d].astype(float)
    max_cnt = max(counts.max(), 1.0)
    frac    = 0.3 + 0.7 * np.log1p(counts) / np.log1p(max_cnt)
    return _dot_size() * frac


def _recolor(active_degs):
    """Apply flat degree colours to dots, update checkbox labels, and rebuild legend."""
    for d in DEGREES:
        base_color = _degree_color(d, active_degs)
        scats[d].set_facecolor(base_color)
        deg_check.labels[DEGREES.index(d)].set_color(base_color)

    # Rebuild legend with fixed full-saturation degree colours
    handles = [scats[d] for d in active_degs]
    if handles:
        legend = ax.legend(handles=handles, loc='upper right', fontsize=8)
        for handle, d in zip(legend.legend_handles, active_degs):
            handle.set_sizes([20.0])
            handle.set_facecolors([_degree_color(d, active_degs)])
    elif ax.get_legend():
        ax.get_legend().remove()


def _toggle_color_mode(event=None):
    if _color_mode[0] == 'fixed':
        _color_mode[0] = 'dynamic'
        btn_color.label.set_text('Color: Dynamic')
    else:
        _color_mode[0] = 'fixed'
        btn_color.label.set_text('Color: Fixed')
    active_degs = [d for d, on in zip(DEGREES, deg_check.get_status()) if on]
    _recolor(active_degs)
    fig.canvas.draw_idle()


def _flip_gradient(event=None):
    _gradient_flip[0] = not _gradient_flip[0]
    active_degs = [d for d, on in zip(DEGREES, deg_check.get_status()) if on]
    _recolor(active_degs)
    fig.canvas.draw_idle()


def _on_gradient_select(label):
    _gradient_idx[0] = next(i for i, (name, _) in enumerate(GRADIENTS) if name == label)
    active_degs = [d for d, on in zip(DEGREES, deg_check.get_status()) if on]
    _recolor(active_degs)
    fig.canvas.draw_idle()


# ── Main update ──────────────────────────────────────────────────────────────

def update(label=None):
    active_degs   = [d for d, on in zip(DEGREES,      deg_check.get_status())   if on]
    active_coeffs = [c for c, on in zip(COEFF_VALUES, coeff_check.get_status()) if on]

    _dismiss_annotation()   # clear any annotation when data changes

    for d in DEGREES:
        if d not in active_degs or not active_coeffs:
            scats[d].set_offsets(np.empty((0, 2)))
            _root_meta.pop(d, None)
            _dot_counts.pop(d, None)
            continue

        n_leading = len(active_coeffs) - (1 if 0 in active_coeffs else 0)
        n_combos  = n_leading * len(active_coeffs) ** d
        if n_combos > COMBO_LIMIT:
            print(f'[skip] degree {d}: {n_combos:,} combinations > limit {COMBO_LIMIT:,}')
            scats[d].set_offsets(np.empty((0, 2)))
            _root_meta.pop(d, None)
            _dot_counts.pop(d, None)
            continue

        roots, polys = compute_roots_with_meta(d, active_coeffs)
        valid = np.isfinite(roots.real) & np.isfinite(roots.imag)
        roots  = roots[valid]
        polys  = [p for p, v in zip(polys, valid) if v]

        if len(roots):
            counts = _compute_counts(roots, polys)
            _dot_counts[d]  = counts
            _root_meta[d]   = {'roots': roots, 'polys': polys}
            scats[d].set_offsets(np.column_stack([roots.real, roots.imag]))
            sizes = _sized_from_counts(d)
            scats[d].set_sizes(sizes if sizes is not None else np.full(len(roots), _dot_size()))
        else:
            scats[d].set_offsets(np.empty((0, 2)))
            _root_meta.pop(d, None)
            _dot_counts.pop(d, None)

    _recolor(active_degs)   # called after sats are computed so dot colours are correct

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

    # For each degree, find every root within the threshold.
    # matched[d] = {'count': n_distinct_polys, 'distinct_polys': set of tuples,
    #               'nearest_root': complex}
    matched = {}
    for d, meta in _root_meta.items():
        roots  = meta['roots']
        polys  = meta['polys']
        dist2  = (roots.real - cx) ** 2 + (roots.imag - cy) ** 2
        within = np.where(dist2 <= threshold2)[0]
        if len(within) == 0:
            continue
        nearest_idx    = within[int(np.argmin(dist2[within]))]
        distinct_polys = {polys[i] for i in within}
        matched[d] = {
            'count':         len(distinct_polys),
            'distinct_polys': distinct_polys,
            'nearest_root':  roots[nearest_idx],
        }

    _dismiss_annotation()

    if not matched:
        fig.canvas.draw_idle()
        return

    active_degs   = [d for d, on in zip(DEGREES, deg_check.get_status()) if on]
    total_count   = sum(info['count'] for info in matched.values())
    distinct_degs = sorted(matched.keys())
    best_degree   = distinct_degs[0]   # lowest degree with a match

    # Among all matching polynomials of best_degree, prefer the one with the
    # smallest positive leading coefficient; fall back to smallest |leading coeff|.
    candidate_polys = matched[best_degree]['distinct_polys']
    positive_polys  = [p for p in candidate_polys if p[0] > 0]
    if positive_polys:
        best_poly = min(positive_polys, key=lambda p: p[0])
    else:
        best_poly = min(candidate_polys, key=lambda p: abs(p[0]))

    # Point the arrow at the root of best_poly nearest to the click
    meta       = _root_meta[best_degree]
    poly_idxs  = [i for i, p in enumerate(meta['polys']) if p == best_poly]
    if poly_idxs:
        poly_roots = meta['roots'][poly_idxs]
        d2         = (poly_roots.real - cx) ** 2 + (poly_roots.imag - cy) ** 2
        best_root  = poly_roots[int(np.argmin(d2))]
    else:
        best_root  = matched[best_degree]['nearest_root']

    poly_str = _format_poly(best_degree, best_poly)
    root_str = (f'{best_root.real:+.4f} {best_root.imag:+.4f}i'
                if abs(best_root.imag) > 1e-10 else f'{best_root.real:+.4f}')

    label = '\n'.join([
        f'{total_count} polynomial{"s" if total_count != 1 else ""} share this root',
        f'Degrees contributing: {distinct_degs}',
        '',
        f'Lowest degree (d = {best_degree}):',
        poly_str,
        f'root \u2248 {root_str}',
    ])

    # Annotation colour: shade of the best-degree colour scaled by repeat count.
    # 1 polynomial → near white;  many → full degree colour (log scale).
    base_color = _degree_color(best_degree, active_degs)
    sat  = float(np.clip(np.log1p(total_count) / np.log1p(500), 0.5, 1.0))
    face = tuple(1.0 * (1.0 - sat) + base_color[i] * sat for i in range(3))

    _annot[0] = ax.annotate(
        label,
        xy         = (best_root.real, best_root.imag),
        xytext     = (18, 18), textcoords='offset points',
        fontsize   = 9,
        bbox       = dict(boxstyle='round,pad=0.4', facecolor=face,
                          alpha=0.92, edgecolor=base_color[:3], linewidth=1.5),
        arrowprops = dict(arrowstyle='->', color=base_color[:3], lw=1.0),
        zorder     = 9999,   # always above every other artist
    )
    fig.canvas.draw_idle()


fig.canvas.mpl_connect('button_press_event', on_click)


# ── Wire up ──────────────────────────────────────────────────────────────────

deg_check.on_clicked(update)
coeff_check.on_clicked(update)
slider_xrange.on_changed(_apply_range)
slider_size.on_changed(_apply_sizes)
btn_fit.on_clicked(_fit_all)
btn_flip.on_clicked(_flip_gradient)
btn_color.on_clicked(_toggle_color_mode)
grad_radio.on_clicked(_on_gradient_select)

update()
plt.show()
