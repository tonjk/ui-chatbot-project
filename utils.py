import boto3
import os
import logging
from dotenv import load_dotenv
load_dotenv()

# --- LOGGER SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = "jk-ui-chatbot-template"

if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION]):
    logger.error("Missing AWS credentials or region in environment variables.")
    raise EnvironmentError("Missing AWS credentials or region in environment variables.")

# Initialize S3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def s3_upload_file(file_obj, filename, bucket=S3_BUCKET_NAME):
    ext = os.path.splitext(filename)[1].lower()
    if ext in ('.xlsx', '.csv'):
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if ext == '.xlsx' else 'text/csv'
        key = f"data_file/{filename}"
        s3.upload_fileobj(file_obj, bucket, key, ExtraArgs={'ContentType': content_type})
        logger.info(f"✅ Uploaded: {filename} -> s3://{bucket}/{key}")
        return f"https://{bucket}.s3.{AWS_REGION}.amazonaws.com/{key}"
    elif ext in ('.png', '.jpg', '.jpeg', '.gif'):
        content_type = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif'
        }.get(ext, 'application/octet-stream')
        key = f"logo/{filename}"
        s3.upload_fileobj(file_obj, bucket, key, ExtraArgs={'ContentType': content_type})
        logger.info(f"✅ Uploaded: {filename} -> s3://{bucket}/{key}")
        return f"https://{bucket}.s3.{AWS_REGION}.amazonaws.com/{key}"
    else:
        logger.warning(f"❌ Unsupported file type: {filename}")
        return