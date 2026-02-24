from manim import *
import numpy as np
from itertools import product

class RootsDistinctPolys(Scene):
    def construct(self):
        abs_coeff_bound = 1
        max_degree = 8

        xlim, ylim = 2.1, 2.1

        # sprinkle controls
        chunks = 30
        chunk_run_time = 0.001
        pause_per_degree = 0.0000001

        dot_stroke_width = 2.0

        # -------------------- Axes --------------------
        axes = Axes(
            x_range=[-xlim, xlim, 1],
            y_range=[-ylim, ylim, 1],
            x_length=7,
            y_length=7,
            tips=False,
            # turn off default numbers; we’ll add custom y labels
            axis_config={"include_numbers": False, "font_size": 24},
        )

        # Custom x-axis numeric labels (optional; comment out if you don't want x numbers)
        x_labels = axes.get_x_axis().add_numbers()

        # Custom y-axis labels: -2i, -i, i, 2i
        y_vals = [-2, -1, 1, 2]
        y_text = { -2: "-2i", -1: "-i", 1: "i", 2: "" }
        y_labels = VGroup(*[
            MathTex(y_text[v], font_size=28).next_to(
                axes.c2p(0, v), LEFT, buff=0.15
            )
            for v in y_vals
        ])

        # Unit circle in data coords
        unit_circle = ParametricFunction(
            lambda t: axes.coords_to_point(np.cos(t), np.sin(t)),
            t_range=[0, TAU],
        ).set_stroke(GREY_B, opacity=0.5)

        # -------------------- Title / subtitle (moved up) --------------------
        title = Text("Complex Roots of n-degree Polynomials", font_size=32).to_edge(UP).shift(UP * 0.25)
        subtitle = Text(f"coeffs in [-{abs_coeff_bound}, {abs_coeff_bound}]",
                        font_size=24).next_to(title, DOWN, buff=0.15)

        deg_label = Text("degree = 1", font_size=30).to_edge(LEFT).shift(UP * 2.6)

        self.add(axes, x_labels, y_labels, unit_circle, title, subtitle, deg_label)

        rng = range(-abs_coeff_bound, abs_coeff_bound + 1)

        PASTEL_YELLOW = ManimColor("#FFFFA9")
        PASTEL_BLUE   = ManimColor("#B8E4FF")

        def degree_color(d: int):
            t = (d - 1) / max(1, (max_degree - 1))
            t = t**0.7
            return interpolate_color(PASTEL_YELLOW, PASTEL_BLUE, t)

        sprinkled = Group()

        for degree in range(1, max_degree + 1):
            new_label = Text(f"degree = {degree}", font_size=30).move_to(deg_label)
            self.play(TransformMatchingShapes(deg_label, new_label), run_time=0.35)
            deg_label = new_label

            roots = []
            for t in product(rng, repeat=degree):
                coeffs = np.array([1, *t], dtype=float)
                roots.extend(np.roots(coeffs))

            roots = np.array(roots, dtype=np.complex128)

            xs = roots.real
            ys = roots.imag
            in_view = (
                (np.abs(xs) <= xlim) &
                (np.abs(ys) <= ylim) &
                np.isfinite(xs) &
                np.isfinite(ys)
            )
            xs = xs[in_view]
            ys = ys[in_view]

            pts = np.array([axes.coords_to_point(x, y) for x, y in zip(xs, ys)])

            rng_np = np.random.default_rng(12345 + degree)
            rng_np.shuffle(pts)

            color = degree_color(degree)
            n = len(pts)

            for i in range(chunks):
                a = i * n // chunks
                b = (i + 1) * n // chunks
                if a == b:
                    continue

                cloud_chunk = PMobject(stroke_width=dot_stroke_width)
                cloud_chunk.add_points(pts[a:b], color=color, alpha=1.0)

                sprinkled.add(cloud_chunk)
                self.add(cloud_chunk)
                self.play(FadeIn(cloud_chunk), run_time=chunk_run_time, rate_func=linear)

            self.wait(pause_per_degree)

        self.wait(1.0)