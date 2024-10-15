variable "toronto_api_url" {
  type        = string
  description = "The URL of the Toronto Open Data API"
}

variable "supabase_url" {
  type        = string
  description = "Supabase API URL"
}

variable "supabase_key" {
  type        = string
  description = "Supabase API Key"
  sensitive   = true
}
