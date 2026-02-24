import numpy as np
import matplotlib.pyplot as plt
from itertools import product
from mpmath import polyroots, mp

abs_coeff_bound = 1
degrees = np.arange(1, 10)  
degrees = degrees[::-1]

mp.dps = 50  # set precision 

rng = range(-abs_coeff_bound, abs_coeff_bound + 1)

fig, ax = plt.subplots(figsize=(8, 8))

for degree in degrees:
    # Generate all monic polynomials of this degree with coefficients in [-bound, bound]
    polynomials = [[1] + list(t) for t in product(rng, repeat=degree)]

    roots_this_degree = []
    exception_count = 0

    for coeffs in polynomials:
        try:
            roots_mpm = polyroots(coeffs, maxsteps=100)
            roots_this_degree.extend([complex(r) for r in roots_mpm])
        except Exception:
            exception_count += 1

    roots_this_degree = np.array(roots_this_degree, dtype=np.complex128)

    # Plot roots for this degree as one "series" (matplotlib auto-assigns a new color each loop)
    cmap = plt.cm.YlGnBu
    color = cmap(0.1 if degree % 2 == 0 else 0.6)
    ax.plot(roots_this_degree.real, roots_this_degree.imag, '.', markersize=2, color=color, label=f"deg {degree}")

# Unit circle
theta = np.linspace(0, 2*np.pi, 400)
ax.plot(np.cos(theta), np.sin(theta), 'k--', alpha=0.3, label='Unit circle')
ax.set_xlabel('Real part', fontsize=12)
ax.set_ylabel('Imaginary part', fontsize=12)
ax.set_title(f'Roots of {len(degrees)} degrees polynomials with coeffs in [-{abs_coeff_bound}, {abs_coeff_bound}]', fontsize=14)
ax.grid(True, alpha=0.3)
ax.axhline(0, color='k', linewidth=0.5)
ax.axvline(0, color='k', linewidth=0.5)
ax.set_aspect('equal')

# Put legend outside if it gets crowded
ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=9)

plt.tight_layout()
plt.show()
