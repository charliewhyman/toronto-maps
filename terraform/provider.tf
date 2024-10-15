provider "aws" {
  region = "us-east-2"
}

provider "supabase" {
  api_url = "https://uzhcmbppmoghkkpdepub.supabase.co"
  api_key = var.supabase_api_key
}