---
name: schienendashboard
description: Entry point for work through the Schienendashboard MCP (railway infrastructure projects, FinVe, Haushalt, Infraplan, planning state, data maintenance). Use whenever a task uses the Schienendashboard tools, especially multi-step work such as an import run, before the first write call.
---

# Schienendashboard

The step-by-step guides for this dashboard live on its MCP server, not in this skill,
so they always match the deployed tools. This skill only tells you where to get them.

1. Call `list_skills` on the Schienendashboard MCP server.
2. If a skill fits the task, load it with `get_skill(name)` and follow its `content`.
   Supporting files listed under `files` are read with `get_skill(name, file=...)`.
3. If no skill fits, work with the tools directly; the server instructions explain
   the basics (search with `list_projects`, then drill down by id).

Never rely on an older copy of a guide from memory or another conversation —
fetch it again, the server's version is the authoritative one.
