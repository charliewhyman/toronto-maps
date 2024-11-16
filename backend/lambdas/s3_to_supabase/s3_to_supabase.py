import boto3
import requests
import os
import pandas as pd
import csv
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

    # Get the bucket and key from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    print(f"Bucket: {bucket}, Key: {key}")

    # Initialize the S3 client
    s3 = boto3.client('s3')

    # Create a streaming response from S3
    try:
        s3_object = s3.get_object(Bucket=bucket, Key=key)
        stream = s3_object['Body']

        # Process the CSV file in chunks using CSV reader
        chunk_size = 5000
        csv_reader = csv.reader(io.TextIOWrapper(stream, encoding='utf-8'))
        
        header = next(csv_reader)  # Read the header row
        rows = []
        
        for i, row in enumerate(csv_reader):
            rows.append(row)
            
            # Process in chunks
            if (i + 1) % chunk_size == 0 or (i + 1) == len(rows):
                df_chunk = pd.DataFrame(rows, columns=header)  # Convert chunk to DataFrame

                # Handle missing data (empty values)
                df_chunk = df_chunk.where(df_chunk.notna(), None) 

                # Process the chunk
                process_chunk(df_chunk, supabase_url, supabase_access_token, supabase_table, headers)
                rows = []  # Clear the rows for the next chunk
    except Exception as e:
        print(f"Error processing file from S3: {e}")
        return {'statusCode': 500, 'body': f'Error processing file: {e}'}

    return {'statusCode': 200, 'body': 'Data processed successfully'}

def process_chunk(df_chunk, supabase_url, supabase_access_token, supabase_table, headers):
    
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
    if "_id" not in df_chunk.columns:
        print("Error: '_id' column not found in CSV.")
        return {'statusCode': 400, 'body': "Error: '_id' column not found in CSV."}

    df_new = df_chunk[~df_chunk["_id"].isin(existing_ids)]
    if df_new.empty:
        print("No new data to push.")
        return {'statusCode': 200, 'body': 'No new data to push.'}

    # Push data in chunks to Supabase
    for chunk_start in range(0, len(df_new), 500):
        chunk = df_new.iloc[chunk_start:chunk_start + 500]
        chunk_records = chunk.to_dict(orient='records')

        print(f"Pushing chunk with {len(chunk_records)} records")
        response = requests.post(
            f'{supabase_url}/rest/v1/{supabase_table}',
            headers=headers,
            json=chunk_records
        )
        if response.status_code == 201:
            print(f"Chunk with {len(chunk_records)} records pushed successfully!")
        else:
            print(f"Failed to push chunk: {response.status_code} - {response.text}")
