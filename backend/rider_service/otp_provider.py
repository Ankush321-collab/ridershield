import logging
import random
from typing import TypedDict

from shared.config import settings
from shared.redis_client import get_redis


logger = logging.getLogger("zylo.otp")


class OTPDispatchResult(TypedDict, total=False):
    message: str
    expires_in: int
    dev_otp: str


def _otp_provider() -> str:
    return settings.OTP_PROVIDER.strip().lower() or "dev"


def _otp_length() -> int:
    return max(4, settings.OTP_LENGTH)


def _otp_expiry_seconds() -> int:
    return max(60, settings.OTP_EXPIRY_SECONDS)


def _dev_bypass_enabled() -> bool:
    return settings.OTP_DEV_BYPASS_ENABLED


def dev_bypass_code() -> str:
    return settings.OTP_DEV_BYPASS_CODE.strip() or "123456"


def _debug_enabled() -> bool:
    return settings.DEBUG


def _generate_otp() -> str:
    length = _otp_length()
    lower = 10 ** (length - 1)
    upper = (10**length) - 1
    return str(random.randint(lower, upper))


async def send_otp_code(phone: str) -> OTPDispatchResult:
    provider = _otp_provider()
    if provider != "dev":
        raise RuntimeError(f"Unsupported OTP provider '{provider}'. Configure OTP_PROVIDER=dev for free/demo use.")

    otp = _generate_otp()
    expiry = _otp_expiry_seconds()
    redis_client = await get_redis()
    await redis_client.set(f"otp:{phone}", otp, ex=expiry)

    logger.info("Generated dev OTP for %s: %s", phone, otp)

    result: OTPDispatchResult = {"message": "OTP sent", "expires_in": expiry}
    if _debug_enabled():
        result["dev_otp"] = otp
    return result


async def verify_otp_code(phone: str, otp: str) -> tuple[bool, str | None]:
    redis_client = await get_redis()
    stored_otp = await redis_client.get(f"otp:{phone}")

    if stored_otp and stored_otp == otp:
        await redis_client.delete(f"otp:{phone}")
        return True, None

    if stored_otp and stored_otp != otp:
        if _otp_provider() == "dev" and _dev_bypass_enabled() and otp == dev_bypass_code():
            logger.info("Accepted dev bypass OTP for %s", phone)
            return True, None
        return False, "INVALID_OTP"

    if _otp_provider() == "dev" and _dev_bypass_enabled() and otp == dev_bypass_code():
        logger.info("Accepted dev bypass OTP for %s", phone)
        return True, None

    return False, "OTP_EXPIRED"
