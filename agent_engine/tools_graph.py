import yfinance as yf
import pandas as pd
from crewai.tools import BaseTool
from typing import Type, List, Dict
from pydantic import BaseModel, Field

class RelationshipInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol (e.g., 'AAPL', '005930.KS')")

class RelationshipTool(BaseTool):
    name: str = "GraphRAG Network Tool"
    description: str = "Analyzes the stock's relationship network (competitors, supply chain, key partners) and their recent performance to identify ripple effects."
    args_schema: Type[BaseModel] = RelationshipInput

    def _run(self, ticker: str) -> str:
        try:
            # 1. Identify Key Relationships (simulated Knowledge Graph)
            relationships = self._get_related_entities(ticker)
            
            if not relationships:
                return f"No network data available for {ticker}. (GraphRAG: Node isolated)"
            
            # 2. Fetch Market Data for Related Entities
            network_impact = []
            
            for entity in relationships:
                rel_ticker = entity["ticker"]
                rel_type = entity["type"]
                rel_name = entity["name"]
                
                # Fetch recent return (1 week)
                try:
                    tick = yf.Ticker(rel_ticker)
                    hist = tick.history(period="5d")
                    if len(hist) >= 2:
                        last = hist["Close"].iloc[-1]
                        first = hist["Close"].iloc[0]
                        ret_1w = (last / first - 1) * 100
                        
                        # Determine signal
                        signal = "Neutral"
                        if ret_1w > 3: signal = "Bullish"
                        elif ret_1w < -3: signal = "Bearish"
                        
                        network_impact.append({
                            "name": rel_name,
                            "type": rel_type,
                            "ret_1w": ret_1w,
                            "signal": signal
                        })
                except:
                    continue

            # 3. Synthesize "Network Effect" Report
            if not network_impact:
                return f"Found {len(relationships)} related entities but failed to fetch market data."
            
            # Calculate Network Momentum
            avg_ret = sum(x["ret_1w"] for x in network_impact) / len(network_impact)
            
            report = f"""
[GraphRAG Network Analysis for {ticker}]

🕸️ Network Centrality Scan:
- Identified {len(network_impact)} key nodes in the value chain.
- Network Sentiment: {'POSITIVE' if avg_ret > 1 else 'NEGATIVE' if avg_ret < -1 else 'NEUTRAL'} (Avg Peer Return: {avg_ret:+.2f}%)

🔗 Key Ripple Effects (Competitors & Partners):
"""
            for node in network_impact:
                icon = "🟢" if node["ret_1w"] > 0 else "🔴"
                report += f"- {icon} {node['type']} [{node['name']}]: {node['ret_1w']:+.2f}% ({node['signal']})\n"
                
            report += f"\n💡 Insight: {self._generate_insight(avg_ret, ticker)}"
            
            return report

        except Exception as e:
            return f"Error in GraphRAG Tool: {str(e)}"

    def _get_related_entities(self, ticker: str) -> List[Dict]:
        """
        Simulates a Knowledge Graph lookup.
        In a real production environment, this would query a Neo4j/Vector DB.
        """
        # Dictionary of "Ego Networks" for major stocks
        # Format: Ticker -> List of {ticker, name, type}
        
        # Normalize ticker
        t = ticker.upper()
        
        # 1. KOREA STOCKS
        if "005930" in t: # Samsung Electronics
            return [
                {"ticker": "000660.KS", "name": "SK Hynix", "type": "Competitor/Peer"},
                {"ticker": "AAPL", "name": "Apple", "type": "Major Client"},
                {"ticker": "NVDA", "name": "NVIDIA", "type": "Major Client"},
                {"ticker": "TSM", "name": "TSMC", "type": "Rival Foundry"}
            ]
        elif "000660" in t: # SK Hynix
            return [
                {"ticker": "005930.KS", "name": "Samsung Elec", "type": "Competitor"},
                {"ticker": "NVDA", "name": "NVIDIA", "type": "Key Partner (HBM)"},
                {"ticker": "MU", "name": "Micron", "type": "Competitor"}
            ]
        elif "035420" in t: # Naver
            return [
                {"ticker": "035720.KQ", "name": "Kakao", "type": "Competitor"},
                {"ticker": "GOOGL", "name": "Google", "type": "Global Peer"}
            ]
        elif "035720" in t: # Kakao
            return [
                {"ticker": "035420.KS", "name": "Naver", "type": "Competitor"}
            ]
        elif "005380" in t: # Hyundai Motor
            return [
                {"ticker": "000270.KS", "name": "Kia", "type": "Group Affiliate"},
                {"ticker": "TSLA", "name": "Tesla", "type": "Global Competitor"},
                {"ticker": "TM", "name": "Toyota", "type": "Global Competitor"}
            ]
            
        # 2. US STOCKS
        if "AAPL" in t:
            return [
                {"ticker": "MSFT", "name": "Microsoft", "type": "Tech Peer"},
                {"ticker": "GOOGL", "name": "Alphabet", "type": "Competitor"},
                {"ticker": "005930.KS", "name": "Samsung", "type": "Supplier/Rival"}
            ]
        elif "NVDA" in t:
            return [
                {"ticker": "AMD", "name": "AMD", "type": "Competitor"},
                {"ticker": "INTC", "name": "Intel", "type": "Competitor"},
                {"ticker": "TSM", "name": "TSMC", "type": "Supplier"},
                {"ticker": "000660.KS", "name": "SK Hynix", "type": "HBM Partner"}
            ]
        elif "TSLA" in t:
            return [
                {"ticker": "RIVN", "name": "Rivian", "type": "Competitor"},
                {"ticker": "BYDDF", "name": "BYD", "type": "Global Rival"},
                {"ticker": "006400.KS", "name": "Samsung SDI", "type": "Battery Supplier"}
            ]
            
        return [] # Return empty if not in hardcoded knowledge graph for now

    def _generate_insight(self, avg_ret: float, ticker: str) -> str:
        if avg_ret > 2.0:
            return f"Strong tailwind from related companies. The ecosystem around {ticker} is growing."
        elif avg_ret < -2.0:
            return f"Significant headwinds detected in the value chain. Partners/Competitors are struggling."
        else:
            return "Mixed signals from the network. No clear systematic risk or benefit detected."

# Instance
relationship_tool = RelationshipTool()
