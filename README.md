# Toronto Traffic Data Pipeline

This repo contains a serverless data pipeline that fetches data (currently traffic volume data) from the City of Toronto’s Open Data Portal, and stores it in Supabase for easy querying and future app development. Built with **AWS Lambda** functions and managed with **Terraform**.
## Overview

The pipeline performs the following steps:
1. **Data Retrieval**: AWS Lambda periodically fetches CSV traffic data from the City of Toronto’s CKAN API, using EventBridge.
2. **Temporary Storage**: The data is stored temporarily in an S3 bucket for processing.
3. **Event-Driven Processing**: Lambda functions are triggered by new files in S3 to update the data efficiently.
4. **Data Storage in Supabase**: Processed data is transferred to Supabase for storage and querying.

## Tech Stack

- **AWS Lambda**: Serverless functions for data retrieval and processing.
- **S3**: Temporary storage for raw data.
- **Supabase**: Final storage for accessible and queryable data.
- **Terraform**: Infrastructure-as-Code to manage AWS resources and deployment.

## Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/toronto-traffic-data-pipeline.git
   cd toronto-traffic-data-pipeline
