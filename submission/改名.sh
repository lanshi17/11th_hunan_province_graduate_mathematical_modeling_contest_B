#!/usr/bin/env bash
# 将占位符 TEAMID 换成官方队号。
# 用法：bash 改名.sh 202618001001
set -euo pipefail
id="${1:?用法: bash 改名.sh <官方队号>  例如 202618001001}"
if [[ ! "$id" =~ ^[0-9]{8,}$ ]]; then
  echo "队号应为官方完整数字编号，例如 202618001001" >&2
  exit 1
fi
name="B${id}"
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
if [[ ! -f B_TEAMID.pdf || ! -f B_TEAMID.zip ]]; then
  echo "本目录需要已有 B_TEAMID.pdf 与 B_TEAMID.zip" >&2
  exit 1
fi
cp -f B_TEAMID.pdf "${name}.pdf"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
unzip -q B_TEAMID.zip -d "$tmp"
if [[ ! -f "$tmp/B_TEAMID.pdf" ]]; then
  echo "zip 内未找到 B_TEAMID.pdf" >&2
  exit 1
fi
mv "$tmp/B_TEAMID.pdf" "$tmp/${name}.pdf"
rm -f "${DIR}/${name}.zip"
( cd "$tmp" && zip -r -q "${DIR}/${name}.zip" "${name}.pdf" support )
echo "已生成："
ls -lh "${DIR}/${name}.pdf" "${DIR}/${name}.zip"
echo "接下来：官方承诺书打印签字，扫描为 PDF，与上述两份一并交领队。"
