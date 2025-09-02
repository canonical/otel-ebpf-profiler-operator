module "pyroscope" {
  source      = "../../terraform"
  model       = var.model
  channel     = "2/edge"
}
