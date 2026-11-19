# Group Assignment Report

- **Team** (Blackboard group name):
- **Section**: [BBADBA 5A | BBADBA 5B | PPLEDBA 5A]
- **App URL** (on Render):
- **Final commit** (tag `final`):

*At most about 3,000 words, tables excluded. Members and who did what go in CONTRIBUTIONS.md.*

## Business case

*Who uses it, which decision or task it supports, what happens today without it (the baseline), the success metric, and a rough value in euros with the assumptions behind it.*

## Architecture

`list photo → Gemini vision → grocery lines → Gemini catalog agent → verified product IDs and shelf sides → walking route`

The vision call reads the image into ordered grocery lines and flags unclear
text. The agent receives those lines, calls the local catalog tool and returns
a match decision for each line. The application verifies each product ID
against the store catalog. The route planner uses the verified shelf stops and
the store's walkable paths to compute the route from Entrance to Checkout.

Both AI components currently use Gemini 3.1 Flash-Lite with separate prompts
and inputs. The agent uses Gemini function calling for the catalog lookup and
structured match decisions. The route planner is deterministic.

*Team to document model choices and any code reused from Assignments 1–3.*

## Data

The app bundles a synthetic supermarket catalog, floor plan, and walking
graph in `store.json`. They were prepared for the demonstration and are
independent of the evaluation photos. The application logs a generic image
summary, numerical photo brightness, redacted vision output, and verified
catalog results. Request records exclude raw photos, upload paths, and
unrestricted transcriptions.

*Team to document the evaluation images, sources and permissions, dataset
sizes, and verify that the images contain no personal details.*

## Evaluation

### Components

*Each component on its own: the metric, the result, the test data and its size.*

### End to end

*How you wrote `eval/cases.csv` (counts by kind, two examples). Results against the baseline. Where the output is free text: the judge's rubric and your agreement with it on your own labels.*

### Cost and latency

*Per request: tokens, euros and seconds, for each component and in total. What it would cost per month at the volume in your business case.*

## Operations

The Monitoring tab shows the share of requests sent to review and the
share of rated requests that received a thumbs down. It compares grayscale
image brightness in recent requests with a reference set using population
stability index (PSI). A template alert rule combines a minimum PSI and a
sample-size adjustment. The deployment blueprint provisions Postgres for
request and feedback logs.

*Team to choose and justify the final rule and document the normal and
shifted runs, their alert outcomes, and the rate of false alarms.*

## Failures

*Failed end-to-end cases grouped by cause (which component, or the hand-off between them), with counts, and what you would fix first.*

## Decision

*Which cases go to a person: the rule, and how many cases a day that would be. Go / no-go / go with conditions: the conditions, and the evidence behind them.*

## Bonus: reinforcement learning

*Delete this section if you did not do it. The loop (feedback → reward → update → behaviour), the reward and what it could reward by accident, the exploration strategy and its cost, the evidence from real logs (and which part was simulated), the risks.*

## How to run it

Follow `SETUP.md` and provide `GEMINI_API_KEY`. The demo store file is
bundled locally. See `eval/README.md` for the offline preflight, scoring
command, and drift replay.

## AI use

Codex was used to develop and test the Aisle Run demo and Gradio code,
including the two AI components, the route planner, evaluation tooling,
and this technical description.

*Team to verify and complete this disclosure before submission.*
