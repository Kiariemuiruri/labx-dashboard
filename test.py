import base64, json
encoded = base64.b64encode(open("credentials.json", "rb").read()).decode()
print(encoded)
