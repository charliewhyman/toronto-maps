import boto3
import requests
import os
import json

def handler(event, context):
    # Get environment variables for Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_access_token = os.getenv('SUPABASE_ACCESS_TOKEN')
    supabase_table = os.getenv('SUPABASE_TABLE')

    # Set up headers for Supabase API requests
    headers = {
        'Authorization': f'Bearer {supabase_access_token}',
        'Content-Type': 'application/json'
    }

    # Get object names and keys from event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    # Initialize S3 client and fetch the data from S3
    s3 = boto3.client('s3')
    s3_object = s3.get_object(Bucket=bucket, Key=key)
    data = json.loads(s3_object['Body'].read().decode('utf-8'))

    # Identify new records and prepare them for insertion
    new_data = []
    for record in data:
        unique_id = record.get("_id")  # Ensure this is a unique identifier in your dataset
        if not unique_id:
            continue

        # Check if the record already exists in Supabase
        response = requests.get(
            f'{supabase_url}/rest/v1/{supabase_table}',
            headers=headers,
            params={'id': f'eq.{unique_id}'}
        )
        
        if response.status_code == 200 and len(response.json()) == 0:
            new_data.append(record)  # Add new records to the list

    # Push new records to Supabase if there are any
    if new_data:
        response = requests.post(
            f'{supabase_url}/rest/v1/{supabase_table}',
            headers=headers,
            json=new_data
        )
        if response.status_code == 201:
            print("New data pushed successfully!")
        else:
            print(f"Failed to push data: {response.status_code} - {response.text}")
    else:
        print("No new data to push.")

    return {'statusCode': 200, 'body': 'Success'}
