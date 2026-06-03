from langchain.tools import tool
from app.db import graph_db, settings
import requests


BOCHA_API_KEY = settings.BOCHA_API_KEY
@tool
def news_scraper_tool(query: str, count: int = 10) -> str:
    """
    使用Bocha News API 进行新闻爬取。

    参数:
    - query: 搜索关键词
    - count: 返回的搜索结果数量

    返回:
    - 新闻结果的详细信息，包括新闻标题、URL、摘要、来源、发布时间等。
    """
    
    url = 'https://api.bochaai.com/v1/web-search'
    headers = {
        'Authorization': f'Bearer {BOCHA_API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        "query": query,
        "freshness": "oneMonth",
        "summary": True,
        "count": count,
        "type": "news"
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        json_response = response.json()
        try:
            if json_response["code"] != 200 or not json_response["data"]:
                return "新闻API请求失败，原因是: 未知错误"
            
            webpages = json_response["data"]["webPages"]["value"]
            if not webpages:
                return "未找到相关新闻。"
            formatted_results = ""
            for idx, page in enumerate(webpages, start=1):
                formatted_results += (
                    f"新闻 {idx}:\n"
                    f"标题: {page['name']}\n"
                    f"URL: {page['url']}\n"
                    f"摘要: {page['summary']}\n"
                    f"来源: {page['siteName']}\n"
                    f"发布时间: {page.get('datePublished', '未知')}\n\n"
                )
            return formatted_results.strip()
        except Exception as e:
            return f"新闻API请求失败，原因是：搜索结果解析失败 {str(e)}"
    else:
        return f"新闻API请求失败，状态码: {response.status_code}, 错误信息: {response.text}"

@tool
def bocha_websearch_tool(query: str, count: int = 10) -> str:
    """
    使用Bocha Web Search API 进行网页搜索。

    参数:
    - query: 搜索关键词
    - freshness: 搜索的时间范围
    - summary: 是否显示文本摘要
    - count: 返回的搜索结果数量

    返回:
    - 搜索结果的详细信息，包括网页标题、网页URL、网页摘要、网站名称、网站Icon、网页发布时间等。
    """
    
    url = 'https://api.bochaai.com/v1/web-search'
    headers = {
        'Authorization': f'Bearer {BOCHA_API_KEY}',  # 请替换为你的API密钥
        'Content-Type': 'application/json'
    }
    data = {
        "query": query,
        "freshness": "noLimit", # 搜索的时间范围，例如 "oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"
        "summary": True, # 是否返回长文本摘要
        "count": count
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        json_response = response.json()
        try:
            if json_response["code"] != 200 or not json_response["data"]:
                return "搜索API请求失败，原因是: 未知错误"
            
            webpages = json_response["data"]["webPages"]["value"]
            if not webpages:
                return "未找到相关结果。"
            formatted_results = ""
            for idx, page in enumerate(webpages, start=1):
                formatted_results += (
                    f"引用: {idx}\n"
                    f"标题: {page['name']}\n"
                    f"URL: {page['url']}\n"
                    f"摘要: {page['summary']}\n"
                    f"网站名称: {page['siteName']}\n"
                    f"网站图标: {page['siteIcon']}\n"
                    f"发布时间: {page['dateLastCrawled']}\n\n"
                )
            return formatted_results.strip()
        except Exception as e:
            return f"搜索API请求失败，原因是：搜索结果解析失败 {str(e)}"
    else:
        return f"搜索API请求失败，状态码: {response.status_code}, 错误信息: {response.text}"


@tool
async def neo4j_graph_reason(query: str) -> str:
    """查询Neo4j知识图谱中的公司信息、事件、专利和投资关系"""
    try:
        company = graph_db.query(
            "MATCH (c:Company) WHERE c.name CONTAINS $name RETURN c.name as name LIMIT 1",
            {"name": query}
        )
        if not company:
            return f"未在知识图谱中找到与'{query}'相关的公司"

        company_name = company[0]["name"]

        events = graph_db.query(
            "MATCH (c:Company {name: $name})-[r:HAPPEN]->(e:EventType) RETURN e.name as event, r.title as detail LIMIT 10",
            {"name": company_name}
        )
        patents = graph_db.query(
            "MATCH (c:Company {name: $name})-[r:HAVE]->(p:Patent) RETURN p.name as patent LIMIT 10",
            {"name": company_name}
        )
        investors = graph_db.query(
            "MATCH (i:Investor)-[r:INVEST]->(c:Company {name: $name}) RETURN i.name as investor LIMIT 10",
            {"name": company_name}
        )

        result = f"公司: {company_name}\n"
        if events:
            result += "\n相关事件:\n"
            for ev in events:
                detail = ev.get("detail") or ""
                result += f"  - {ev['event']}" + (f" ({detail})" if detail else "") + "\n"
        if patents:
            result += "\n相关专利:\n"
            for p in patents:
                result += f"  - {p['patent']}\n"
        if investors:
            result += "\n投资方:\n"
            for inv in investors:
                result += f"  - {inv['investor']}\n"
        if not events and not patents and not investors:
            result += "\n暂无关联事件、专利或投资信息"

        return result
    except Exception as exc:
        return f"图查询失败: {exc}"

@tool
def generate_pdf(report_content: str, filename: str = "report.pdf") -> str:
    """生成PDF报告"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT

        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        styles = getSampleStyleSheet()
        cn_style = ParagraphStyle('CN', parent=styles['Normal'], fontName='STSong-Light', fontSize=10, leading=16)
        title_style = ParagraphStyle('CNTitle', parent=styles['Title'], fontName='STSong-Light', fontSize=16, alignment=TA_CENTER)
        right_style = ParagraphStyle('CNRight', parent=styles['Normal'], fontName='STSong-Light', fontSize=8, alignment=TA_RIGHT)

        doc = SimpleDocTemplate(filename, pagesize=A4)
        story = []
        story.append(Paragraph("AetherReport 研究报告", title_style))
        story.append(Spacer(1, 12))
        for line in report_content.split("\n"):
            story.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), cn_style))
        story.append(Spacer(1, 12))
        now = __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')
        story.append(Paragraph(f"生成时间：{now}", right_style))
        doc.build(story)
        return f"PDF生成成功: {filename}"
    except Exception as e:
        fallback_path = filename.replace(".pdf", ".txt")
        with open(fallback_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        return f"PDF生成失败({e})，已回退文本: {fallback_path}"


_bocha_search = bocha_websearch_tool.func
_neo4j_reason = neo4j_graph_reason.coroutine
_generate_pdf = generate_pdf.func