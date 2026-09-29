"""Exercise only the isolated, authenticated localhost mock API."""

import json
import os
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:18012"
KEY = os.environ["BACKEND_API_KEY"]


def request(path, method="GET", payload=None, authenticated=True, expected=200):
    headers = {"Content-Type": "application/json"}
    if authenticated:
        headers["x-gemmalens-api-key"] = KEY
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        response = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        assert response.status == expected, (path, response.status, expected)
        body = response.read()
        return json.loads(body) if body else None


def main():
    assert request("/health", authenticated=False) == {"status": "ok"}
    request("/documents", authenticated=False, expected=401)
    model = request("/models/status")
    assert model["provider"] == "mock" and model["mock_fallback"] is True, model
    document = request("/documents", "POST", {
        "title": "Linux isolated smoke",
        "content": (
            "Although previous studies have suggested a correlation between sleep deprivation "
            "and reduced cognitive performance, the extent to which these findings generalize "
            "across real-world learning environments remains unclear. To address this gap, "
            "we analyze longitudinal study logs collected from undergraduate students."
        ),
        "source_type": "text",
    })
    item_id = None
    try:
        analysis = request(f"/documents/{document['id']}/analyze", "POST")
        assert analysis["document_id"] == document["id"] and analysis["terms"]
        term = analysis["terms"][0]
        item = request("/dictionary/items", "POST", {
            "item_type": "term", "text": term["term"],
            "meaning": term["meaning"], "document_id": document["id"],
        })
        item_id = item["id"]
        assert any(row["id"] == item_id for row in request("/dictionary/items"))
    finally:
        if item_id:
            request(f"/dictionary/items/{item_id}", "DELETE", expected=204)
        request(f"/documents/{document['id']}", "DELETE", expected=204)
    print("PASS: health, authentication, mock analysis, dictionary save/read/delete, document cleanup")


if __name__ == "__main__":
    main()
