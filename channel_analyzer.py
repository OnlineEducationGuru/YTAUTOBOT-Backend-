"""
Channel Analyzer - Analyzes channel name/niche to generate relevant content
"""

import g4f
import json


class ChannelAnalyzer:
    def analyze(self, channel_name):
        """Analyze channel and suggest content strategy"""
        try:
            prompt = f"""
Analyze this YouTube/Facebook channel name: "{channel_name}"

Based on the name, determine:
1. What niche/category does this channel belong to?
2. What type of content should they create?
3. Suggest 10 trending video topics in Hindi
4. Best hashtags for this niche
5. Target audience

Return JSON:
{{
    "detected_niche": "niche name",
    "content_type": "description of content type",
    "suggested_topics": ["topic1 in Hindi", "topic2", ...],
    "hashtags": ["#tag1", "#tag2", ...],
    "target_audience": "description",
    "posting_strategy": "how many videos per day and best times"
}}
"""
            response = g4f.ChatCompletion.create(
                model=g4f.models.gpt_4,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            import re
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```\w*\n?', '', response)
                response = re.sub(r'\n?```$', '', response)
            
            return json.loads(response)
        except:
            return {
                "detected_niche": "general",
                "suggested_topics": [
                    "मोटिवेशनल कहानी",
                    "जीवन बदलने वाली बातें",
                    "Amazing Facts हिंदी में"
                ],
                "hashtags": ["#hindi", "#viral", "#trending"]
            }