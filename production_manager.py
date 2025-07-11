"""
Production Manager สำหรับ Discord Shop Bot
จัดการ auto-restart และ monitoring สำหรับ Render.com
"""

import subprocess
import time
import json
import os
import sys
import logging
from datetime import datetime
from heartbeat import BotHeartbeat

# ตั้งค่า logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('production.log')
    ]
)
logger = logging.getLogger(__name__)

class ProductionManager:
    def __init__(self):
        self.heartbeat = BotHeartbeat()
        self.bot_process = None
        self.restart_count = 0
        self.max_restarts = 10
        self.restart_cooldown = 60  # วินาที
        self.last_restart = 0
        
    def start_bot(self):
        """เริ่มบอท"""
        try:
            logger.info("Starting Discord bot...")
            self.bot_process = subprocess.Popen(
                [sys.executable, "shopbot.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            logger.info(f"Bot started with PID: {self.bot_process.pid}")
            return True
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            return False
    
    def stop_bot(self):
        """หยุดบอท"""
        if self.bot_process and self.bot_process.poll() is None:
            logger.info("Stopping bot...")
            self.bot_process.terminate()
            try:
                self.bot_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Bot didn't stop gracefully, killing...")
                self.bot_process.kill()
            self.bot_process = None
    
    def is_bot_running(self):
        """ตรวจสอบว่าบอทยังทำงานอยู่หรือไม่"""
        if not self.bot_process:
            return False
        return self.bot_process.poll() is None
    
    def should_restart(self):
        """ตรวจสอบว่าควร restart หรือไม่"""
        # ตรวจสอบ process
        if not self.is_bot_running():
            logger.warning("Bot process is not running")
            return True
        
        # ตรวจสอบ heartbeat
        if not self.heartbeat.check_heartbeat():
            logger.warning("Bot heartbeat failed")
            return True
        
        return False
    
    def can_restart(self):
        """ตรวจสอบว่าสามารถ restart ได้หรือไม่"""
        current_time = time.time()
        
        # ตรวจสอบ restart count
        if self.restart_count >= self.max_restarts:
            logger.error(f"Maximum restart count ({self.max_restarts}) reached")
            return False
        
        # ตรวจสอบ cooldown
        if current_time - self.last_restart < self.restart_cooldown:
            remaining = self.restart_cooldown - (current_time - self.last_restart)
            logger.info(f"Restart cooldown: {remaining:.1f} seconds remaining")
            return False
        
        return True
    
    def restart_bot(self):
        """Restart บอท"""
        if not self.can_restart():
            return False
        
        logger.info(f"Restarting bot (attempt {self.restart_count + 1}/{self.max_restarts})")
        
        # หยุดบอทเก่า
        self.stop_bot()
        
        # รอสักครู่
        time.sleep(5)
        
        # เริ่มบอทใหม่
        success = self.start_bot()
        
        if success:
            self.restart_count += 1
            self.last_restart = time.time()
            logger.info("Bot restarted successfully")
        else:
            logger.error("Failed to restart bot")
        
        return success
    
    def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Starting production monitoring...")
        
        # เริ่มบอทครั้งแรก
        if not self.start_bot():
            logger.error("Failed to start bot initially")
            return
        
        # เริ่ม monitoring loop
        while True:
            try:
                time.sleep(30)  # ตรวจสอบทุก 30 วินาที
                
                if self.should_restart():
                    if self.restart_bot():
                        continue
                    else:
                        logger.error("Cannot restart bot - entering maintenance mode")
                        # รอ 5 นาทีแล้วลองใหม่
                        time.sleep(300)
                        self.restart_count = 0  # รีเซ็ต count
                        continue
                
                # อ่าน output จากบอท
                if self.bot_process and self.is_bot_running():
                    try:
                        # อ่าน stdout ถ้ามี
                        if self.bot_process.stdout.readable():
                            line = self.bot_process.stdout.readline()
                            if line:
                                logger.info(f"Bot: {line.strip()}")
                    except:
                        pass
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                self.stop_bot()
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(10)

def main():
    """Main function"""
    # ตรวจสอบว่าเป็น Production environment
    is_render = os.environ.get("RENDER") is not None
    
    if not is_render:
        print("⚠️ Production Manager is designed for Render.com")
        print("💡 For local development, run: python shopbot.py")
        return
    
    manager = ProductionManager()
    try:
        manager.monitor_loop()
    except Exception as e:
        logger.error(f"Production manager failed: {e}")
    finally:
        manager.stop_bot()

if __name__ == "__main__":
    main()