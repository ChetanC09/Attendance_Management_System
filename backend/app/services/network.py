import ipaddress
import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit import SystemSetting

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Return the original client IP supplied by the trusted deployment proxy."""
    forwarded = request.headers.get("x-vercel-forwarded-for") or request.headers.get(
        "x-forwarded-for"
    )
    if forwarded:
        candidate = forwarded.split(",")[0].strip()
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            address = None
        if address and not (settings.env == "production" and address.is_loopback):
            return str(address)

    # In production request.client is the Render/Vercel connection, not the
    # user's device. Falling back to it can bind every session to loopback or a
    # shared proxy address and make the geofence both unusable and misleading.
    if settings.env == "production":
        raise HTTPException(
            status_code=503,
            detail="The deployment proxy did not provide a valid client IP. Try again shortly.",
        )
    if request.client:
        return request.client.host
    return "127.0.0.1"


def derive_subnet(ip_str: str) -> str:
    """Derive an appropriate CIDR subnet for classroom Wi-Fi / NAT geofencing."""
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_loopback:
            return "127.0.0.1/32"
        # If IPv4 private network (10.x, 172.16-31.x, 192.168.x), derive /24 subnet
        if isinstance(ip, ipaddress.IPv4Address) and ip.is_private:
            net = ipaddress.ip_network(f"{ip_str}/24", strict=False)
            return str(net)
        # If public IPv4 (e.g. cloud NAT egress), match the exact egress IP
        return f"{ip_str}/32"
    except ValueError:
        return "127.0.0.1/32"


def bind_session_network(
    db: Session, session_id: UUID, ip_str: str, enforced: bool = True
) -> dict:
    """Bind the detected faculty IP and derived subnet to the attendance session."""
    subnet = derive_subnet(ip_str)
    data = {
        "session_id": str(session_id),
        "detected_ip": ip_str,
        "bound_subnet": subnet,
        "enforced": enforced,
        "bound_at": datetime.now(UTC).isoformat(),
    }
    key = f"session_network_{session_id}"
    setting = db.get(SystemSetting, key)
    if setting:
        setting.value = data
    else:
        setting = SystemSetting(key=key, value=data)
        db.add(setting)

    # Also keep an active pointer for rapid lookup
    active_ptr = db.get(SystemSetting, "active_classroom_network")
    if active_ptr:
        active_ptr.value = data
    else:
        db.add(SystemSetting(key="active_classroom_network", value=data))

    db.flush()
    return data


def get_session_network(db: Session, session_id: UUID) -> dict:
    """Retrieve the network binding for an attendance session."""
    key = f"session_network_{session_id}"
    setting = db.get(SystemSetting, key)
    if setting and isinstance(setting.value, dict):
        return setting.value
    # Fallback to active pointer if available
    active_ptr = db.get(SystemSetting, "active_classroom_network")
    if active_ptr and isinstance(active_ptr.value, dict):
        return active_ptr.value
    # Default unconfigured
    return {
        "session_id": str(session_id),
        "detected_ip": "127.0.0.1",
        "bound_subnet": "127.0.0.1/32",
        "enforced": True,
        "bound_at": None,
    }


def update_session_network(
    db: Session, session_id: UUID, enforced: bool, custom_subnet: str | None = None
) -> dict:
    """Update enforcement flag or override subnet for a session."""
    current = get_session_network(db, session_id)
    current["enforced"] = enforced
    if custom_subnet:
        current["bound_subnet"] = custom_subnet
    key = f"session_network_{session_id}"
    setting = db.get(SystemSetting, key)
    if setting:
        setting.value = current
    else:
        db.add(SystemSetting(key=key, value=current))

    active_ptr = db.get(SystemSetting, "active_classroom_network")
    if active_ptr:
        active_ptr.value = current

    db.flush()
    return current


def is_ip_allowed_for_session(
    db: Session, session_id: UUID | None, client_ip_str: str
) -> tuple[bool, str, dict]:
    """Validate client IP against the active session's network lock."""
    # 1. Parse client IP
    try:
        client_ip = ipaddress.ip_address(client_ip_str)
    except ValueError:
        return False, f"Invalid client IP: {client_ip_str}", {}

    # Loopback is always accepted for local testing
    if client_ip.is_loopback:
        return True, "Loopback connection allowed", {"enforced": False}

    # 2. Check session-specific network binding
    net_info = {}
    if session_id:
        net_info = get_session_network(db, session_id)
    else:
        active_ptr = db.get(SystemSetting, "active_classroom_network")
        if active_ptr and isinstance(active_ptr.value, dict):
            net_info = active_ptr.value

    # If enforcement is explicitly disabled (Demo bypass mode)
    if net_info and not net_info.get("enforced", True):
        return (
            True,
            "Network enforcement is set to Demo Mode (all networks permitted)",
            net_info,
        )

    # Check match against bound session subnet
    bound_subnet = net_info.get("bound_subnet") if net_info else None
    if bound_subnet:
        try:
            if client_ip in ipaddress.ip_network(bound_subnet, strict=False):
                return (
                    True,
                    f"Verified on Classroom Network ({bound_subnet})",
                    net_info,
                )
        except ValueError:
            pass

    # 3. Check institutional subnets from system settings & env
    allowed_list = list(settings.allowed_checkin_subnets)
    inst_setting = db.get(SystemSetting, "checkin_subnets")
    if inst_setting and isinstance(inst_setting.value, dict) and "subnets" in inst_setting.value:
        allowed_list = inst_setting.value["subnets"]

    for cidr in allowed_list:
        try:
            if client_ip in ipaddress.ip_network(cidr, strict=False):
                return (
                    True,
                    f"Verified on Institutional Subnet ({cidr})",
                    net_info,
                )
        except ValueError:
            continue

    expected = bound_subnet or (allowed_list[0] if allowed_list else "Campus Wi-Fi")
    return (
        False,
        f"Outside Classroom Network. Device IP ({client_ip_str}) does not match classroom Wi-Fi ({expected}).",
        net_info,
    )
