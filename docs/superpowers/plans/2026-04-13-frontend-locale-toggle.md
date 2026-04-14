# Frontend Locale Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a temporary zh/en locale toggle for the frontend, defaulting to Chinese on each page load and covering the core static UI text.

**Architecture:** Keep localization lightweight by adding a small in-repo message dictionary, a `locale` state in the existing Pinia store, and component-level lookups via a shared `translate(locale, key)` helper. Avoid `vue-i18n` and avoid persistence so refreshes naturally restore Chinese.

**Tech Stack:** Vue 3, Pinia, Vite, node-based smoke tests

---
