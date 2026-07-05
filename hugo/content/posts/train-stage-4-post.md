---
title: 'training tracker: stage 4 — the coach that flinched at the word "leg"'
date: 2026-07-06T16:00:00
draft: false
tags: ["aws", "lambda", "dynamodb", "claude-api", "ai", "security", "python", "train", "10k"]
summary: "fourth post in the training tracker series: turning the AI coach spec into a running endpoint, the bugs that only showed up once something real was talking to it, a security gap closed before a second user existed, and a chat UI to finally use the thing."
---

### Building the Thing the Spec Described

*This is the fourth post in a series documenting the build of a personal running habit tracker at train.tacedata.ca. The [project page](/projects/running-tracker-proj/) covers the full scope. [Stage 1](/posts/train-stage-1-post/) put the infrastructure in place, [Stage 2](/posts/train-stage-2-post/) was a security audit, and [Stage 3](/posts/train-stage-3-post/) rebuilt the data model around a real identity and wrote out, in full, what an AI coach should do before any of it existed. This post is where the spec became code — and where two more real problems turned up, one caught by a test harness before anyone saw it, and one caught only by actually using the thing.*

---

### Building in the order the spec demanded

The Stage 3 spec laid out a build order for the coach — conversation storage, then a settings toggle, then the safety rail standing entirely on its own, and only then the part that actually talks to a model — specifically so each piece could be proven before the next one depended on it. That order held. Thread creation, renaming, and deletion shipped and were validated first, with nothing yet capable of generating a reply. The safety rail shipped next, wired up to return its canned redirect on a triggered message and a deliberate "not built yet" error on everything else — proof, before a single token of coaching advice existed, that a risky message could never reach a model it hadn't been screened against. Only after that did the actual coach turn get built: the athlete's real plan and progress computed into concrete facts in code — current streak, this week's numbers, the next long run — and handed to the model as answers, not raw material to guess from. The model's job stays limited to talking about the facts, never producing them.

Proving each layer before adding the next one meant that by the time the model was in the loop at all, everything around it — storage, isolation, the rail — had already been shown to work without it.

---

### Bugs that only show up when something real is calling the code

Three problems surfaced during this build that no amount of reading the spec would have caught, because they were all specific to how the actual model and the actual database behave under real calls, not how the design document assumed they would.

The classifier — a fast, cheap model whose only job is to read one message and answer "medical" or "ok" — was told, explicitly, to reply with nothing but raw JSON. It mostly did. Sometimes it wrapped that same JSON in a markdown code fence anyway, the way it would if it were writing documentation instead of an API response. That broke the parser, which is a survivable failure only because the rail is built to fail closed — an unparseable answer gets treated as "better safe," not passed through. Still, "better safe" that fires on every fenced response isn't really safe, it's just broken in a direction that happens to be less embarrassing. Fixed by tightening the instruction and stripping a fence defensively if one shows up anyway.

Deleting a conversation turned out to have an ordering bug: the thread record was deleted before its messages were, and a missing permission on the batch-delete step meant that on one real run, the thread vanished while its messages didn't — orphaned rows pointing at a conversation that no longer existed anywhere. The fix was mechanical once found (delete messages first, the thread last, so a failure partway through stays retryable instead of leaving debris), but it's the kind of bug that a design document can describe correctly and still not prevent, because "delete the conversation" reads as one step until you watch it actually run as two.

The third was smaller and stranger: the coach model occasionally returned its "thinking" as a separate block ahead of its actual reply, and code that assumed the first block was always the answer broke on it. Newer Claude models reason before answering by default, and that reasoning arrives as its own block in the response — a reasonable design on the model's side that nonetheless nobody without the model's own release notes would think to expect. Fixed with a small helper that looks for the first block that's actually text, wherever it lands.

None of these are dramatic. They're the specific, unglamorous cost of the phrase "in production" — a category of bug that a spec, however careful, cannot pre-empt, because it doesn't yet know how the real thing misbehaves.

---

### The gap a test caught before a person did

The whole point of writing an eval harness alongside the coach — a set of test conversations, scored automatically, that has to pass before anything ships — was to catch exactly the kind of mistake that reads as fine in isolation and only shows its teeth in combination. It caught one.

