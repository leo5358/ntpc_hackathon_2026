/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 部署到 S3/CloudFront 時指向 Lambda Function URL；本機留空即走 vite proxy 的 /api */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
