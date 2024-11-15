import os
import requests
import boto3
from botocore.exceptions import ClientError

# Initialize S3 client and set parameters
s3_client = boto3.client("s3")
ckan_id = "traffic-volumes-at-intersections-for-all-modes"
base_url = os.getenv("TORONTO_API_URL")
s3_bucket = os.getenv("S3_BUCKET")
s3_folder = f"{ckan_id}/"

# Check if csv exists in S3 based on resource ID
def file_exists_in_s3(resource_id):
    try:
        s3_key = f"{s3_folder}{resource_id}.csv"
        response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=s3_key)
        return "Contents" in response
    except ClientError as e:
        print(f"Error checking file existence in S3: {e}")
        return False

def handler(event, context):
    # Set URL and parameters for the API request
    package_url = f"{base_url}/api/3/action/package_show"
    params = {"id": ckan_id}
    
    try:
        # Fetch the metadata for the dataset
        package = requests.get(package_url, params=params)
        package.raise_for_status()  # Raise an error for bad status codes
        package = package.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching package metadata: {e}")
        return {
            "statusCode": 500,
            "body": "Failed to retrieve dataset metadata"
        }
    
    for resource in package["result"]["resources"]:
        # Only process CSV files that start with "raw-data" and are not already in S3
        if resource["format"].lower() == "csv" and resource["name"].lower().startswith("raw-data") and not file_exists_in_s3(resource["id"]):
            file_url = resource["url"]
            s3_key = f"{s3_folder}{resource['id']}.csv"

            try:
                # Stream the CSV file directly to S3
                with requests.get(file_url, stream=True) as response:
                    response.raise_for_status()
                    s3_client.upload_fileobj(response.raw, s3_bucket, s3_key)
        
                print(f"Uploaded {resource['name']} (ID: {resource['id']}) to s3://{s3_bucket}/{s3_key}")

            except requests.exceptions.RequestException as e:
                print(f"Error fetching CSV from {file_url}: {e}")
                continue
            except ClientError as e:
                print(f"Error uploading CSV file to S3: {e}")
                continue
            except Exception as e:
                print(f"Unexpected error during conversion or upload: {e}")
                continue


    return {
        "statusCode": 200,
        "body": f"New files processed and uploaded to {s3_bucket}."
    }
