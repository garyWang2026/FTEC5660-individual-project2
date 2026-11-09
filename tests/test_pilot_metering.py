from types import SimpleNamespace
import json
import pytest
from reproduction.run_pilot import UsageRecorder, PilotLimitReached, select_questions

class Usage:
    prompt_tokens = 100
    completion_tokens = 20
    total_tokens = 120
    def model_dump(self):
        return {'prompt_cache_hit_tokens': 40}

def response():
    return SimpleNamespace(usage=Usage(), model='test-model', id='test-id', choices=[SimpleNamespace(finish_reason='stop')])

def test_records_durable_json_lines_and_cached_tokens(tmp_path):
    path=tmp_path/'usage.jsonl'
    meter=UsageRecorder(path)
    call=meter.wrap(lambda **kw: response())
    for _ in range(2):
        call(model='test-model', messages=[{'role':'user','content':'test'}])
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows)==2
    assert meter.summary()['total_tokens']==240
    assert meter.summary()['cached_input_tokens']==80
    assert meter.summary()['estimated_cost_cny_off_peak']==pytest.approx((120+80*.02+40*4)/1e6)
    assert meter.reserved_tokens==0

def test_call_limit_stops_before_another_request(tmp_path):
    calls=[]
    meter=UsageRecorder(tmp_path/'usage.jsonl',max_calls=1)
    def create(**kwargs):
        calls.append(kwargs)
        return response()
    call=meter.wrap(create)
    call(model='test-model',messages=[{'role':'user','content':'test'}])
    with pytest.raises(PilotLimitReached):
        call(model='test-model',messages=[{'role':'user','content':'test'}])
    assert len(calls)==1

def test_token_reservation_stops_before_request(tmp_path):
    meter=UsageRecorder(tmp_path/'usage.jsonl',max_tokens=1)
    with pytest.raises(PilotLimitReached):
        meter.wrap(lambda **kw: pytest.fail('must not send'))(model='test-model',messages=[{'role':'user','content':'test'}])
    assert meter.events==[]

def test_failures_preserve_usage_log_and_release_reservation(tmp_path):
    path=tmp_path/'usage.jsonl'
    meter=UsageRecorder(path)
    def create(**kwargs):
        raise TimeoutError('simulated failure')
    with pytest.raises(TimeoutError):
        meter.wrap(create)(model='test-model',messages=[{'role':'user','content':'test'}])
    assert json.loads(path.read_text())['error_type']=='TimeoutError'
    assert meter.summary()['failed_api_calls']==1
    assert meter.reserved_tokens==0

def test_fixed_selection_covers_categories_without_adversarial_questions():
    sample={'qa':[{'category':c,'answer':str(i)} for c in range(1,6) for i in range(5)]}
    a=select_questions(sample)
    assert a==select_questions(sample)
    assert len(a)==8
    assert sorted(q['category'] for _,q in a)==[1,1,2,2,3,3,4,4]
