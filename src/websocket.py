import websocket


class WebsocketClient:
    def __init__(self, ws_url="ws://10.10.65.8:8800"):
        self.ws = None
        self.ws_url = ws_url

    def __del__(self):
        pass

    def on_message(self, _, message):
        print("Received message:", message)

    def on_error(self, _, error):
        print("WebSocket error:", error)

    def on_close(self, _, error):
        print("WebSocket connection closed")

    def on_open(self, _):
        print("WebSocket connection opened")
        # 在连接建立后发送消息
        self.ws.send("Hello, WebSocket!")

    def connect(self):
        self.ws = websocket.WebSocketApp(self.ws_url,
                                on_message=self.on_message,
                                on_error=self.on_error,
                                on_close=self.on_close,
                                on_open=self.on_open)
        self.ws.run_forever()


