# AWS implementation notes

AWS mapping for this skill's principles. As of 2026-10; services change, verify before use.

Load this when a role's model is tuned, hosted or called on AWS. The principles live in SKILL.md and the other reference files; this file only says which AWS feature or setting carries each one and where the labs tripped. Items marked "(unverified)" were seen in practice labs or inferred, but not confirmed against current AWS documentation.

## Mapping

| Principle (skill section) | AWS feature or setting | Gotcha |
|---|---|---|
| LoRA by default; a quantised frozen base fits one GPU (adaptation-ladder.md §4; §8 item 5) | A SageMaker notebook instance with one 16 GB GPU, base loaded in 8-bit with LoRA adapters | Training by hand in a notebook is not a repeatable pipeline (§6, "Specialisation versus the upstream release cycle"). Run the same script as a SageMaker training job so data location, hyperparameters and container image are recorded per run (not exercised in the labs; unverified) |
| Checkpoint by validation metric (adaptation-ladder.md §6, memorisation; §8 item 4) | The training script's evaluation interval and best-checkpoint setting | The lab evaluated every 100 steps but saved the final adapter, which was the most overfit. Keep the best validation checkpoint and copy it to S3 before the instance stops |
| Training and serving match (adaptation-ladder.md §8 item 11) | The serving container image and the library versions inside it | The adapter loaded only when the serving image's model, adapter and quantisation library versions matched training. The prompt markers were special tokens, so the serving stop marker depended on the same tokenizer files. Ship tokenizer and template with the adapter |
| Pin and mirror the base (SKILL.md step 9; adaptation-ladder.md §8 item 5) | The model artifact in S3: adapter, serving config and handler, plus a mirrored copy of the base at a fixed revision | In the lab the endpoint downloaded the base from a public hub at every start. Startup then depended on the hub, cold start included the download, and an unpinned reference could change under the adapter |
| One base, adapters loaded per request (adaptation-ladder.md §4) | SageMaker Large Model Inference (LMI) containers with built-in LoRA and multi-adapter serving (unverified) | The lab used an old DJL DeepSpeed image with a custom Python handler that loaded base and adapter on the first call. Check the current LMI documentation before writing a handler |
| Hosting economics (role-model-mapping.md §6; serving cost belongs to agent-ops-reviewer) | A dedicated real-time SageMaker GPU endpoint versus a managed API on Bedrock | An always-on GPU endpoint for low or bursty traffic usually costs more than per-token pricing. Ask agent-ops-reviewer to size it |
| Managed open-weight model (role-model-mapping.md §6) | Bedrock Custom Model Import (unverified details) | Imports supported open-weight architectures in standard weight formats; merge the LoRA adapter into the base first if adapters are not accepted. Billing per active model copy with scale-to-zero and a cold start (unverified) |
| Hosted tuning dies with its base (adaptation-ladder.md §3 and §6, vendor lock-in) | Bedrock-native customisation of first-party models (unverified menu) | Keep the data, scripts and eval so the tuning can be repeated elsewhere, and name an open-weight fallback |
| A model change is a migration through the bake-off (bakeoff-protocol.md §9 and §10) | Callers resolve the endpoint name or model ID from configuration, such as a function's environment variable | Editing one variable to point callers at a new endpoint is a hard cutover with no gate, shadow or canary. Run the bake-off first, then hand the traffic shift to agent-ops-reviewer |

## A LoRA run on one GPU

- An 8-bit frozen base plus LoRA fit a 3B model on a single 16 GB GPU; about 3% of the weights were trainable at rank 256. The memory budget worked; the 58 training rows were still too few.
- Loss was computed on the response tokens only, with the prompt tokens masked. Keep that when you move the script into a training job.
- Read the curves before you deploy anything. Both lab runs memorised: training loss went to near zero while validation loss climbed from the first evaluation. Follow adaptation-ladder.md §6 (more data, fewer epochs, lower rank, more dropout) and judge the result on the held-out task eval against the base, not on the loss curves.

## Serving an adapter on a SageMaker endpoint

- The artifact held only the adapter, a serving config and a handler. That keeps it small (about 300 MB in the lab), but the endpoint still has to load the base at startup. Point the serving config at your mirrored, pinned copy.
- Pin the serving image's library versions to the training versions, and keep the template, special tokens, tokenizer files and stop marker with the adapter (adaptation-ladder.md §8 item 11).
- Creating the endpoint took about 7.5 to 10 minutes in the lab. Wait with the SDK or CLI waiter for the in-service state, not a fixed sleep; much longer than that usually means the deployment failed, so read the endpoint logs.

## Moving a tuned model behind Bedrock (unverified)

- Custom Model Import suits a tuned open-weight model when you want Bedrock's API, access control and logging instead of running an endpoint. Confirm the supported architectures, weight format, adapter handling, regions and pricing on the current documentation before you plan on it.
- Bedrock-native customisation of first-party models is hosted tuning: the tuned model lives in the provider's environment and goes when its base is retired. Treat it like any hosted tuning in this skill (SKILL.md step 8, named fallback).
