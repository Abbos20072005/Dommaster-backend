import requests

response = requests.post(
    "http://localhost:8080/send_order",
    headers={"X-Auth-Token": "supersecrettoken123"},
    json={
        "orders": [
            {"fruit": "sement", "qty": "5kg"},
            {"fruit": "shkaturka", "qty": "20 bags"},
            {"fruit": "shpatel", "qty": "100 pcs"},
            {"fruit": "kirpich", "qty": "500 pcs"}
        ]
    }
)

print(response.status_code)
print(response.json())
