import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # 1. Start the Server
    server_params = StdioServerParameters(
        command="python3",
        args=["server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 2. List Tools
            tools = await session.list_tools()
            print("--- Available Tools ---")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")
            print("-----------------------")

            # 3. Call 'list_buckets'
            print("\n> Asking server to list S3 buckets...")
            result = await session.call_tool("list_buckets")
            print(result.content[0].text)

            # 4. Create a new bucket
            import random
            bucket_name = f"mcp-test-bucket-{random.randint(1000, 9999)}"
            print(f"\n> Creating a new bucket: {bucket_name}...")
            result = await session.call_tool("create_bucket", arguments={"bucket_name": bucket_name})
            print(result.content[0].text)
            
            # 5. List again to verify
            print("\n> Verifying bucket list...")
            result = await session.call_tool("list_buckets")
            print(result.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())
