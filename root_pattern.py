import numpy as np
import matplotlib.pyplot as plt
from itertools import product
from mpmath import polyroots, mp

degree = 8
abs_coeff_bound = 1

rng = range(-abs_coeff_bound, abs_coeff_bound+1)
polynomials = [[1] + list(t) for t in product(rng, repeat=degree)]  # yields lists of length degree+1

root_list = []
polynomials_count = len(polynomials)
exception_count = 0

for coefficients in polynomials:

    # Set precision for mpmath (higher = more accurate but slower)
    mp.dps = 50  # 50 decimal places

    try:
        # Find roots using mpmath's polyroots (implements a variant of the MPSolve algorithm)
        roots_mpm = polyroots(coefficients, maxsteps=100)
        roots = [complex(r) for r in roots_mpm]

        root_list.extend(roots)

    except Exception as e:
        exception_count += 1
        # print(f"Polynomial coefficients: {coefficients}")
        # print(f"An error occurred while finding roots: {e}")

print(f"Exceptions encountered for {exception_count} polynomials out of {polynomials_count}, or {exception_count/polynomials_count*100:.2f}%.")

# Convert to numpy complex for plotting
roots = np.array([complex(r) for r in root_list])

# Plot the roots in the complex plane
fig, ax = plt.subplots(figsize=(8, 8))

# Plot roots as red dots
ax.plot(roots.real, roots.imag, 'ko', markersize=2, label='Roots')

# Add unit circle for reference
theta = np.linspace(0, 2*np.pi, 200)
ax.plot(np.cos(theta), np.sin(theta), 'k--', alpha=0.3, label='Unit circle')

# Labels and formatting
ax.set_xlabel('Real part', fontsize=12)
ax.set_ylabel('Imaginary part', fontsize=12)
ax.set_title(f'Roots of polys of degree {degree} with int coeffs in [-{abs_coeff_bound}, {abs_coeff_bound}]', fontsize=14)
ax.grid(True, alpha=0.3)
ax.axhline(0, color='k', linewidth=0.5)
ax.axvline(0, color='k', linewidth=0.5)
ax.set_aspect('equal')
ax.legend()

plt.tight_layout()
#plt.savefig('polynomial_roots.png', dpi=150)
#print("\nPlot saved to 'polynomial_roots.png'")
plt.show()