The medical backstop is the coach's last line of defense: if an athlete's message describes real pain or injury, the coach is supposed to say, essentially, one thing — that's a question for your physiotherapist — and stop. The first version did say that. It just didn't *stop*: right after the referral, it added "I'd hold off on the 60-minute session until you've got their input." That's a training recommendation, tied directly to the symptom, from a system explicitly built never to give one. It's also exactly the kind of sentence that sounds *responsible* out of context — which is precisely why it's dangerous to let slip through unnoticed. The instruction had told the model not to advise; it hadn't told the model that the referral and the advice were the same forbidden category, not two separate moves where only the second one counts. Tightened the wording to say the backstop reply *is* the acknowledgment-plus-referral and nothing else, re-ran the harness, and it held — including, later, on a real conversation with a genuine symptom mentioned earlier in the same thread, where the coach correctly left the go/no-go call to the physiotherapist instead of quietly making it anyway.

---

### Shipping again was still not the finish line

Stage 2 of this project was, in its own words, a security audit nobody had asked for — the point being that finishing a feature and finishing the job are not the same milestone. That lesson repeated itself twice more this stage, in two different shapes.

The first was a real conversation with the coach, after it had already shipped and passed every eval. Two ordinary messages — a bare "leg," and "my soleus is feeling better today" — both got wrongly deferred to a physiotherapist. Nothing was wrong with either message. Both the rail and the coach's own backstop had been built to key on *topic*: does this message mention a body part. That's a nearly useless boundary in a running app, where legs, knees, and calves come up constantly and harmlessly. The correct boundary is *intent*: is an actual symptom, pain, or injury being reported, versus a body part just being mentioned in passing. Rewriting both prompts around that distinction, with worked examples showing the difference side by side, fixed it — and both of those exact real messages, plus the genuine medical cases that still correctly need to defer, became permanent entries in the eval harness, so this specific mistake can't quietly come back later without a test failing first.

The second was a gap left over from Stage 3's own migration, and it had been written down honestly at the time rather than hidden: the athlete's physio-adjustment overrides — a small table of "actually, do this instead" notes attached to specific days — had been left keyed only by date, global to the whole table, not yet partitioned per person like everything else had just been rebuilt to be. With one user, that's invisible. With a second user, it would mean one athlete's physio note showing up as another athlete's plan. Closing it meant standing up a properly partitioned version of that table, migrating the existing rows across, and proving isolation the same deliberate way Stage 3 had — seeding a second identity with a row on a date that carried a real override, and confirming, through the actual running code, that it saw none of it. It's a small fix. It's also exactly the kind of gap that's cheap to close before anyone is depending on it and expensive to discover after.

---

### Finally, something to click

Everything up to this point had only ever been exercised by invoking a Lambda function directly — a real endpoint, but not a real conversation, since nothing in the browser could reach it. This stage added an actual chat view to the app: a thread list, a message history, a toggle for whether the coach sticks strictly to the plan or can also talk general running advice, and a small amount of markdown rendering so the coach's own **bold text** and lists show up as such instead of literal asterisks and dashes.

It got built and checked twice before anyone saw it for real. First against a local, disconnected mock — the actual interface code, pointed at fake data instead of the live API — to catch layout and rendering mistakes without touching anything real. Then, after deploying it to the live site, a genuinely new bug turned up that had nothing to do with the coach at all: the deployed files had no explicit caching instruction attached, so browsers were free to guess how long to keep the old version around — and guessed generously. The new Coach button was live, correct, and completely inert in an ordinary browser tab, while working perfectly in a private one, because a private tab starts with no cache to be wrong about. The fix was to tell the browser explicitly to always double-check rather than assume, which meant one final hard refresh to clear out the guess that was already sitting there, and no such guesswork on any deploy after this one.

---

### What comes next

The coach now has a real endpoint, a tuned pair of prompts locked in by a growing set of regression cases, an isolated data layer, and an interface to actually talk to it. What's still deliberately unbuilt is the rest of "multi-user" that Stage 3 set aside to make room for all of this: a real onboarding flow for a second athlete, an invite mechanism instead of a hardcoded allow-list, and a daily email that fans out to more than one inbox. That work waits for an actual second person to build it for — everything shipped since Stage 3 was built to be ready for them without needing to be revisited when they arrive.

---

*Next in the series: Stage 5 — bringing on a second athlete, for real.*

---

[running tracker — project page](/projects/running-tracker-proj/)
