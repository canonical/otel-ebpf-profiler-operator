Feature: profiling

  Scenario: eBPF profiler is able to send system-wide profiles to a profiling backend
    Given an ebpf profiler charm is deployed on a juju virtual machine
    * an otel collector charm is deployed on the same machine
    When the profiler is integrated with the collector over profiling
    Then system-wide profiles are successfully pushed to the collector