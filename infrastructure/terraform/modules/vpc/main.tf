data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  name = "${var.project}-${var.environment}"
  azs  = slice(data.aws_availability_zones.available.names, 0, var.az_count)

  common_tags = merge(var.tags, {
    Module = "vpc"
  })
}

# ── VPC ─────────────────────────────────────────────────────────
resource "aws_vpc" "main" {
  cidr_block           = var.cidr_block
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, {
    Name = local.name
  })
}

# ── Internet gateway ────────────────────────────────────────────
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${local.name}-igw"
  })
}

# ── Public subnets (ALB) ────────────────────────────────────────
resource "aws_subnet" "public" {
  count = var.az_count

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.cidr_block, 8, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${local.name}-public-${local.azs[count.index]}"
    Tier = "public"
  })
}

# ── Private subnets (ECS, RDS, ElastiCache) ─────────────────────
resource "aws_subnet" "private" {
  count = var.az_count

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.cidr_block, 8, count.index + 100)
  availability_zone = local.azs[count.index]

  tags = merge(local.common_tags, {
    Name = "${local.name}-private-${local.azs[count.index]}"
    Tier = "private"
  })
}

# ── NAT gateway (one per AZ for HA in prod, single for staging) ─
resource "aws_eip" "nat" {
  count  = var.az_count
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${local.name}-nat-${local.azs[count.index]}"
  })
}

resource "aws_nat_gateway" "main" {
  count = var.az_count

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(local.common_tags, {
    Name = "${local.name}-nat-${local.azs[count.index]}"
  })

  depends_on = [aws_internet_gateway.main]
}

# ── Route tables ────────────────────────────────────────────────
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "${local.name}-public-rt"
  })
}

resource "aws_route_table_association" "public" {
  count = var.az_count

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  count = var.az_count

  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = merge(local.common_tags, {
    Name = "${local.name}-private-rt-${local.azs[count.index]}"
  })
}

resource "aws_route_table_association" "private" {
  count = var.az_count

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}
