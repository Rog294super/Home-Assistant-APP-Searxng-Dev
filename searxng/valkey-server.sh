#!/bin/sh
set -eu

# Use Valkey's bundled glibc loader and libraries without replacing the app's Void libraries.
case "$(uname -m)" in
    x86_64)
        LOADER="/opt/valkey/lib/ld-linux-x86-64.so.2"
        ;;
    aarch64)
        LOADER="/opt/valkey/lib/ld-linux-aarch64.so.1"
        ;;
    *)
        echo "Unsupported Valkey architecture: $(uname -m)" >&2
        exit 1
        ;;
esac

exec "$LOADER" --library-path /opt/valkey/lib /opt/valkey/bin/valkey-server "$@"