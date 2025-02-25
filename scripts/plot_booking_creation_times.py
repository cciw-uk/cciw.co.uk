#!/usr/bin/env python
"""
Script to analyze and plot booking creation times for a specified year.
Shows a timeline of bookings and calculates the maximum bookings per minute.
"""

import os
import sys
import django
import argparse
from datetime import datetime, timedelta
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncMinute, TruncDay

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cciw.settings")
django.setup()

from cciw.bookings.models import Booking


def plot_booking_creation_times(year):
    # Get all bookings created in the specified year
    year_start = datetime(year, 1, 1, tzinfo=timezone.get_current_timezone())
    year_end = datetime(year + 1, 1, 1, tzinfo=timezone.get_current_timezone())
    
    bookings = Booking.objects.filter(
        created_at__gte=year_start,
        created_at__lt=year_end
    ).order_by('created_at')
    
    if not bookings.exists():
        print(f"No bookings found for {year}")
        return
    
    # Count bookings per minute
    bookings_per_minute = (
        bookings
        .annotate(minute=TruncMinute('created_at'))
        .values('minute')
        .annotate(count=Count('id'))
        .order_by('minute')
    )
    
    # Find the maximum bookings per minute
    max_per_minute = max(bookings_per_minute, key=lambda x: x['count'])
    print(f"Maximum bookings per minute: {max_per_minute['count']} at {max_per_minute['minute']}")
    
    # Create the plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [1, 3]})
    
    # Extract data for plotting
    minutes = [b['minute'] for b in bookings_per_minute]
    counts = [b['count'] for b in bookings_per_minute]
    
    # Plot 1: Bookings per minute over time
    ax1.bar(minutes, counts, width=0.01, color='blue', alpha=0.7)
    ax1.set_title(f'Bookings Created Per Minute in {year}')
    ax1.set_ylabel('Bookings Count')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    
    # Highlight the maximum
    max_idx = counts.index(max_per_minute['count'])
    ax1.bar([minutes[max_idx]], [counts[max_idx]], width=0.01, color='red')
    ax1.annotate(f"Max: {max_per_minute['count']}", 
                xy=(minutes[max_idx], counts[max_idx]),
                xytext=(minutes[max_idx], counts[max_idx] + 1),
                arrowprops=dict(facecolor='black', shrink=0.05),
                ha='center')
    
    # Plot 2: Cumulative bookings over time
    all_dates = [b.created_at for b in bookings]
    ax2.hist(all_dates, bins=100, cumulative=True, histtype='step', linewidth=2)
    ax2.set_title(f'Cumulative Bookings in {year}')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Total Bookings')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator())
    
    # Add a grid for better readability
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(f'booking_creation_times_{year}.png')
    plt.show()
    
    # Additional analysis: Distribution of bookings by hour of day
    hour_counts = Counter([b.created_at.hour for b in bookings])
    hours = sorted(hour_counts.keys())
    hour_values = [hour_counts[h] for h in hours]
    
    plt.figure(figsize=(10, 6))
    plt.bar(hours, hour_values, color='green', alpha=0.7)
    plt.title(f'Distribution of Bookings by Hour of Day ({year})')
    plt.xlabel('Hour of Day (24h format)')
    plt.ylabel('Number of Bookings')
    plt.xticks(range(0, 24))
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(f'booking_creation_by_hour_{year}.png')
    plt.show()
    
    # Find the busiest day
    bookings_per_day = (
        bookings
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    
    if not bookings_per_day:
        print(f"No booking data available for {year}")
        return
        
    busiest_day = bookings_per_day[0]['day']
    print(f"Busiest day: {busiest_day.strftime('%Y-%m-%d')} with {bookings_per_day[0]['count']} bookings")
    
    # Zoom in on the busiest day
    busiest_day_start = datetime.combine(
        busiest_day.date(), 
        datetime.min.time(), 
        tzinfo=timezone.get_current_timezone()
    )
    busiest_day_end = busiest_day_start + timedelta(hours=12)  # First 12 hours
    
    busiest_day_bookings = bookings.filter(
        created_at__gte=busiest_day_start,
        created_at__lt=busiest_day_end
    )
    
    if busiest_day_bookings.exists():
        # Create a detailed timeline for the busiest day
        fig, ax = plt.figure(figsize=(12, 6)), plt.gca()
        
        # Plot individual booking times
        booking_times = [b.created_at for b in busiest_day_bookings]
        
        # Create a scatter plot with jitter for better visibility if times are close
        y_jitter = np.random.normal(0, 0.1, size=len(booking_times))
        ax.scatter(booking_times, y_jitter, alpha=0.7, s=50, color='blue')
        
        # Format the x-axis to show hours and minutes
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator())
        ax.xaxis.set_minor_locator(mdates.MinuteLocator(byminute=range(0, 60, 15)))
        
        # Add booking details as annotations
        for i, booking in enumerate(busiest_day_bookings):
            ax.annotate(
                f"{booking.created_at.strftime('%H:%M:%S')}",
                (booking.created_at, y_jitter[i]),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=8
            )
        
        plt.title(f'Booking Times on Busiest Day ({busiest_day.strftime("%Y-%m-%d")}) - First 12 Hours')
        plt.xlabel('Time')
        plt.ylabel('Bookings')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(f'busiest_day_booking_times_{year}.png')
        plt.show()
        
        # Also create a minute-by-minute histogram for the busiest day
        plt.figure(figsize=(12, 6))
        plt.hist(booking_times, bins=24, alpha=0.7, color='purple')
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.gca().xaxis.set_major_locator(mdates.HourLocator())
        plt.title(f'Booking Frequency on {busiest_day.strftime("%Y-%m-%d")} (First 12 Hours)')
        plt.xlabel('Time')
        plt.ylabel('Number of Bookings')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(f'busiest_day_booking_histogram_{year}.png')
        plt.show()


def main():
    parser = argparse.ArgumentParser(description='Analyze and plot booking creation times for a specific year')
    parser.add_argument('year', type=int, nargs='?', default=datetime.now().year,
                        help='Year to analyze (defaults to current year)')
    args = parser.parse_args()
    
    plot_booking_creation_times(args.year)

if __name__ == "__main__":
    main()
