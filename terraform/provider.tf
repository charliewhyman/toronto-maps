provider "aws" {
  region = "us-east-2"
}

provider "supabase" {
  access_token = var.supabase_access_token
}