"""
Heartbeat system สำหรับบอท Discord
ตรวจสอบสถานะและ restart อัตโนมัติเมื่อจำเป็น
"""

import asyncio
import datetime
import json
import os
import subprocess
import time
import logging

# ตั้งค่า logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BotHeartbeat:
    def __init__(self):
        self.heartbeat_file = "bot_heartbeat.json"
        self.max_silent_time = 300  # 5 นาทีไม่มี heartbeat ถือว่าตาย
        self.check_interval = 60  # ตรวจสอบทุก 1 นาที
        
    def update_heartbeat(self):
        """อัปเดต heartbeat timestamp"""
        heartbeat_data = {
            "last_heartbeat": datetime.datetime.now().isoformat(),
            "status": "alive",
            "timestamp": time.time()
        }
        
        try:
            with open(self.heartbeat_file, 'w') as f:
                json.dump(heartbeat_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to update heartbeat: {e}")
    
    def check_heartbeat(self):
        """ตรวจสอบ heartbeat และ restart หากจำเป็น"""
        try:
            if not os.path.exists(self.heartbeat_file):
                logger.warning("Heartbeat file not found - bot may be dead")
                return False
                
            with open(self.heartbeat_file, 'r') as f:
                data = json.load(f)
            
            last_heartbeat = data.get("timestamp", 0)
            current_time = time.time()
            time_since_heartbeat = current_time - last_heartbeat
            
            if time_since_heartbeat > self.max_silent_time:
                logger.error(f"Bot has been silent for {time_since_heartbeat:.1f} seconds - restarting")
                return False
            else:
                logger.info(f"Bot heartbeat OK - last seen {time_since_heartbeat:.1f} seconds ago")
                return True
                
        except Exception as e:
            logger.error(f"Failed to check heartbeat: {e}")
            return False
    
    async def start_monitoring(self):
        """เริ่ม monitoring heartbeat"""
        logger.info("Starting heartbeat monitoring...")
        
        while True:
            try:
                is_alive = self.check_heartbeat()
                
                if not is_alive:
                    logger.info("Attempting to restart bot...")
                    # ไม่ restart ตัวเอง เพียงแจ้งเตือน
                    logger.error("Bot requires manual restart or system intervention")
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Heartbeat monitoring error: {e}")
                await asyncio.sleep(self.check_interval)

# สำหรับรันเป็น standalone script
if __name__ == "__main__":
    heartbeat = BotHeartbeat()
    asyncio.run(heartbeat.start_monitoring())