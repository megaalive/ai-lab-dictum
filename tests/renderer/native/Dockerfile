FROM debian:13.5-slim@sha256:a617c1cdde36a7e0194b2f07dff669e1753c03c3205356b94f9f350b0f9a57d1 AS build
RUN apt-get -o APT::Update::Error-Mode=any update && apt-get install -y --no-install-recommends gcc libc6-dev cmake make libssl-dev python3-jsonschema
COPY source /src
WORKDIR /src
RUN cmake -S . -B /build -DCMAKE_BUILD_TYPE=Release -DCMAKE_COMPILE_WARNING_AS_ERROR=ON && cmake --build /build --target renderer_probe dictum --parallel 2
RUN gcc -std=c17 -O2 -Wall -Wextra -Wpedantic -Wconversion -Werror tests/spikes/s1/argv-dumper.c -o /build/argv-dumper

FROM debian:13.5-slim@sha256:a617c1cdde36a7e0194b2f07dff669e1753c03c3205356b94f9f350b0f9a57d1
RUN apt-get -o APT::Update::Error-Mode=any update && apt-get install -y --no-install-recommends python3 strace bash dash libseccomp2 libssl3t64 && dpkg-query -W python3 strace bash dash libseccomp2 libssl3t64 && rm -rf /var/lib/apt/lists/*
COPY --from=build /build/argv-dumper /fixture/bin/argv-dumper
COPY --from=build /build/tests/renderer_probe /fixture/bin/renderer-probe
COPY --from=build /build/dictum /fixture/bin/dictum
RUN mkdir -p /fixture/data /fixture/private /fixture/logs /fixture/projects && printf '%s\n' CANARY_SECRET_CONTENT_FIXTURE_V1 > /fixture/data/.env && printf '%s\n' CANARY_SECRET_CONTENT_FIXTURE_V2 > /fixture/private/hidden && ln -s /fixture/private /fixture/data/escape
COPY source/tests/spikes/s1/run.py /lab/tests/spikes/s1/run.py
COPY source/tests/renderer/run.py source/tests/renderer/native_run.py /lab/tests/renderer/
COPY source/tests/renderer/fixtures/preview-v1.json /lab/tests/renderer/fixtures/preview-v1.json
COPY source/tests/pipeline/functional-v1.json source/tests/pipeline/security_trace.py source/tests/pipeline/catalog_lookup.py /lab/tests/pipeline/
COPY source/catalog/core/intents-v1.json /lab/catalog/core/intents-v1.json
COPY source/catalog/debian-13/v1.json /lab/catalog/debian-13/v1.json
WORKDIR /lab
USER 65532:65532
ENTRYPOINT ["/usr/bin/python3","-B","/lab/tests/renderer/native_run.py","/fixture/bin/renderer-probe"]
