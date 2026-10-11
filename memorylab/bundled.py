"""Verified, licensed numerical inputs; paper references are not cached bytes."""
import hashlib
from pathlib import Path
from .common import digest, read_json, write_json, MissingData


def verified_group(directory, group):
    directory = Path(directory).resolve()
    manifest = read_json(directory/'manifest.json')
    records = []
    # Verify the entire group before writing any derived output.
    for item in manifest['groups'][group]:
        path = (directory/item['path']).resolve()
        if not path.is_relative_to(directory) or not path.is_file():
            raise MissingData('Bundled input missing: '+item['path'])
        if item['license'] != 'CC-BY-4.0':
            raise MissingData('Bundled input license not reviewed')
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise MissingData('Bundled input SHA256 mismatch: '+item['path'])
        records.append((item, path))
    return records


def install_group(directory, group, cache):
    verified = verified_group(directory, group)
    cache = Path(cache)
    records = []
    for item, path in verified:
        name = item['original_file_name']
        relative = Path('raw')/item['sha256']/name
        target = cache/relative; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        rec = {'id':digest([group,item['url'],item['revision'],item['sha256']]),
               'source_id':group, 'url':item['url'], 'source_revision':item['revision'],
               'sha256':item['sha256'], 'file_name':name, 'relative_path':relative.as_posix(),
               'license':item['license'], 'redistribution_approved':True,
               'bytes_verified':True, 'transport':'bundled released data; no network'}
        records.append(rec)
    return records


def reviewed_baseline_inputs(config, cache, directory):
    records = install_group(directory, 'teller2025', cache)
    artifacts = {r['file_name']:r for r in records}
    expected = set(config['download_files'])-{'3a.csv'}
    if set(artifacts) != expected:
        raise MissingData('Bundled Teller numerical inputs do not match reviewed configuration')
    for name, rec in artifacts.items():
        raw = (Path(cache)/rec['relative_path']).read_bytes()
        locked = config['source_lock']['files'][name]
        if rec['sha256'] != locked['sha256'] or 'md5:'+hashlib.md5(raw).hexdigest() != locked['archive_checksum']:
            raise MissingData('Reviewed Teller lock mismatch: '+name)
    # Reviewed transcriptions remain tied to their original paper hashes.
    # No claim is made that unbundled paper bytes were downloaded/verified now.
    for source in config['paper_sources']:
        artifacts[source['filename']] = {'id':digest(['reviewed_source_reference',source]),
            'source_id':source['id'], 'url':source['url'], 'source_revision':None,
            'sha256':source['sha256'], 'file_name':source['filename'],
            'record_kind':'reviewed_source_reference', 'bytes_verified':False}
    manifest_path = Path(directory)/'manifest.json'
    metadata = {'id':digest(['bundled_manifest',manifest_path.read_bytes().hex()]),
        'source_id':'bundled_manifest', 'source_revision':'westquant_bundled_experimental_inputs_v1',
        'url':'https://doi.org/10.5281/zenodo.14929997',
        'sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'record_kind':'bundled_manifest', 'bytes_verified':True}
    return artifacts, metadata


def prepare_reviewed(root, directory):
    from .t2data import parse_pr2026
    root = Path(root)
    records = install_group(directory, 'pr2026', root/'cache')
    curves, quantum = parse_pr2026(root, records)
    for curve in curves:
        write_json(root/'processed/curves'/(curve['id']+'.json'), curve)
    write_json(root/'processed/quantum_readout.json', quantum)
    write_json(root/'processed/molecular_rows.json', [])
    write_json(root/'source_lock.json', {'artifacts':records, 'source_revisions_pinned':True})
    return {'artifacts':len(records), 'curves':len(curves),
        'provisional_observations':0, 'reviewed_observations':0,
        'molecular_source_audit':'not_reproduced; unlicensed source requires separate online retrieval',
        'physical_T2_requires_review':True, 'output':str(root/'processed')}
