"""Headless CLI for the tenacity graph."""

from __future__ import annotations

import argparse
import os
import uuid
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from .graph import build_graph

DB_PATH = Path(os.getenv("DCODE_DB", "./dcode_tenacity.sqlite"))


def _stream(thread_id: str, payload: dict | None) -> None:
    graph = build_graph()
    with SqliteSaver.from_conn_string(str(DB_PATH)) as saver:
        cfg = {
            "configurable": {"thread_id": thread_id, "checkpointer": saver},
            "recursion_limit": 200,
        }
        for event in graph.stream(payload or {}, config=cfg, stream_mode="updates"):
            for node, update in event.items():
                print(f" >> [{node}] keys={list(update.keys())}")


def cmd_start(args: argparse.Namespace) -> None:
    thread_id = args.thread or f"goal-{uuid.uuid4().hex[:8]}"
    print(f"thread_id: {thread_id} (save this - needed for status/resume)")
    payload = {"messages": [HumanMessage(content=args.goal)]}
    _stream(thread_id, payload)
    print(f"\ndone. thread_id={thread_id}")


def cmd_resume(args: argparse.Namespace) -> None:
    print(f"Resuming thread_id={args.thread}")
    _stream(args.thread, None)


def cmd_status(args: argparse.Namespace) -> None:
    graph = build_graph()
    with SqliteSaver.from_conn_string(str(DB_PATH)) as saver:
        cfg = {"configurable": {"thread_id": args.thread, "checkpointer": saver}}
        snap = graph.get_state(cfg)
    if not snap:
        print("no state for that thread_id")
        return
    values = snap.values
    print(f"goal:   {values.get('goal')}")
    print(f"turns:  {values.get('turns')}")
    print(f"done:   {values.get('done')}")
    print(f"verdict: {values.get('verdict')}")


def cmd_clear(args: argparse.Namespace) -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"cleared {DB_PATH}")
    else:
        print("nothing to clear")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="dcode-tenacity")
    sub = parser.add_subparsers(dest="cmd", required=True)

    start = sub.add_parser("start", help="set a goal and run until done or budget hit")
    start.add_argument("goal", help="the goal - keep it specific and verifiable")
    start.add_argument("--thread", default=None, help="optional thread_id")
    start.set_defaults(func=cmd_start)

    resume = sub.add_parser("resume", help="continue a paused/interrupted goal")
    resume.add_argument("--thread", required=True)
    resume.set_defaults(func=cmd_resume)

    status = sub.add_parser("status", help="print current state of a thread")
    status.add_argument("--thread", required=True)
    status.set_defaults(func=cmd_status)

    clear = sub.add_parser("clear", help="wipe the checkpoint db")
    clear.set_defaults(func=cmd_clear)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
