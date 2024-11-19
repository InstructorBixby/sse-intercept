# sse-intercept

An intercepting proxy for streaming HTTP responses.

Burp buffers `text/event-stream`. The response arrives in the proxy
history as one blob once the stream closes, which means frame
boundaries are gone, inter-frame timing is gone, and there is no moment
at which a single frame can be modified while the client is still
reading. For an endpoint that streams tokens that is most of the
behaviour worth looking at.

Right now this is one script. It is a plain-HTTP proxy that forwards
the request, and when the response is `text/event-stream` it prints
every frame with the time since the previous one.

    python sniff.py --port 8080
    http_proxy=http://127.0.0.1:8080 curl -N http://localhost:9000/stream
