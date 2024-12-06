up-signoz:
	sudo docker compose -f ./deployment/signoz/clickhouse-setup/docker-compose-minimal.yaml up -d

down-signoz:
	sudo docker compose -f ./deployment/signoz/clickhouse-setup/docker-compose-minimal.yaml down -v

up-app:
	uv run python3 -m src.app