# Review contract

## Mode
`audit | plan | feasibility`

## User request
State the original intent without reinterpretation.

## Acceptance criteria
List observable outcomes.

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
