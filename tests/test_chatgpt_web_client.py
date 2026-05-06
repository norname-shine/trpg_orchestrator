from trpg_orchestrator.chatgpt_web_client import ChatGPTWebClient


def test_chatgpt_binding_takes_precedence_over_campaign_title(monkeypatch):
    monkeypatch.setattr("trpg_orchestrator.chatgpt_web_client.load_project_env", lambda: None)

    client = ChatGPTWebClient({
        "title": "怪物猎人",
        "chatgpt_conversation_binding": {
            "project_name": "TRPG 自动主持",
            "conversation_name": "怪物猎人 固定对话",
        },
    })

    assert client.project_name == "TRPG 自动主持"
    assert client.conversation_name == "怪物猎人 固定对话"
