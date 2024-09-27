provider "aws" {
  profile = "devken"
  region  = "ap-southeast-2"
}

# VPCの作成
resource "aws_vpc" "my_vpc" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "my_vpc"
  }
}

# インターネットゲートウェイの作成
resource "aws_internet_gateway" "my_igw" {
  vpc_id = aws_vpc.my_vpc.id

  tags = {
    Name = "my_igw"
  }
}

# サブネットの作成
resource "aws_subnet" "my_subnet" {
  vpc_id     = aws_vpc.my_vpc.id
  cidr_block = "10.0.1.0/24"

  tags = {
    Name = "my_subnet"
  }
}

# ルートテーブルの作成
resource "aws_route_table" "my_route_table" {
  vpc_id = aws_vpc.my_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.my_igw.id
  }

  tags = {
    Name = "my_route_table"
  }
}

# ルートテーブルをサブネットに関連付け
resource "aws_route_table_association" "my_route_table_association" {
  subnet_id      = aws_subnet.my_subnet.id
  route_table_id = aws_route_table.my_route_table.id
}

# セキュリティグループの作成
resource "aws_security_group" "my_security_group" {
  vpc_id = aws_vpc.my_vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "my_security_group"
  }
}

# EC2インスタンスの作成
resource "aws_instance" "my_instance" {
  ami                         = "ami-0cc51e967b1cbe471" # Amazon Linux2
  instance_type               = "t2.micro"
  subnet_id                   = aws_subnet.my_subnet.id
  vpc_security_group_ids      = [aws_security_group.my_security_group.id]
  key_name                    = "my-ec2key"
  associate_public_ip_address = true

  tags = {
    Name = "my_ec2_instance"
  }
}

resource "aws_s3_bucket" "untusbacket" {
  bucket = "untusbacket"
  acl    = "private"
}

# S3バケットのバージョニング設定
resource "aws_s3_bucket_versioning" "untusbacket_versioning" {
  bucket = aws_s3_bucket.untusbackett.id

  versioning_configuration {
    status = "Enabled"
  }
}
