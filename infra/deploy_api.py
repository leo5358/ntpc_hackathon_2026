"""Deploy FastAPI app to AWS Lambda with Function URL.

Usage:
    python -m infra.deploy_api --stage dev
"""
import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("infra.deploy_api")


def package_and_deploy_lambda(stage: str = "dev", profile: str = "workshop", region: str = "us-west-2") -> str:
    """Package api/ and dependencies into a zip and deploy/update AWS Lambda Function URL.

    Infra stub: interface defined per hackathon-plan-2.md.
    Returns:
        Lambda Function URL string.
    """
    logger.info("Packaging backend for Lambda (Stage: %s, Region: %s)...", stage, region)
    logger.info("[STUB] Building zip bundle with api/ and Mangum handler...")
    logger.info("[STUB] Creating/Updating Lambda function 'kiro-smart-watchdog-api'...")
    logger.info("[STUB] Configuring Lambda Function URL (AuthType: NONE, CORS enabled)...")
    
    mock_url = f"https://mock-lambda-function-url.{region}.on.aws/"
    logger.info("Lambda Function URL deployed at: %s", mock_url)
    return mock_url


def main():
    parser = argparse.ArgumentParser(description="Deploy API to AWS Lambda Function URL")
    parser.add_argument("--stage", default="dev", help="Deployment stage (dev, staging, prod)")
    parser.add_argument("--profile", default="workshop", help="AWS CLI profile name")
    parser.add_argument("--region", default="us-west-2", help="AWS region")
    args = parser.parse_args()

    url = package_and_deploy_lambda(stage=args.stage, profile=args.profile, region=args.region)
    print(f"API_URL={url}")


if __name__ == "__main__":
    main()
