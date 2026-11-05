# Review contract

## Mode
`audit | plan | feasibility`

## User request
State the original intent without reinterpretation.

## Acceptance criteria
List observable outcomes. Derive them from the user's goal, not only from what
the builder chose to check. When the work makes claims or promises outcomes,
include one criterion that its central claims survive their strongest expert
objection; "the claims match the evidence" alone is not sufficient.

## Central claims or promised outcomes
Quote, verbatim, the headline claims, guarantees, or key assumptions of the work
(for code: the behavior it promises; for analysis or writing: its main
conclusions; for a plan: the assumption it rests on). Supply the evidence for
each, not a rebuttal of objections; the reviewer forms objections independently.

## Explicit exclusions
List what must remain out of scope.

## Builder summary
Describe what the builder changed or proposes.

## Diff or plan
Include the focused patch or numbered plan.

## Relevant context
Include only excerpts required to understand the change. Label every excerpt with its repository path.

## Verification evidence
Include commands, exit status, and concise output. Never claim a command ran when it did not.

## Rubric
Optional. When the user passed `rubric:<path>`, include the domain checklist verbatim. The reviewer must return one `rubric_results` entry per item (PASS/FAIL/UNVERIFIABLE with evidence); any FAIL forces `revise`. Omit this section when no rubric was provided.

## Known constraints and uncertainties
List platform, compatibility, dependency, migration, and unresolved assumptions.
