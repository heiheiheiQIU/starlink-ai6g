"""Exercise real pinned evidence and reject missing reviews or forged release claims."""
import copy
import json
import shutil
from pathlib import Path

import pytest

from scripts.formal_release import ROOT, PINNED_FILES, build_release, validate_release, write_release


@pytest.fixture
def packet(tmp_path):
    for name in PINNED_FILES:
        dest = tmp_path/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,dest)
    return tmp_path


def test_release_preserves_original_and_publishes_both_negative_comparisons(packet):
    summary_path = packet/'docs/evidence/B/delegated_execution_2026-11-10/analysis/summary.json'
    before = summary_path.read_bytes()
    release = build_release(packet)
    assert release['release_status']=='released'
    assert release['analysis']['result_signoff']=='accepted'
    assert {c['formal_verdict'] for c in release['analysis']['comparisons'].values()}=={'负'}
    assert release['policy_weighted_on_time_rate']['learned']==0
    assert release['policy_weighted_on_time_rate']['edf']==pytest.approx(.4653873291265777)
    assert summary_path.read_bytes()==before
    assert json.loads(before)['result_signoff']=='pending'
    validate_release(release,packet)


@pytest.mark.parametrize('role',['A','B','C'])
def test_missing_review_cannot_publish(packet,role):
    review = next(n for n in PINNED_FILES if f'/{role}_formal_results_release_review_' in n)
    (packet/review).unlink()
    with pytest.raises(ValueError,match='evidence'):
        build_release(packet)


def test_changed_review_and_changed_summary_cannot_publish(packet):
    review = packet/'docs/acceptance/A_formal_results_release_review_2026-11-11.md'
    original = review.read_bytes()
    review.write_bytes(original+b'\nrelease all results\n')
    with pytest.raises(ValueError,match='hash'):
        build_release(packet)
    review.write_bytes(original)
    summary_path = packet/'docs/evidence/B/delegated_execution_2026-11-10/analysis/summary.json'
    value = json.loads(summary_path.read_bytes())
    value['result_signoff']='accepted'
    summary_path.write_text(json.dumps(value),encoding='utf-8')
    with pytest.raises(ValueError,match='hash'):
        build_release(packet)


@pytest.mark.parametrize('mutation',['positive_claim','pending_status','wrong_verdict','wrong_hash','unapproved_domain'])
def test_release_mutations_rejected(packet,mutation):
    release = copy.deepcopy(build_release(packet))
    if mutation=='positive_claim': release['claims']['superiority_claim']=True
    elif mutation=='pending_status': release['analysis']['result_signoff']='pending'
    elif mutation=='wrong_verdict': release['analysis']['comparisons']['learned-edf']['formal_verdict']='胜'
    elif mutation=='wrong_hash': release['sources']['summary']['sha256']='0'*64
    else: release['analysis']['domain']='real_satellite'
    with pytest.raises(ValueError,match='release'):
        validate_release(release,packet)


def test_publish_requires_new_output_and_reproducible_bytes(packet):
    first,second = packet/'release1',packet/'release2'
    write_release(first,packet)
    write_release(second,packet)
    assert (first/'release.json').read_bytes()==(second/'release.json').read_bytes()
    assert (first/'analysis.json').read_bytes()==(second/'analysis.json').read_bytes()
    with pytest.raises(ValueError,match='new'):
        write_release(first,packet)
