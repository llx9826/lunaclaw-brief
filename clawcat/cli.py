"""ClawCat CLI — run the full pipeline from command line.

Usage:
    python -m clawcat.cli "做个每日AI新闻"
    python -m clawcat.cli "今天A股怎么样"
    python -m clawcat.cli "OCR技术周报，要GitHub竞品"
"""

from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("clawcat")


def main():
    parser = argparse.ArgumentParser(description="clawCat-BRIEF — AI-driven briefing engine")
    parser.add_argument("query", nargs="?", default="", help="Report request (e.g. '做个每日AI新闻')")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--json-only", action="store_true", help="Output Brief JSON only (no HTML/PDF)")
    args = parser.parse_args()

    if not args.query:
        parser.print_help()
        print("\nExample: python -m clawcat.cli '做个每日AI新闻'")
        sys.exit(1)

    from clawcat.graph import compile_graph

    graph = compile_graph()

    logger.info("Running pipeline for: %s", args.query)
    result = graph.invoke({"user_input": args.query})

    if result.get("error"):
        logger.error("Pipeline error: %s", result["error"])
        sys.exit(1)

    json_path = result.get("json_path", "")
    html_path = result.get("html_path", "")
    pdf_path = result.get("pdf_path", "")

    if json_path:
        logger.info("Brief JSON: %s", json_path)
    if html_path:
        logger.info("HTML: %s", html_path)
    if pdf_path:
        logger.info("PDF: %s", pdf_path)

    logger.info("Done!")


if __name__ == "__main__":
    main()
