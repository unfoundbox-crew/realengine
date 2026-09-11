"""Use Blender's actual stdio MCP tools; no UI automation."""
import asyncio, sys, json
from pathlib import Path
from datetime import timedelta
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params=StdioServerParameters(command='/Users/saurabh/.local/bin/uvx',args=['blender-mcp'],env={'BLENDER_MCP_DISABLE_TELEMETRY':'1'})
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=600)) as session:
            await session.initialize()
            if sys.argv[1]=='--inspect':
                code="import bpy,json; print(json.dumps({'scene':bpy.context.scene.name,'scenes':[(s.name,len(s.objects)) for s in bpy.data.scenes],'collections':[c.name for c in bpy.data.collections],'file':bpy.data.filepath}))"
            else: code=Path(sys.argv[1]).read_text()
            result=await session.call_tool('execute_blender_code',{'code':code,'user_prompt':'hey astra - take this from your baby boi and finish the work in class'},read_timeout_seconds=timedelta(seconds=600))
            for item in result.content:
                if item.type=='text': print(item.text)
asyncio.run(main())
