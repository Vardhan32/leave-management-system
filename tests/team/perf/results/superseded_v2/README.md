# Superseded results (script version 2)

These runs used a workload where every iteration of one virtual user created a request on the
same date and then cancelled it. In `vus5_run1` a single cancel call failed during a latency
spike (one of 428 cancel calls), the request stayed pending, and every later create of that
user hit the overlap rule (HTTP 422), which produced 123 "unexpected" create failures
(22.3 %). That is a flaw in the script, not a measurement of the application, so the workload
was changed (one new weekday date per iteration) and all four runs were repeated. The files
are kept as evidence of the first analysis; `docs/team/performance.md` explains the change.
