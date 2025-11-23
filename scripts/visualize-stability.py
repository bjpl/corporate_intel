#!/usr/bin/env python3
"""
Generate ASCII charts for stability monitoring data
Creates visual representations of time-series performance data
"""

import json
import statistics
from pathlib import Path

METRICS_FILE = Path("C:/Users/brand/Development/Project_Workspace/active-development/corporate_intel/docs/deployment/stability-report-day3.json")

def create_ascii_chart(data, width=60, height=10, title=""):
    """Create simple ASCII line chart"""
    if not data:
        return "No data"

    min_val = min(data)
    max_val = max(data)
    range_val = max_val - min_val if max_val != min_val else 1

    chart = []
    chart.append(f"\n{title}")
    chart.append("=" * width)

    # Create chart rows
    for i in range(height, 0, -1):
        threshold = min_val + (range_val * i / height)
        row = f"{threshold:6.2f} │"

        for value in data:
            if value >= threshold:
                row += "█"
            else:
                row += " "

        chart.append(row)

    # X-axis
    chart.append("       └" + "─" * len(data))
    chart.append(f"       Min: {min_val:.2f}  Max: {max_val:.2f}  Avg: {statistics.mean(data):.2f}")

    return "\n".join(chart)

def create_histogram(data, bins=10, width=50, title=""):
    """Create ASCII histogram"""
    if not data:
        return "No data"

    min_val = min(data)
    max_val = max(data)
    range_val = max_val - min_val if max_val != min_val else 1
    bin_width = range_val / bins

    # Count values in each bin
    bin_counts = [0] * bins
    for value in data:
        bin_idx = min(int((value - min_val) / bin_width), bins - 1)
        bin_counts[bin_idx] += 1

    max_count = max(bin_counts) if bin_counts else 1

    chart = []
    chart.append(f"\n{title}")
    chart.append("=" * width)

    for i in range(bins):
        bin_start = min_val + (i * bin_width)
        bin_end = bin_start + bin_width
        count = bin_counts[i]
        bar_length = int((count / max_count) * (width - 20))

        chart.append(f"{bin_start:6.2f}-{bin_end:6.2f} │{'█' * bar_length} {count}")

    return "\n".join(chart)

def generate_visualizations():
    """Generate all visualizations from monitoring data"""
    # Load data
    with open(METRICS_FILE, 'r') as f:
        data = json.load(f)

    samples = data['samples']
    analysis = data['analysis']

    # Extract time series
    response_times = [s['api_performance']['aggregate']['avg_response_time_ms'] for s in samples]
    success_rates = [s['api_performance']['aggregate']['success_rate'] for s in samples]

    # Split into segments for trend analysis
    segment_size = len(samples) // 3
    segment1 = response_times[:segment_size]
    segment2 = response_times[segment_size:2*segment_size]
    segment3 = response_times[2*segment_size:]

    print("=" * 80)
    print("STABILITY MONITORING - VISUAL ANALYSIS")
    print("=" * 80)

    # Response time over time
    print(create_ascii_chart(
        response_times,
        width=80,
        height=15,
        title="Response Time Over 1-Hour Period (120 samples @ 30s intervals)"
    ))

    # Response time distribution
    print(create_histogram(
        response_times,
        bins=15,
        width=70,
        title="Response Time Distribution (Histogram)"
    ))

    # Success rate over time
    print(create_ascii_chart(
        success_rates,
        width=80,
        height=10,
        title="Success Rate Over Time (%)"
    ))

    # Trend analysis
    print("\n" + "=" * 80)
    print("TREND ANALYSIS - Response Time by Time Segment")
    print("=" * 80)

    print(f"\nSegment 1 (Minutes 0-20):   Avg: {statistics.mean(segment1):.2f}ms  StdDev: {statistics.stdev(segment1):.2f}ms")
    print(f"Segment 2 (Minutes 20-40):  Avg: {statistics.mean(segment2):.2f}ms  StdDev: {statistics.stdev(segment2):.2f}ms")
    print(f"Segment 3 (Minutes 40-60):  Avg: {statistics.mean(segment3):.2f}ms  StdDev: {statistics.stdev(segment3):.2f}ms")

    trend = statistics.mean(segment3) - statistics.mean(segment1)
    if abs(trend) < 0.5:
        trend_status = "✅ STABLE (no significant trend)"
    elif trend > 0:
        trend_status = f"⚠️ INCREASING (+{trend:.2f}ms)"
    else:
        trend_status = f"✅ DECREASING ({trend:.2f}ms)"

    print(f"\nTrend: {trend_status}")

    # Statistics summary
    print("\n" + "=" * 80)
    print("STATISTICAL SUMMARY")
    print("=" * 80)

    stats = analysis['statistics']
    print(f"\nResponse Time:")
    print(f"  Mean:     {stats['response_time']['mean']:.2f}ms")
    print(f"  Median:   {stats['response_time']['median']:.2f}ms")
    print(f"  Std Dev:  {stats['response_time']['stdev']:.2f}ms")
    print(f"  Range:    {stats['response_time']['min']:.2f}ms - {stats['response_time']['max']:.2f}ms")

    print(f"\nSuccess Rate:")
    print(f"  Mean:     {stats['success_rate']['mean']:.2f}%")
    print(f"  Range:    {stats['success_rate']['min']:.2f}% - {stats['success_rate']['max']:.2f}%")

    # Anomalies
    print("\n" + "=" * 80)
    print(f"ANOMALIES DETECTED: {len(analysis['anomalies'])}")
    print("=" * 80)

    if analysis['anomalies']:
        for i, anomaly in enumerate(analysis['anomalies'], 1):
            severity_icon = {'critical': '🔴', 'warning': '🟡', 'info': '🔵'}.get(anomaly['severity'], '⚪')
            print(f"\n{i}. {severity_icon} {anomaly['type'].upper()}")
            print(f"   Severity: {anomaly['severity'].upper()}")
            print(f"   Message:  {anomaly['message']}")
    else:
        print("\n✅ No anomalies detected - system stable!")

    # Final verdict
    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    health_icon = "🟢" if analysis['health_status'] == 'healthy' else "🟡"
    print(f"\nHealth Status: {health_icon} {analysis['health_status'].upper()}")
    print(f"Stability Score: {max(0, 100 - len(analysis['anomalies']) * 10)}/100")

    if analysis['health_status'] == 'healthy':
        print("\n✅ System is STABLE and ready for production deployment")
    else:
        print("\n⚠️  System has minor issues - review anomalies before deployment")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    generate_visualizations()
