#!/usr/bin/env bash
# Fungsi bersama skrip deploy multi-instance SIPRO (di-source, bukan dijalankan langsung).
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$REPO_DIR/deploy"
INST_DIR="$DEPLOY_DIR/instances"
EDGE_DIR="$DEPLOY_DIR/edge"
EDGE_ENV="$EDGE_DIR/edge.env"
CADDYFILE="$EDGE_DIR/caddy/Caddyfile"
COMPOSE_FILE="$DEPLOY_DIR/compose.instance.yml"
EDGE_NET="sipro_edge"

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mPERINGATAN: %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32mOK: %s\033[0m\n' "$*"; }
die()  { printf '\n\033[1;31mGAGAL: %s\033[0m\n' "$*" >&2; exit 1; }

envget() { { grep -E "^$2=" "$1" 2>/dev/null || true; } | tail -1 | cut -d= -f2-; }

envset() {  # envset FILE KEY VALUE  (ganti bila ada, tambah bila belum)
  local f="$1" k="$2" v="$3"
  if grep -qE "^$k=" "$f"; then
    local tmp; tmp="$(mktemp)"
    awk -v k="$k" -v v="$v" 'BEGIN{FS=OFS="="} $1==k{print k"="v; next} {print}' "$f" > "$tmp"
    cat "$tmp" > "$f"; rm -f "$tmp"
  else
    [ -s "$f" ] && [ -n "$(tail -c1 "$f")" ] && printf '\n' >> "$f"
    printf '%s=%s\n' "$k" "$v" >> "$f"
  fi
}

inst_env() { echo "$INST_DIR/$1.env"; }
inst_list() { ls "$INST_DIR"/*.env 2>/dev/null | xargs -r -n1 basename | sed 's/\.env$//'; }
inst_project() { envget "$(inst_env "$1")" COMPOSE_PROJECT_NAME; }

dc() {  # dc <instance> <args docker compose...>
  local f; f="$(inst_env "$1")"; shift
  [ -f "$f" ] || die "instance env $f tidak ada"
  docker compose -p "$(envget "$f" COMPOSE_PROJECT_NAME)" --env-file "$f" -f "$COMPOSE_FILE" "$@"
}

dc_edge() { docker compose -p sipro_edge --env-file "$EDGE_ENV" -f "$EDGE_DIR/docker-compose.yml" "$@"; }

ensure_edge_infra() {
  docker network inspect "$EDGE_NET" >/dev/null 2>&1 || docker network create "$EDGE_NET" >/dev/null
  docker volume inspect sipro_caddy_data >/dev/null 2>&1 || docker volume create sipro_caddy_data >/dev/null
  docker volume inspect sipro_caddy_config >/dev/null 2>&1 || docker volume create sipro_caddy_config >/dev/null
  mkdir -p "$EDGE_DIR/caddy"
}

wait_healthy() {  # wait_healthy <instance> [menit]
  local inst="$1" max=$(( ${2:-6} * 12 )) status i
  for i in $(seq 1 "$max"); do
    status="$(dc "$inst" ps --format '{{.Service}} {{.Health}}' 2>/dev/null | awk '$1=="backend"{print $2}')"
    [ "$status" = "healthy" ] && { ok "backend $inst sehat"; return 0; }
    sleep 5
  done
  dc "$inst" logs --tail=80 backend || true
  return 1
}

vps_ip() { curl -fsS --max-time 8 https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}'; }

dns_ok() {  # dns_ok <domain> → 0 bila A record = IP VPS
  local ip_dns ip_vps
  ip_vps="$(vps_ip)"
  ip_dns="$(dig +short A "$1" @1.1.1.1 2>/dev/null | grep -E '^[0-9.]+$' | tail -1)"
  [ -z "$ip_dns" ] && { warn "DNS $1 belum ada A record (harus → $ip_vps)"; return 1; }
  [ "$ip_dns" != "$ip_vps" ] && { warn "DNS $1 → $ip_dns, padahal IP VPS $ip_vps (matikan proxy Cloudflare / cek A record)"; return 1; }
  ok "DNS $1 → $ip_vps"
  return 0
}

gen_caddyfile() {  # bangkitkan Caddyfile dari semua instance
  ensure_edge_infra
  {
    echo "# DIBANGKITKAN OTOMATIS oleh deploy/lib.sh — jangan edit manual."
    local acme; acme="$(envget "$EDGE_ENV" ACME_EMAIL)"
    if [ -n "$acme" ]; then
      echo "{"
      echo "	email $acme"
      echo "}"
    fi
    echo
    echo "(sipro_headers) {"
    echo "	encode zstd gzip"
    echo "	header {"
    echo "		X-Content-Type-Options nosniff"
    echo "		Referrer-Policy strict-origin-when-cross-origin"
    echo "		-Server"
    echo "	}"
    echo "}"
    local inst f dom old
    for inst in $(inst_list); do
      f="$(inst_env "$inst")"; dom="$(envget "$f" DOMAIN)"
      [ -n "$dom" ] || continue
      echo
      echo "$dom {"
      echo "	import sipro_headers"
      echo "	handle /api/* {"
      echo "		reverse_proxy $inst-backend:8001"
      echo "	}"
      echo "	handle {"
      echo "		reverse_proxy $inst-frontend:80"
      echo "	}"
      echo "	log {"
      echo "		output file /data/access-$inst.log {"
      echo "			roll_size 20mb"
      echo "			roll_keep 5"
      echo "		}"
      echo "	}"
      echo "}"
      for old in $(envget "$f" REDIRECT_FROM); do
        echo
        echo "# Domain lama → dialihkan permanen ke $dom (webhook tetap dilayani langsung)."
        echo "$old {"
        echo "	handle /api/webhooks/* {"
        echo "		reverse_proxy $inst-backend:8001"
        echo "	}"
        echo "	handle {"
        echo "		redir https://$dom{uri} 308"
        echo "	}"
        echo "}"
      done
    done
  } > "$CADDYFILE"
}

edge_up() {  # jalankan / muat ulang Caddy bersama
  ensure_edge_infra
  gen_caddyfile
  [ -f "$EDGE_ENV" ] || die "$EDGE_ENV tidak ada (ACME_EMAIL)"
  if [ -n "$(dc_edge ps -q caddy 2>/dev/null)" ]; then
    dc_edge exec -T caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile \
      || dc_edge restart caddy
  else
    dc_edge up -d
  fi
}

mongo_counts() {  # mongo_counts <container_id> <db> → "koleksi jumlah" per baris
  docker exec "$1" mongosh --quiet "$2" --eval \
    'db.getCollectionNames().sort().forEach(c => print(c + " " + db.getCollection(c).countDocuments({})))'
}

https_ok() {  # https_ok <domain> [percobaan]
  local i code
  for i in $(seq 1 "${2:-30}"); do
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "https://$1/api/health" 2>/dev/null || true)"
    [ "$code" = "200" ] && { ok "https://$1 aktif"; return 0; }
    sleep 6
  done
  warn "https://$1 belum merespons 200 (cek DNS; Caddy akan terus mencoba menerbitkan SSL)"
  return 1
}

install_backup_cron() {
  local line="0 2 * * * bash $DEPLOY_DIR/backup.sh >> /var/log/sipro-backup.log 2>&1"
  ( crontab -l 2>/dev/null | grep -v 'deploy/backup.sh' ; echo "$line" ) | crontab -
}
