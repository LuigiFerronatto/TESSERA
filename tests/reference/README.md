# Independent OKF reference validator

`okf_document.py` is an unmodified copy of the Apache-2.0 licensed upstream file:
https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/ad30107c31c06aec8a7d5636e0d1058118604e6f/src/reference_agent/bundle/document.py

Observed on 2026-10-02. Upstream Git blob:
`b770a92f33adf9942e2932529308d066430b02a6`.
Local SHA-256: `7d9be6961b38f0fd2196e1cbe630afb1a4682e33ccd43daf3f233401ca62a43b`.
The upstream copyright header is retained; see LICENSE.okf.

Used only by the offline synthetic #204 experiment. It parses concepts and
checks the required type key. It is not a complete bundle/spec validator and
is not imported by TESSERA runtime modules. No upstream agent, executor,
attester, service or dependency bundle is installed or invoked.
