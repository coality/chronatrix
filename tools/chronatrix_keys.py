#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import os
import secrets
from urllib.parse import urlparse

import pymysql


def connect():
    dsn = os.getenv("CHRONATRIX_DB_DSN", "")
    parsed = urlparse(dsn)
    return pymysql.connect(
        host=parsed.hostname or "localhost",
        port=parsed.port or 3306,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip("/"),
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


def secret() -> str:
    value = os.getenv("CHRONATRIX_KEY_SECRET", "")
    if not value:
        raise SystemExit("CHRONATRIX_KEY_SECRET is required")
    return value


def key_hash(raw_key: str) -> bytes:
    return hmac.new(secret().encode(), raw_key.encode(), hashlib.sha256).digest()


def create(args: argparse.Namespace) -> None:
    raw = "ctx_" + base64.urlsafe_b64encode(secrets.token_bytes(24)).decode().rstrip("=")
    prefix = raw[:12]
    kh = key_hash(raw)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_keys(key_hash, key_prefix, label, status, created_at, rate_limit_rpm)
                VALUES(%s, %s, %s, 'active', UTC_TIMESTAMP(), %s)
                """,
                (kh, prefix, args.label, args.rate),
            )
            print(raw)


def list_keys(args: argparse.Namespace) -> None:
    clauses = []
    values: list[object] = []
    if args.status:
        clauses.append("status=%s")
        values.append(args.status)
    if args.search:
        clauses.append("label LIKE %s")
        values.append(f"%{args.search}%")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = (
        "SELECT id,key_prefix,label,status,created_at,last_used_at,revoked_at "
        f"FROM api_keys {where} ORDER BY id DESC LIMIT %s"
    )
    values.append(args.limit)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, values)
            for row in cur.fetchall():
                print(
                    row["id"],
                    row["key_prefix"],
                    row["label"],
                    row["status"],
                    row["created_at"],
                    row["last_used_at"],
                    row["revoked_at"],
                )


def revoke(args: argparse.Namespace) -> None:
    if not args.id and not args.prefix:
        raise SystemExit("use --id or --prefix")
    where = "id=%s" if args.id else "key_prefix=%s"
    value = args.id or args.prefix
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE api_keys SET status='revoked', revoked_at=UTC_TIMESTAMP() WHERE {where}",
                (value,),
            )
            print(f"revoked={cur.rowcount}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_create = sub.add_parser("create")
    p_create.add_argument("--label", required=True)
    p_create.add_argument("--rate", type=int, default=60)
    p_create.set_defaults(func=create)

    p_list = sub.add_parser("list")
    p_list.add_argument("--status", choices=["active", "revoked"])
    p_list.add_argument("--search")
    p_list.add_argument("--limit", type=int, default=100)
    p_list.set_defaults(func=list_keys)

    p_revoke = sub.add_parser("revoke")
    p_revoke.add_argument("--id", type=int)
    p_revoke.add_argument("--prefix")
    p_revoke.set_defaults(func=revoke)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
