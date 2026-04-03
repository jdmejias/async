# Definimos las variables para no hardcodear todo si es posible
variable "vpc_id" {
  default = "vpc-0a241bbbc4405b4dd"
}

variable "subnet_id" {
  default = "subnet-02a6c2f22030aa8cb"
}

variable "ami_id" {
  default = "ami-02dfbd4ff395f2a1b" # Amazon Linux 2023
}

variable "key_name" {
  default = "nestorkp"
}

variable "instance_type" {
  default = "t3.micro"
}

variable "repo_url" {
  default = "https://github.com/jdmejias/async.git"
}
