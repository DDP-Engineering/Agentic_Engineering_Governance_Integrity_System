# AEGIS workflow transport

Use `.agentic/aegis/bin/aegis --format json stage-show` to resume the selected
Run and Stage. Treat every response as an `aegis.machine.response`; show at
most its three declared next actions and dispatch only operation identifiers
defined by the host-adapter contract.

Do not infer approval, exceptions, skips, dispositions, or completion from
conversation. Record them through the applicable AEGIS operation. Git commit,
branch, push, and merge policy remains outside AEGIS.
