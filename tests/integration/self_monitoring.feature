Feature: Self-monitoring integration with OTel Collector

  Scenario: eBPF profiler self-monitoring data is scraped and aggregated
    Given an otel-ebpf-profiler charm is deployed
    When an opentelemetry-collector charm is deployed 
    * integrated with the otel-ebpf-profiler over cos-agent
    Then logs are being scraped by the collector
    * metrics are being scraped by the collector
    * the collector aggregates the profiler's log alert rules