import argparse
import hashlib
import secrets

from app.core.supabase import get_service_supabase


def main() -> None:
    parser = argparse.ArgumentParser(description="Cria instancia de robo e retorna credenciais para o EA")
    parser.add_argument("--profile-id", required=True, help="UUID de user_profiles.id")
    parser.add_argument("--organization-id", required=True, help="UUID de organizations.id")
    parser.add_argument("--name", default="EA-Demo-1", help="Nome da instancia de robo")
    parser.add_argument("--allowed-modes", default="demo", help="Modos permitidos: demo,real (csv)")
    parser.add_argument("--enable-real", action="store_true", help="Habilita execucao em conta real")
    parser.add_argument("--max-risk-real", type=float, default=1.5, help="Risco maximo permitido no modo real")
    args = parser.parse_args()

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    sb = get_service_supabase()

    allowed_modes = [m.strip().lower() for m in args.allowed_modes.split(",") if m.strip()]
    allowed_modes = [m for m in allowed_modes if m in {"demo", "real"}]
    if not allowed_modes:
        allowed_modes = ["demo"]

    resp = (
        sb.table("robot_instances")
        .insert(
            {
                "organization_id": args.organization_id,
                "profile_id": args.profile_id,
                "name": args.name,
                "robot_token_hash": token_hash,
                "status": "active",
                "allowed_modes": allowed_modes,
                "real_trading_enabled": bool(args.enable_real),
                "max_risk_real": float(args.max_risk_real),
            }
        )
        .execute()
    )

    row = (resp.data or [None])[0]
    if not row:
        raise RuntimeError("Falha ao criar robot_instance")

    print("ROBOT_ID", row["id"])
    print("ROBOT_TOKEN", token)
    print("PROFILE_ID", args.profile_id)
    print("ORGANIZATION_ID", args.organization_id)
    print("ALLOWED_MODES", ",".join(allowed_modes))
    print("REAL_ENABLED", bool(args.enable_real))
    print("MAX_RISK_REAL", float(args.max_risk_real))


if __name__ == "__main__":
    main()
