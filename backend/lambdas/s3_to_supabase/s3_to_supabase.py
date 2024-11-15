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
        'apikey': supabase_access_token,
        'Authorization': f'Bearer {supabase_access_token}',
        'Content-Type': 'application/json'
    }

    # Get object names and keys from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    print("Bucket:", bucket)
    print("Key:", key)
    
    # Initialize S3 client and fetch the CSV data from S3
    s3 = boto3.client('s3')
    try:
        s3_object = s3.get_object(Bucket=bucket, Key=key)
        csv_data = s3_object['Body'].read()
        df = pd.read_csv(io.BytesIO(csv_data))
        print("CSV data loaded successfully")
    except Exception as e:
        print("Error loading CSV from S3:", e)
        return {'statusCode': 500, 'body': f'Error loading CSV: {e}'}

    # Handle empty values in the CSV
    df = df.where(df.notna(), '')

    # Fetch existing IDs from Supabase
    existing_ids = set()
    response = requests.get(
        f'{supabase_url}/rest/v1/{supabase_table}',
        headers=headers,
        params={'select': '_id'}
    )
    if response.status_code == 200:
        existing_ids = {record['_id'] for record in response.json()}
        print(f"Fetched {len(existing_ids)} existing IDs")
    else:
        print("Failed to fetch existing IDs:", response.status_code, response.text)

    # Filter out records that already exist
    if "_id" not in df.columns:
        print("Error: '_id' column not found in CSV.")
        return {'statusCode': 400, 'body': "Error: '_id' column not found in CSV."}

    df_new = df[~df["_id"].isin(existing_ids)]
    if df_new.empty:
        print("No new data to push.")
        return {'statusCode': 200, 'body': 'No new data to push.'}

    # Push data in chunks
    for chunk_start in range(0, len(df_new), 500):
        chunk = df_new.iloc[chunk_start:chunk_start+500]
        chunk_records = chunk.to_dict(orient='records')

        print(chunk)
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
