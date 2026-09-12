"""AWS Lambda Mangum entrypoint."""
from mangum import Mangum
from api.main import app

# Handler entrypoint for AWS Lambda Function URL
handler = Mangum(app, lifespan="auto")
