# AI prompt history

Tool: Claude Code (CLI). The full raw transcript of the working session is in
`claude-code-session-raw.jsonl` (one JSON event per line: my prompts, the model's
replies, tool calls and results).

Below are my prompts exactly as I typed them (spelling left as written), in order.

---

## Prompt 1

this is the an assigment , firstly we need to take care of all the requirement and then implementation plan and then implement complete things , make sure to take care of all the things mentiono in the readme , this is github :https://github.com/amreshkyadav998/RAYY_ASSIGNMENT.git , you can clone and then work , it's upto you and do in react.

(Pasted with it: the email from the hiring team.)

> Hi Amresh,
>
> Thanks for your answers. The next step is a take-home exercise of about two and a half hours; if you reach three hours, stop and write in NOTES.md what is left. Use any tools you like, including AI. We care about what you ship and how you checked it.
>
> 1. Open this template and click Use this template on GitHub to make your own copy: https://github.com/rayy-hiring/rayy-takehome-a
> 2. Work in your own GitHub account. The README has everything you need.
> 3. The exercise has a backend part and a short client task of about 20 minutes. Do the client task in Flutter or React, whichever you prefer.
> 4. Within 48 hours of receiving this email, reply to this email with the link to your repo. If it's private, give read access to ashishrayy. Once we have it, the review is usually done within one working day.
>
> Every item is needed. The client task (about 20 minutes) and prompts/ are required for a pass, so if time is short do a smaller version of each rather than skipping one.
>
> Your AI prompt history is required. Put it in a prompts/ folder, as the README describes: a raw export or screenshots is fine; no need to tidy it. If your tool does not keep a history, copy or screenshot the conversation as you go. A submission without prompts/ cannot pass. Please include NOTES.md too; short bullets are fine.
>
> Best,

## Prompt 2

i wanted to run it locally first to test it properly , tell me how to run it locally and what things i need to take care while testing , give some proper example to test it using postman ,and tell me how we can run the frontend side as well , run it locally one here , and in last give me the command to run it locally

## Prompt 3

at which port frontend is running , 3000 is not working at all

## Prompt 4

make sure to keep the same prompt i wrote in the prompt readme file properly

---

## What the AI did in response (short summary)

1. Cloned the repo, read the README, the app, the seed data and fixtures, and the web starter, and ran both baseline test suites.
2. Wrote the design: integer-only pricing, an atomic conditional-update discount guard, HMAC verification over the raw body, an atomic "pay only if pending and amount matches" update, and a per-order discount snapshot for settlement.
3. Implemented the backend, then tests (pricing, apply-discount, webhook, settlement), then mutation-checked the guards.
4. Implemented the React client (`formatPaise`, `OrderSummary`) and its tests; fixed one wrong expected value in a test (see NOTES.md).
5. Wrote NOTES.md.
6. For prompt 2: started a local replica-set Mongo, ran the full Python suite against it (61 passed), ran the API and the Vite frontend, added `scripts/send_webhook.py` and a Postman collection (checked with Newman, 21 requests, 16 assertions, 0 failed), and added demo options to the client's `main.tsx`.
7. For prompt 3: the Vite dev server runs on port 5173, not 3000.
