#!/usr/bin/env python3
"""
Tweet Metrics Logger

This module tracks and logs metrics about tweet generation efficiency, 
including how many tweets are generated, filtered, and ultimately used.
"""

import os
import json
import time
from datetime import datetime
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import math

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('tweet_metrics')

# Base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS_DIR = os.path.join(BASE_DIR, "metrics")
GRAPHS_DIR = os.path.join(METRICS_DIR, "graphs")

# Ensure metrics directories exist
Path(METRICS_DIR).mkdir(exist_ok=True)
Path(GRAPHS_DIR).mkdir(exist_ok=True)

class TweetMetricsTracker:
    """
    Tracks and logs metrics related to tweet generation and posting efficiency.
    """
    
    def __init__(self):
        """Initialize the metrics tracker with default values."""
        # Today's date for file naming
        self.date = datetime.now().strftime("%Y%m%d")
        self.metrics_file = os.path.join(METRICS_DIR, f"tweet_metrics_{self.date}.json")
        
        # Initialize metrics
        self.metrics = {
            "date": self.date,
            "generation": {
                "started_at": None,
                "completed_at": None,
                "duration_seconds": 0,
                "initial_pool_size": 0,
                "unique_tweets_generated": 0,
                "duplicates_filtered": 0,
                "uniqueness_threshold": 0.0,
                "temperature_settings": {},
                "tweet_types": {
                    "article": 0,
                    "signal_leak": 0,
                    "commentary": 0,
                    "absurd_take": 0
                }
            },
            "posting": {
                "platforms": {}
            },
            "efficiency": {
                "generation_ratio": 0.0,  # ratio of unique tweets to total attempted
                "posting_ratio": 0.0,     # ratio of posted tweets to unique generated
                "overall_efficiency": 0.0  # ratio of posted tweets to total attempted
            }
        }
        
        # Load existing metrics if file exists
        self._load_metrics()
    
    def _load_metrics(self):
        """Load existing metrics from the JSON file if it exists."""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, 'r') as f:
                    self.metrics = json.load(f)
                logger.info(f"Loaded existing metrics from {self.metrics_file}")
            except Exception as e:
                logger.error(f"Error loading metrics: {e}")
    
    def save_metrics(self):
        """Save current metrics to the JSON file."""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
            logger.info(f"Saved metrics to {self.metrics_file}")
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
    
    def log_generation_start(self, pool_size, uniqueness_threshold, temperature_settings=None):
        """
        Log the start of tweet generation.
        
        Args:
            pool_size: Size of the initial pool to generate
            uniqueness_threshold: Threshold used for similarity detection
            temperature_settings: Dictionary of temperature settings for different tweet types
        """
        self.metrics["generation"]["started_at"] = datetime.now().isoformat()
        self.metrics["generation"]["initial_pool_size"] = pool_size
        self.metrics["generation"]["uniqueness_threshold"] = uniqueness_threshold
        
        if temperature_settings:
            self.metrics["generation"]["temperature_settings"] = temperature_settings
        
        self.save_metrics()
    
    def log_generation_complete(self, unique_tweets, duplicates_filtered, tweet_type_counts=None):
        """
        Log the completion of tweet generation.
        
        Args:
            unique_tweets: Number of unique tweets successfully generated
            duplicates_filtered: Number of tweets filtered out as duplicates
            tweet_type_counts: Dictionary with counts of each tweet type generated
        """
        self.metrics["generation"]["completed_at"] = datetime.now().isoformat()
        
        # Calculate duration
        if self.metrics["generation"]["started_at"]:
            start = datetime.fromisoformat(self.metrics["generation"]["started_at"])
            end = datetime.fromisoformat(self.metrics["generation"]["completed_at"])
            duration = (end - start).total_seconds()
            self.metrics["generation"]["duration_seconds"] = duration
        
        self.metrics["generation"]["unique_tweets_generated"] = unique_tweets
        self.metrics["generation"]["duplicates_filtered"] = duplicates_filtered
        
        # Track tweet types if provided
        if tweet_type_counts:
            for tweet_type, count in tweet_type_counts.items():
                if tweet_type in self.metrics["generation"]["tweet_types"]:
                    self.metrics["generation"]["tweet_types"][tweet_type] = count
        
        # Calculate efficiency metrics
        total_attempted = unique_tweets + duplicates_filtered
        if total_attempted > 0:
            self.metrics["efficiency"]["generation_ratio"] = unique_tweets / total_attempted
        
        self.save_metrics()
    
    def log_posting_results(self, platform, attempted, posted, similarity_threshold):
        """
        Log the results of posting tweets to a specific platform.
        
        Args:
            platform: The platform name (x, bluesky)
            attempted: Number of tweets attempted to post
            posted: Number of tweets successfully posted
            similarity_threshold: Threshold used for similarity detection
        """
        # Initialize platform if not exists
        if platform not in self.metrics["posting"]["platforms"]:
            self.metrics["posting"]["platforms"][platform] = {
                "attempted": 0,
                "posted": 0,
                "similarity_threshold": 0.0,
                "time": datetime.now().isoformat()
            }
        
        # Update platform metrics
        self.metrics["posting"]["platforms"][platform]["attempted"] = attempted
        self.metrics["posting"]["platforms"][platform]["posted"] = posted
        self.metrics["posting"]["platforms"][platform]["similarity_threshold"] = similarity_threshold
        self.metrics["posting"]["platforms"][platform]["time"] = datetime.now().isoformat()
        
        # Calculate posting efficiency metrics
        total_posted = sum(p["posted"] for p in self.metrics["posting"]["platforms"].values())
        total_attempted_posts = sum(p["attempted"] for p in self.metrics["posting"]["platforms"].values())
        
        if self.metrics["generation"]["unique_tweets_generated"] > 0:
            self.metrics["efficiency"]["posting_ratio"] = total_posted / total_attempted_posts if total_attempted_posts > 0 else 0
        
        # Overall efficiency (from generation to posting)
        total_generation_attempts = self.metrics["generation"]["unique_tweets_generated"] + self.metrics["generation"]["duplicates_filtered"]
        if total_generation_attempts > 0:
            self.metrics["efficiency"]["overall_efficiency"] = total_posted / total_generation_attempts
        
        self.save_metrics()
    
    def generate_daily_report(self):
        """
        Generate a text report summarizing the day's metrics.
        
        Returns:
            str: A formatted report string
        """
        report = []
        report.append(f"TWEET METRICS REPORT - {self.date}")
        report.append("=" * 40)
        
        # Generation metrics
        gen = self.metrics["generation"]
        report.append("\nGENERATION METRICS:")
        report.append(f"Duration: {gen['duration_seconds']:.2f} seconds")
        report.append(f"Pool Size: {gen['initial_pool_size']}")
        report.append(f"Unique Tweets: {gen['unique_tweets_generated']}")
        report.append(f"Duplicates Filtered: {gen['duplicates_filtered']}")
        
        # Tweet type breakdown
        report.append("\nTWEET TYPE BREAKDOWN:")
        for tweet_type, count in gen["tweet_types"].items():
            report.append(f"{tweet_type.capitalize()}: {count}")
        
        # Posting metrics
        report.append("\nPOSTING METRICS:")
        for platform, metrics in self.metrics["posting"]["platforms"].items():
            report.append(f"{platform.upper()}:")
            report.append(f"  Attempted: {metrics['attempted']}")
            report.append(f"  Posted: {metrics['posted']}")
            post_ratio = metrics['posted'] / metrics['attempted'] if metrics['attempted'] > 0 else 0
            report.append(f"  Success Rate: {post_ratio:.1%}")
        
        # Efficiency metrics
        eff = self.metrics["efficiency"]
        report.append("\nEFFICIENCY METRICS:")
        report.append(f"Generation Efficiency: {eff['generation_ratio']:.1%}")
        report.append(f"Posting Efficiency: {eff['posting_ratio']:.1%}")
        report.append(f"Overall Efficiency: {eff['overall_efficiency']:.1%}")
        
        # Summary
        total_generated = gen['unique_tweets_generated'] + gen['duplicates_filtered']
        report.append("\nSUMMARY:")
        report.append(f"Needed to generate {total_generated} tweets to get {gen['unique_tweets_generated']} unique ones")
        
        total_posted = sum(p["posted"] for p in self.metrics["posting"]["platforms"].values())
        report.append(f"Posted {total_posted} tweets across all platforms")
        
        if total_generated > 0:
            report.append(f"Overall Yield: {total_posted / total_generated:.1%}")
        
        return "\n".join(report)
    
    def plot_metrics_history(self, days=30):
        """
        Generate plots visualizing historical metrics trends.
        
        Args:
            days: Number of days of history to include
        
        Returns:
            str: Path to the generated graph image
        """
        try:
            # Import required visualization packages
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend
            
            # Collect metrics from past X days
            metrics_data = []
            for i in range(days):
                date = (datetime.now() - pd.Timedelta(days=i)).strftime("%Y%m%d")
                metrics_file = os.path.join(METRICS_DIR, f"tweet_metrics_{date}.json")
                
                if os.path.exists(metrics_file):
                    try:
                        with open(metrics_file, 'r') as f:
                            day_metrics = json.load(f)
                            metrics_data.append(day_metrics)
                    except Exception as e:
                        logger.error(f"Error loading metrics for {date}: {e}")
            
            if not metrics_data:
                logger.warning("No historical metrics data found")
                return None
            
            # Create pandas DataFrame for easier analysis
            df_list = []
            for m in metrics_data:
                date = m.get("date", "unknown")
                
                # Generation metrics
                gen = m.get("generation", {})
                unique_tweets = gen.get("unique_tweets_generated", 0)
                duplicates = gen.get("duplicates_filtered", 0)
                total_generated = unique_tweets + duplicates
                
                # Posting metrics
                platforms = m.get("posting", {}).get("platforms", {})
                total_posted = sum(p.get("posted", 0) for p in platforms.values())
                
                # Efficiency metrics
                generation_ratio = unique_tweets / total_generated if total_generated > 0 else 0
                overall_efficiency = total_posted / total_generated if total_generated > 0 else 0
                
                df_list.append({
                    "date": date,
                    "unique_tweets": unique_tweets,
                    "duplicates": duplicates,
                    "total_generated": total_generated,
                    "total_posted": total_posted,
                    "generation_ratio": generation_ratio,
                    "overall_efficiency": overall_efficiency
                })
            
            df = pd.DataFrame(df_list)
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
            df = df.sort_values("date")
            
            # Create plot
            fig, axes = plt.subplots(2, 1, figsize=(10, 12), dpi=100)
            
            # Plot 1: Generation counts
            ax1 = axes[0]
            ax1.bar(df["date"], df["total_generated"], color="skyblue", label="Total Generated")
            ax1.bar(df["date"], df["unique_tweets"], color="darkblue", label="Unique Tweets")
            
            # Add second Y axis for efficiency
            ax1_eff = ax1.twinx()
            ax1_eff.plot(df["date"], df["generation_ratio"] * 100, color="red", marker="o", label="Generation Efficiency (%)")
            
            ax1.set_title("Tweet Generation History")
            ax1.set_xlabel("Date")
            ax1.set_ylabel("Number of Tweets")
            ax1_eff.set_ylabel("Efficiency (%)")
            
            # Combine legends
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax1_eff.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
            
            # Format date axis
            ax1.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%m/%d'))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
            
            # Plot 2: Posting efficiency 
            ax2 = axes[1]
            ax2.bar(df["date"], df["unique_tweets"], color="darkblue", label="Unique Generated")
            ax2.bar(df["date"], df["total_posted"], color="green", label="Actually Posted")
            
            # Add second Y axis for overall efficiency
            ax2_eff = ax2.twinx()
            ax2_eff.plot(df["date"], df["overall_efficiency"] * 100, color="purple", marker="o", label="Overall Efficiency (%)")
            
            ax2.set_title("Tweet Posting Efficiency")
            ax2.set_xlabel("Date")
            ax2.set_ylabel("Number of Tweets")
            ax2_eff.set_ylabel("Efficiency (%)")
            
            # Combine legends
            lines1, labels1 = ax2.get_legend_handles_labels()
            lines2, labels2 = ax2_eff.get_legend_handles_labels()
            ax2.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
            
            # Format date axis
            ax2.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%m/%d'))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
            
            # Adjust layout and save
            plt.tight_layout()
            graph_path = os.path.join(GRAPHS_DIR, f"tweet_metrics_history_{self.date}.png")
            plt.savefig(graph_path)
            plt.close()
            
            logger.info(f"Generated metrics history graph at {graph_path}")
            return graph_path
            
        except ImportError as e:
            logger.error(f"Error importing visualization libraries: {e}")
            logger.error("Please install matplotlib and pandas to generate graphs")
            return None
        except Exception as e:
            logger.error(f"Error generating metrics history plot: {e}")
            return None


# Function to get the current metrics tracker instance
def get_metrics_tracker():
    """Get a TweetMetricsTracker instance for the current day."""
    return TweetMetricsTracker()


if __name__ == "__main__":
    # When run directly, generate reports for the current day
    tracker = get_metrics_tracker()
    
    # Generate and print daily report
    report = tracker.generate_daily_report()
    print(report)
    
    # Save report to file
    report_file = os.path.join(METRICS_DIR, f"tweet_metrics_report_{tracker.date}.txt")
    try:
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"Report saved to {report_file}")
    except Exception as e:
        print(f"Error saving report: {e}")
    
    # Generate history graph if possible
    try:
        graph_path = tracker.plot_metrics_history()
        if graph_path:
            print(f"History graph saved to {graph_path}")
    except Exception as e:
        print(f"Error generating history graph: {e}")