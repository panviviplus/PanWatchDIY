#!/bin/bash
# 安装 Git hooks
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOKS_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)/.git/hooks"

cp "$SCRIPT_DIR/pre-push" "$HOOKS_DIR/pre-push"
chmod +x "$HOOKS_DIR/pre-push"

echo "Git hooks installed successfully."
