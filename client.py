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

            # Optional: Uncomment to create a bucket (Change the name first!)
            # print("\n> Creating a new bucket...")
            # result = await session.call_tool("create_bucket", arguments={"bucket_name": "my-test-bucket-mcp-123"})
            # print(result.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())
