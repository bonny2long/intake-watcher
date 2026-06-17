# Operations Guide

## Day To Day

1. Put downloads or copied media into `_INGEST/incoming`.
2. Leave Intake Watcher running.
3. Wait for items to appear in `Ready for Archive Assistant`.
4. Open Archive Assistant and scan `_INGEST/ready`.
5. Review, approve, and move in Archive Assistant.

## What Means Good

```text
Ready for Archive Assistant = Intake Watcher is done.
```

The item is stable and ready for Archive Assistant review.

## What Means Blocked

```text
Blocked / Needs Check = Bonny should inspect.
```

Common causes:

- Destination collision in `ready`.
- Temporary files still present.
- Empty or unsupported folder.
- Promotion failed.

## Incoming / Waiting

```text
Incoming / Waiting = normal while copying/downloading.
```

Do not interrupt active copies unless you know the transfer is wrong.

## Stability Window

The stability window is the amount of time an item must stop changing before promotion.

`STABILITY_SECONDS=1200` means the item must remain unchanged for 20 minutes.

## Clear Recent

Clear recent hides recent dashboard events.

It does not delete raw logs and does not delete media.

## After Ready

Archive Assistant takes over after an item reaches `_INGEST/ready`.

Archive Assistant identifies media, asks for review, approves, moves, and writes manifests/logs.

## What Not To Touch

- Do not delete media from Intake Watcher as a cleanup step.
- Do not point Archive Assistant at `_INGEST/incoming`.
- Do not expose the dashboard publicly.
- Do not use Intake Watcher as a media organizer.

