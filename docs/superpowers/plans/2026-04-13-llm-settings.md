# LLM Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the frontend edit the active model name and system prompt, persist those settings in SQLite, and apply them to future suggestions across restarts.

**Architecture:** Add a small `app_settings` key-value table to SQLite, expose `GET/PUT /api/settings/llm`, and have `LivePromptAgent` resolve prompt/model overrides from the database instead of only from `.env`. On the frontend, add a settings panel and store state/actions that load, edit, save, and reset those values.

**Tech Stack:** FastAPI, SQLite, Vue 3, Pinia, Vite, Python `unittest`, node-based smoke tests

---
