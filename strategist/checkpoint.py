"""Save one prepared research stage with one atomic state commit.

No sources, approvals, shell commands or external actions are accepted here.
Existing core validators run against a private staging copy while the project
write lock is held. Failed validation leaves the original state unchanged.
"""
import shutil
import tempfile
from pathlib import Path
from . import core


def save(project, bundle):
    core.require(isinstance(bundle, dict), 'Checkpoint must be an object')
    allowed = {'base_revision', 'claims', 'research', 'options', 'proposal'}
    core.require(set(bundle) <= allowed, 'Unsupported checkpoint fields; approvals and external actions are excluded')
    core.require(type(bundle.get('base_revision')) is int, 'base_revision must come from current resume')
    core.require(isinstance(bundle.get('claims', []), list) and len(bundle.get('claims', [])) <= 100, 'At most 100 claims per checkpoint')
    core.require(bool(set(bundle)-{'base_revision'}), 'Empty checkpoint')
    root = Path(project).resolve()
    sha = core.digest(core.canonical(bundle))
    changed = False
    with core.transaction(root) as state:
        previous = state.get('last_checkpoint', {})
        if previous.get('sha256') == sha and previous.get('after_revision') == state['revision']:
            return {'changed': False, 'revision': state['revision'], 'checkpoint_sha256': sha, 'retry': 'Already saved; no repeated actions'}
        core.require(state['revision'] == bundle['base_revision'], 'Stale base_revision; run resume and reconcile new state before saving')
        before_revision = state['revision']
        core.require((root/'blobs').is_dir() and not (root/'blobs').is_symlink(), 'Expected a local blob directory')
        core.require(all(p.is_file() and not p.is_symlink() for p in (root/'blobs').iterdir()), 'Blob directory must contain only local immutable files')
        with tempfile.TemporaryDirectory(prefix='.checkpoint-', dir=root) as temp:
            stage = Path(temp).resolve()
            # Check the exact temporary subtree before automatic recursive cleanup.
            core.require(stage.parent == root and stage.name.startswith('.checkpoint-'), 'Unsafe staging path')
            shutil.copytree(root/'blobs', stage/'blobs')
            core.atomic_write(stage/'state.json', core.canonical(state))
            for claim in bundle.get('claims', []):
                core.claim_add(stage, claim)
            for slot in ('research', 'options'):
                if slot in bundle:
                    core.commit_document(stage, slot, bundle[slot])
            if 'proposal' in bundle:
                p = bundle['proposal']
                core.require(isinstance(p, dict) and set(p) == {'option_id', 'rationale', 'claims'}, 'proposal requires option_id, rationale and a JSON claims array')
                core.propose(stage, p['option_id'], p['rationale'], p['claims'])
            saved = core.load(stage)
            # Revision counts one original transaction, not the staging operations.
            saved['revision'] = before_revision
            if core.canonical(saved) != core.canonical(state):
                for blob in (stage/'blobs').iterdir():
                    core.require(blob.is_file() and not blob.is_symlink(), 'Unexpected staging blob')
                    data = blob.read_bytes()
                    core.require(blob.stem == core.digest(data), 'Staging blob name does not match content')
                    core.put_blob(root, data, blob.suffix)
                saved['last_checkpoint'] = {'sha256': sha, 'before_revision': before_revision,
                                            'after_revision': before_revision+1}
                core.event(saved, 'checkpoint_saved', {'sha256': sha, 'claims': len(bundle.get('claims', [])),
                            'documents': [k for k in ('research', 'options') if k in bundle], 'proposal': 'proposal' in bundle})
                state.clear(); state.update(saved)
                changed = True
    return {'changed': changed, 'revision': core.load(root)['revision'], 'checkpoint_sha256': sha,
            'claims_received': len(bundle.get('claims', [])),
            'documents_received': [k for k in ('research', 'options') if k in bundle],
            'proposal_received': 'proposal' in bundle,
            'decision_approved': core.approved(core.load(root), 'decision')}
