# LLM-connected Data Visualization Workflow

## What this project demonstrates

This project demonstrates a technical integration layer that lets an LLM-connected workflow store tabular data and render Vega-Lite visualizations. The repository implements a Model Context Protocol server, but the business-facing proof is broader: connecting language-model workflows to structured data and chart generation.

The project is useful as proof of work for AI-assisted reporting, data visualization workflows, analytics prototypes, and integration layers between LLMs and business data.

## Use case

A user or AI workflow has tabular data and needs to turn it into a chart without manually moving between tools. The server exposes tools for saving table-like data and generating a Vega-Lite visualization from that saved data. Output can be returned as text/spec data or as a PNG image.

## Features

- Save named tabular datasets for later visualization.
- Generate Vega-Lite visualizations from saved datasets.
- Return visualization output as text/spec artifacts or PNG images.
- Support stdio transport for local MCP clients.
- Include an SSE/FastAPI path for integration experiments.
- Store generated visualization files locally during runs.

## Technical stack

- Runtime: Python 3.10+.
- Protocol layer: Model Context Protocol Python SDK.
- API/server experiments: FastAPI and uvicorn.
- Visualization: Vega-Lite through vl-convert-python.
- Packaging: pyproject.toml with a console script entrypoint.

## Architecture

The server exposes two core tools. The first saves a named table of JSON-like rows. The second accepts a Vega-Lite specification, attaches the saved data, renders the chart, and returns either a visualization artifact or PNG image content. This keeps the data handoff explicit and makes the visualization step reproducible.

## How to run locally

Prerequisites:

- Python 3.10 or newer.
- uv or another Python environment manager.

Install and run with uv:

```bash
uv sync
uv run mcp_server_vegalite --output-type png
```

Alternative output:

```bash
uv run mcp_server_vegalite --output-type text
```

## Portfolio notes

This repository can mention MCP for technical readers, but acty.dev should not sell MCP as a standalone service line. The client-facing framing is LLM-connected data visualization and analytics workflow integration.

This repository is a portfolio/proof-of-work project. It does not include private client data, production credentials, internal datasets, or confidential business logic.

Related acty.dev proof page: `/examples/llm-data-visualization/`.
