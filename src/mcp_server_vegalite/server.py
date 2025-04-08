import logging
import json
import base64
import os
import sys
import argparse
from typing import Any, Dict, List, Optional, Union
from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
import asyncio
import anyio
import vl_convert as vlc
from pydantic import BaseModel
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.server.sse

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("mcp_vegalite_server.log"),  # Файл логов
        logging.StreamHandler(),  # Вывод в консоль
    ],
)

logger = logging.getLogger("mcp_vegalite_server")
logger.info("Starting MCP Vega-Lite Server")

# Хранилище данных
saved_data = {
    "sample_data": [
        {"name": "Alice", "age": 25, "city": "New York"},
        {"name": "Bob", "age": 30, "city": "San Francisco"},
        {"name": "Charlie", "age": 35, "city": "Los Angeles"},
    ]
}

# Описания инструментов
SAVE_DATA_TOOL_DESCRIPTION = """
A tool which allows you to save data to a named table for later use in visualizations.
When to use this tool:
- Use this tool when you have data that you want to visualize later.
How to use this tool:
- Provide the name of the table to save the data to (for later reference) and the data itself.
""".strip()

VISUALIZE_DATA_TOOL_DESCRIPTION = """
A tool which allows you to produce a data visualization using the Vega-Lite grammar.
When to use this tool:
- At times, it will be advantageous to provide the user with a visual representation of some data, rather than just a textual representation.
- This tool is particularly useful when the data is complex or has many dimensions, making it difficult to understand in a tabular format. It is not useful for singular data points.
How to use this tool:
- Prior to visualization, data must be saved to a named table using the save_data tool.
- After saving the data, use this tool to visualize the data by providing the name of the table with the saved data and a Vega-Lite specification.
""".strip()

app = FastAPI()

# Разрешаем CORS для поддержки запросов от разных источников
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаем обработчики для сервера MCP
async def setup_mcp_server(output_type: str = "png"):
    logger.info(f"Setting up Vega-Lite MCP Server with output_type={output_type}")
    
    server = Server("vegalite-manager")
    
    @server.list_resources()
    async def handle_list_resources() -> List[types.Resource]:
        logger.debug("Handling list_resources request")
        return []
    
    @server.read_resource()
    async def handle_read_resource(uri: str) -> str:
        logger.debug(f"Handling read_resource request for URI: {uri}")
        path = str(uri).replace("memo://", "")
        raise ValueError(f"Unknown resource path: {path}")
    
    @server.list_prompts()
    async def handle_list_prompts() -> List[types.Prompt]:
        logger.debug("Handling list_prompts request")
        return []
    
    @server.get_prompt()
    async def handle_get_prompt(name: str, arguments: Optional[Dict[str, str]] = None) -> types.GetPromptResult:
        logger.debug(f"Handling get_prompt request for {name} with args {arguments}")
        raise ValueError(f"Unknown prompt: {name}")
    
    @server.list_tools()
    async def handle_list_tools() -> List[types.Tool]:
        """List available tools"""
        return [
            types.Tool(
                name="save_data",
                description=SAVE_DATA_TOOL_DESCRIPTION,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "The name of the table to save the data to"},
                        "data": {
                            "type": "array",
                            "items": {"type": "object", "description": "Row of the table as a dictionary/object"},
                            "description": "The data to save",
                        },
                    },
                    "required": ["name", "data"],
                },
            ),
            types.Tool(
                name="visualize_data",
                description=VISUALIZE_DATA_TOOL_DESCRIPTION,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "data_name": {
                            "type": "string",
                            "description": "The name of the data table to visualize",
                        },
                        "vegalite_specification": {
                            "type": "string",
                            "description": "The vegalite v5 specification for the visualization. Do not include the data field, as this will be added automatically.",
                        },
                    },
                    "required": ["data_name", "vegalite_specification"],
                },
            ),
        ]
    
    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """Handle tool execution requests"""
        logger.info(f"Handling tool execution request for {name} with args {arguments}")
        try:
            if arguments is None:
                arguments = {}
                
            if name == "save_data":
                save_name = arguments["name"]
                saved_data[save_name] = arguments["data"]
                return [types.TextContent(type="text", text=f"Data saved successfully to table {save_name}")]
            
            elif name == "visualize_data":
                data_name = arguments["data_name"]
                vegalite_specification = eval(arguments["vegalite_specification"])
                data = saved_data[data_name]
                vegalite_specification["data"] = {"values": data}
                
                if output_type == "png":
                    png = vlc.vegalite_to_png(vl_spec=vegalite_specification, scale=2)
                    png = base64.b64encode(png).decode("utf-8")
                    return [types.ImageContent(type="image", data=png, mimeType="image/png")]
                else:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Visualized data from table {data_name} with provided spec.",
                            artifact=vegalite_specification,
                        )
                    ]
            else:
                raise ValueError(f"Unknown tool: {name}")
                
        except Exception as e:
            logger.error(f"Error handling tool execution: {str(e)}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    
    return server

# Основная функция для запуска сервера через SSE
async def create_server(output_type: str = "png"):
    # Создаем сервер MCP
    server = await setup_mcp_server(output_type)
    return server

# Прямой запуск через STDIO
async def run_stdio_server(output_type: str):
    """Запуск сервера через STDIO"""
    logger.info(f"Starting STDIO server with output_type={output_type}")
    
    server = await setup_mcp_server(output_type)
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running with stdio transport")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="vegalite",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

# Основная функция выбора транспорта
def main():
    import argparse
    import sys
    from starlette.routing import Route, Mount
    from starlette.applications import Starlette
    
    parser = argparse.ArgumentParser(description="Data Visualization MCP Server")
    parser.add_argument("--output-type", default="png", choices=["text", "png"], 
                        help="Format of the output")
    parser.add_argument("--transport", default="sse", choices=["stdio", "sse"], 
                        help="Transport type to use (stdio or sse)")
    parser.add_argument("--port", type=int, default=8000, 
                        help="Port for SSE server (only used with --transport=sse)")
    
    # Парсим аргументы командной строки
    args = parser.parse_args()
    
    # Логируем настройки
    logger.info(f"Starting server with transport={args.transport}, output_type={args.output_type}, port={args.port}")
    
    if args.transport == "sse":
        # Запуск SSE сервера
        logger.info(f"Starting SSE server on port {args.port}")
        
        # Создаем SSE транспорт для MCP
        sse_transport = mcp.server.sse.SseServerTransport("/messages/")
        
        # Функция для обработки SSE соединений
        async def handle_sse(request):
            logger.info("SSE connection established")
            async with sse_transport.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                # Создаем сервер MCP
                server = await setup_mcp_server(args.output_type)
                
                # Запускаем сервер с полученными стримами
                await server.run(
                    streams[0],
                    streams[1],
                    InitializationOptions(
                        server_name="vegalite",
                        server_version="0.1.0",
                        capabilities=server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )
        
        # Настраиваем маршруты для Starlette
        routes = [
            Route("/sse", endpoint=handle_sse),
            Mount("/messages", app=sse_transport.handle_post_message),
        ]
        
        # Создаем приложение Starlette
        app = Starlette(routes=routes)
        
        # Добавляем CORS поддержку
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Запускаем uvicorn сервер
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    else:
        # Запуск STDIO сервера
        import asyncio
        asyncio.run(run_stdio_server(args.output_type))

# Позволяет импортировать как модуль
if __name__ == "__main__":
    main()
