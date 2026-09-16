import gradio as gr
import requests
import json

BACKEND_URL = "http://localhost:8000/v1/chat/completions"
HEADERS = {"Content-Type": "application/json"}


def chat_with_bot(message, history):
    if not message or not message.strip():
        return "请输入你想咨询的淘宝问题。"

    data = {
        "messages": [
            {"role": "user", "content": message}
        ],
        "stream": False
    }

    try:
        response = requests.post(
            BACKEND_URL,
            headers=HEADERS,
            data=json.dumps(data),
            timeout=60
        )

        print("状态码:", response.status_code)
        print("原始返回:", response.text)

        res_json = response.json()

        if response.status_code != 200:
            return f"后端返回异常：{res_json.get('detail', res_json)}"

        if "choices" in res_json:
            bot_reply = res_json["choices"][0]["message"]["content"]
        else:
            bot_reply = f"后端返回异常：{res_json}"

    except Exception as e:
        bot_reply = (
            "请求失败：请确认后端已启动，且可访问 http://localhost:8000。\n"
            f"错误信息：{e}"
        )

    return bot_reply


demo = gr.ChatInterface(
    fn=chat_with_bot,
    title="淘宝知识库问答助手",
    description="可咨询订单、退款、退货、物流、物流状态、优惠券、售后等淘宝相关问题。",
    textbox=gr.Textbox(
        placeholder="例如：淘宝退款多久到账？/怎么申请退货？/优惠券为什么不能用？",
        scale=7
    )
)


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860
    )