"""Provider compatibility verified through an HTTP mock: no real API requests."""
import httpx
import pytest
from openai import OpenAI
from simplemem.core.utils.llm_client import LLMClient

@pytest.mark.parametrize('base,thinking,expected', [
    ('https://api.deepseek.com', False, {'type':'disabled'}),
    ('https://api.deepseek.com/v1', True, {'type':'enabled'}),
    ('https://example.com/v1', False, None),
])
def test_thinking_setting_reaches_request(base, thinking, expected):
    import json
    requests = []
    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={'id':'mock', 'object':'chat.completion', 'created':0, 'model':'mock-model', 'choices':[{'index':0, 'message':{'role':'assistant','content':'OK'}, 'finish_reason':'stop'}]})
    transport = httpx.MockTransport(handle)
    http = httpx.Client(transport=transport)
    client = LLMClient(api_key='offline-test-only', model='mock-model', base_url=base, enable_thinking=thinking, use_streaming=False)
    client.client.close()
    client.client = OpenAI(api_key='offline-test-only', base_url=base, http_client=http)
    try:
        assert client.chat_completion([{'role':'user','content':'test'}], max_retries=1) == 'OK'
        assert len(requests) == 1
        assert requests[0].get('thinking') == expected
    finally:
        client.client.close()
