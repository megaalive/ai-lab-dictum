FROM debian:13.5-slim@sha256:a617c1cdde36a7e0194b2f07dff669e1753c03c3205356b94f9f350b0f9a57d1 AS build
RUN apt-get -o APT::Update::Error-Mode=any update && apt-get install -y --no-install-recommends gcc libc6-dev
COPY argv-dumper.c /tmp/argv-dumper.c
RUN gcc --version && gcc -std=c17 -O2 -Wall -Wextra -Werror -Wconversion -Wpedantic /tmp/argv-dumper.c -o /tmp/argv-dumper

FROM debian:13.5-slim@sha256:a617c1cdde36a7e0194b2f07dff669e1753c03c3205356b94f9f350b0f9a57d1
RUN apt-get -o APT::Update::Error-Mode=any update && apt-get install -y --no-install-recommends python3 strace bash dash && dpkg-query -W bash dash strace python3 libc6 && rm -rf /var/lib/apt/lists/*
COPY --from=build /tmp/argv-dumper /fixture/bin/argv-dumper
COPY tests /lab/tests
WORKDIR /lab
USER 65532:65532
ENTRYPOINT ["/usr/bin/python3", "-B", "/lab/tests/spikes/s1/run.py"]
