terraform {
  required_providers {
    supabase = {
      source  = "supabase/supabase"
      version = "~> 1.0"
    }
  }
}

provider "aws" {
  region = "us-east-2"
}

provider "supabase" {
  access_token = var.supabase_access_token
}