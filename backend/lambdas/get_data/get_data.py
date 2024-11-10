import os
import requests
import boto3

# Initialize S3 client and set parameters
s3_client = boto3.client("s3")
ckan_id = "traffic-volumes-at-intersections-for-all-modes"
base_url = os.getenv("TORONTO_API_URL")
s3_bucket = os.getenv("S3_BUCKET")
s3_folder = f"{ckan_id}/"

# Check if csv exists in S3 based on resource ID
def file_exists_in_s3(resource_id):
    s3_key = f"{s3_folder}{resource_id}.csv"
    response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=s3_key)
    return "Contents" in response

def handler(event, context):
    # Set URL and parameters for the API request
    package_url = f"{base_url}/api/3/action/package_show"
    params = {"id": ckan_id}
    
    # Fetch the metadata for the dataset
    package = requests.get(package_url, params=params).json()
    
    for resource in package["result"]["resources"]:
        # Check if the resource is a CSV and new based on its ID
        if resource["format"].lower() == "csv" and not file_exists_in_s3(resource["id"]):
            file_url = resource["url"]
            response = requests.get(file_url)
            
            # Define the S3 key (path) for the file using resource ID
            s3_key = f"{s3_folder}{resource['id']}.csv"
            
            # Upload directly to S3
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=s3_key,
                Body=response.content
            )
            
            print(f"Uploaded {resource['name']} (ID: {resource['id']}) to s3://{s3_bucket}/{s3_key}")

    return {
        "statusCode": 200,
        "body": f"New files processed and uploaded to {s3_bucket}."
    }
