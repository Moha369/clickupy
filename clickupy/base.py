class ClickUpResource:
    def __init__(self, client):
        self.client = client

    def _request(self, method, endpoint, **kwargs):
        return self.client.request(method, endpoint, **kwargs)
