# Where this can hurt me

This thing terminates TLS and writes transcripts of a client's traffic
to disk, on a laptop I carry between engagements. The failure modes
are not hypothetical and they are not the ones I would guess under
pressure, so they are written down.

## the four that matter

- **Scope-guard bypass.** A request reaching an upstream host I did
  not name in `--allow-host` or `allow_hosts` is the worst bug this
  code can have: it means I relayed traffic I had no authorisation to
  touch, through an instrument that records it. It is the one
  behaviour here with a test suite whose only purpose is to stop it
  regressing, and the only part of the diff I always read twice.
- **Credentials in a session file that redaction should have caught**,
  or a `meta` record claiming `redacted: true` for a file that is not.
  Session files end up attached to findings. A false `redacted: true`
  is worse than no redaction at all, because it is the line I would
  check before sending the file.
- **Code execution out of a rule file, a session file or a stream.**
  Rule files are YAML through `safe_load`, session files are JSON. A
  decoder is fed hostile bytes by definition: a crash is a bug,
  anything past a crash means a target's stream is running code on my
  machine.
- **Unbounded memory off a hostile stream.** The decoders have
  explicit caps. A way past one of them kills the process mid-capture
  and takes the run with it.

## not this tool's problem, and I should stop looking here

- **mitmproxy's TLS interception, CA handling and HTTP stacks.**
  Upstream. If something looks wrong there, reproduce it against
  mitmproxy alone before touching anything in here.
- **The CA being able to intercept TLS.** That is the tool. The
  private key is the sensitive artefact and it is mitmproxy's, in its
  `confdir`. That directory is as sensitive as a password store:
  import the certificate into the client under test, nowhere else,
  and remove it when the engagement ends.
- **A `--no-redact` session file containing credentials.** It says so
  in its own first line. That file is engagement material and belongs
  in the engagement directory, encrypted, not in `/tmp`.

## the habit

One scope file per engagement, checked before the proxy starts, and
the session files under the engagement directory from the first run --
not moved there afterwards, because afterwards is when I forget.
