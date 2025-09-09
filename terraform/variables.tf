variable "app_name" {
  description = "Name to give the deployed application"
  type        = string
  default     = "otel-ebpf-profiler"
}

variable "channel" {
  description = "Channel that the charm is deployed from"
  type        = string
}

variable "config" {
  description = "Map of the charm configuration options"
  type        = map(string)
  default     = {}
}

variable "constraints" {
  description = "String listing constraints for this application"
  type        = string
  # CAUTION: without virt-type=virtual-machine, the charm won't function!
  default = "arch=amd64 virt-type=virtual-machine"
}

variable "model" {
  description = "Reference to an existing model resource or data source for the model to deploy to"
  type        = string
}

variable "revision" {
  description = "Revision number of the charm"
  type        = number
  default     = null
}

variable "storage_directives" {
  description = "Map of storage used by the application, which defaults to 1 GB, allocated by Juju"
  type        = map(string)
  default     = {}
}

variable "units" {
  description = "Unit count/scale"
  type        = number
  default     = 1
}


variable "trust" {
  description = "Whether this application is trusted to control the cluster"
  type        = bool
  default     = false
}
