#!/usr/bin/env python3
"""
孫子の兵法 簡易RAGサーバー (Railway対応版)
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# FastAPIアプリケーション
app = FastAPI(
    title="孫子の兵法 RAG API",
    description="Ancient Chinese military strategy meets modern AI",
    version="1.0.0"
)

# データモデル
class QueryRequest(BaseModel):
    question: str
    max_results: int = 3

class SearchResult(BaseModel):
    title: str
    content: str
    relevance_score: float
    file_path: str

class QueryResponse(BaseModel):
    question: str
    results: List[SearchResult]
    answer: str

# 孫子の兵法データを読み込み
class SunziKnowledgeBase:
    def __init__(self, data_dir: str = "/app/data"):
        self.data_dir = Path(data_dir)
        self.documents = {}
        self.load_documents()
    
    def load_documents(self):
        """マークダウンファイルを読み込み"""
        if not self.data_dir.exists():
            print(f"Warning: Data directory {self.data_dir} not found")
            return
            
        for md_file in self.data_dir.glob("*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.documents[md_file.name] = {
                        'title': self.extract_title(content),
                        'content': content,
                        'file_path': str(md_file)
                    }
                print(f"Loaded: {md_file.name}")
            except Exception as e:
                print(f"Error loading {md_file}: {e}")
    
    def extract_title(self, content: str) -> str:
        """マークダウンからタイトルを抽出"""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return "Unknown Title"
    
    def search(self, query: str, max_results: int = 3) -> List[SearchResult]:
        """簡易検索（キーワードマッチング）"""
        results = []
        query_lower = query.lower()
        
        for filename, doc in self.documents.items():
            content_lower = doc['content'].lower()
            
            # 簡易な関連度スコア計算
            score = 0
            query_words = query_lower.split()
            
            for word in query_words:
                if word in content_lower:
                    score += content_lower.count(word)
            
            if score > 0:
                # 関連する段落を抽出
                relevant_content = self.extract_relevant_content(
                    doc['content'], query_words
                )
                
                results.append(SearchResult(
                    title=doc['title'],
                    content=relevant_content,
                    relevance_score=score,
                    file_path=filename
                ))
        
        # スコア順でソート
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:max_results]
    
    def extract_relevant_content(self, content: str, query_words: List[str]) -> str:
        """クエリに関連する内容を抽出"""
        paragraphs = content.split('\n\n')
        relevant_paragraphs = []
        
        for paragraph in paragraphs:
            paragraph_lower = paragraph.lower()
            if any(word in paragraph_lower for word in query_words):
                relevant_paragraphs.append(paragraph.strip())
        
        return '\n\n'.join(relevant_paragraphs[:3])  # 最大3段落
    
    def generate_answer(self, query: str, results: List[SearchResult]) -> str:
        """検索結果に基づく回答生成（簡易版）"""
        if not results:
            return "申し訳ございませんが、関連する情報が見つかりませんでした。"
        
        # 最も関連度の高い結果から回答を構成
        best_result = results[0]
        
        answer = f"「{best_result.title}」より：\n\n"
        answer += best_result.content[:500]  # 最初の500文字
        
        if len(results) > 1:
            answer += f"\n\n関連する他の教えもあります：{', '.join([r.title for r in results[1:]])}"
        
        return answer

# ナレッジベースの初期化
kb = SunziKnowledgeBase()

@app.get("/", response_class=HTMLResponse)
async def root():
    """ホームページ"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>孫子の兵法 RAG システム</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .header { text-align: center; margin-bottom: 30px; }
            .search-box { margin-bottom: 20px; }
            input[type="text"] { width: 70%; padding: 10px; font-size: 16px; }
            button { padding: 10px 20px; font-size: 16px; background: #007bff; color: white; border: none; cursor: pointer; }
            .result { background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #007bff; }
            .examples { background: #e9ecef; padding: 15px; margin: 20px 0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏮 孫子の兵法 RAG システム</h1>
            <p>古代中国の戦略思想をAIで検索・質問応答</p>
        </div>
        
        <div class="search-box">
            <input type="text" id="question" placeholder="質問を入力してください（例：リーダーシップで最も重要なことは？）">
            <button onclick="search()">検索</button>
        </div>
        
        <div class="examples">
            <h3>質問例：</h3>
            <ul>
                <li>「戦わずして勝つ」の意味は？</li>
                <li>リーダーシップで最も重要な要素は？</li>
                <li>ビジネス戦略の基本原則は？</li>
                <li>計画を立てる時に考慮すべきことは？</li>
            </ul>
        </div>
        
        <div id="results"></div>
        
        <script>
            async function search() {
                const question = document.getElementById('question').value;
                if (!question) return;
                
                try {
                    const response = await fetch('/search', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ question: question })
                    });
                    
                    const data = await response.json();
                    displayResults(data);
                } catch (error) {
                    document.getElementById('results').innerHTML = '<p>エラーが発生しました</p>';
                }
            }
            
            function displayResults(data) {
                const resultsDiv = document.getElementById('results');
                let html = '<h3>回答：</h3>';
                html += '<div class="result">' + data.answer.replace(/\\n/g, '<br>') + '</div>';
                
                if (data.results.length > 0) {
                    html += '<h3>関連する教え：</h3>';
                    data.results.forEach(result => {
                        html += '<div class="result">';
                        html += '<h4>' + result.title + '</h4>';
                        html += '<p>' + result.content.replace(/\\n/g, '<br>').substring(0, 300) + '...</p>';
                        html += '</div>';
                    });
                }
                
                resultsDiv.innerHTML = html;
            }
            
            // Enterキーで検索
            document.getElementById('question').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') search();
            });
        </script>
    </body>
    </html>
    """
    return html_content

@app.post("/search", response_model=QueryResponse)
async def search_knowledge(query: QueryRequest):
    """知識検索API"""
    try:
        results = kb.search(query.question, query.max_results)
        answer = kb.generate_answer(query.question, results)
        
        return QueryResponse(
            question=query.question,
            results=results,
            answer=answer
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "healthy", "documents_loaded": len(kb.documents)}

@app.get("/documents")
async def list_documents():
    """利用可能な文書一覧"""
    return {
        "documents": [
            {"filename": filename, "title": doc["title"]}
            for filename, doc in kb.documents.items()
        ]
    }

if __name__ == "__main__":
    # Railwayのポート設定
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting Sunzi RAG Server on port {port}")
    print(f"📚 Loaded {len(kb.documents)} documents")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        access_log=True
    )