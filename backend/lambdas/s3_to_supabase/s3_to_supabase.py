import boto3
import requests
import os
import pandas as pd
import io

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
    
    # Initialize S3 client and fetch the CSV data from S3
    s3 = boto3.client('s3')
    s3_object = s3.get_object(Bucket=bucket, Key=key)
    
    # Read the CSV file content into a pandas DataFrame
    csv_data = s3_object['Body'].read()
    df = pd.read_csv(io.BytesIO(csv_data))

     # Fetch existing IDs from Supabase to reduce duplicate checks
    existing_ids = set()
    response = requests.get(
        f'{supabase_url}/rest/v1/{supabase_table}',
        headers=headers,
        params={'select': 'id'}
    )
    if response.status_code == 200:
        existing_ids = {record['id'] for record in response.json()}

    # Filter out records that already exist in Supabase
    df_new = df[~df["_id"].isin(existing_ids)]
    if df_new.empty:
        print("No new data to push.")
        return {'statusCode': 200, 'body': 'No new data to push.'}

    # Prepare new records for insertion in chunks
    for chunk_start in range(0, len(df_new), 500):  # Chunk size of 500
        chunk = df_new.iloc[chunk_start:chunk_start+500]
        chunk_records = chunk.to_dict(orient='records')  # Convert chunk to list of dictionaries

        # Push the chunk of new records to Supabase
        response = requests.post(
            f'{supabase_url}/rest/v1/{supabase_table}',
            headers=headers,
            json=chunk_records
        )
        if response.status_code == 201:
            print(f"Chunk with {len(chunk_records)} records pushed successfully!")
        else:
            print(f"Failed to push chunk: {response.status_code} - {response.text}")

    return {'statusCode': 200, 'body': 'Data pushed successfully'}
