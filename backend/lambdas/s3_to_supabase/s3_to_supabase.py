import json

def handler(event, context):
    print("Received event: " + json.dumps(event))
    # Mock 200 response
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Hello, World!"})
    }