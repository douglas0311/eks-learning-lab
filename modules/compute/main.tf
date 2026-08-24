# ---------------------------------
# Amazon Linux 2023 AMI
# ---------------------------------

data "aws_ssm_parameter" "amazon_linux_2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}


# ---------------------------------
# Launch Template
# ---------------------------------

resource "aws_launch_template" "application" {
  name_prefix = "${var.project_name}-"

  image_id = data.aws_ssm_parameter.amazon_linux_2023.value

  instance_type = var.instance_type

  vpc_security_group_ids = [
    var.application_security_group_id
  ]

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash

    # ---------------------------------
    # Application
    # ---------------------------------

    cat > /opt/app.py <<'PYTHON'
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import socket

    class Handler(BaseHTTPRequestHandler):

        def do_GET(self):
            if self.path == "/":

                body = f"""
                <html>
                    <body>
                        <h1>Terraform SRE Lab</h1>
                        <p>Instance: {socket.gethostname()}</p>
                    </body>
                </html>
                """

                body_bytes = body.encode()

                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header(
                    "Content-Length",
                    str(len(body_bytes))
                )
                self.end_headers()

                self.wfile.write(body_bytes)

            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            print(format % args)


    server = HTTPServer(
        ("0.0.0.0", 8080),
        Handler
    )

    server.serve_forever()

    PYTHON


    # ---------------------------------
    # Systemd Service
    # ---------------------------------

    cat > /etc/systemd/system/sre-lab-app.service <<'SERVICE'

    [Unit]
    Description=Terraform SRE Lab Application
    After=network.target

    [Service]
    ExecStart=/usr/bin/python3 /opt/app.py
    Restart=always
    User=root

    [Install]
    WantedBy=multi-user.target

    SERVICE


    # ---------------------------------
    # Start Application
    # ---------------------------------

    systemctl daemon-reload

    systemctl enable sre-lab-app

    systemctl start sre-lab-app

  EOF
  )

  tag_specifications {
    resource_type = "instance"

    tags = {
      Name        = "${var.project_name}-application"
      Environment = var.environment
      Tier        = "application"
    }
  }

  tags = {
    Name        = "${var.project_name}-launch-template"
    Environment = var.environment
  }
}


# ---------------------------------
# Auto Scaling Group
# ---------------------------------

resource "aws_autoscaling_group" "application" {

  name = "${var.project_name}-asg"

  min_size = var.min_size

  desired_capacity = var.desired_capacity

  max_size = var.max_size

  vpc_zone_identifier = var.private_subnet_ids

  target_group_arns = [
    var.target_group_arn
  ]

  health_check_type = "ELB"

  health_check_grace_period = 60

  launch_template {
    id = aws_launch_template.application.id

    version = "$Latest"
  }

  # ---------------------------------
  # Instance Tags
  # ---------------------------------

  tag {
    key = "Name"

    value = "${var.project_name}-application"

    propagate_at_launch = true
  }

  tag {
    key = "Environment"

    value = var.environment

    propagate_at_launch = true
  }

  tag {
    key = "Tier"

    value = "application"

    propagate_at_launch = true
  }
}