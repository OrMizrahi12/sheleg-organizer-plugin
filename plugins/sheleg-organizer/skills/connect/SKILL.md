---
name: connect
description: Checks the connection to Sheleg Organizer and says who it acts as, or how to sign in when it is not connected yet.
disable-model-invocation: true
allowed-tools: mcp__plugin_sheleg-organizer_sheleg__me_get, Read
---

# Check the Sheleg Organizer connection

Answer in the user's language: Hebrew if they write Hebrew.

1. Call the tool `me_get` of the Sheleg Organizer server (`mcp__plugin_sheleg-organizer_sheleg__me_get`). Use no other tool of the server.

2. **If it answers**, report in two or three lines: the name, the grade (root admin, company admin or project manager), the company, and the projects the user manages. Then say the connection works and that the agent acts with exactly this user's permissions. If the phone is null, say the account has no mobile number yet: they can add their own (`me_setPhone`), or a manager can add it.

3. **If the tool is missing, or the call fails because the server needs authentication**, tell the user these steps:
   1. Type `/mcp`.
   2. Choose `plugin:sheleg-organizer:sheleg` and press **Authenticate**.
   3. The browser opens the page "חיבור סוכן לחשבון שלך". Enter your ID number and password there, never in this chat. Leave the narrowing boxes unticked for full use, or tick them to narrow this connection.
   4. If you manage more than one project, choose which projects the agent may reach.
   5. Return here and run `/sheleg-organizer:connect` again.

4. **If the call is refused**, explain the reason:
   - `agents_not_for_this_grade`: only managers connect agents, and workers never do.
   - `agents_disabled`: the company's agent switch is off. A company admin or the root admin can turn it on.
   - A revoked or unknown token: the connection was cancelled on the web page. Type `/mcp`, choose the server, and use **Clear authentication**, then **Authenticate** again.

5. **Updates.** Read `~/.claude/plugins/known_marketplaces.json` if it exists. If the `sheleg-lavan` entry lacks `"autoUpdate": true`, tell the user how to keep the plugin current by itself: type `/plugin`, open **Marketplaces**, choose `sheleg-lavan`, and select **Enable auto-update**. Do not change the file yourself.
