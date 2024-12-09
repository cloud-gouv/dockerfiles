terraform {
  required_providers {
    outscale = {
      source  = "outscale/outscale"
      # version = "0.10.0"
    }
    cloudinit = {
      source  = "hashicorp/cloudinit"
      # version = "2.3.2"
    }
  }
}

provider "outscale" {
  # Configuration options
  # use env variables
  #   OUTSCALE_ACCESSKEYID
  #   OUTSCALE_SECRETKEYID
  #   OUTSCALE_REGION
}

