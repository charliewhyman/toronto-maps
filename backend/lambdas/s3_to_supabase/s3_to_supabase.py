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

    # Identify new records and prepare them for insertion
    new_data = []
    for chunk_start in range(0, len(df), 500):  # Chunk the data into 500 rows
        chunk = df.iloc[chunk_start:chunk_start+500]
        chunk_records = chunk.to_dict(orient='records')  # Convert the chunk to a list of dictionaries
        
        # Process each record in the chunk
        for record in chunk_records:
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

        # Push the chunk of new records to Supabase if there are any
        if new_data:
            response = requests.post(
                f'{supabase_url}/rest/v1/{supabase_table}',
                headers=headers,
                json=new_data
            )
            if response.status_code == 201:
                print(f"Chunk with {len(new_data)} records pushed successfully!")
            else:
                print(f"Failed to push chunk: {response.status_code} - {response.text}")
            new_data.clear()  # Clear new data after each chunk push
        else:
            print("No new data to push in this chunk.")
    
    return {'statusCode': 200, 'body': 'Success'}
