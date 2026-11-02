variable "prefix" {
  description = "Name prefix for all resources"
  type        = string
  default     = "mlproject"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "centralindia"
}

variable "vm_size" {
  description = "AKS node size (change if your subscription lacks quota)"
  type        = string
  default     = "Standard_B2s"
}

variable "min_nodes" {
  type    = number
  default = 1
}

variable "max_nodes" {
  type    = number
  default = 3
}

variable "tags" {
  type = map(string)
  default = {
    project = "mlproject"
    env     = "demo"
  }
}
