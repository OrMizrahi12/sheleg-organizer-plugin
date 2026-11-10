# sheleg-organizer

The Claude Code plugin for **Sheleg Organizer**, Sheleg Lavan's shift-scheduling system.

- **MCP server `sheleg`:** the system's tools, at `https://sheleg-organizer-api.fly.dev/mcp`. Sign in once through `/mcp` with your ID number and password. The agent then acts as you, with exactly your grade's permissions.
- **Skill `guide`:** the system's vocabulary, grades and rules, and the safe workflows for project setup, accounts and rosters. Claude loads it when you work with the system.
- **Local engine runner** (`skills/guide/scripts/solve_locally.py`): Claude solves an engine run on this computer, with [uv](https://docs.astral.sh/uv/), and the server only hands out the input and takes back the result. Without uv, the run is solved on the server.
- **Skill `/sheleg-organizer:connect`:** checks the connection and says who Claude acts as, or how to sign in.

Install it from a terminal:

```sh
claude plugin marketplace add https://github.com/OrMizrahi12/sheleg-organizer-plugin.git
claude plugin install sheleg-organizer@sheleg-lavan
```

Sign-in, Claude Desktop, updates and troubleshooting are in the [repository's README](../../README.md).
