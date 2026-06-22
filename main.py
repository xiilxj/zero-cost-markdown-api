import re
import urllib.parse
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests
from bs4 import BeautifulSoup
import html2text

app = FastAPI(
    title="Web to Markdown API",
    description="一个免费、零成本的网页内容抓取并转换为 Markdown 格式的 API 服务。非常适合 LLM/GPT 上下文灌入和知识库构建。",
    version="1.0.0"
)

# 允许跨域请求，方便前端和小程序调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MarkdownResponse(BaseModel):
    status: str = Field(..., description="请求状态 (success 或 error)")
    url: str = Field(..., description="原始网页的 URL")
    title: str = Field(..., description="提取出的网页标题")
    description: str = Field("", description="网页 Meta 描述信息")
    markdown: str = Field(..., description="提取并转换后的 Markdown 文本")

def clean_html(soup: BeautifulSoup) -> BeautifulSoup:
    """去除无用标签（广告、页脚、导航栏等）以实现内容降噪"""
    # 移除脚本和样式
    for element in soup(["script", "style", "noscript", "iframe", "header", "footer", "nav", "aside"]):
        element.decompose()
    
    # 移除常见的广告、弹窗或分享侧栏类标签类名
    ad_patterns = re.compile(r'ad-|popup|share|footer|header|sidebar|nav|menu', re.I)
    for tag in soup.find_all(attrs={"class": ad_patterns}):
        # 如果不是核心内容区（简单检查内容长度），则移除
        if len(tag.get_text()) < 200:
            tag.decompose()
            
    for tag in soup.find_all(attrs={"id": ad_patterns}):
        if len(tag.get_text()) < 200:
            tag.decompose()
            
    return soup

@app.get("/", summary="健康检查接口")
def read_root():
    return {
        "status": "healthy",
        "message": "Web to Markdown API 正在运行！",
        "usage": "使用 /api/to-markdown?url=网页地址 来转换内容"
    }

@app.get("/api/to-markdown", response_model=MarkdownResponse, summary="提取网页并转换为 Markdown")
def to_markdown(
    url: str = Query(..., description="需要提取的网页完整 URL"),
    include_images: bool = Query(True, description="转换后的 Markdown 是否保留图片链接"),
    timeout: int = Query(10, description="网络请求超时时间（秒）")
):
    # 验证 URL 格式
    parsed_url = urllib.parse.urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise HTTPException(status_code=400, detail="无效的 URL 格式。请提供包含 http/https 的完整链接。")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # 智能检测编码，防止中文网页乱码
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding or 'utf-8'
            
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"无法抓取目标网页，错误原因: {str(e)}")

    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")
    
    # 提取标题
    title = ""
    if soup.title:
        title = soup.title.string.strip() if soup.title.string else ""
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text().strip() if h1 else "Untitled Webpage"
        
    # 提取描述
    description = ""
    desc_meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if desc_meta and desc_meta.get("content"):
        description = desc_meta.get("content").strip()

    # 降噪清洗 HTML
    cleaned_soup = clean_html(soup)

    # 转换为 Markdown
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = not include_images
    converter.body_width = 0  # 不限制行宽，防止换行断句
    
    try:
        markdown_text = converter.handle(str(cleaned_soup))
        # 过滤掉过多连续换行
        markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转换为 Markdown 失败: {str(e)}")

    return MarkdownResponse(
        status="success",
        url=url,
        title=title,
        description=description,
        markdown=markdown_text.strip()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
