# Container image

Built here, by me, and kept here. There is no registry involved and
nothing to pull:

    podman build -t sseint:1.1 -f Containerfile .

## running it

    podman run --rm -it \
      -p 8080:8080 \
      -v "$PWD/mitmproxy:/home/sseint/.mitmproxy" \
      -v "$PWD/sessions:/home/sseint/sessions" \
      sseint:1.1 \
      proxy --host 0.0.0.0 --allow-host api.example.test \
            --record sessions/run.jsonl

Mount both volumes. `.mitmproxy` holds the CA: regenerate it on every
container start and I get to import a new certificate into the client
on every container start. `sessions` is where the recordings land, and
they have to survive the container -- they are engagement evidence.

`--host 0.0.0.0` is needed inside a container and is the one place
this tool binds anything but loopback. The scope guard is what makes
that acceptable: the proxy still refuses every host I did not name,
and the image has no default scope -- `CMD` is `--help`.

## getting it onto the other machine

`podman save` to a tar, copy it over, `podman load`. Same as the
wheel: the point of the image is that the laptop sitting next to the
client's client needs no toolchain, no checkout, and nothing of mine
half-finished on it.

## reading a session afterwards

The session subcommands do not need the proxy, so read it on this
machine out of the checkout, or:

    podman run --rm -v "$PWD/sessions:/s" \
      sseint:1.1 show /s/run.jsonl --timing

`sseint view` wants a real terminal; `-it` is enough.

## what is not in the image

`samples/`, the tests and the docs. The image is for running a proxy
next to something, not for working on this.
