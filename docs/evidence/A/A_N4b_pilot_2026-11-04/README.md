# A-N4b synthetic pilot audit

This is synthetic pilot evidence, not a formal experiment result.
Status: blocked_diagnostics_verified
Sources: 30; eligible states: 8; diagnostics: 3.

Actual source and state counts by family:

| Family | Sources | Sampled states | Eligible states |
|---|---:|---:|---:|
| deadline_before_window | 2 | 4 | 4 |
| decision | 24 | 7 | 4 |
| low_energy | 2 | 0 | 0 |
| no_window | 2 | 0 | 0 |

Label quality (idle_in_optimal_set and tied_optimal_set are separate):
{"feasible_top_two_margin":{"defined_count":4,"max":0.0,"mean":0.0,"median":0.0,"min":0.0,"p95_nearest_rank":0.0,"undefined_count":4,"zero_count":4},"idle_in_optimal_set":{"count":7,"fraction":0.875},"optimal_set_size_counts":{"1":4,"2":1,"3":2,"5":1},"task_action_all_zero":{"count":4,"fraction":0.5},"tied_optimal_set":{"count":4,"fraction":0.5},"unique_non_idle_best":{"count":0,"fraction":0.0}}

Coverage:
{"all_task_actions_infeasible":{"count":4,"fraction":0.5},"any_task_without_feasible_mode":{"count":4,"fraction":0.5},"deadline_before_or_at_first_window":{"count":4,"fraction":0.5},"low_energy_at_or_below_reserve":{"count":0,"fraction":0.0,"reserve_Wh":0.5},"no_forecast_window":{"count":0,"fraction":0.0}}

All attempts, including UNSUPPORTED, TIME/NODE limited and ERROR counts (absent statuses count as zero):
{"OPTIMAL":8,"TIME_LIMIT_FEASIBLE":3}
Exclusions: {"TIME_LIMIT_FEASIBLE":3}
Stop reason: REPEATED_SOLVER_LIMIT

Public plan checks: first failed ConstraintCheck per task/mode; idle has no rejection reason.
{"fast":{"checked_count":16,"first_failed_check_counts":{"NO_VISIBLE_WINDOW":4},"rejected_count":4},"robust":{"checked_count":16,"first_failed_check_counts":{"NO_VISIBLE_WINDOW":4},"rejected_count":4}}
Teacher diagnostics by mode: {"fast":{"TIME_LIMIT_FEASIBLE":1,"searched_count":12},"idle":{"TIME_LIMIT_FEASIBLE":3,"searched_count":11},"robust":{"TIME_LIMIT_FEASIBLE":4,"searched_count":12}}
Feasibility crosscheck: {"verified":11}

Model training remains disabled pending B acceptance.
