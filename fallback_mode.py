"""
Fallback Mode สำหรับจัดการ Cloudflare Rate Limit
เมื่อเจอ Error 1015 จะเปลี่ยนเป็นโหมดพื้นฐานที่ทำงานแบบเงียบๆ
"""

import json
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class FallbackManager:
    def __init__(self):
        self.is_fallback_mode = False
        self.fallback_start_time = None
        self.fallback_duration = 300  # 5 นาที
        self.rate_limit_count = 0
        self.max_rate_limits = 5
        
    def activate_fallback(self, reason="Unknown"):
        """เปิดใช้งาน fallback mode"""
        self.is_fallback_mode = True
        self.fallback_start_time = datetime.now()
        self.rate_limit_count += 1
        
        logger.warning(f"🔒 Fallback mode activated: {reason}")
        logger.info(f"⏰ Fallback mode will last {self.fallback_duration} seconds")
        
        return True
    
    def deactivate_fallback(self):
        """ปิด fallback mode"""
        self.is_fallback_mode = False
        self.fallback_start_time = None
        
        logger.info("✅ Fallback mode deactivated")
        
    def should_exit_fallback(self):
        """ตรวจสอบว่าควรออกจาก fallback mode หรือไม่"""
        if not self.is_fallback_mode:
            return False
            
        if not self.fallback_start_time:
            return True
            
        elapsed = (datetime.now() - self.fallback_start_time).total_seconds()
        return elapsed >= self.fallback_duration
    
    def check_and_update_fallback(self):
        """ตรวจสอบและอัปเดต fallback mode"""
        if self.is_fallback_mode and self.should_exit_fallback():
            self.deactivate_fallback()
            
        return self.is_fallback_mode
    
    def is_cloudflare_error(self, error_message):
        """ตรวจสอบว่าเป็น Cloudflare error หรือไม่"""
        error_str = str(error_message).lower()
        cloudflare_indicators = [
            "cloudflare",
            "1015",
            "access denied",
            "rate limited",
            "too many requests",
            "you are being rate limited"
        ]
        
        return any(indicator in error_str for indicator in cloudflare_indicators)
    
    def handle_discord_error(self, error):
        """จัดการ Discord error และตัดสินใจเข้า fallback mode"""
        error_str = str(error)
        
        # ตรวจสอบ Cloudflare Rate Limit
        if self.is_cloudflare_error(error_str):
            self.activate_fallback(f"Cloudflare Error: {error.status if hasattr(error, 'status') else 'Unknown'}")
            return True
            
        # ตรวจสอบ Discord Rate Limit ปกติ
        if hasattr(error, 'status') and error.status == 429:
            if not self.is_cloudflare_error(error_str):
                # Discord Rate Limit ปกติ - ไม่เข้า fallback mode
                logger.info("🐌 Discord rate limit - waiting normally")
                return False
            else:
                self.activate_fallback("Cloudflare + Discord Rate Limit")
                return True
                
        # ตรวจสอบ Permission errors
        if hasattr(error, 'status') and error.status == 403:
            logger.warning(f"🚫 Permission denied: {error}")
            # ไม่เข้า fallback mode สำหรับ permission error
            return False
            
        return False
    
    def get_status(self):
        """ดึงสถานะปัจจุบัน"""
        if not self.is_fallback_mode:
            return {
                "mode": "normal",
                "rate_limit_count": self.rate_limit_count
            }
            
        elapsed = 0
        if self.fallback_start_time:
            elapsed = (datetime.now() - self.fallback_start_time).total_seconds()
            
        remaining = max(0, self.fallback_duration - elapsed)
        
        return {
            "mode": "fallback",
            "elapsed": elapsed,
            "remaining": remaining,
            "rate_limit_count": self.rate_limit_count
        }

# Global instance
fallback_manager = FallbackManager()