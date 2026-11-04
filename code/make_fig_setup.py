"""Fig. 12a - breach-trial setup and protocol schematic (IPA R1, Section 4.9).

Draws the sealed-jar arrangement and the three-phase protocol. No measured or
predicted data appear here: the CO2 record itself is plotted separately once the
trial has been run.
"""
import sys, os
sys.path.insert(0, 'D:/claude_ai/_templates')
import pro_style
pro_style.apply()

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle

C = pro_style.PALETTE
BLUE, RED, GREEN, ORANGE, PURPLE, CYAN, GREY = C
OUT = 'D:/claude_ai/IoT_Paper/R1/figures'

fig = plt.figure(figsize=(7.4, 3.5))
gs = fig.add_gridspec(1, 2, width_ratios=[1.12, 1.0], wspace=0.40)

# ---------------------------------------------------------------- panel (a)
ax = fig.add_subplot(gs[0, 0])
ax.set_xlim(0, 13.2); ax.set_ylim(0, 10.6); ax.axis('off')
ax.set_title('(a) Sealed-jar arrangement', loc='left', pad=6, x=-0.02)

JX0, JX1 = 4.35, 8.85          # jar walls
ax.add_patch(FancyBboxPatch((JX0, 0.75), JX1 - JX0, 7.15,
                            boxstyle='round,pad=0,rounding_size=0.3',
                            lw=1.6, ec='#3A3A3A', fc='#F4F8FB', zorder=1))
ax.add_patch(FancyBboxPatch((JX0 - 0.26, 7.75), JX1 - JX0 + 0.52, 0.8,
                            boxstyle='round,pad=0,rounding_size=0.16',
                            lw=1.6, ec='#3A3A3A', fc='#D7DEE4', zorder=3))
ax.plot([JX0 - 0.26, JX1 + 0.26], [7.75, 7.75], color=RED, lw=2.4, zorder=4)

# node, suspended from the underside of the lid
ax.plot([6.6, 6.6], [7.70, 6.35], color='#555', lw=1.0, zorder=4)
ax.plot([7.3, 7.3], [7.70, 6.35], color='#555', lw=1.0, zorder=4)
ax.add_patch(FancyBboxPatch((5.65, 2.95), 2.6, 3.45,
                            boxstyle='round,pad=0,rounding_size=0.16',
                            lw=1.3, ec='#2A2A2A', fc='white', zorder=5))
ax.add_patch(Rectangle((5.88, 3.35), 0.9, 1.5, lw=0.9, ec=BLUE,
                       fc='#E3ECF4', zorder=6))
ax.add_patch(Circle((7.80, 5.90), 0.24, lw=1.2, ec=GREEN, fc='white', zorder=7))
ax.text(7.05, 4.05, 'node', ha='center', va='center', fontsize=8.5, zorder=6)

# jar floor
ax.plot([JX0 + 0.12, JX1 - 0.12], [1.30, 1.30], color='#9AA3AB', lw=1.0, zorder=2)

# greaseproof paper and whole mushroom on the jar floor, below the node
ax.plot([5.35, 7.55], [1.30, 1.30], color=GREY, lw=2.6,
        solid_capstyle='round', zorder=5)
ax.add_patch(Rectangle((6.33, 1.30), 0.28, 0.48, lw=1.1, ec=ORANGE,
                       fc='#F6E3D2', zorder=5))
ax.add_patch(Circle((6.47, 2.02), 0.46, lw=1.2, ec=ORANGE, fc='#F6E3D2', zorder=6))

# clearance between produce and node
ax.annotate('', xy=(8.50, 2.88), xytext=(8.50, 1.34),
            arrowprops=dict(arrowstyle='<->', color='#444', lw=1.0))

# headspace bracket, inside the jar

LEAD = dict(arrowstyle='-', lw=0.8, color='#666',
            shrinkA=2, shrinkB=2, connectionstyle='arc3,rad=0')
def tag(text, xy, xytext, color, ha):
    ax.annotate(text, xy=xy, xytext=xytext, ha=ha, va='center',
                fontsize=7.8, color=color, linespacing=1.25,
                arrowprops=dict(**LEAD))

# right gutter
tag('headspace\n1.4 L', (8.55, 7.00), (9.45, 7.45), BLUE, 'left')
tag('lid sealed throughout;\nnothing passes through it', (JX1 + 0.1, 8.15), (9.45, 9.35), RED, 'left')
tag('sensor vent\nunobstructed',    (8.04, 5.90),      (9.45, 6.60),  GREEN, 'left')
tag('suspended\nfrom the lid', (6.6, 7.05), (3.85, 7.70), '#444', 'right')
# left gutter
tag('display faces\nglass wall',    (5.88, 4.10),      (3.85, 5.10),  BLUE,  'right')
tag('13.49 g whole mushrooms\non paper on the jar floor',
            (6.01, 2.02), (3.85, 1.55), ORANGE, 'right')

tag('5-10 cm\nclearance', (8.50, 2.1), (9.45, 1.70), '#444', 'left')

# ---------------------------------------------------------------- panel (b)
ax2 = fig.add_subplot(gs[0, 1])
ax2.set_title('(b) Three-phase protocol', loc='left', pad=6, x=-0.02)

phases = [(0, 45, 4.0, BLUE, 'A  baseline'),
          (45, 90, 21.0, RED, 'B  breach'),
          (90, 135, 4.0, BLUE, 'C  recovery')]
for t0, t1, T, col, lbl in phases:
    ax2.add_patch(Rectangle((t0, 0), t1 - t0, T, fc=col, alpha=0.12,
                            ec='none', zorder=0))
    ax2.plot([t0, t1], [T, T], color=col, lw=2.6, solid_capstyle='butt', zorder=3)
    ax2.text((t0 + t1) / 2, 25.2, lbl, ha='center', va='bottom',
             fontsize=8, color=col, linespacing=1.3)

for t, y0, y1 in [(45, 4.0, 21.0), (90, 21.0, 4.0)]:
    ax2.annotate('', xy=(t, y1), xytext=(t, y0),
                 arrowprops=dict(arrowstyle='->', color='#444', lw=1.2))

ax2.axvline(15, color=GREY, ls=':', lw=1.2, zorder=2)
ax2.annotate('pilot check\n(jar stays sealed)', xy=(15, 11.5), xytext=(21, 14.2),
             fontsize=7.8, color='#444', va='center', ha='left', linespacing=1.25,
             arrowprops=dict(arrowstyle='-', lw=0.8, color='#666'))

ax2.set_xlim(-5, 143); ax2.set_ylim(0, 32)
ax2.set_xticks([0, 15, 45, 90, 135])
ax2.set_xlabel('Elapsed time after sealing (min)')
ax2.set_ylabel('Air temperature (°C)')
ax2.set_yticks([0, 4, 21])
ax2.spines['left'].set_bounds(0, 21)

fig.savefig(os.path.join(OUT, 'fig12a_breach_setup.pdf'))
fig.savefig(os.path.join(OUT, 'fig12a_breach_setup.png'), dpi=600)
print('written')
