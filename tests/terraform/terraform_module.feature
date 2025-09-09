Feature: Terraform deployment

  Scenario: The charm can be deployed with terraform
    Given a machine controller
    When you run terraform apply using the provided module
    Then the otel-ebpf-profiler charm is deployed and active