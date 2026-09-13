"""部署後驗證：直接叫用 Lambda，不經過對外網路。

    python -m infra.verify_deploy --stage dev

刻意不打 API Gateway 的公開網址，因為 config.yaml 的 IP 白名單只允許
指定來源，CI runner 的 IP 不在其中會被 403 擋下。改用 lambda:Invoke
送出合成的 API Gateway 事件，驗證的是同一份程式與同一組設定。
"""
import argparse
import json
import logging
import sys

from infra.aws_common import caller_identity, get_session, resource_names

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("infra.verify_deploy")


def api_gateway_event(path: str, method: str = "GET", body: str = None) -> dict:
    """組出 REST API proxy 整合格式的事件。"""
    return {
        "resource": "/{proxy+}",
        "path": path,
        "httpMethod": method,
        "headers": {"Host": "verify.execute-api.amazonaws.com", "Content-Type": "application/json"},
        "multiValueHeaders": {},
        "queryStringParameters": None,
        "multiValueQueryStringParameters": None,
        "pathParameters": {"proxy": path.lstrip("/")},
        "stageVariables": None,
        "requestContext": {
            "resourcePath": "/{proxy+}",
            "httpMethod": method,
            "path": path,
            "stage": "verify",
            "identity": {"sourceIp": "127.0.0.1", "userAgent": "infra.verify_deploy"},
            "protocol": "HTTP/1.1",
        },
        "body": body,
        "isBase64Encoded": False,
    }


def invoke(lam, function_name: str, path: str, method: str = "GET", body: str = None):
    resp = lam.invoke(
        FunctionName=function_name,
        Payload=json.dumps(api_gateway_event(path, method, body)).encode("utf-8"),
    )
    payload = json.loads(resp["Payload"].read().decode("utf-8"))
    if "errorMessage" in payload:
        return None, payload["errorMessage"]
    return payload, None


def main():
    parser = argparse.ArgumentParser(description="Verify deployed Lambda behind API Gateway")
    parser.add_argument("--stage", default="dev")
    parser.add_argument("--region", default=None)
    args = parser.parse_args()

    session = get_session(region=args.region)
    ident = caller_identity(session)
    function_name = resource_names(args.stage, ident["Account"])["function"]
    lam = session.client("lambda")

    checks = [
        ("/api/health", "GET", None),
        ("/api/rankings", "GET", None),
        ("/api/institutions", "GET", None),
        ("/api/report/scales", "GET", None),
        ("/api/report/N07", "GET", None),
    ]

    failures = []
    for path, method, body in checks:
        payload, err = invoke(lam, function_name, path, method, body)
        if err:
            print(f"  FAIL  {method} {path} — Lambda 例外：{err[:160]}")
            failures.append(path)
            continue
        status = payload.get("statusCode")
        if status == 200:
            if path == "/api/institutions":
                try:
                    count = len(json.loads(payload.get("body", "[]")))
                    print(f"  PASS  {method} {path} （共載入 {count} 所機構）")
                    if count < 1000:
                        print(f"  WARN  {method} {path} 機構數量僅 {count} 所（未達 1000 所）")
                except Exception:
                    print(f"  PASS  {method} {path}")
            else:
                print(f"  PASS  {method} {path}")
        else:
            print(f"  FAIL  {method} {path} — HTTP {status}：{str(payload.get('body'))[:160]}")
            failures.append(path)

    print()
    if failures:
        print(f"部署驗證失敗 {len(failures)} 項：{', '.join(failures)}")
        sys.exit(1)
    print(f"部署驗證通過（函式 {function_name}）")


if __name__ == "__main__":
    main()
