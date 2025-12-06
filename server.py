from mcp.server.fastmcp import FastMCP
import boto3
import json

# 1. Create the Server
mcp = FastMCP("AWS S3 Manager")

# 2. Initialize AWS S3 Client
# boto3 will automatically look for credentials in ~/.aws/credentials
s3 = boto3.client('s3')

@mcp.tool()
def list_buckets() -> str:
    """
    Lists all S3 buckets in your AWS account.
    """
    try:
        response = s3.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        
        if not buckets:
            return "You have no S3 buckets."
            
        return "Your S3 Buckets:\n" + "\n".join(f"- {b}" for b in buckets)
    except Exception as e:
        return f"Error listing buckets: {str(e)}"

@mcp.tool()
def create_bucket(bucket_name: str, region: str = "us-east-1") -> str:
    """
    Creates a new S3 bucket.
    Args:
        bucket_name: The unique name for the new bucket.
        region: The AWS region (default: us-east-1).
    """
    try:
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        return f"Successfully created bucket: {bucket_name} in {region}"
    except Exception as e:
        return f"Error creating bucket: {str(e)}"

if __name__ == "__main__":
    mcp.run()
