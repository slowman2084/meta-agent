#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯云 CLS 日志查询脚本
基于腾讯云 SearchLog API: https://cloud.tencent.com/document/product/614/56447
"""

import os
import json
import time
import hashlib
import hmac
import base64
import requests
from datetime import datetime
from urllib.parse import urlencode


class CLSClient:
    """腾讯云 CLS 客户端"""

    def __init__(self, secret_id, secret_key, endpoint="cls.internal.tencentcloudapi.com", region="ap-guangzhou"):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.endpoint = endpoint
        self.region = region
        self.service = "cls"
        self.version = "2020-10-16"
        self.action = "SearchLog"

    def _sign_tc3(self, secret_key, date, service, string_to_sign):
        """TC3-HMAC-SHA256 签名"""
        def _hmac_sha256(key, msg):
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

        def _sha256_hex(s):
            return hashlib.sha256(s.encode('utf-8')).hexdigest()

        secret_date = _hmac_sha256(("TC3" + secret_key).encode('utf-8'), date)
        secret_service = _hmac_sha256(secret_date, service)
        secret_signing = _hmac_sha256(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        return signature

    def _build_payload(self, params):
        """构建请求 payload"""
        payload = {}
        for k, v in params.items():
            if v is not None and v != "":
                payload[k] = v
        return json.dumps(payload)

    def _request(self, params):
        """发送 API 请求"""
        # 时间戳
        timestamp = int(time.time())
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")

        # 请求参数
        payload = self._build_payload(params)
        hashed_request_payload = hashlib.sha256(payload.encode('utf-8')).hexdigest()

        # 构建签名字符串
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_query_string = ""
        canonical_headers = f"content-type:application/json\nhost:{self.endpoint}\n"
        signed_headers = "content-type;host"
        canonical_request = (
            f"{http_request_method}\n"
            f"{canonical_uri}\n"
            f"{canonical_query_string}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{hashed_request_payload}"
        )

        # 规范请求哈希
        hashed_canonical_request = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()

        # 待签名字符串
        algorithm = "TC3-HMAC-SHA256"
        credential_scope = f"{date}/{self.service}/tc3_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{timestamp}\n"
            f"{credential_scope}\n"
            f"{hashed_canonical_request}"
        )

        # 计算签名
        signature = self._sign_tc3(self.secret_key, date, self.service, string_to_sign)

        # 构建 Authorization header
        authorization = (
            f"{algorithm} "
            f"Credential={self.secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        # 构建请求 URL
        url = f"https://{self.endpoint}/"

        # 请求 headers
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Host": self.endpoint,
            "X-TC-Action": self.action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": self.version,
            "X-TC-Region": self.region,
            "Accept-Encoding": "gzip",  # 启用 gzip 压缩
        }

        # 发送请求
        try:
            response = requests.post(url, headers=headers, data=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"请求失败: {str(e)}")

    def search_log(self, topic_id, query, from_time, to_time,
                   limit=100, sort="desc", highlight=False,
                   use_new_analysis=True, syntax_rule=1):
        """
        检索分析日志

        Args:
            topic_id: 日志主题 ID
            query: 检索分析语句
            from_time: 起始时间 (毫秒时间戳)
            to_time: 结束时间 (毫秒时间戳)
            limit: 返回条数，默认 100，最大 1000
            sort: 排序方式，asc 或 desc
            highlight: 是否高亮
            use_new_analysis: 是否使用新的分析格式
            syntax_rule: 语法规则，0-Lucene 或 1-CQL

        Returns:
            dict: API 响应结果
        """
        params = {
            "TopicId": topic_id,
            "Query": query,
            "From": from_time,
            "To": to_time,
            "Limit": limit,
            "Sort": sort,
            "HighLight": highlight,
            "UseNewAnalysis": use_new_analysis,
            "SyntaxRule": syntax_rule,
        }

        return self._request(params)


def _load_dotenv():
    """尝试加载 .env 文件（使用 python-dotenv），加载失败则静默忽略"""
    try:
        from dotenv import load_dotenv
        # 依次尝试：当前目录 .env -> skill 目录 .env
        load_dotenv()  # 当前工作目录
        skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_file = os.path.join(skill_dir, ".env")
        if os.path.exists(env_file):
            load_dotenv(env_file)
    except ImportError:
        pass  # python-dotenv 未安装，静默跳过


def _get_config(args_value, env_key, default=None):
    """
    获取配置值，优先级：命令行参数 > 环境变量 > 默认值

    Args:
        args_value: 命令行参数值（可能为 None）
        env_key: 环境变量名
        default: 默认值

    Returns:
        配置值
    """
    if args_value is not None:
        return args_value
    env_value = os.environ.get(env_key)
    if env_value is not None and env_value != "":
        return env_value
    return default


def main():
    """CLI 入口"""
    import argparse

    # 尝试加载 .env 文件（在解析参数之前，以便环境变量生效）
    _load_dotenv()

    parser = argparse.ArgumentParser(description="腾讯云 CLS 日志查询工具")
    parser.add_argument("--secret-id", default=None, help="腾讯云 SecretId（也可通过环境变量 CLS_SECRET_ID 设置）")
    parser.add_argument("--secret-key", default=None, help="腾讯云 SecretKey（也可通过环境变量 CLS_SECRET_KEY 设置）")
    parser.add_argument("--endpoint", default=None, help="服务端点（也可通过环境变量 CLS_ENDPOINT 设置，默认 cls.internal.tencentcloudapi.com）")
    parser.add_argument("--region", default=None, help="地域（也可通过环境变量 CLS_REGION 设置，默认 ap-guangzhou）")
    parser.add_argument("--topic-id", required=True, help="日志主题 ID")
    parser.add_argument("--query", required=True, help="检索语句")
    parser.add_argument("--from", required=True, type=int, dest="from_time", help="起始时间(毫秒)")
    parser.add_argument("--to", required=True, type=int, dest="to_time", help="结束时间(毫秒)")
    parser.add_argument("--limit", type=int, default=100, help="返回条数")
    parser.add_argument("--sort", default="desc", choices=["asc", "desc"], help="排序方式")
    parser.add_argument("--highlight", action="store_true", help="高亮关键词")
    parser.add_argument("--old-analysis", action="store_true", help="使用旧的分析格式")

    args = parser.parse_args()

    # 按优先级获取配置：命令行参数 > 环境变量 > 默认值
    secret_id = _get_config(args.secret_id, "CLS_SECRET_ID")
    secret_key = _get_config(args.secret_key, "CLS_SECRET_KEY")
    endpoint = _get_config(args.endpoint, "CLS_ENDPOINT", "cls.internal.tencentcloudapi.com")
    region = _get_config(args.region, "CLS_REGION", "ap-guangzhou")

    # 校验必填参数
    if not secret_id:
        parser.error("SecretId 未提供，请通过 --secret-id 参数或 CLS_SECRET_ID 环境变量设置")
    if not secret_key:
        parser.error("SecretKey 未提供，请通过 --secret-key 参数或 CLS_SECRET_KEY 环境变量设置")

    client = CLSClient(
        secret_id=secret_id,
        secret_key=secret_key,
        endpoint=endpoint,
        region=region
    )

    result = client.search_log(
        topic_id=args.topic_id,
        query=args.query,
        from_time=args.from_time,
        to_time=args.to_time,
        limit=args.limit,
        sort=args.sort,
        highlight=args.highlight,
        use_new_analysis=not args.old_analysis
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
