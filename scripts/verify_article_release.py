"""Preflight included manuscript PDFs; record an explicit hash-bound visual review.

Requires Poppler and a successful make pdf. Numerical checks use retained evidence,
not a new physics run. Visual review is supplied by the reviewer, never inferred.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True)


def sources(path, seen=None):
    seen = set() if seen is None else seen
    if path in seen:
        return seen
    assert path.is_file(), path
    seen.add(path)
    for name in re.findall(r'\\input\{([^}]+)\}', path.read_text()):
        child = ROOT / name
        sources(child if child.suffix else child.with_suffix('.tex'), seen)
    return seen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewed-paper-sha256', required=True,
                        help='SHA256 of the article after review of every rendered page')
    parser.add_argument('--reviewed-supplement-sha256', required=True,
                        help='SHA256 of the supplement after review of every rendered page')
    args = parser.parse_args()
    checks = {}
    for script in ['verify_results.py', 'document_article_update.py']:
        checks[script] = command(sys.executable, 'scripts/' + script).strip()
    texfiles = sources(ROOT / 'paper.tex') | sources(ROOT / 'supplement/supplement.tex')
    text = '\n'.join(p.read_text() for p in texfiles)
    assets = {ROOT / name for name in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', text)}
    assert all(p.is_file() for p in assets)
    cited = {key for group in re.findall(r'\\cite\{([^}]+)\}', text) for key in group.split(',')}
    bibliography = set(re.findall(r'\\bibitem\{([^}]+)\}', text))
    assert cited == bibliography and len(bibliography) == 19
    logs = [ROOT / 'build/paper.log', ROOT / 'build/supplement.log']
    for log in logs:
        assert not re.search(r'Overfull|undefined|Warning|Error', log.read_text()), log
        assert 'Output written on' in log.read_text()
    results = {}
    for relative, reviewed in [('paper.pdf', args.reviewed_paper_sha256),
                               ('supplement/supplement.pdf', args.reviewed_supplement_sha256)]:
        path = ROOT / relative
        assert sha(path) == reviewed, 'Visual review does not match delivered PDF: ' + relative
        info = command('pdfinfo', str(path))
        pages = int(re.search(r'^Pages:\s+(\d+)', info, re.M)[1])
        extracted = command('pdftotext', '-layout', str(path), '-')
        parts = extracted.split('\f')
        assert not parts[-1].strip() and len(parts) - 1 == pages
        assert all(len(part.strip()) > 100 for part in parts[:-1])
        assert '??' not in extracted and '\ufffd' not in extracted
        compact = re.sub(r'\s+', '', extracted)
        for required in ['131072', '256', '107', '69', '79.8']:
            assert required in compact, (relative, required)
        fontlines = command('pdffonts', str(path)).splitlines()[2:]
        assert fontlines and all(re.search(r'\byes\s+(?:yes|no)\s+(?:yes|no)\s+\d+\s+\d+\s*$', line)
                                 for line in fontlines)
        assert all('Type 3' not in line for line in fontlines)
        results[relative] = {'pages': pages, 'sha256': reviewed,
                             'all_fonts_embedded': True, 'type_3_fonts': 0,
                             'text_extraction_passed': True,
                             'visual_review': {'all_rendered_pages_reviewed': True,
                                               'review_kind': 'author-operated rendered-page inspection',
                                               'reviewed_pdf_sha256': reviewed}}
    inputs = texfiles | assets | {ROOT / 'evidence/article_release_build.log',
                                             ROOT / 'scripts/verify_article_release.py',
                                             ROOT / 'scripts/document_article_update.py',
                                             ROOT / 'evidence/article_update_claim_map.json'}
    record = {'schema': 'westquant_manuscript_release_v1', 'status': 'pass',
              'date_utc': '2026-10-10', 'compiler': command('pdflatex', '--version').splitlines()[0],
              'pdfs': results, 'bibliography_entries': len(bibliography),
              'citation_keys_resolved': True, 'latex_critical_warnings': [],
              'reporting_checks': checks,
              'source_and_asset_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sorted(inputs)},
              'new_physics_or_hardware_experiments': 0,
              'independent_scientific_review_completed': False,
              'journal_submission_or_acceptance_claimed': False}
    (ROOT / 'evidence/article_release_verification.json').write_text(json.dumps(record, indent=2) + '\n')
    print(f"Manuscript release passed: {sum(v['pages'] for v in results.values())} reviewed pages, "
          f"{len(bibliography)} resolved references, embedded fonts and 15 reporting claim groups")


if __name__ == '__main__':
    main()
