"""Security Headers Middleware 測試"""

import pytest
from httpx import AsyncClient

from app.middleware.security_headers import CONTENT_SECURITY_POLICY


@pytest.mark.asyncio
async def test_security_headers_on_api_response(client: AsyncClient):
    """測試 API 響應包含所有安全 Headers"""
    response = await client.get("/health")
    assert response.status_code == 200

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
    assert response.headers["Content-Security-Policy"] == CONTENT_SECURITY_POLICY


@pytest.mark.asyncio
async def test_csp_blocks_external_resources(client: AsyncClient):
    """測試 CSP 採最嚴格策略（default-src 'none'）"""
    response = await client.get("/")
    csp = response.headers["Content-Security-Policy"]

    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    # 允許直接瀏覽 /uploads 圖片
    assert "img-src 'self'" in csp


@pytest.mark.asyncio
async def test_docs_exempt_from_csp(client: AsyncClient):
    """測試 /docs 豁免 CSP（Swagger UI 需載入 CDN 腳本），但仍有其他安全 Headers"""
    response = await client.get("/docs")
    assert response.status_code == 200

    assert "Content-Security-Policy" not in response.headers
    # 其他安全 Headers 仍須存在
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


@pytest.mark.asyncio
async def test_security_headers_on_error_response(client: AsyncClient):
    """測試錯誤響應（404）也包含安全 Headers"""
    response = await client.get("/api/nonexistent-path")
    assert response.status_code == 404

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
