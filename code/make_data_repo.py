"""Assemble the public data and code repository for the IoT-Tracer paper.

Copies the measurement records, the analysis scripts, the derived results, the
figures they produce and the bench documentation into a standalone directory
that runs without anything from the authors' working tree.

Run from anywhere:  python code/make_data_repo.py [destination]
"""
import os
import shutil
import sys

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = sys.argv[1] if len(sys.argv) > 1 else r'D:/iot-tracer-cold-chain-validation'

DATA = [
    'data/node_7CDFA1FE05B5_breach_2026-11-03.csv',
    'data/reference_extech_sd800_2026-11-03.tsv',
    'data/refrigerator _7CDFA1FE05B5_05102026.csv',
    'data/parsed_05102026_two_streams.csv',
    'data/fridge_steady_window.csv',
    'data/EXP C cold_7CDFA1FE05B5.csv',
    'data/EXP C_7CDFA1FE05B5_t0_t1.csv',
    'data/reference_extech_sd800_2026-11-04.tsv',
    'data/BDM_20261105_084817682.csv',
]
CODE = [
    'code/pro_style.py',
    'code/analyze_expA.py',
    'code/analyze_expA_kinetics.py',
    'code/analyze_expA_detection.py',
    'code/analyze_expA_thermal.py',
    'code/energy_model.py',
    'code/analyze_expC.py',
    'code/table5_budget.py',
    'code/audit_numbers.py',
    'code/analyze_current_log.py',
    'code/make_fig_breach.py',
    'code/make_fig_setup.py',
    'code/make_fig_fridge.py',
    'code/make_data_repo.py',
]
RESULTS = [
    'results/expA_summary.json',
    'results/expA_kinetics.json',
    'results/expA_detection.json',
    'results/expA_thermal.json',
    'results/energy_model.json',
    'results/expC_selfheating.json',
    'results/table5_budget.json',
    'results/current_log.json',
]
FIGURES = [
    'figures/fig11_fridge_dynamics.pdf', 'figures/fig11_fridge_dynamics.png',
    'figures/fig12a_breach_setup.pdf', 'figures/fig12a_breach_setup.png',
    'figures/fig12b_breach_timeseries.pdf', 'figures/fig12b_breach_timeseries.png',
    'figures/fig12c_breach_kinetics.pdf', 'figures/fig12c_breach_kinetics.png',
]
DOCS = [('EXPA_RUN_LOG.md', 'docs/breach_trial_run_log.md')]
PHOTOS = [
    ('RTEU_Tracer/Tracer/20261104_112434.jpg', 'docs/photos/06_selfheating_run1.jpg'),
    ('RTEU_Tracer/Tracer/20261104_132121.jpg', 'docs/photos/07_selfheating_run2.jpg'),
    ('RTEU_Tracer/Tracer/20261103_131843.jpg', 'docs/photos/01_produce_weighed.jpg'),
    ('RTEU_Tracer/Tracer/20261103_135427.jpg', 'docs/photos/02_reference_in_refrigerator.jpg'),
    ('RTEU_Tracer/Tracer/20261103_140757.jpg', 'docs/photos/03_sealed_jar_in_refrigerator.jpg'),
    ('RTEU_Tracer/Tracer/20261103_151804.jpg', 'docs/photos/04_breach_at_ambient.jpg'),
    ('RTEU_Tracer/Tracer/20261103_160130.jpg', 'docs/photos/05_returned_to_refrigerator.jpg'),
]


def copy(rel, dest_rel=None):
    src = os.path.join(SRC, rel)
    if not os.path.exists(src):
        print('  MISSING  ' + rel)
        return False
    dst = os.path.join(DEST, dest_rel or rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    print('  %-52s %s' % (rel, dest_rel or rel))
    return True


MAX_PHOTO_PX = 1600


def copy_photo(rel, dest_rel):
    """Downscale on the way in, honouring the EXIF orientation.

    Copying the camera original leaves a 4 MB file that some viewers show
    sideways, because the rotation lives in EXIF and is lost on resize unless
    it is applied first. Doing this here rather than by hand means a rebuild of
    the repository cannot undo it.
    """
    src = os.path.join(SRC, rel)
    if not os.path.exists(src):
        print('  MISSING  ' + rel)
        return False
    dst = os.path.join(DEST, dest_rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        from PIL import Image, ImageOps
    except ImportError:
        shutil.copy2(src, dst)
        print('  %-52s %s  (Pillow missing: copied full size)' % (rel, dest_rel))
        return True
    im = ImageOps.exif_transpose(Image.open(src))
    im.thumbnail((MAX_PHOTO_PX, MAX_PHOTO_PX))
    im.save(dst, quality=85, optimize=True)
    print('  %-52s %s  %dx%d' % (rel, dest_rel, im.size[0], im.size[1]))
    return True


def main():
    os.makedirs(DEST, exist_ok=True)
    n = 0
    for group, items in (('data', DATA), ('code', CODE), ('results', RESULTS),
                         ('figures', FIGURES)):
        print(group + ':')
        for rel in items:
            n += copy(rel)
    print('docs:')
    for rel, dst in DOCS:
        n += copy(rel, dst)
    for rel, dst in PHOTOS:
        n += copy_photo(rel, dst)
    print('')
    print('%d files written to %s' % (n, DEST))


if __name__ == '__main__':
    main()
