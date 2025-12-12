#!/usr/bin/env python3
"""
Script để phân tích và visualization kết quả recommendation system
"""

import sys
import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Thêm thư mục gốc vào Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.embeddings_store import EmbeddingsStore
from processors.embeddings import EmbeddingGenerator
from processors.similarity import SimilarityCalculator
from utils.logger import get_logger

logger = get_logger(__name__)

# Set style cho plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

class RecommendationAnalyzer:
    def __init__(self):
        self.embeddings_store = EmbeddingsStore()
        self.videos = self.embeddings_store.get_all_videos()
        self.similarity_calc = SimilarityCalculator()
        
    def analyze_recommendation_quality(self, query_text, top_results, k_values=[1, 3, 5, 10]):
        """
        Phân tích chất lượng recommendation
        
        Args:
            query_text: Query string
            top_results: Top K recommended videos
            k_values: List of K values to analyze
        """
        print("\n" + "=" * 80)
        print("📊 RECOMMENDATION QUALITY ANALYSIS")
        print("=" * 80)
        
        print(f"\n🔍 Query: '{query_text}'")
        print(f"📈 Total videos in database: {len(self.videos)}")
        print(f"✅ Top K results: {len(top_results)}")
        
        # 1. Similarity Score Distribution
        print("\n" + "-" * 80)
        print("1️⃣ SIMILARITY SCORE DISTRIBUTION")
        print("-" * 80)
        
        similarity_scores = [v['similarity_score'] for v in top_results]
        
        print(f"   Mean Similarity:     {np.mean(similarity_scores):.4f}")
        print(f"   Median Similarity:   {np.median(similarity_scores):.4f}")
        print(f"   Std Dev:             {np.std(similarity_scores):.4f}")
        print(f"   Min Score:           {np.min(similarity_scores):.4f}")
        print(f"   Max Score:           {np.max(similarity_scores):.4f}")
        
        # Score ranges
        high_sim = sum(1 for s in similarity_scores if s >= 0.7)
        med_sim = sum(1 for s in similarity_scores if 0.4 <= s < 0.7)
        low_sim = sum(1 for s in similarity_scores if s < 0.4)
        
        print(f"\n   High Similarity (≥0.7):   {high_sim} videos ({high_sim/len(similarity_scores)*100:.1f}%)")
        print(f"   Medium Similarity (0.4-0.7): {med_sim} videos ({med_sim/len(similarity_scores)*100:.1f}%)")
        print(f"   Low Similarity (<0.4):    {low_sim} videos ({low_sim/len(similarity_scores)*100:.1f}%)")
        
        # 2. Ranking Quality Metrics
        print("\n" + "-" * 80)
        print("2️⃣ RANKING QUALITY METRICS")
        print("-" * 80)
        
        # Precision at K
        print("\n   📍 Precision@K (proportion of relevant items):")
        for k in k_values:
            if k <= len(top_results):
                top_k = top_results[:k]
                relevant = sum(1 for v in top_k if v['similarity_score'] >= 0.5)
                precision = relevant / k
                print(f"      P@{k:2d}: {precision:.3f} ({relevant}/{k} videos with similarity ≥ 0.5)")
        
        # Mean Reciprocal Rank (MRR)
        for i, video in enumerate(top_results, 1):
            if video['similarity_score'] >= 0.7:
                mrr = 1.0 / i
                print(f"\n   🎯 MRR (Mean Reciprocal Rank): {mrr:.3f}")
                print(f"      First highly relevant result at position: {i}")
                break
        
        # 3. Diversity Metrics
        print("\n" + "-" * 80)
        print("3️⃣ DIVERSITY METRICS")
        print("-" * 80)
        
        channels = [v['channel'] for v in top_results]
        unique_channels = len(set(channels))
        
        print(f"   Unique Channels:     {unique_channels}/{len(top_results)}")
        print(f"   Diversity Score:     {unique_channels/len(top_results):.2f}")
        
        # Channel distribution
        channel_counts = pd.Series(channels).value_counts()
        print(f"\n   Channel Distribution:")
        for channel, count in channel_counts.head(5).items():
            print(f"      {channel}: {count} videos")
        
        # 4. Temporal Distribution
        print("\n" + "-" * 80)
        print("4️⃣ TEMPORAL DISTRIBUTION")
        print("-" * 80)
        
        dates = [datetime.strptime(v['published_date'], '%Y-%m-%d') 
                for v in top_results if v['published_date'] != 'Unknown']
        
        if dates:
            oldest = min(dates)
            newest = max(dates)
            avg_age_days = np.mean([(datetime.now() - d).days for d in dates])
            
            print(f"   Oldest Video:        {oldest.strftime('%Y-%m-%d')} ({(datetime.now() - oldest).days} days ago)")
            print(f"   Newest Video:        {newest.strftime('%Y-%m-%d')} ({(datetime.now() - newest).days} days ago)")
            print(f"   Average Age:         {avg_age_days:.0f} days")
            
            # Recency distribution
            recent = sum(1 for d in dates if (datetime.now() - d).days <= 365)
            old = len(dates) - recent
            print(f"\n   Recent (<1 year):    {recent} videos ({recent/len(dates)*100:.1f}%)")
            print(f"   Older (>1 year):     {old} videos ({old/len(dates)*100:.1f}%)")
        
        # 5. Popularity Metrics
        print("\n" + "-" * 80)
        print("5️⃣ POPULARITY METRICS")
        print("-" * 80)
        
        view_counts = []
        for v in top_results:
            view_str = v['view_count']
            if 'M' in view_str:
                views = float(view_str.replace('M', '')) * 1_000_000
            elif 'K' in view_str:
                views = float(view_str.replace('K', '')) * 1_000
            else:
                views = float(view_str)
            view_counts.append(views)
        
        print(f"   Average Views:       {np.mean(view_counts):,.0f}")
        print(f"   Median Views:        {np.median(view_counts):,.0f}")
        print(f"   Total Views:         {np.sum(view_counts):,.0f}")
        
        # 6. Score Component Analysis
        print("\n" + "-" * 80)
        print("6️⃣ SCORE COMPONENTS BREAKDOWN")
        print("-" * 80)
        
        print(f"\n   Weight Distribution:")
        print(f"      Similarity:  70% (primary ranking factor)")
        print(f"      Popularity:  15% (view count influence)")
        print(f"      Recency:     10% (temporal relevance)")
        print(f"      Channel:      5% (source quality)")
        
        # Final scores vs similarity
        final_scores = [v['final_score'] for v in top_results]
        print(f"\n   Final Score Statistics:")
        print(f"      Mean:    {np.mean(final_scores):.4f}")
        print(f"      Median:  {np.median(final_scores):.4f}")
        print(f"      Std Dev: {np.std(final_scores):.4f}")
        
        print("\n" + "=" * 80)
    
    def generate_visualizations(self, query_text, top_results, output_dir='data/analysis'):
        """
        Tạo các biểu đồ visualization
        
        Args:
            query_text: Query string
            top_results: Top K recommended videos
            output_dir: Thư mục lưu plots
        """
        os.makedirs(output_dir, exist_ok=True)
        
        print("\n📊 Generating visualizations...")
        
        # Prepare data
        df = pd.DataFrame(top_results)
        
        # Parse view counts
        def parse_views(view_str):
            if 'M' in view_str:
                return float(view_str.replace('M', '')) * 1_000_000
            elif 'K' in view_str:
                return float(view_str.replace('K', '')) * 1_000
            return float(view_str)
        
        df['views_numeric'] = df['view_count'].apply(parse_views)
        
        # Create figure with subplots
        fig = plt.figure(figsize=(16, 12))
        
        # 1. Similarity Score Distribution
        ax1 = plt.subplot(2, 3, 1)
        sns.histplot(data=df, x='similarity_score', bins=10, kde=True, ax=ax1, color='skyblue')
        ax1.axvline(df['similarity_score'].mean(), color='red', linestyle='--', 
                   label=f'Mean: {df["similarity_score"].mean():.3f}')
        ax1.set_title('Similarity Score Distribution', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Similarity Score')
        ax1.set_ylabel('Count')
        ax1.legend()
        
        # 2. Ranking vs Similarity
        ax2 = plt.subplot(2, 3, 2)
        ax2.plot(df['rank'], df['similarity_score'], marker='o', linewidth=2, markersize=8, color='#2E86AB')
        ax2.fill_between(df['rank'], df['similarity_score'], alpha=0.3, color='#2E86AB')
        ax2.set_title('Similarity Score by Rank', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Rank')
        ax2.set_ylabel('Similarity Score')
        ax2.grid(True, alpha=0.3)
        ax2.invert_xaxis()
        
        # 3. Channel Distribution
        ax3 = plt.subplot(2, 3, 3)
        channel_counts = df['channel'].value_counts().head(10)
        colors = sns.color_palette('husl', len(channel_counts))
        ax3.barh(range(len(channel_counts)), channel_counts.values, color=colors)
        ax3.set_yticks(range(len(channel_counts)))
        ax3.set_yticklabels(channel_counts.index, fontsize=9)
        ax3.set_title('Top Channels in Results', fontsize=12, fontweight='bold')
        ax3.set_xlabel('Number of Videos')
        ax3.invert_yaxis()
        
        # 4. Views vs Similarity
        ax4 = plt.subplot(2, 3, 4)
        scatter = ax4.scatter(df['similarity_score'], df['views_numeric'], 
                            s=100, alpha=0.6, c=df['rank'], cmap='YlOrRd_r')
        ax4.set_title('Views vs Similarity Score', fontsize=12, fontweight='bold')
        ax4.set_xlabel('Similarity Score')
        ax4.set_ylabel('View Count')
        ax4.set_yscale('log')
        plt.colorbar(scatter, ax=ax4, label='Rank')
        
        # 5. Final Score vs Similarity Score
        ax5 = plt.subplot(2, 3, 5)
        ax5.scatter(df['similarity_score'], df['final_score'], 
                   s=100, alpha=0.6, c=df['rank'], cmap='viridis')
        ax5.plot([0, 1], [0, 1], 'r--', alpha=0.5, label='y=x')
        ax5.set_title('Final Score vs Similarity Score', fontsize=12, fontweight='bold')
        ax5.set_xlabel('Similarity Score')
        ax5.set_ylabel('Final Score')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        
        # 6. Score Components Heatmap
        ax6 = plt.subplot(2, 3, 6)
        
        # Calculate component scores (approximate)
        components_data = {
            'Video': [f"#{i+1}" for i in range(min(10, len(df)))],
            'Similarity': (df['similarity_score'].head(10) * 0.70).tolist(),
            'Popularity': [(parse_views(v) / 10_000_000 * 0.15) for v in df['view_count'].head(10)],
            'Final': df['final_score'].head(10).tolist()
        }
        
        components_df = pd.DataFrame(components_data)
        components_df.set_index('Video', inplace=True)
        
        sns.heatmap(components_df.T, annot=True, fmt='.3f', cmap='RdYlGn', 
                   ax=ax6, cbar_kws={'label': 'Score'})
        ax6.set_title('Score Components Heatmap', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        # Save plot
        output_file = os.path.join(output_dir, f'recommendation_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"   ✅ Saved visualization: {output_file}")
        
        # Close plot
        plt.close()
        
        # Generate detailed report
        self._generate_detailed_report(df, query_text, output_dir)
    
    def _generate_detailed_report(self, df, query_text, output_dir):
        """Tạo báo cáo chi tiết dạng text"""
        
        report_file = os.path.join(output_dir, f'detailed_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("YOUTUBE VIDEO RECOMMENDATION SYSTEM - DETAILED ANALYSIS REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Query: {query_text}\n")
            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Results: {len(df)}\n\n")
            
            f.write("-" * 80 + "\n")
            f.write("TOP RECOMMENDED VIDEOS\n")
            f.write("-" * 80 + "\n\n")
            
            for _, row in df.iterrows():
                f.write(f"Rank #{row['rank']}: {row['title']}\n")
                f.write(f"   Channel: {row['channel']}\n")
                f.write(f"   Similarity: {row['similarity_score']:.4f}\n")
                f.write(f"   Final Score: {row['final_score']:.4f}\n")
                f.write(f"   Views: {row['view_count']}\n")
                f.write(f"   Published: {row['published_date']}\n")
                f.write(f"   URL: {row['url']}\n")
                f.write(f"   Relevance: {row['why_relevant']}\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("STATISTICAL SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Similarity Scores:\n")
            f.write(f"   Mean:   {df['similarity_score'].mean():.4f}\n")
            f.write(f"   Median: {df['similarity_score'].median():.4f}\n")
            f.write(f"   Std:    {df['similarity_score'].std():.4f}\n")
            f.write(f"   Min:    {df['similarity_score'].min():.4f}\n")
            f.write(f"   Max:    {df['similarity_score'].max():.4f}\n\n")
            
            f.write(f"Channel Diversity: {df['channel'].nunique()}/{len(df)} unique channels\n\n")
            
            f.write("=" * 80 + "\n")
        
        print(f"   ✅ Saved detailed report: {report_file}")

def main():
    """Main function"""
    print("\n" + "=" * 80)
    print("YOUTUBE RECOMMENDATION SYSTEM - COMPREHENSIVE ANALYSIS")
    print("=" * 80)
    
    # Check if we have recent results
    if not os.path.exists('search_results.json'):
        print("\n❌ No search results found!")
        print("Please run a search first:")
        print("   python scripts/search_videos.py -q \"your query\" -o search_results.json")
        return 1
    
    # Load results
    with open('search_results.json', 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    if not results:
        print("\n❌ Empty results file!")
        return 1
    
    # Extract query from results (use first result's context)
    query_text = "Recent search query"  # Default
    
    # Initialize analyzer
    analyzer = RecommendationAnalyzer()
    
    # Run analysis
    analyzer.analyze_recommendation_quality(query_text, results)
    
    # Generate visualizations
    analyzer.generate_visualizations(query_text, results)
    
    print("\n✅ Analysis complete!")
    print("\n📁 Check the following files:")
    print("   - data/analysis/*.png  (visualizations)")
    print("   - data/analysis/*.txt  (detailed reports)")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)