# A proxy is a sensible thing to have as an image: it needs a
# mitmproxy of a particular age, it writes to one directory, and the
# machine it has to run next to is frequently not a machine I control
# or want to install a toolchain on.
FROM python:3.13-slim AS build

WORKDIR /src
COPY pyproject.toml README.md LICENSE constraints-dev.txt ./
COPY sseint ./sseint
RUN pip install --no-cache-dir build \
 && python -m build --wheel --outdir /dist

FROM python:3.13-slim

# Run as a normal user. Nothing here needs root, and the one thing
# that looks like it might -- binding 8080 -- does not.
RUN useradd --create-home --uid 10001 sseint
COPY --from=build /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

USER sseint
WORKDIR /home/sseint

# The CA lives here and the session files land here. Mount both; a
# CA regenerated on every container start is a CA I have to import
# into the client on every container start.
VOLUME ["/home/sseint/.mitmproxy", "/home/sseint/sessions"]
EXPOSE 8080

ENTRYPOINT ["sseint"]
# No default scope: an image that proxies something by default is the
# one mistake this tool is built not to make.
CMD ["--help"]
