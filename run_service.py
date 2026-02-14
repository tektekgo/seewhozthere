#!/usr/bin/env python3
"""
SeeWhozThere Service Runner

This script runs the face detection and recognition system continuously (24/7).
It includes auto-recovery, error handling, and graceful shutdown.

Features:
- Continuous monitoring
- Auto-restart on failure
- Graceful shutdown on SIGTERM/SIGINT
- Performance logging
- Health monitoring

Usage:
    python3 run_service.py
    
    Or as a systemd service (see install_service.sh)
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.hailo_processor_v2 import get_processor


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/seewhozthere.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('SeeWhozThere')


class ServiceRunner:
    """
    Manages the continuous operation of the SeeWhozThere service.
    """
    
    def __init__(self):
        self.processor = None
        self.running = False
        self.restart_count = 0
        self.max_restarts = 10
        self.restart_window = 300  # 5 minutes
        self.restart_times = []
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info("Service runner initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        signal_name = 'SIGTERM' if signum == signal.SIGTERM else 'SIGINT'
        logger.info(f"Received {signal_name}, shutting down gracefully...")
        self.stop()
        sys.exit(0)
    
    def _check_restart_limit(self) -> bool:
        """
        Check if we've exceeded the restart limit.
        
        Returns:
            True if we can restart, False if limit exceeded
        """
        now = time.time()
        
        # Remove old restart times outside the window
        self.restart_times = [t for t in self.restart_times if now - t < self.restart_window]
        
        # Check if we've exceeded the limit
        if len(self.restart_times) >= self.max_restarts:
            logger.error(f"Exceeded maximum restarts ({self.max_restarts}) in {self.restart_window}s window")
            return False
        
        return True
    
    def _record_restart(self):
        """Record a restart attempt"""
        self.restart_times.append(time.time())
        self.restart_count += 1
    
    def start(self):
        """Start the service"""
        if self.running:
            logger.warning("Service is already running")
            return
        
        logger.info("=" * 60)
        logger.info("SeeWhozThere Face Detection & Recognition Service")
        logger.info("=" * 60)
        logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        self.running = True
        
        while self.running:
            try:
                # Check restart limit
                if not self._check_restart_limit():
                    logger.error("Restart limit exceeded. Service will not restart automatically.")
                    logger.error("Please check the logs and restart manually.")
                    break
                
                # Create processor instance
                logger.info("Initializing processor...")
                self.processor = get_processor()
                
                # Start processing
                logger.info("Starting face detection and recognition...")
                self.processor.start()
                
                # Monitor the processor
                self._monitor_processor()
                
            except KeyboardInterrupt:
                logger.info("Service interrupted by user")
                break
                
            except Exception as e:
                logger.error(f"Unexpected error in service: {e}", exc_info=True)
                
                # Record restart and wait before retrying
                self._record_restart()
                
                if self.running:
                    logger.info("Restarting in 10 seconds...")
                    time.sleep(10)
            
            finally:
                # Clean up processor
                if self.processor:
                    try:
                        self.processor.stop()
                    except Exception as e:
                        logger.error(f"Error stopping processor: {e}")
                    self.processor = None
        
        logger.info("Service stopped")
    
    def _monitor_processor(self):
        """Monitor the processor and keep it running"""
        last_status_time = time.time()
        status_interval = 300  # Log status every 5 minutes
        
        while self.running:
            try:
                # Check if processor is still running
                if self.processor:
                    status = self.processor.get_status()
                    
                    if not status['running']:
                        logger.warning("Processor stopped unexpectedly, restarting...")
                        break
                    
                    # Log status periodically
                    current_time = time.time()
                    if current_time - last_status_time >= status_interval:
                        last_status_time = current_time
                        self._log_status(status)
                
                # Sleep for a bit
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
                break
    
    def _log_status(self, status: dict):
        """Log current status"""
        stats = status.get('stats', {})
        uptime = stats.get('uptime_seconds', 0)
        
        logger.info("=" * 60)
        logger.info("STATUS UPDATE")
        logger.info(f"Uptime: {uptime:.0f}s ({uptime/3600:.1f}h)")
        logger.info(f"Cameras: {status['active_cameras']} active - {', '.join(status['camera_names'])}")
        logger.info(f"Known people: {status['known_people']}")
        logger.info(f"Total detections: {stats.get('total_detections', 0)}")
        logger.info(f"Recognized: {stats.get('total_recognitions', 0)}")
        logger.info(f"Unknown: {stats.get('unknown_faces', 0)}")
        logger.info(f"Restarts: {self.restart_count}")
        logger.info("=" * 60)
    
    def stop(self):
        """Stop the service"""
        logger.info("Stopping service...")
        self.running = False
        
        if self.processor:
            try:
                self.processor.stop()
            except Exception as e:
                logger.error(f"Error stopping processor: {e}")
            self.processor = None


def main():
    """Main entry point"""
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Create and start the service
    service = ServiceRunner()
    
    try:
        service.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
