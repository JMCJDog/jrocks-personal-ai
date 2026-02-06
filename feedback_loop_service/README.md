# Vibe Coding Feedback Loop Service

This directory contains the autonomous feedback loop service that connects Google Docs to your local Agent.

## Overview
The service polls a specific Google Doc (`config.json`) for new commands, executes them using the local AI agent (Ollama + CodeAgent), and writes the results back to the Doc.

## Contents
*   `run_feedback_loop.py`: The main Python logic.
*   `start_watcher.ps1`: Robust launcher script (auto-restarts on crash).
*   `config.json`: Configuration (Doc Name, Poll Interval).
*   `credentials.json` & `token.pickle`: Google API Authentication.
*   `watcher_debug.log`: active logs.

## Usage
To start the service:
1.  Open PowerShell.
2.  Run: `.\start_watcher.ps1`
    (Or right-click -> Run with PowerShell)

## Troubleshooting
*   **Logs**: Check `watcher_debug.log`.
*   **Auth**: If auth fails, delete `token.pickle` and re-run to re-authenticate.
